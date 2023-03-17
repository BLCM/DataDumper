#!/usr/bin/env python3
# vim: set expandtab tabstop=4 shiftwidth=4:

import os
import re
import sys
import lzma
import sqlite3
import argparse

# NOTE: this is still a work-in-progress, and the BLCMM version which
# uses this data hasn't been released yet (and will probably have a
# slightly new name for the fork, when it is released)

# When the BLCMM core was opensourced in 2022, we needed to reimplement the
# Data Library components if we wanted a fully-opensource BLCMM, since those
# parts were reserved.  This is the code to generate the required data
# structures for this new 2023 BLCMM fork!
#
# The original BLCMM data library has a pretty thorough understanding of UE
# objects, including their attributes, and had a complete object model for
# basically everything found in the engine.  That allows for some pretty
# nifty functionality, but at the moment that's way more work than Apocalyptech's
# willing to spend reimplementing, in 2023.  If I ever do start digging into
# that, I expect that'll get folded up into some generation stuff in here,
# but for now this just generates enough metadata to support knowing about the
# class structure, how it correlates to the objects, and the structure of the
# whole object tree (plus where exactly to find the raw dump data).
#
# The core of the new data library functionality is a Sqlite3 database which
# OE (or any other app) can use to query information about the data.  There's
# a set of tables describing the engine class layout, and another set of tables
# describing the object layout.  "Object" entries are technically just nodes in
# a tree -- there may not be an object dump attached.  But the whole parent/child
# structure lets us put in the dump info where it's applicable.
#
# The app expects to have a `completed` directory that was populated via
# `categorize_data.py`, so this has to be run at the tail end of the data
# extraction process.  You could alternatively just grab the data extracts
# provided with FT Explorer (https://github.com/apocalyptech/ft-explorer).  That's
# basically just the raw `completed` dir.
#
# While processing, in addition to creating the sqlite database, this'll
# copy/store the dumps into a new directory with a different format.  For the
# new BLCMM OE dumps, it'll still be categorized by class type, but there's also
# a maximum individual file size.  That's done so that random access to object
# dumps near the end of the file don't take a noticeable amount of time to load,
# since those dumps will be compressed, and need to be uncompressed to seek to
# the specified position.
#
# That position is found via the `object` table, in the fields `filename_index` and
# `filename_position`.  The index is the numeric suffix of the filename, and
# the main filename comes from the class name.  So for instance there's
# `StaticMeshComponent.dump.0` as the first dump file, `StaticMeshComponent.dump.1`
# as the next, and so on.  Then the `filename_position` attribute is the starting
# byte in the specified uncompressed dump file.
#
# The database itself has several denormalizations done in the name of speed.
# Theoretically, all OE interactions apart from fulltext searching (and refs, at
# the moment, which is effectively just fulltext search) should be nice and snappy,
# and the database structure should let us dynamically populate the Class and Object
# trees as users click around, without having to load *everything* all at once.
# This should let us get rid of the annoying "there are too many objects!" notifications
# (though of course that could've been reimplemented in a less-annoying way, too).
#
# As mentioned elsewhere below, the denormalization does come at a cost: database size.
# At time of writing, the uncompressed "base" database (classes, class aggregation,
# and objects) clocks in at about 350MB.  Adding in the "shown class IDs" table (see
# below for details on that - it's what lets the lower-left-hand Object Explorer
# window be nice and quick) adds in another 230MB or so.
#
# ================================================================
# NOTE: ASSUMPTIONS ABOUT THE DATABASE WHICH BLCMM'S OE RELIES ON:
# ================================================================
#
#   1. The `class.id` numbering starts at 1 for the first valid object (ResultSet
#      objects will end up with `0` for integer values when they're null -- you
#      can explicitly check for null after getting the value, but since sqlite
#      autoincrement PKs are already 1-indexed, we're not bothering).
#
#   2. There is a single root `class` element, which is `id` 1 (and is the first
#      row in the database.  (This happens to be named `Object`, but BLCMM
#      doesn't actually care about that.)
#
#   3. When ordered by `id`, the `class` table rows are in "tree" order -- as in,
#      there will *never* be a `parent` field whose row we haven't already seen.
#
#   4. Datafile filename indexes start at 1, for the same reason as point #1 above.
#
#   5. BLCMM OE expects the `categories` keys to be those exact names in the
#      database, including the code-added `Others` category.  It'll refuse
#      to load the data if they aren't all found.  New categories in here
#      will also require a BLCMM update.
#
#   6. BLCMM relies on the text indexes in the DB being case-insensitive
#      (at least for `object.name` -- the others may not be as important)

# Categories for user to choose for fulltext search.  This list is kind of a
# conglomeration of both BL2 and TPS classtypes, but it won't result in any
# strange stuff in the database -- apart from the category names, these only
# exist in the DB as foreign keys into the categories table.
categories = {
        'Actions': {
            'Action_AimAtScanRange',
            'Action_AimAtThreat',
            'Action_AnimAttack',
            'Action_AttackLoop',
            'Action_BasicAttack',
            'Action_BikeMove',
            'Action_BunkerBoss_Flight',
            'Action_Burrow',
            'Action_BurrowIdle',
            'Action_ChangeRuleSet',
            'Action_ChargeTarget',
            'Action_CombatPerch',
            'Action_CombatPoint',
            'Action_CoverAttack',
            'Action_DeathTrap',
            'Action_DiveBombAttack',
            'Action_Drive_AlongsideTarget',
            'Action_Drive_AvoidWall',
            'Action_Drive_BackUpAndAdjust',
            'Action_Drive_GoBackToCombatArea',
            'Action_Drive_Pursuit',
            'Action_Drive_Pursuit_TargetOnFoot',
            'Action_DriveVehicle',
            'Action_FaceThreat',
            'Action_FinalBoss',
            'Action_FinalBossFly',
            'Action_FlyAnimAttack',
            'Action_FollowPath',
            'Action_GenericAttack',
            'Action_GoToScriptedDestination',
            'Action_GrabPickup',
            'Action_Idle',
            'Action_JumpOnWall',
            'Action_LeapAtTarget',
            'Action_LeapWallAttack',
            'Action_MortarAttack',
            'Action_MoveRandom',
            'Action_MoveTo',
            'Action_MoveToFormation',
            'Action_MoveToVehicle',
            'Action_Patrol',
            'Action_PawnMovementBase',
            'Action_PlayCustomAnimation',
            'Action_PopRuleSet',
            'Action_PushRuleSet',
            'Action_ScriptedNPC',
            'Action_SetFlight',
            'Action_ShootTarget',
            'Action_ShootThreatWhenInView',
            'Action_SweepAttack',
            'Action_SwoopAttack',
            'Action_VehicleTurret',
            'Action_WallAttack',
            'ActionSequence',
            'ActionSequenceList',
            'ActionSequencePawn',
            'ActionSequenceRandom',
            'OzAction_DoppelgangerPickup',
            'OzAction_LeapAndShootAtTarget',
            'OzAction_ZarpedonBoss_Flight',
            'WillowActionSequencePawn',
            },
        'AI': {
            'AIClassDefinition',
            'AIComponent',
            'AIController',
            'AICostExpressionEvaluator',
            'AIDefinition',
            'AIPawnBalanceDefinition',
            'AIPawnBalanceModifierDefinition',
            'AIResource',
            'DeployableTurretActor',
            'GearboxAIController',
            'GearboxMind',
            'WillowAIBlackboardComponent',
            'WillowAIComponent',
            'WillowAICranePawn',
            'WillowAIDefinition',
            'WillowAIDenComponent',
            'WillowAIDenDefinition',
            'WillowAIEncounterComponent',
            'WillowAIPawn',
            'WillowMind',
            },
        'Animations': {
            'AnimationCompressionAlgorithm',
            'AnimationCompressionAlgorithm_Automatic',
            'AnimationCompressionAlgorithm_BitwiseCompressOnly',
            'AnimationCompressionAlgorithm_GBXCustom',
            'AnimationCompressionAlgorithm_LeastDestructive',
            'AnimationCompressionAlgorithm_PerTrackCompression',
            'AnimationCompressionAlgorithm_RemoveEverySecondKey',
            'AnimationCompressionAlgorithm_RemoveLinearKeys',
            'AnimationCompressionAlgorithm_RemoveTrivialKeys',
            'AnimationCompressionAlgorithm_RevertToRaw',
            'AnimMetaData',
            'AnimMetaData_SkelControl',
            'AnimMetaData_SkelControlKeyFrame',
            'AnimNode',
            'AnimNode_MultiBlendPerBone',
            'AnimNodeAdditiveBlending',
            'AnimNodeAimOffset',
            'AnimNodeBlend',
            'AnimNodeBlendBase',
            'AnimNodeBlendByBase',
            'AnimNodeBlendByPhysics',
            'AnimNodeBlendByPosture',
            'AnimNodeBlendByProperty',
            'AnimNodeBlendBySpeed',
            'AnimNodeBlendDirectional',
            'AnimNodeBlendList',
            'AnimNodeBlendMultiBone',
            'AnimNodeBlendPerBone',
            'AnimNodeCrossfader',
            'AnimNodeMirror',
            'AnimNodePlayCustomAnim',
            'AnimNodeRandom',
            'AnimNodeScalePlayRate',
            'AnimNodeScaleRateBySpeed',
            'AnimNodeSequence',
            'AnimNodeSequenceBlendBase',
            'AnimNodeSequenceBlendByAim',
            'AnimNodeSlot',
            'AnimNodeSpecialMoveBlend',
            'AnimNodeSynch',
            'AnimNotify',
            'AnimNotify_AkEvent',
            'AnimNotify_CameraEffect',
            'AnimNotify_ClothingMaxDistanceScale',
            'AnimNotify_CustomEvent',
            'AnimNotify_DialogEvent',
            'AnimNotify_EnableHandIK',
            'AnimNotify_EnableHeadLookAt',
            'AnimNotify_Footstep',
            'AnimNotify_ForceField',
            'AnimNotify_Kismet',
            'AnimNotify_PawnMaterialParam',
            'AnimNotify_PlayFaceFXAnim',
            'AnimNotify_PlayParticleEffect',
            'AnimNotify_Rumble',
            'AnimNotify_Script',
            'AnimNotify_Scripted',
            'AnimNotify_Sound',
            'AnimNotify_SoundSpatial',
            'AnimNotify_Trails',
            'AnimNotify_UseBehavior',
            'AnimNotify_ViewShake',
            'AnimObject',
            'AnimSequence',
            'AnimSet',
            'AnimTree',
            'GameSkelCtrl_Recoil',
            'MorphNodeBase',
            'MorphNodeMultiPose',
            'MorphNodePose',
            'MorphNodeWeight',
            'MorphNodeWeightBase',
            'MorphNodeWeightByBoneAngle',
            'MorphNodeWeightByBoneRotation',
            'OzAnimNodeBlendPerBone',
            'OzWillowAnimNode_OptimizeCondition',
            'SkelControl_CCD_IK',
            'SkelControl_Multiply',
            'SkelControl_TwistBone',
            'SkelControlBase',
            'SkelControlFootPlacement',
            'SkelControlHandlebars',
            'SkelControlHandModifier',
            'SkelControlLeftHandGripWeapon',
            'SkelControlLimb',
            'SkelControlLookAt',
            'SkelControlSingleBone',
            'SkelControlSpline',
            'SkelControlTrail',
            'SkelControlWheel',
            'WillowAnimBlendByPosture',
            'WillowAnimNode_AddCameraBone',
            'WillowAnimNode_AimState',
            'WillowAnimNode_Audio',
            'WillowAnimNode_ClimbLadder',
            'WillowAnimNode_Condition',
            'WillowAnimNode_Falling',
            'WillowAnimNode_MovementTransition',
            'WillowAnimNode_Prism',
            'WillowAnimNode_Simple',
            'WillowAnimNode_WeaponHold',
            'WillowAnimNode_WeaponRecoil',
            'WillowAnimNodeAimOffset',
            'WillowAnimNodeAimOffset_BoundaryTurret',
            'WillowAnimNodeBlendByAimState',
            'WillowAnimNodeBlendByRotationSpeed',
            'WillowAnimNodeBlendByStance',
            'WillowAnimNodeBlendDirectional',
            'WillowAnimNodeBlendInjured',
            'WillowAnimNodeBlendList',
            'WillowAnimNodeBlendSwitch',
            'WillowAnimNodeBlendThirdPersonMenu',
            'WillowAnimNodeBlendTurning',
            'WillowAnimNodeBlendVehicleDirectional',
            'WillowAnimNodeBlendWheeledPawn',
            'WillowAnimNodeFeatherBlend',
            'WillowAnimNodeSequence',
            'WillowAnimNodeSequenceAdditiveBlend',
            'WillowAnimNodeSlot',
            'WillowAnimTree',
            'WillowSkelControl_EyelidLook',
            'WillowSkelControl_FootPlacement',
            'WillowSkelControl_LeftLowerEyelidLook',
            'WillowSkelControl_LeftUpperEyelidLook',
            'WillowSkelControl_LookAtActor',
            'WillowSkelControl_LowerEyelidLook',
            'WillowSkelControl_RightLowerEyelidLook',
            'WillowSkelControl_RightUpperEyelidLook',
            'WillowSkelControl_RotateFlapFromFiring',
            'WillowSkelControl_RotateWeaponBoneFromFiring',
            'WillowSkelControl_RotationRate',
            'WillowSkelControl_RotationRateBySpeed',
            'WillowSkelControl_TurretConstrained',
            'WillowSkelControl_UpperEyelidLook',
            'WillowSkelControlHandPlacement',
            'WillowSkelControlLerpSingleBone',
            'WillowSkelControlSpline',
            'WillowStaggerAnimNodeBlend',
            },
        'Base': {
            'AccessControl',
            'ActionSkill',
            'ActionSkillStateExpressionEvaluator',
            'Admin',
            'AdvancedAxisDefinition',
            'AIResourceAttributeValueResolver',
            'AIResourceExpressionEvaluator',
            'AIState',
            'AIState_Priority',
            'AIState_Random',
            'AIState_Sequential',
            'AIStateBase',
            'AkAmbientSound',
            'AllegianceExpressionEvaluator',
            'AmbientSound',
            'AmmoDropWeightAttributeValueResolver',
            'AmmoResourcePool',
            'AmmoResourceUpgradeAttributeValueResolver',
            'AnemoneInfectionDefinition',
            'AnemoneInfectionState',
            'ArtifactDefinition',
            'ArtifactPartDefinition',
            'AttributeDefinition',
            'AttributeDefinitionBase',
            'AttributeDefinitionMultiContext',
            'AttributeExpressionEvaluator',
            'AttributeInitializationDefinition',
            'AttributeModifier',
            'AttributePresentationDefinition',
            'AttributePresentationListDefinition',
            'AttributeSlotEffectAttributeValueResolver',
            'AwarenessZoneCollectionDefinition',
            'AwarenessZoneDefinition',
            'BadassAttributeValueResolver',
            'BadassRewardDefinition',
            'BalanceModifierDefinition',
            'BankGFxDefinition',
            'BaronessActionSkill',
            'BehaviorEventFilterBase',
            'BehaviorHelpers',
            'BestTargetAttributeContextResolver',
            'BlackMarketDefinition',
            'BlackMarketUpgradeAttributeValueResolver',
            'BlackMarketUpgradeDefinition',
            'BlackMarketUpgradeManager',
            'BodyClassDeathDefinition',
            'BodyClassDefinition',
            'BodyHitRegionDefinition',
            'BodyRegionProtectionDefinition',
            'BodyWeaponHoldDefinition',
            'BuzzaxeActionSkill',
            'BuzzaxeWeaponTypeDefinition',
            'CarVehicleHandlingDefinition',
            'ChallengeCategoryDefinition',
            'ChallengeConditionDefinition',
            'ChallengeDefinition',
            'ChallengeFeedbackMessage',
            'CharacterClassDefinition',
            'CharacterClassMessageDefinition',
            'ChassisDefinition',
            'CheatManager',
            'ChildConnection',
            'ChopperVehicleHandlingDefinition',
            'ClassDropWeightValueResolver',
            'ClassModBalanceDefinition',
            'ClassModDefinition',
            'ClassModPartDefinition',
            'ColiseumRuleDefinition',
            'CombatMusicParameters',
            'Commandlet',
            'CompoundExpressionEvaluator',
            'ConditionalAttributeValueResolver',
            'ConstantAttributeValueResolver',
            'ConstraintAttributeValueResolver',
            'Controller',
            'CoordinatedEffectDefinition',
            'CoverReplicator',
            'CoverSearchCriteria',
            'CreditsGFxDefinition',
            'CreditsLineDefinition',
            'CrossDLCClassModDefinition',
            'CrossDLCItemPoolDefinition',
            'CurrencyAttributeValueResolver',
            'CurrencyListDefinition',
            'CustomizationData',
            'CustomizationData_Head',
            'CustomizationData_Skin',
            'CustomizationDefinition',
            'CustomizationGFxDefinition',
            'CustomizationType',
            'CustomizationType_Head',
            'CustomizationType_Skin',
            'CustomizationUsage',
            'CustomizationUsage_Assassin',
            'CustomizationUsage_BanditTech',
            'CustomizationUsage_ExtraPlayerA',
            'CustomizationUsage_ExtraPlayerB',
            'CustomizationUsage_ExtraPlayerC',
            'CustomizationUsage_ExtraPlayerD',
            'CustomizationUsage_ExtraPlayerE',
            'CustomizationUsage_ExtraPlayerF',
            'CustomizationUsage_ExtraPlayerG',
            'CustomizationUsage_ExtraPlayerH',
            'CustomizationUsage_ExtraPlayerI',
            'CustomizationUsage_ExtraPlayerJ',
            'CustomizationUsage_ExtraPlayerK',
            'CustomizationUsage_ExtraPlayerL',
            'CustomizationUsage_ExtraPlayerM',
            'CustomizationUsage_ExtraPlayerN',
            'CustomizationUsage_ExtraPlayerO',
            'CustomizationUsage_ExtraPlayerP',
            'CustomizationUsage_FanBoat',
            'CustomizationUsage_Hovercraft',
            'CustomizationUsage_Mercenary',
            'CustomizationUsage_Player',
            'CustomizationUsage_Runner',
            'CustomizationUsage_Siren',
            'CustomizationUsage_Soldier',
            'CustomizationUsage_Vehicle',
            'DamagePipeline',
            'DamageType',
            'DamageTypeAttributeValueResolver',
            'DeathtrapActionSkill',
            'DebugCameraController',
            'DefinitionGlobalsDefinition',
            'DefinitionUITestCaseDefinition',
            'DemoRecConnection',
            'DemoRecDriver',
            'DesignerAttributeContextResolver',
            'DesignerAttributeDefinition',
            'DialogNameTagExpressionEvaluator',
            'DLCLegacyPlayerClassIdentifierDefinition',
            'DmgType_Crushed',
            'DmgType_Fell',
            'DmgType_Suicided',
            'DmgType_Telefragged',
            'DownloadableBalanceModifierDefinition',
            'DownloadableCharacterDefinition',
            'DownloadableContentDefinition',
            'DownloadableContentManager',
            'DownloadableContentOfferEnumerator',
            'DownloadableCustomizationSetDefinition',
            'DownloadableExpansionDefinition',
            'DownloadableFixupAIPawnNamesDefinition',
            'DownloadableItemSetDefinition',
            'DownloadableVehicleDefinition',
            'DrunkenBaseComponent',
            'DrunkenRandomComponent',
            'DrunkenWaveComponent',
            'DualWieldActionSkill',
            'EquipableItemDefinition',
            'EquipableItemPartDefinition',
            'EquippedInventoryAttributeContextResolver',
            'EquippedManufacturerAttributeValueResolver',
            'EventFilter_OnTakeDamage',
            'EventFilter_OnTouch',
            'ExecuteActionSkill',
            'ExperienceFeedbackMessage',
            'ExperienceResourcePool',
            'ExplosionCollectionDefinition',
            'ExplosionDefinition',
            'ExpressionEvaluatorDefinition',
            'ExpressionTree',
            'FailedConnect',
            'FastTravelStationDefinition',
            'FastTravelStationDiscoveryMessage',
            'FastTravelStationsListOrder',
            'FeatherBoneBlendDefinition',
            'FiringBehaviorDefinition',
            'FiringModeDefinition',
            'FiringModeSoundDefinition',
            'FiringZoneCollectionDefinition',
            'FiringZoneDefinition',
            'FixedMarker',
            'FlagDefinition',
            'FlagExpressionEvaluator',
            'FocusCameraDefinition',
            'FractalViewWanderingDefinition',
            'FragtrapActionSkill',
            'FromContextFlagValueResolver',
            'FrontendGFxMovieDefinition',
            'GameBalanceDefinition',
            'GameInfo',
            'GameMessage',
            'GamePawn',
            'GamePlayerController',
            'GameplayEvents',
            'GameplayEventsHandler',
            'GameplayEventsReader',
            'GameplayEventsWriter',
            'GameReleaseDefinition',
            'GameReplicationInfo',
            'GameStateObject',
            'GameStatsAggregator',
            'GammaScreenGFxDefinition',
            'GbxMessageDefinition',
            'GearboxAccountActions',
            'GearboxAccountEntitlement',
            'GearboxAnimDefinition',
            'GearboxCalloutDefinition',
            'GearboxCheatManager',
            'GearboxEngineGlobals',
            'GearboxEULAGFxMovieDefinition',
            'GearboxGameInfo',
            'GearboxGlobals',
            'GearboxGlobalsDefinition',
            'GearboxPawn',
            'GearboxPlayerController',
            'GearboxPlayerReplicationInfo',
            'GearboxProcess',
            'GearboxProfileSettings',
            'GenericReviveMessageDefinition',
            'GestaltPartMatricesCollectionDefinition',
            'GFxManagerDefinition',
            'GFxMovieDefinition',
            'GFxTextListDefinition',
            'GladiatorActionSkill',
            'GlobalAttributeValueResolver',
            'GlobalsDefinition',
            'GrenadeModDefinition',
            'GrenadeModPartDefinition',
            'GrinderRecipeDefinition',
            'HashDisplayGFxDefinition',
            'HealthResourcePool',
            'HealthStateExpressionEvaluator',
            'HelpCommandlet',
            'HoldingAreaDestination',
            'HoverVehicleHandlingDefinition',
            'HUDDefinition',
            'HUDScalingAnchorDefinition',
            'InjuredDefinition',
            'InjuredFeedbackMessage',
            'InputActionDefinition',
            'InputContextDefinition',
            'InputDeviceCollectionDefinition',
            'InputDeviceDefinition',
            'InputRemappingDefinition',
            'InputSetDefinition',
            'InstanceDataContextResolver',
            'InteractionIconDefinition',
            'InteractionProxy',
            'InteractiveObjectBalanceDefinition',
            'InteractiveObjectDefinition',
            'InteractiveObjectLootListDefinition',
            'InventoryAttributeContextResolver',
            'InventoryAttributeDefinition',
            'InventoryBalanceDefinition',
            'InventoryCardPresentationDefinition',
            'InventoryPartListCollectionDefinition',
            'IpNetConnectionEpicStore',
            'IpNetConnectionSteamworks',
            'ItemBalanceDefinition',
            'ItemDefinition',
            'ItemInspectionGFxMovieDefinition',
            'ItemNamePartDefinition',
            'ItemPartDefinition',
            'ItemPartListCollectionDefinition',
            'ItemPartListDefinition',
            'ItemPickupGFxDefinition',
            'ItemPoolDefinition',
            'ItemPoolListDefinition',
            'ItemQualityDefinition',
            'JsonObject',
            'KAsset',
            'KAssetSpawnable',
            'KeyedItemPoolDefinition',
            'Keypoint',
            'KillZDamageType',
            'LawbringerActionSkill',
            'Level',
            'LevelDependencyList',
            'LevelStreaming',
            'LevelStreamingAlwaysLoaded',
            'LevelStreamingDistance',
            'LevelStreamingDomino',
            'LevelStreamingKismet',
            'LevelStreamingPersistent',
            'LevelTransitionWaypointComponent',
            'LevelTravelStationDefinition',
            'LeviathanService',
            'LiftActionSkill',
            'LocalInventoryRefreshMessage',
            'LocalItemMessage',
            'LocalizedStringDefinition',
            'LocalMapChangeMessage',
            'LocalMessage',
            'LocalPlayer',
            'LocalTrainingDefinitionMessage',
            'LocalTrainingMessage',
            'LocalWeaponMessage',
            'LockoutDefinition',
            'LookAxisDefinition',
            'LootConfigurationDefinition',
            'ManufacturerAttributeValueResolver',
            'ManufacturerDefinition',
            'MarketingUnlockDefinition',
            'MarketingUnlockInventoryDefinition',
            'MarketplaceGFxMovieDefinition',
            'MatineePawn',
            'MeleeDefinition',
            'MeshComponent',
            'MissionFeedbackMessage',
            'MissionItemDefinition',
            'MissionItemPartDefinition',
            'MissionWeaponBalanceDefinition',
            'MovementComponent',
            'MultipleFlagValueResolver',
            'NameListDefinition',
            'NestedAttributeDefinition',
            'NetConnection',
            'NetDriver',
            'NounAttributeValueResolver',
            'NumberWeaponsEquippedExpressionEvaluator',
            'ObjectFunctionAttributeValueResolver',
            'ObjectFunctionFlagValueResolver',
            'ObjectPropertyAttributeValueResolver',
            'ObjectPropertyContextResolver',
            'ObjectPropertyFlagValueResolver',
            'OnlineGameInterfaceImpl',
            'OnlineGameSettings',
            'OnlinePlayerStorage',
            'OnlineProfileSettings',
            'OpenedChestMessage',
            'OzAIHoldExpressionEvaluator',
            'OzAirBoostDefinition',
            'OzBloodRushDefinition',
            'OzCustomizationUsage_Baroness',
            'OzCustomizationUsage_Doppel',
            'OzCustomizationUsage_Enforcer',
            'OzCustomizationUsage_Gladiator',
            'OzCustomizationUsage_Hovercraft',
            'OzCustomizationUsage_HyperionAPC',
            'OzCustomizationUsage_Lawbringer',
            'OzCustomizationUsage_MoonBuggy',
            'OzCustomizationUsage_Prototype',
            'OzCustomizationUsage_StingRay',
            'OzDebugCameraController',
            'OzDoppelgangingActionSkill',
            'OzExpressionAttributeValueResolver',
            'OzFlagAttributeValueResolver',
            'OzFollowMovementComponent',
            'OzGravityDefinition',
            'OzInstanceDataExpressionEvaluator',
            'OzLawbringerActionSkill',
            'OzMissionExpressionEvaluator',
            'OzObjectFunctionAccessorFlagValueResolver',
            'OzOxygenResourcePool',
            'OzPhysicsTypeAttributeValueResolver',
            'OzPlayerFlagDefinition',
            'OzPlayerFlagExpressionEvaluator',
            'OzPlayersExpressionEvaluator',
            'OzShieldStateExpressionEvaluator',
            'OzSkillGradeExpressionEvaluator',
            'OzStatusInstigatorHasSkillExpressionEvaluator',
            'OzSupportDroneDefinition',
            'OzTargetHealthStateExpressionEvaluator',
            'OzTargetShieldStateExpressionEvaluator',
            'OzTetherProjectileDefinition',
            'OzTravelStationInteractiveObjectDefinition',
            'OzVehicleStateExpressionEvaluator',
            'OzVengeanceCannonWeaponTypeDefinition',
            'OzWillowAegisShieldProjectile',
            'OzWillowDataStreamDefinition',
            'OzWillowDmgSource_FrozenFall',
            'OzWillowDmgSource_Laser',
            'OzWillowDmgSource_Slam',
            'OzWillowReturningProjectile',
            'OzWillowTetherBeamDefinition',
            'OzWillowTetherTargetProjectile',
            'PassengerCameraDefinition',
            'PatchScriptCommandlet',
            'PathTargetPoint',
            'Pawn',
            'PawnAllegiance',
            'PawnInteractionDefinition',
            'PawnInteractionProxy',
            'PerchDefinition',
            'PersistentGameDataManager',
            'PersonalAssistActionSkill',
            'PersonalTeleporterDefinition',
            'PhaseLockDefinition',
            'PhysicsStateExpressionEvaluator',
            'PhysXParticleSystem',
            'Player',
            'PlayerActionExpressionEvaluator',
            'PlayerChallengeListDefinition',
            'PlayerClassAttributeValueResolver',
            'PlayerClassCountAttributeValueResolver',
            'PlayerClassDefinition',
            'PlayerClassIdentifierDefinition',
            'PlayerCollectorGame',
            'PlayerController',
            'PlayerEventProviderDefinition',
            'PlayerNameIdentifierDefinition',
            'PlayerReplicationInfo',
            'PlayerSkillAttributeValueResolver',
            'PlayerSkillTree',
            'PlayerStart',
            'PlayerStatAttributeValueResolver',
            'PlayerTrainingMessageListDefinition',
            'PlayThroughCountAttributeValueResolver',
            'PMESTG_LeaveADecalBase',
            'PopulationMaster',
            'PostureStateExpressionEvaluator',
            'Projectile',
            'ProjectileDefinition',
            'RandomAttributeValueResolver',
            'ReadOnlyObjectPropertyAttributeValueResolver',
            'ReceivedAmmoMessage',
            'ReceivedCreditsMessage',
            'ReceivedItemMessage',
            'ReceivedWeaponMessage',
            'ReplicationInfo',
            'ResourceDefinition',
            'ResourcePool',
            'ResourcePoolAttributeContextResolver',
            'ResourcePoolAttributeDefinition',
            'ResourcePoolDefinition',
            'ResourcePoolManager',
            'ResourcePoolStateAttributeValueResolver',
            'RootMotionDefinition',
            'RuleEventDef',
            'ScorpioActionSkill',
            'Scout',
            'ServerCommandlet',
            'Settings',
            'ShieldDefinition',
            'ShieldPartDefinition',
            'ShieldResourcePool',
            'SimpleMathValueResolver',
            'SkillAttributeContextResolver',
            'SkillDefinition',
            'SkillEffectManager',
            'SkillExpressionEvaluator',
            'SkillExpressionEvaluatorDefinition',
            'SkillPointsFeedbackMessage',
            'SkillTreeBranchDefinition',
            'SkillTreeBranchLayoutDefinition',
            'SkillTreeDefinition',
            'SkillTreeGFxDefinition',
            'SmokeTestCommandlet',
            'SparkInterfaceImpl',
            'SparkServiceConfiguration',
            'SparkTypes',
            'SpecialMove_FirstPerson',
            'SpecialMove_FirstPersonDualWieldAction',
            'SpecialMove_FirstPersonOffHand',
            'SpecialMoveDefinition',
            'SpecialMoveExpressionList',
            'SpecialMoveRandom',
            'SplitscreenHelper',
            'SprintDefinition',
            'StaggerDefinition',
            'StanceExpressionEvaluator',
            'StanceTypeDefinition',
            'StateAttributeResolver',
            'StationTeleporterDestination',
            'StationTeleporterExitPoint',
            'StationTeleporterVehicleExitPoint',
            'StatusEffectDefinition',
            'StatusEffectExpressionEvaluator',
            'StatusEffectProxyActor',
            'StatusEffectsComponent',
            'StatusMenuGFxDefinition',
            'SVehicle',
            'TankVehicleHandlingDefinition',
            'TargetableAttributeValueResolver',
            'TargetingDefinition',
            'TargetMetaInfoValueResolver',
            'TargetPoint',
            'TcpipConnection',
            'TcpNetDriver',
            'TeamInfo',
            'TeleporterDestination',
            'TeleporterFeedbackMessage',
            'TestMapsListDefinition',
            'TextMarkupDictionary',
            'TimeValueResolver',
            'TradingGFxDefinition',
            'TrainingMessageDefinition',
            'TransformedFlagValueResolver',
            'TravelStationDefinition',
            'Trigger',
            'Trigger_PawnsOnly',
            'TriggerStreamingLevel',
            'TurnDefinition',
            'TurretWeaponTypeDefinition',
            'TwoPanelInterfaceGFxDefinition',
            'UsableCustomizationItemDefinition',
            'UsableItemDefinition',
            'UsableItemPartDefinition',
            'Vehicle',
            'VehicleBalanceDefinition',
            'VehicleClassDefinition',
            'VehicleFamilyDefinition',
            'VehicleHandlingDefinition',
            'VehiclePassengerExpressionEvaluator',
            'VehicleSeatSwap_PlayerInteractionClient',
            'VehicleSpawnStationGFxDefinition',
            'VehicleSpawnStationPlatformDefinition',
            'VehicleSpawnStationVehicleDefinition',
            'VehicleWeaponTypeDefinition',
            'VehicleWheelDefinition',
            'VendingMachineExGFxDefinition',
            'VendingMachineGFxDefinition',
            'VSSUIDefinition',
            'WaypointComponent',
            'WeaponAmmoResourceAttributeValueResolver',
            'WeaponAttributeContextResolver',
            'WeaponBalanceDefinition',
            'WeaponEquippedExpressionEvaluator',
            'WeaponGlowEffectDefinition',
            'WeaponNamePartDefinition',
            'WeaponPartDefinition',
            'WeaponPartListCollectionDefinition',
            'WeaponPartListDefinition',
            'WeaponProficiencyFeedbackMessage',
            'WeaponResourcePoolAttributeContextResolver',
            'WeaponScopeGFxDefinition',
            'WeaponStatusEffectAttributePresentationDefinition',
            'WeaponTypeAttributeValueResolver',
            'WeaponTypeDefinition',
            'WillowAccessControl',
            'WillowAutoAimProfileDefinition',
            'WillowAutoAimStrategyDefinition',
            'WillowAwarenessZoneDefinition',
            'WillowBaseStats',
            'WillowCalloutDefinition',
            'WillowCharacterClassDefinition',
            'WillowCheatManager',
            'WillowClanDefinition',
            'WillowCoopGameInfo',
            'WillowCoopPlayerStart',
            'WillowCoverStanceDefinition',
            'WillowDamagePipeline',
            'WillowDamageSource',
            'WillowDamageType',
            'WillowDamageType_Bullet',
            'WillowDamageTypeDefinition',
            'WillowDmgSource_Bullet',
            'WillowDmgSource_CustomCrate',
            'WillowDmgSource_Grenade',
            'WillowDmgSource_MachineGun',
            'WillowDmgSource_Melee',
            'WillowDmgSource_MeleeWithBlade',
            'WillowDmgSource_Pistol',
            'WillowDmgSource_Rocket',
            'WillowDmgSource_Shield',
            'WillowDmgSource_ShieldNova',
            'WillowDmgSource_ShieldSpike',
            'WillowDmgSource_Shotgun',
            'WillowDmgSource_Skill',
            'WillowDmgSource_Skill_IgnoreIOs',
            'WillowDmgSource_Sniper',
            'WillowDmgSource_StatusEffect',
            'WillowDmgSource_SubMachineGun',
            'WillowDmgSource_VehiclePancake',
            'WillowDmgSource_VehicleRanInto',
            'WillowDmgSource_VehicleRanOver',
            'WillowDmgType_VehicleCollision',
            'WillowDownloadableContentManager',
            'WillowExplosionImpactDefinition',
            'WillowGameInfo',
            'WillowGameMessage',
            'WillowGameReplicationInfo',
            'WillowGFxColiseumOverlayDefinition',
            'WillowGFxMovie3DDefinition',
            'WillowGFxThirdPersonDefinition',
            'WillowGFxUIManagerDefinition',
            'WillowGlobals',
            'WillowHUDGFxMovieDefinition',
            'WillowImpactDefinition',
            'WillowInventoryDefinition',
            'WillowInventoryGFxDefinition',
            'WillowInventoryPartDefinition',
            'WillowLevelTimerDefinition',
            'WillowLocalMessage',
            'WillowLocalOnlyProjectile',
            'WillowLockWarningMessage',
            'WillowMapInfo',
            'WillowPawn',
            'WillowPawnInteractionDefinition',
            'WillowPersonalTeleporter',
            'WillowPickupMessage',
            'WillowProjectile',
            'WillowPursuitGridDefinition',
            'WillowScout',
            'WillowServerSideProjectile',
            'WillowShiftGambleInventoryDefinition',
            'WillowShiftGambleItemDefinition',
            'WillowSystemSettings',
            'WillowVehicleControlDefinition',
            'WillowVehicleSeatDefinition',
            'WillowVendingMachineDefinition',
            'WillowVersusDuelGlobals',
            'WillowVersusDuelInfo',
            'WillowVersusDuelMessage',
            'WorldInfo',
            'WwiseSoundGroup',
            },
        'Behaviors': {
            'AIBehaviorProviderDefinition',
            'Behavior_ActivateInstancedMissionBehaviorSequence',
            'Behavior_ActivateListenerSkill',
            'Behavior_ActivateMission',
            'Behavior_ActivateSkill',
            'Behavior_AddInstanceData',
            'Behavior_AddInstanceDataFromBehaviorContext',
            'Behavior_AddInventoryToStorage',
            'Behavior_AddMissionDirectives',
            'Behavior_AddMissionTime',
            'Behavior_AddObjectInstanceData',
            'Behavior_AdjustCameraAnimByEyeHeight',
            'Behavior_AdvanceObjectiveSet',
            'Behavior_AIChangeInventory',
            'Behavior_AICloak',
            'Behavior_AIFollow',
            'Behavior_AIHold',
            'Behavior_AILevelUp',
            'Behavior_AIPatsy',
            'Behavior_AIPriority',
            'Behavior_AIProvoke',
            'Behavior_AIResetProvocation',
            'Behavior_AISetFlight',
            'Behavior_AISetItemTossTarget',
            'Behavior_AISetWeaponFireRotation',
            'Behavior_AISpawn',
            'Behavior_AITakeMoney',
            'Behavior_AITargeting',
            'Behavior_AIThrowProjectileAtTarget',
            'Behavior_AssignBoolVariable',
            'Behavior_AssignFloatVariable',
            'Behavior_AssignIntVariable',
            'Behavior_AssignObjectVariable',
            'Behavior_AssignVectorVariable',
            'Behavior_AttachActor',
            'Behavior_AttachAOEStatusEffect',
            'Behavior_AttachItems',
            'Behavior_AttemptItemCallout',
            'Behavior_AttemptStatusEffect',
            'Behavior_AttributeEffect',
            'Behavior_AwardExperienceForMyDeath',
            'Behavior_BeginLifting',
            'Behavior_BoolMath',
            'Behavior_BroadcastEcho',
            'Behavior_BroadcastTargetPriority',
            'Behavior_CallFunction',
            'Behavior_CauseDamage',
            'Behavior_CauseTinnitus',
            'Behavior_ChangeAllegiance',
            'Behavior_ChangeAnyBehaviorSequenceState',
            'Behavior_ChangeBehaviorSetState',
            'Behavior_ChangeBoneVisibility',
            'Behavior_ChangeCanTarget',
            'Behavior_ChangeCollision',
            'Behavior_ChangeCollisionSize',
            'Behavior_ChangeCounter',
            'Behavior_ChangeDenAllegiance',
            'Behavior_ChangeDialogName',
            'Behavior_ChangeEnvironmentTag',
            'Behavior_ChangeInstanceDataSwitch',
            'Behavior_ChangeLocalBehaviorSequenceState',
            'Behavior_ChangeParticleSystemActiveState',
            'Behavior_ChangeRemoteBehaviorSequenceState',
            'Behavior_ChangeScale',
            'Behavior_ChangeSkillBehaviorSequenceState',
            'Behavior_ChangeSpin',
            'Behavior_ChangeTimer',
            'Behavior_ChangeUsability',
            'Behavior_ChangeVisibility',
            'Behavior_ChangeWeaponVisibility',
            'Behavior_Charm',
            'Behavior_CheckMapChangeConditions',
            'Behavior_ClearObjective',
            'Behavior_ClearStatusEffects',
            'Behavior_ClearWeaponSlot',
            'Behavior_ClientConsoleCommand',
            'Behavior_CombatPerch',
            'Behavior_CombatPerchThrow',
            'Behavior_CompareBool',
            'Behavior_CompareFloat',
            'Behavior_CompareInt',
            'Behavior_CompareObject',
            'Behavior_CompareValues',
            'Behavior_CompleteMission',
            'Behavior_Conditional',
            'Behavior_ConsoleCommand',
            'Behavior_ConvertInstanceDataIntoPhysicsActor',
            'Behavior_CoordinatedEffect',
            'Behavior_Crane',
            'Behavior_CreateImpactEffect',
            'Behavior_CreateWeatherSystem',
            'Behavior_CustomAnimation',
            'Behavior_CustomEvent',
            'Behavior_DamageArea',
            'Behavior_DamageClassSwitch',
            'Behavior_DamageSourceSwitch',
            'Behavior_DamageSurfaceTypeSwitch',
            'Behavior_DeactivateSkill',
            'Behavior_DebugMessage',
            'Behavior_DecrementObjective',
            'Behavior_Delay',
            'Behavior_Destroy',
            'Behavior_DestroyBeams',
            'Behavior_DestroyBeamsForSource',
            'Behavior_DestroyWeatherSystem',
            'Behavior_DetachActor',
            'Behavior_DisableFallingDamage',
            'Behavior_DiscoverLevelChallengeObject',
            'Behavior_DisplayHUDMessage',
            'Behavior_DropItems',
            'Behavior_DropProjectile',
            'Behavior_DropWeapon',
            'Behavior_DuplicateInstanceData',
            'Behavior_EnableHandIK',
            'Behavior_EnemyInRange',
            'Behavior_EnterVehicle',
            'Behavior_Explode',
            'Behavior_FailMission',
            'Behavior_FinishLifting',
            'Behavior_FireBeam',
            'Behavior_FireCustomSkillEvent',
            'Behavior_FireShot',
            'Behavior_FollowAllegiance',
            'Behavior_ForceDownState',
            'Behavior_ForceInjured',
            'Behavior_ForceSave',
            'Behavior_Gate',
            'Behavior_GetClosestEnemy',
            'Behavior_GetClosestPlayer',
            'Behavior_GetFloatParam',
            'Behavior_GetHoundTarget',
            'Behavior_GetItemPrice',
            'Behavior_GetObjectParam',
            'Behavior_GetPlayerStat',
            'Behavior_GetVectorParam',
            'Behavior_GetVelocity',
            'Behavior_GetZoneVelocity',
            'Behavior_GFxMoviePlay',
            'Behavior_GFxMovieRegister',
            'Behavior_GFxMovieSetState',
            'Behavior_GFxMovieStop',
            'Behavior_GiveChallengeToPlayer',
            'Behavior_GiveInjuredPlayerSecondWind',
            'Behavior_HasMissions',
            'Behavior_HeadLookHold',
            'Behavior_IncrementOverpowerLevel',
            'Behavior_IncrementPlayerStat',
            'Behavior_InterpolateFloatOverTime',
            'Behavior_IntMath',
            'Behavior_IntSwitchRange',
            'Behavior_IsCensoredMode',
            'Behavior_IsObjectPlayer',
            'Behavior_IsObjectVehicle',
            'Behavior_IsSequenceEnabled',
            'Behavior_Kill',
            'Behavior_Knockback',
            'Behavior_LanguageSwitch',
            'Behavior_LeaderCommand',
            'Behavior_LeapAtTarget',
            'Behavior_LocalCustomEvent',
            'Behavior_MakeVector',
            'Behavior_MatchTransform',
            'Behavior_MeleeAttack',
            'Behavior_Metronome',
            'Behavior_MissionCustomEvent',
            'Behavior_MissionDirectorParticle',
            'Behavior_MissionRemoteEvent',
            'Behavior_ModifyTimer',
            'Behavior_NetworkRoleSwitch',
            'Behavior_NotifyThoughtLockStatus',
            'Behavior_ObjectClassSwitch',
            'Behavior_OpinionSwitch',
            'Behavior_OverrideWeaponCrosshair',
            'Behavior_PackAttack',
            'Behavior_PawnLeap',
            'Behavior_PhaseLockHold',
            'Behavior_PhysXLevel',
            'Behavior_PlayAIMissionContextDialog',
            'Behavior_PlayAnimation',
            'Behavior_PlayHardFlinch',
            'Behavior_PlayMultipleExplosionsSound',
            'Behavior_PlaySound',
            'Behavior_PlayTermovision',
            'Behavior_PostAkEvent',
            'Behavior_PostAkEventGetRTPC',
            'Behavior_PostProcessChain',
            'Behavior_PostProcessChain_LostShield',
            'Behavior_PostProcessOverlay',
            'Behavior_PursueNodeType',
            'Behavior_QueryDayNightCycle',
            'Behavior_QueuePersonalEcho',
            'Behavior_RadarIcon',
            'Behavior_RandomBranch',
            'Behavior_RandomlyRunBehaviors',
            'Behavior_RandomlySelectBehaviors',
            'Behavior_ReCalculateResourcePoolValues',
            'Behavior_RefillResourcePool',
            'Behavior_RefillWeapon',
            'Behavior_RegisterFastTravelDefinition',
            'Behavior_RegisterTargetable',
            'Behavior_ReloadComplete',
            'Behavior_RemoteCustomEvent',
            'Behavior_RemoteEvent',
            'Behavior_RemoveInstanceData',
            'Behavior_RemoveInventoryFromStorage',
            'Behavior_ResetActionSkillCooldown',
            'Behavior_ResetHitRegionHealth',
            'Behavior_ReviveInjuredPlayer',
            'Behavior_RotatePawn',
            'Behavior_RuleEvent',
            'Behavior_RunBehaviorAlias',
            'Behavior_RunBehaviorCollection',
            'Behavior_ScreenParticle',
            'Behavior_SearchEnemiesInRange',
            'Behavior_SelectPhaselockTarget',
            'Behavior_SendGbxMessage',
            'Behavior_SendMessageToPlayers',
            'Behavior_SetAIFlag',
            'Behavior_SetAkRTPCValue',
            'Behavior_SetAlternateVertexWeight',
            'Behavior_SetAnimSwitchNode',
            'Behavior_SetAnimTree',
            'Behavior_SetBeingHealed',
            'Behavior_SetChallengeCompleted',
            'Behavior_SetCleanupParameters',
            'Behavior_SetCompassIcon',
            'Behavior_SetDeathDefinition',
            'Behavior_SetDemigodMode',
            'Behavior_SetDiscardRootMotion',
            'Behavior_SetDualWieldBlendState',
            'Behavior_SetElevatorButtonGlowing',
            'Behavior_SetExtraImpactEffect',
            'Behavior_SetExtraMuzzleEffect',
            'Behavior_SetFlag',
            'Behavior_SetFloatParam',
            'Behavior_SetGodMode',
            'Behavior_SetHardAttach',
            'Behavior_SetInfoBarVisibility',
            'Behavior_SetJackVoiceModulatorState',
            'Behavior_SetLookAtSpeed',
            'Behavior_SetMaterialParameters',
            'Behavior_SetMaterialScalarFade',
            'Behavior_SetMaterialScalarFadeForGoreDeath',
            'Behavior_SetMorphNodeWeight',
            'Behavior_SetNumBankSlots',
            'Behavior_SetObjectParam',
            'Behavior_SetParticleSystemParameters',
            'Behavior_SetPawnSliceDeath',
            'Behavior_SetPawnThrottleData',
            'Behavior_SetPhysics',
            'Behavior_SetReplicatedWeaponGlitchSequence',
            'Behavior_SetRuleSet',
            'Behavior_SetRuleSetByName',
            'Behavior_SetScreenParticleParameters',
            'Behavior_SetShieldColor',
            'Behavior_SetShieldDamageResistanceType',
            'Behavior_SetShieldTriggeredState',
            'Behavior_SetSkelControlActive',
            'Behavior_SetSkelControlLookAtActor',
            'Behavior_SetSkelControlSingleBoneData',
            'Behavior_SetSkelControlTurretConstrainedValues',
            'Behavior_SetSkillDefinitionForInjuredStrings',
            'Behavior_SetStance',
            'Behavior_SetTimeOfDay',
            'Behavior_SetUsabilityByMissionDirectives',
            'Behavior_SetUsabilityCost',
            'Behavior_SetUsableIcon',
            'Behavior_SetVectorParam',
            'Behavior_SetVehicleSimObject',
            'Behavior_ShiftEvents',
            'Behavior_ShowGenericReviveMessage',
            'Behavior_ShowMissionInterface',
            'Behavior_ShowPullThePinNotification',
            'Behavior_ShowSelfAsTarget',
            'Behavior_ShowSubroutineLoadedMessage',
            'Behavior_SimpleAnimPlay',
            'Behavior_SimpleAnimStop',
            'Behavior_SimpleMath',
            'Behavior_SkillCustomEvent',
            'Behavior_SpawnActor',
            'Behavior_SpawnAttachmentItems',
            'Behavior_SpawnDecal',
            'Behavior_SpawnFirstPersonParticleSystem',
            'Behavior_SpawnFromPopulationSystem',
            'Behavior_SpawnFromVehicleSpawnStation',
            'Behavior_SpawnItems',
            'Behavior_SpawnLoot',
            'Behavior_SpawnLootAroundPoint',
            'Behavior_SpawnLootAtPoints',
            'Behavior_SpawnParticleSystem',
            'Behavior_SpawnParticleSystemAtWorldLocation',
            'Behavior_SpawnPerch',
            'Behavior_SpawnProjectile',
            'Behavior_SpawnProjectileFromImpact',
            'Behavior_SpawnTemporalField',
            'Behavior_SpawnWeapon',
            'Behavior_SpawnWeaponAndEquip',
            'Behavior_SpecialMove',
            'Behavior_SpecialMoveStop',
            'Behavior_StartAkAmbientSound',
            'Behavior_StartDeathRagdoll',
            'Behavior_StartMissionTimer',
            'Behavior_StatusEffectSwitch',
            'Behavior_StopAkAmbientSound',
            'Behavior_StopDialog',
            'Behavior_StopMeleeAttack',
            'Behavior_StopMissionTimer',
            'Behavior_Switch',
            'Behavior_ToggleDialog',
            'Behavior_ToggleNPCAlly',
            'Behavior_ToggleObstacle',
            'Behavior_ToggleTelescopeOverlay',
            'Behavior_ToggleVisibility',
            'Behavior_Trace',
            'Behavior_Transform',
            'Behavior_TriggerDialogEvent',
            'Behavior_UnequipWeaponSlot',
            'Behavior_UnlockAvatarAward',
            'Behavior_UnlockAvatarAwardForAllPlayers',
            'Behavior_UnlockCustomization',
            'Behavior_UnlockCustomizationFromRewardPool',
            'Behavior_UpdateCollision',
            'Behavior_UpdateMissionObjective',
            'Behavior_UpgradeSkill',
            'Behavior_UseObject',
            'Behavior_VectorMath',
            'Behavior_VectorToLocalSpace',
            'Behavior_VoGScreenParticle',
            'Behavior_WeaponBoneControl',
            'Behavior_WeaponGlowEffect',
            'Behavior_WeaponsRestriction',
            'Behavior_WeaponThrow',
            'Behavior_WeaponVisibleAmmoState',
            'BehaviorAliasDefinition',
            'BehaviorAliasLookupDefinition',
            'BehaviorBase',
            'BehaviorCollectionDefinition',
            'BehaviorKernel',
            'BehaviorProviderDefinition',
            'BehaviorSequenceCustomEnableCondition',
            'BehaviorSequenceEnableByMission',
            'BehaviorSequenceEnableByMultipleConditions',
            'BehaviorVolumeDefinition',
            'OzBehavior_ActivateSkillWithGradeOf',
            'OzBehavior_ActorList',
            'OzBehavior_AddAmmoToClip',
            'OzBehavior_AddPlayerVelocity',
            'OZBehavior_AddSkillTarget',
            'OzBehavior_AIStartGravityWellState',
            'OzBehavior_ArrayAt',
            'OzBehavior_BroadcastCustomEventToList',
            'OzBehavior_ChangeOwnerVisibility',
            'OzBehavior_CheckReadiedWeaponsForManufacturer',
            'OzBehavior_ClearStatusEffect',
            'OzBehavior_ClearStatusEffectsType',
            'OZBehavior_CloneMainhandWeaponToOffhand',
            'OZBehavior_DestroyOffhandWeapon',
            'OzBehavior_ForceSpreadStatusEffect',
            'OzBehavior_Freeze',
            'OzBehavior_GenerateIdentifier',
            'OzBehavior_GetCurrentMissionActor',
            'OzBehavior_GetDistanceToDoppel',
            'OzBehavior_GetGrenadeInfo',
            'OzBehavior_GetGrenadePartAlpha',
            'OzBehavior_GetRandomEnemyInRange',
            'OZBehavior_GetSkillTarget',
            'OzBehavior_Gib',
            'OzBehavior_GiveEquipmentToAI',
            'OzBehavior_GiveGrenades',
            'OzBehavior_HasPlayerFlag',
            'OzBehavior_IsStatusEffectInstigator',
            'OzBehavior_IsTargetDead',
            'OzBehavior_MissionCustomPlayerEvent',
            'OzBehavior_NotifyInstinctSkillAction',
            'OZBehavior_RemoveSkillTarget',
            'OzBehavior_SetAITarget',
            'OzBehavior_SetCollisionComponent',
            'OzBehavior_SetFaceFxAsset',
            'OzBehavior_SetForceDualWieldBlendState',
            'OZBehavior_SetParticlePlayerOwner',
            'OzBehavior_SetPlayerFlag',
            'OzBehavior_SetPlayerVoiceFilter',
            'OzBehavior_ShareHealthPool',
            'OzBehavior_SpawnWeaponAndEquipToAI',
            'OzBehavior_TeleportDoppel',
            'OzBehavior_TeleportPlayerToDoppel',
            'OzBehavior_Tether',
            'OzBehavior_ToggleMeleeHold',
            'OzBehavior_TriggerShield',
            'OzBehavior_TriggerSpawnProjectileFromHandsEvent',
            'OzBehavior_Vacuum',
            'OzPlayerBehavior_BloodRushAttack',
            'OZPlayerBehavior_PlayAnimationOnMeleeWeaponMesh',
            'ParameterBehaviorBase',
            'PlayerBehavior_BlockDueling',
            'PlayerBehavior_CameraAnim',
            'PlayerBehavior_DropItems',
            'PlayerBehavior_ForceFeedback',
            'PlayerBehavior_Lunge',
            'PlayerBehavior_Melee',
            'PlayerBehavior_PlayEchoCall',
            'PlayerBehavior_RegisterFastTravelStation',
            'PlayerBehavior_Reload',
            'PlayerBehavior_SetCurrentProjectile',
            'PlayerBehavior_SpawnCurrentProjectile',
            'PlayerBehavior_SpawnTeleporter',
            'PlayerBehavior_ThrowGrenade',
            'PlayerBehavior_ToggleDualMeleeWeapon',
            'PlayerBehavior_ToggleForceFire',
            'PlayerBehavior_ToggleMeleeWeapon',
            'PlayerBehavior_ToggleRevive',
            'PlayerBehavior_UnlockAchievement',
            'PlayerBehavior_UnlockAchievementForAllPlayers',
            'PlayerBehavior_ViewShake',
            'PlayerBehaviorBase',
            'ProjectileBehavior_Attach',
            'ProjectileBehavior_Bounce',
            'ProjectileBehavior_Detonate',
            'ProjectileBehavior_FindHomingTarget',
            'ProjectileBehavior_LevelOff',
            'ProjectileBehavior_SetDamageTypeDefinition',
            'ProjectileBehavior_SetExplosionDefinition',
            'ProjectileBehavior_SetHomingTarget',
            'ProjectileBehavior_SetProximity',
            'ProjectileBehavior_SetSpeed',
            'ProjectileBehavior_SetStickyGrenade',
            'ProjectileBehavior_TagPayloadType',
            'ProjectileBehaviorBase',
            'WillowVersusDuelBehavior',
            },
        'Dialog': {
            'GearboxDialogEventTag',
            'GearboxDialogGlobalsDefinition',
            'GearboxDialogNameTag',
            'WillowDialogEventTag',
            'WillowDialogEventTagSpecialized',
            'WillowDialogGlobalsDefinition',
            'WillowDialogNameTag',
            },
        'Kismets': {
            'GearboxSeqAct_CameraShake',
            'GearboxSeqAct_DestroyPopulationActors',
            'GearboxSeqAct_PawnClonerLink',
            'GearboxSeqAct_PopulationOpportunityLink',
            'GearboxSeqAct_ResetPopulationCount',
            'GearboxSeqAct_TargetPriority',
            'GearboxSeqAct_ToggleDialog',
            'GearboxSeqAct_TriggerDialog',
            'GearboxSeqAct_TriggerDialogName',
            'GearboxSeqAct_TriggerSpecializedDialog',
            'GFxAction_CloseMovie',
            'GFxAction_GetVariable',
            'GFxAction_Invoke',
            'GFxAction_OpenMovie',
            'GFxAction_SetCaptureKeys',
            'GFxAction_SetVariable',
            'GFxEvent_FSCommand',
            'InterpData',
            'OzSeqAct_EncountersWave',
            'OzSeqAct_HideDroppedPickups',
            'OzSeqAct_SetVolumeGravity',
            'OZSeqCond_SwitchByCurrentWeaponType',
            'OZSeqEvent_PlayerFired',
            'PersistentSequenceData',
            'PrefabSequence',
            'PrefabSequenceContainer',
            'SavingSequenceFrame',
            'SeqAct_AccessObjectList',
            'SeqAct_ActivateRemoteEvent',
            'SeqAct_ActorFactory',
            'SeqAct_ActorFactoryEx',
            'SeqAct_AddFloat',
            'SeqAct_AddInt',
            'SeqAct_AddRemoveFaceFXAnimSet',
            'SeqAct_AIAbortMoveToActor',
            'SeqAct_AIMoveToActor',
            'SeqAct_AkClearBanks',
            'SeqAct_AkLoadBank',
            'SeqAct_AkPostEvent',
            'SeqAct_AkPostTrigger',
            'SeqAct_AkSetRTPCValue',
            'SeqAct_AkSetState',
            'SeqAct_AkSetSwitch',
            'SeqAct_AkStopAll',
            'SeqAct_AllPlayersInMesh',
            'SeqAct_AllPlayersInVolume',
            'SeqAct_AndGate',
            'SeqAct_ApplyBehavior',
            'SeqAct_ApplySoundNode',
            'SeqAct_AssignController',
            'SeqAct_AttachPlayerPawnToBase',
            'SeqAct_AttachToActor',
            'SeqAct_AttachToEvent',
            'SeqAct_CameraFade',
            'SeqAct_CameraLookAt',
            'SeqAct_CastToFloat',
            'SeqAct_CastToInt',
            'SeqAct_CausePlayerDeath',
            'SeqAct_ChangeCollision',
            'SeqAct_CommitMapChange',
            'SeqAct_ConditionallyLoadCommons',
            'SeqAct_ConsoleCommand',
            'SeqAct_ControlGameMovie',
            'SeqAct_ControlMovieTexture',
            'SeqAct_ConvertToString',
            'SeqAct_Delay',
            'SeqAct_DelaySwitch',
            'SeqAct_Deproject',
            'SeqAct_Destroy',
            'SeqAct_DiscardInventory',
            'SeqAct_DiscoverLevelChallengeObject',
            'SeqAct_DisplayTrainingDefinitionMessage',
            'SeqAct_DisplayTrainingMessage',
            'SeqAct_DisplayWillowHUDMessage',
            'SeqAct_DivideFloat',
            'SeqAct_DivideInt',
            'SeqAct_DrawText',
            'SeqAct_ExecuteSkill',
            'SeqAct_FinishSequence',
            'SeqAct_FlyThroughHasEnded',
            'SeqAct_ForceFeedback',
            'SeqAct_ForceGarbageCollection',
            'SeqAct_Gate',
            'SeqAct_GetAttributeValue',
            'SeqAct_GetDistance',
            'SeqAct_GetInstanceData',
            'SeqAct_GetLocationAndRotation',
            'SeqAct_GetProperty',
            'SeqAct_GetVectorComponents',
            'SeqAct_GetVelocity',
            'SeqAct_HeadTrackingControl',
            'SeqAct_Interp',
            'SeqAct_IsInObjectList',
            'SeqAct_IsInVolume',
            'SeqAct_Latent',
            'SeqAct_LevelStreaming',
            'SeqAct_LevelStreamingBase',
            'SeqAct_LevelVisibility',
            'SeqAct_LoadingMovie',
            'SeqAct_Log',
            'SeqAct_MathBase',
            'SeqAct_MathFloat',
            'SeqAct_MathInteger',
            'SeqAct_MITV_Activate',
            'SeqAct_ModifyCover',
            'SeqAct_ModifyHealth',
            'SeqAct_ModifyHUDElement',
            'SeqAct_ModifyObjectList',
            'SeqAct_ModifyProperty',
            'SeqAct_MultiLevelStreaming',
            'SeqAct_MultiplyFloat',
            'SeqAct_MultiplyInt',
            'SeqAct_ParticleEventGenerator',
            'SeqAct_PhysXSwitch',
            'SeqAct_PlayBinkMovie',
            'SeqAct_PlayCameraAnim',
            'SeqAct_PlayFaceFXAnim',
            'SeqAct_PlayMusicTrack',
            'SeqAct_PlaySound',
            'SeqAct_Possess',
            'SeqAct_PossessForPlayer',
            'SeqAct_PrepareMapChange',
            'SeqAct_PrimaryPlayerBusyDelay',
            'SeqAct_ProceduralSwitch',
            'SeqAct_ProceduralSwitchNumeric',
            'SeqAct_ProjectileFactory',
            'SeqAct_RandomSwitch',
            'SeqAct_SetApexClothingParam',
            'SeqAct_SetBlockRigidBody',
            'SeqAct_SetBool',
            'SeqAct_SetCameraTarget',
            'SeqAct_SetChallengeCompleted',
            'SeqAct_SetDamageInstigator',
            'SeqAct_SetDOFParams',
            'SeqAct_SetFloat',
            'SeqAct_SetInt',
            'SeqAct_SetLocation',
            'SeqAct_SetMaterial',
            'SeqAct_SetMatInstScalarParam',
            'SeqAct_SetMesh',
            'SeqAct_SetMotionBlurParams',
            'SeqAct_SetNameList',
            'SeqAct_SetObject',
            'SeqAct_SetParticleSysParam',
            'SeqAct_SetPhysics',
            'SeqAct_SetRigidBodyIgnoreVehicles',
            'SeqAct_SetSequenceVariable',
            'SeqAct_SetShadowParent',
            'SeqAct_SetSkelControlTarget',
            'SeqAct_SetSoundMode',
            'SeqAct_SetString',
            'SeqAct_SetVector',
            'SeqAct_SetVectorComponents',
            'SeqAct_SetVelocity',
            'SeqAct_StreamInTextures',
            'SeqAct_SubtractFloat',
            'SeqAct_SubtractInt',
            'SeqAct_Switch',
            'SeqAct_Teleport',
            'SeqAct_TimedMessage',
            'SeqAct_Timer',
            'SeqAct_Toggle',
            'SeqAct_ToggleCinematicMode',
            'SeqAct_ToggleConstraintDrive',
            'SeqAct_ToggleGodMode',
            'SeqAct_ToggleHidden',
            'SeqAct_ToggleHUD',
            'SeqAct_ToggleInput',
            'SeqAct_Trace',
            'SeqAct_UnlockAchievement',
            'SeqAct_UpdatePhysBonesFromAnim',
            'SeqAct_WaitForLevelsVisible',
            'SeqCond_CompareBool',
            'SeqCond_CompareFloat',
            'SeqCond_CompareInt',
            'SeqCond_CompareLocation',
            'SeqCond_CompareObject',
            'SeqCond_CompareString',
            'SeqCond_GetLanguage',
            'SeqCond_GetServerType',
            'SeqCond_HasValidSaveGame',
            'SeqCond_Increment',
            'SeqCond_IncrementFloat',
            'SeqCond_IsAlive',
            'SeqCond_IsBenchmarking',
            'SeqCond_IsConsole',
            'SeqCond_IsInCombat',
            'SeqCond_IsLoggedIn',
            'SeqCond_IsPIE',
            'SeqCond_IsPlayerCharacterClass',
            'SeqCond_IsSameTeam',
            'SeqCond_MatureLanguage',
            'SeqCond_ShowGore',
            'SeqCond_SwitchBase',
            'SeqCond_SwitchClass',
            'SeqCond_SwitchObject',
            'SeqCond_SwitchPlatform',
            'SeqDef_Base',
            'SeqEvent_AIReachedRouteActor',
            'SeqEvent_AISeeEnemy',
            'SeqEvent_AllSpawned',
            'SeqEvent_AnimNotify',
            'SeqEvent_ArrivedAtMoveNode',
            'SeqEvent_Console',
            'SeqEvent_ConstraintBroken',
            'SeqEvent_Death',
            'SeqEvent_Destroyed',
            'SeqEvent_EncounterWaveComplete',
            'SeqEvent_HitWall',
            'SeqEvent_LeavingMoveNode',
            'SeqEvent_LevelLoaded',
            'SeqEvent_LOS',
            'SeqEvent_Mover',
            'SeqEvent_ParticleEvent',
            'SeqEvent_PickupStatusChange',
            'SeqEvent_PlayerSpawned',
            'SeqEvent_PopulatedActor',
            'SeqEvent_PopulatedPoint',
            'SeqEvent_ProjectileLanded',
            'SeqEvent_RemoteEvent',
            'SeqEvent_RigidBodyCollision',
            'SeqEvent_SeamlessTravelComplete',
            'SeqEvent_SeeDeath',
            'SeqEvent_SequenceActivated',
            'SeqEvent_SinglePopulationDeath',
            'SeqEvent_SpawnedMissionPickup',
            'SeqEvent_TakeDamage',
            'SeqEvent_TakeHitRegionDamage',
            'SeqEvent_Touch',
            'SeqEvent_TrainingMessage',
            'SeqEvent_Used',
            'SeqEvent_WorldDiscoveryArea',
            'Sequence',
            'SequenceAction',
            'SequenceCondition',
            'SequenceDefinition',
            'SequenceEvent',
            'SequenceEventEnableByMission',
            'SequenceFrame',
            'SequenceFrameWrapped',
            'SequenceObject',
            'SequenceOp',
            'SequenceVariable',
            'SeqVar_Bool',
            'SeqVar_Byte',
            'SeqVar_Character',
            'SeqVar_External',
            'SeqVar_Float',
            'SeqVar_Group',
            'SeqVar_Int',
            'SeqVar_Name',
            'SeqVar_Named',
            'SeqVar_Object',
            'SeqVar_ObjectList',
            'SeqVar_ObjectVolume',
            'SeqVar_OverpowerLevel',
            'SeqVar_Player',
            'SeqVar_PrimaryLocalPlayer',
            'SeqVar_RandomFloat',
            'SeqVar_RandomInt',
            'SeqVar_String',
            'SeqVar_Union',
            'SeqVar_Vector',
            'Trigger_Dynamic',
            'Trigger_LOS',
            'WillowSeqAct_ActivateInstancedBehaviorSequences',
            'WillowSeqAct_AICombatVolume',
            'WillowSeqAct_AILookAt',
            'WillowSeqAct_AIProvoke',
            'WillowSeqAct_AIScripted',
            'WillowSeqAct_AIScriptedAnim',
            'WillowSeqAct_AIScriptedDeath',
            'WillowSeqAct_AIScriptedFollow',
            'WillowSeqAct_AIScriptedHold',
            'WillowSeqAct_AISetItemTossTarget',
            'WillowSeqAct_AIStopPerch',
            'WillowSeqAct_BossBar',
            'WillowSeqAct_CleanUpPlayerVehicles',
            'WillowSeqAct_ClientFlagGet',
            'WillowSeqAct_ClientFlagSet',
            'WillowSeqAct_CloseColiseumOverlay',
            'WillowSeqAct_ColiseumAllDead',
            'WillowSeqAct_ColiseumAnnouncePenaltyBox',
            'WillowSeqAct_ColiseumAwardCertificate',
            'WillowSeqAct_ColiseumNotify',
            'WillowSeqAct_ColiseumRoundAnnounce',
            'WillowSeqAct_ColiseumRuleAnnounce',
            'WillowSeqAct_ColiseumStartTimer',
            'WillowSeqAct_ColiseumVictory',
            'WillowSeqAct_CompleteMission',
            'WillowSeqAct_ConfigureBossMusic',
            'WillowSeqAct_ConfigureCustomAmbientMusic',
            'WillowSeqAct_ConfigureLevelMusic',
            'WillowSeqAct_CoordinateOperations',
            'WillowSeqAct_DayNightCycle',
            'WillowSeqAct_DisableCombatMusicLogic',
            'WillowSeqAct_ElevatorFinished',
            'WillowSeqAct_EnableCombatMusicLogic',
            'WillowSeqAct_ExitVehicle',
            'WillowSeqAct_GiveMission',
            'WillowSeqAct_InterpMenu',
            'WillowSeqAct_InterpPawn',
            'WillowSeqAct_KillPawnBasedOnAllegiance',
            'WillowSeqAct_MarkEnteredRegion',
            'WillowSeqAct_MarkExitedRegion',
            'WillowSeqAct_MarkPlaythroughCompleted',
            'WillowSeqAct_MissionCustomEvent',
            'WillowSeqAct_MissionSmokeTest',
            'WillowSeqAct_MoveElevator',
            'WillowSeqAct_NotifyDesignerAttribute',
            'WillowSeqAct_OpenColiseumOverlay',
            'WillowSeqAct_PlayArmAnimation',
            'WillowSeqAct_PlayCameraAnim',
            'WillowSeqAct_PrepareMapChangeFromDefinition',
            'WillowSeqAct_PrepareSavedMapChange',
            'WillowSeqAct_QueryTeleporterStatus',
            'WillowSeqAct_ReleaseTeleporterHeldLevel',
            'WillowSeqAct_ResurrectPlayer',
            'WillowSeqAct_RunCustomEvent',
            'WillowSeqAct_SetAIFlag',
            'WillowSeqAct_SetInteractionProxyState',
            'WillowSeqAct_SetLockout',
            'WillowSeqAct_SetLookAtActor',
            'WillowSeqAct_StopCameraAnim',
            'WillowSeqAct_ToggleCinematicModeAffectsAll',
            'WillowSeqAct_TogglePostRenderFor',
            'WillowSeqAct_ToggleRestrictions',
            'WillowSeqAct_TravelStationTeleport',
            'WillowSeqAct_TurnOffCombatMusic',
            'WillowSeqAct_UpdateColiseumRuleOverlay',
            'WillowSeqAct_WaypointObjective',
            'WillowSeqCond_AnyPlayerHasMarketingUnlock',
            'WillowSeqCond_CheckLockout',
            'WillowSeqCond_GoStraightToMainMenu',
            'WillowSeqCond_IsCombatMusicPlaying',
            'WillowSeqCond_IsMissionObjectiveSetActive',
            'WillowSeqCond_IsPlayerServer',
            'WillowSeqCond_MultiplePlayersInGame',
            'WillowSeqCond_PlaythroughNumber',
            'WillowSeqCond_ShouldStartNewGameCinematics',
            'WillowSeqCond_SplitScreen',
            'WillowSeqCond_SwitchByPlatform',
            'WillowSeqEvent_CharacterSelectUIClosed',
            'WillowSeqEvent_CombatMusicStarted',
            'WillowSeqEvent_CounterAtTarget',
            'WillowSeqEvent_CustomEvent',
            'WillowSeqEvent_DenStat',
            'WillowSeqEvent_DuelChallengeAccepted',
            'WillowSeqEvent_DuelChallengeIssued',
            'WillowSeqEvent_ElevatorUsed',
            'WillowSeqEvent_FastTravel',
            'WillowSeqEvent_JumpAnimIdle',
            'WillowSeqEvent_JumpAnimStart',
            'WillowSeqEvent_JumpAnimStop',
            'WillowSeqEvent_MissionRemoteEvent',
            'WillowSeqEvent_PlayerJoined',
            'WillowSeqEvent_PlayerLeft',
            'WillowSeqEvent_Provoked',
            'WillowSeqEvent_ShowCharacterSelectUI',
            'WillowSeqEvent_StartNewGameCinematics',
            'WillowSeqEvent_TimerElapsed',
            'WillowSeqEvent_VehicleSpawned',
            'WillowSeqVar_DayNightCycleRate',
            'WillowSeqVar_DayNightCycleVariable',
            'WillowSeqVar_TimeOfDay',
            'WillowTrigger',
            'WillowWaypoint',
            },
        'Meshes': {
            'ApexComponentBase',
            'ApexDynamicComponent',
            'ApexStaticComponent',
            'ApexStaticDestructibleComponent',
            'CustomSkeletalMeshComponent',
            'GearboxSkeletalMeshComponent',
            'GearLikenessMeshComponent',
            'GestaltSkeletalMeshDefinition',
            'PerchPreviewComponent',
            'PhysicsJumpPreviewComponent',
            'SkeletalMesh',
            'SkeletalMeshComponent',
            'StaticMesh',
            'WillowPopulationPointPreviewComponent',
            'WillowPreviewComponent',
            'WiringMesh',
            },
        'Missions': {
            'FailableMissionDirectiveWaypointComponent',
            'MissionDefinition',
            'MissionDirectivesDefinition',
            'MissionDirectiveWaypointComponent',
            'MissionObjectiveDefinition',
            'MissionObjectiveSetBranchingDefinition',
            'MissionObjectiveSetCollectionDefinition',
            'MissionObjectiveSetDefinition',
            'MissionObjectiveWaypointComponent',
            'MissionPopulationAspect',
            'QuestAcceptGFxDefinition',
            },
        'Particles': {
            'EffectCollectionDefinition',
            'Emitter',
            'EmitterCameraLensEffectBase',
            'EmitterPool',
            'EmitterSpawnable',
            'OzParticleModuleLocationIceChunks',
            'OzParticleModuleLocationLine',
            'OzParticleModuleSound',
            'OzParticleModuleSoundBase',
            'ParticleEmitter',
            'ParticleLODLevel',
            'ParticleModule',
            'ParticleModuleAcceleration',
            'ParticleModuleAccelerationBase',
            'ParticleModuleAccelerationOverLifetime',
            'ParticleModuleAttractorBase',
            'ParticleModuleAttractorLine',
            'ParticleModuleAttractorParticle',
            'ParticleModuleAttractorPoint',
            'ParticleModuleBeamBase',
            'ParticleModuleBeamModifier',
            'ParticleModuleBeamNoise',
            'ParticleModuleBeamSource',
            'ParticleModuleBeamTarget',
            'ParticleModuleBeamTrace',
            'ParticleModuleCameraBase',
            'ParticleModuleCameraOffset',
            'ParticleModuleCollision',
            'ParticleModuleCollisionActor',
            'ParticleModuleCollisionBase',
            'ParticleModuleColor',
            'ParticleModuleColor_Seeded',
            'ParticleModuleColorBase',
            'ParticleModuleColorByParameter',
            'ParticleModuleColorOverLife',
            'ParticleModuleColorScaleOverDensity',
            'ParticleModuleColorScaleOverLife',
            'ParticleModuleEventBase',
            'ParticleModuleEventGenerator',
            'ParticleModuleEventGeneratorDecal',
            'ParticleModuleEventReceiverBase',
            'ParticleModuleEventReceiverKillParticles',
            'ParticleModuleEventReceiverSpawn',
            'ParticleModuleForceFieldBase',
            'ParticleModuleForceFieldCylindrical',
            'ParticleModuleForceFieldGeneric',
            'ParticleModuleForceFieldRadial',
            'ParticleModuleForceFieldTornado',
            'ParticleModuleKillBase',
            'ParticleModuleKillBox',
            'ParticleModuleKillHeight',
            'ParticleModuleLifetime',
            'ParticleModuleLifetime_Seeded',
            'ParticleModuleLifetimeBase',
            'ParticleModuleLocation',
            'ParticleModuleLocation_Seeded',
            'ParticleModuleLocationBase',
            'ParticleModuleLocationBoneSocket',
            'ParticleModuleLocationDirect',
            'ParticleModuleLocationEmitter',
            'ParticleModuleLocationEmitterDirect',
            'ParticleModuleLocationPrimitiveBase',
            'ParticleModuleLocationPrimitiveCylinder',
            'ParticleModuleLocationPrimitiveCylinder_Seeded',
            'ParticleModuleLocationPrimitiveSphere',
            'ParticleModuleLocationPrimitiveSphere_Seeded',
            'ParticleModuleLocationSkelVertSurface',
            'ParticleModuleMaterialBase',
            'ParticleModuleMaterialByParameter',
            'ParticleModuleMeshMaterial',
            'ParticleModuleMeshRotation',
            'ParticleModuleMeshRotation_Seeded',
            'ParticleModuleMeshRotationRate',
            'ParticleModuleMeshRotationRate_Seeded',
            'ParticleModuleMeshRotationRateMultiplyLife',
            'ParticleModuleMeshRotationRateOverLife',
            'ParticleModuleOrbit',
            'ParticleModuleOrbitBase',
            'ParticleModuleOrientationAxisLock',
            'ParticleModuleOrientationBase',
            'ParticleModuleParameterBase',
            'ParticleModuleParameterDynamic',
            'ParticleModuleParameterDynamic_Seeded',
            'ParticleModuleRequired',
            'ParticleModuleRotation',
            'ParticleModuleRotation_Seeded',
            'ParticleModuleRotationBase',
            'ParticleModuleRotationOverLifetime',
            'ParticleModuleRotationRate',
            'ParticleModuleRotationRate_Seeded',
            'ParticleModuleRotationRateBase',
            'ParticleModuleRotationRateMultiplyLife',
            'ParticleModuleSize',
            'ParticleModuleSize_Seeded',
            'ParticleModuleSizeBase',
            'ParticleModuleSizeMultiplyLife',
            'ParticleModuleSizeMultiplyVelocity',
            'ParticleModuleSizeScale',
            'ParticleModuleSizeScaleByTime',
            'ParticleModuleSizeScaleOverDensity',
            'ParticleModuleSourceMovement',
            'ParticleModuleSpawn',
            'ParticleModuleSpawnBase',
            'ParticleModuleSpawnPerUnit',
            'ParticleModuleStoreSpawnTime',
            'ParticleModuleStoreSpawnTimeBase',
            'ParticleModuleSubUV',
            'ParticleModuleSubUVBase',
            'ParticleModuleSubUVDirect',
            'ParticleModuleSubUVMovie',
            'ParticleModuleSubUVSelect',
            'ParticleModuleTrailBase',
            'ParticleModuleTrailSource',
            'ParticleModuleTrailSpawn',
            'ParticleModuleTrailTaper',
            'ParticleModuleTypeDataAnimTrail',
            'ParticleModuleTypeDataApex',
            'ParticleModuleTypeDataBase',
            'ParticleModuleTypeDataBeam',
            'ParticleModuleTypeDataBeam2',
            'ParticleModuleTypeDataMesh',
            'ParticleModuleTypeDataMeshPhysX',
            'ParticleModuleTypeDataPhysX',
            'ParticleModuleTypeDataRibbon',
            'ParticleModuleTypeDataTrail',
            'ParticleModuleTypeDataTrail2',
            'ParticleModuleUberBase',
            'ParticleModuleUberLTISIVCL',
            'ParticleModuleUberLTISIVCLIL',
            'ParticleModuleUberLTISIVCLILIRSSBLIRR',
            'ParticleModuleUberRainDrops',
            'ParticleModuleUberRainImpacts',
            'ParticleModuleUberRainSplashA',
            'ParticleModuleUberRainSplashB',
            'ParticleModuleVelocity',
            'ParticleModuleVelocity_Seeded',
            'ParticleModuleVelocityBase',
            'ParticleModuleVelocityInheritParent',
            'ParticleModuleVelocityOverLifetime',
            'ParticleSpriteEmitter',
            'ParticleSystem',
            'ParticleSystemComponent',
            },
        'Populations': {
            'PopulationDefinition',
            'PopulationEncounter',
            'PopulationFactory',
            'PopulationFactoryBalancedAIPawn',
            'PopulationFactoryBlackMarket',
            'PopulationFactoryGeneric',
            'PopulationFactoryInteractiveObject',
            'PopulationFactoryPopulationDefinition',
            'PopulationFactoryVendingMachine',
            'PopulationFactoryVendingMachineShift',
            'PopulationFactoryWillowAIPawn',
            'PopulationFactoryWillowInventory',
            'PopulationFactoryWillowProjectile',
            'PopulationFactoryWillowVehicle',
            'PopulationOpportunity',
            'PopulationOpportunityArea',
            'PopulationOpportunityCloner',
            'PopulationOpportunityCombat',
            'PopulationOpportunityDen',
            'PopulationOpportunityDen_Dynamic',
            'PopulationOpportunityPoint',
            'PopulationPoint',
            'PopulationPoint_Dynamic',
            'WillowPopulationDefinition',
            'WillowPopulationEncounter',
            'WillowPopulationMaster',
            'WillowPopulationOpportunityPoint',
            'WillowPopulationPoint',
            'WillowPopulationPoint_Dynamic',
            'WillowPopulationPointDefinition',
            },
        'Skins': {
            'DecalMaterial',
            'LightMapTexture2D',
            'Material',
            'MaterialInstance',
            'MaterialInstanceConstant',
            'MaterialInstanceTimeVarying',
            'MaterialInterface',
            'ScriptedTexture',
            'ShadowMapTexture2D',
            'TerrainWeightMapTexture',
            'Texture',
            'Texture2D',
            'Texture2DComposite',
            'Texture2DDynamic',
            'TextureCube',
            'TextureFlipBook',
            'TextureMovie',
            'TextureRenderTarget',
            'TextureRenderTarget2D',
            'TextureRenderTargetCube',
            },
        'StaticMeshes': {
            'BlockingMeshComponent',
            'CoverMeshComponent',
            'GearboxStaticMeshComponent',
            'InstancedStaticMeshComponent',
            'InteractiveFoliageComponent',
            'SplineMeshComponent',
            'StaticMeshComponent',
            },
        'WillowData': {
            'FastTravelStation',
            'Inventory',
            'LevelTravelStation',
            'OzPlayerJumpPad',
            'OzSupportDrone',
            'OzWillowVehicle_HovercraftVehicle',
            'OzWillowVehicle_JumpWheeledVehicle',
            'OzWillowVehicle_UDKManta',
            'OzWillowVengeanceCannonWeapon',
            'ResurrectTravelStation',
            'SpecialMove_Cloak',
            'SpecialMove_Cover',
            'SpecialMove_Cringe',
            'SpecialMove_Dodge',
            'SpecialMove_FirstAndThirdPersonAnimation',
            'SpecialMove_Motion',
            'SpecialMove_Perch',
            'SpecialMove_PerchLoop',
            'SpecialMove_PerchRandomLoop',
            'SpecialMove_PhaseLock',
            'SpecialMove_PhysicsJump',
            'SpecialMove_PopulationPoint',
            'SpecialMove_Spawned',
            'SpecialMove_SpawnOnWall',
            'SpecialMove_Turn',
            'SpecialMove_Vehicle',
            'SpecialMove_WeaponAction',
            'SpecialMove_WeaponActionOffHand',
            'TravelStation',
            'VehicleSpawnStationPlatform',
            'VehicleSpawnStationTerminal',
            'Weapon',
            'WillowAnimDefinition',
            'WillowArtifact',
            'WillowBuzzaxeWeapon',
            'WillowClassMod',
            'WillowDamageArea',
            'WillowElevatorButton',
            'WillowEquipAbleItem',
            'WillowGrenadeMod',
            'WillowInteractiveObject',
            'WillowInteractiveSwitch',
            'WillowInventory',
            'WillowItem',
            'WillowMissionItem',
            'WillowPendingLevelPlayerController',
            'WillowPlayerController',
            'WillowPlayerPawn',
            'WillowPlayerReplicationInfo',
            'WillowPlayerStats',
            'WillowProfileSettings',
            'WillowPropObject',
            'WillowShield',
            'WillowTurretWeapon',
            'WillowUsableCustomizationItem',
            'WillowUsableItem',
            'WillowVehicle',
            'WillowVehicle_ChopperVehicle',
            'WillowVehicle_FlyingVehicle',
            'WillowVehicle_Tank',
            'WillowVehicle_Turret',
            'WillowVehicle_WheeledVehicle',
            'WillowVehicleBase',
            'WillowVehicleWeapon',
            'WillowVendingMachine',
            'WillowVendingMachineBase',
            'WillowVendingMachineBlackMarket',
            'WillowVendingMachineShift',
            'WillowWeapon',
            'WillowWeaponPawn',
            },
        }


class Category:
    """
    Class to hold info about a single category
    """

    def __init__(self, name, classes):
        self.name = name
        self.classes = set()
        for classname in sorted(classes, key=str.casefold):
            self.classes.add(classname.lower())
        self.id = None

    def __lt__(self, other):
        return self.name.casefold() < other.name.casefold()

    def populate_db(self, conn, curs):
        """
        Populate ourself in the database.
        """
        curs.execute('insert into category (name) values (?)',
                (self.name,))
        self.id = curs.lastrowid


class CategoryRegistry:
    """
    Class to hold info about all the Categories we know about.
    Basically just a glorified dict.
    """

    def __init__(self):
        self.cats = {}
        self.class_lookup = {}
        self.add('Others', set())

    def __getitem__(self, key):
        """
        Act like a dict
        """
        return self.cats[key.lower()]

    def add(self, name, classes):
        """
        Create a new category
        """
        new_cat = Category(name, classes)
        self.cats[name.lower()] = new_cat
        for classname in new_cat.classes:
            if classname in self.class_lookup:
                raise RuntimeError(f'Class {classname} is in more than one category')
            self.class_lookup[classname] = new_cat
        return new_cat

    def get_by_classname(self, classname):
        classname = classname.lower()
        if classname not in self.class_lookup:
            other = self['others']
            other.classes.add(classname)
            self.class_lookup[classname] = other
        return self.class_lookup[classname]

    def populate_db(self, conn, curs):
        """
        Kick off populating the database, once we have the entire set.
        """
        for cat in sorted(self.cats.values()):
            cat.populate_db(conn, curs)
        conn.commit()


class UEClass:
    """
    Class to hold info about a single UE Class.
    """

    def __init__(self, name, category):
        self.name = name
        self.category = category
        self.id = None
        self.parent = None
        self.children = []
        self.total_children = 0
        self.aggregate_ids = set()
        self.num_datafiles = 0

    def __lt__(self, other):
        # BLCMM's historically sorted *with* case sensitivity, but nuts to that.  I've long
        # since come to terms with case-insensitive sorting.  :)  Swap these around to
        # order differently.  (Note that this technically only has bearing on the row
        # ordering in the DB, of course -- the Java app's free to sort however it likes.)
        #return self.name < other.name
        return self.name.casefold() < other.name.casefold()

    def set_parent(self, parent):
        """
        Sets our parent, and sets the reciprocal `children` reference on
        the parent obj
        """
        if self.parent is not None:
            raise RuntimeError(f'{self.name} already has parent {self.parent}, tried to add {parent}!')
        self.parent = parent
        self.parent.children.append(self)

    def display(self, level=0):
        """
        Print out the class tree starting at this level
        """
        print('  '*level + ' -> ' + self.name)
        for child in sorted(self.children):
            child.display(level+1)

    def populate_db(self, conn, curs):
        """
        Recursively populate ourselves in the database.  Intended to be called
        initially from the top-level `Object` class.
        """
        if self.parent is None:
            curs.execute('insert into class (name, category, num_children) values (?, ?, ?)',
                    (self.name, self.category.id, len(self.children)))
        else:
            curs.execute('insert into class (name, category, num_children, parent) values (?, ?, ?, ?)',
                    (self.name, self.category.id, len(self.children), self.parent.id))
        self.id = curs.lastrowid
        for child in sorted(self.children):
            child.populate_db(conn, curs)
            curs.execute('insert into class_children (parent, child) values (?, ?)',
                    (self.id, child.id))

    def inc_children(self):
        """
        Keeping track of how many objects in total are of this class
        type (including objects belonging to a descendant of this class).
        Used to denormalize that info in the DB, to provide some info to
        the user when clicking through the tree.  With our current schema,
        this is probably gonna be ignored entirely 'cause our performance
        for building the trees shouldn't care.  Still, no good reason
        *not* to keep it in here, since we've already implemented it.
        """

        self.total_children += 1
        if self.parent is not None:
            self.parent.inc_children()

    def fix_total_children_and_datafiles(self, conn, curs):
        """
        Store our `total_children` value in the database.  When building the DB
        we process the Classes first, then Objects, but we don't have this
        information until we're through with the Object processing, so we've
        gotta come back after the fact and update the record.

        This also updates `num_datafiles` as well, since that's something else
        we don't know until we've processed objects
        """
        curs.execute('update class set total_children=?, num_datafiles=? where id=?',
                (self.total_children, self.num_datafiles, self.id))

    def set_aggregate_ids(self, ids=None):
        """
        Sets our "aggregate" IDs.  This basically lets us easily know the
        full inheritance path for a given class.  For instance, an
        `ItemPoolDefinition` object is also a `GBXDefinition` object, and
        an instance of the top-level `Object`.  We need to know about that
        because we technically want to show all ItemPoolDefinition objects
        when the user's clicked on GBXDfinition, so having the info
        denormalized is pretty helpful.
        """
        if ids is None:
            ids = {self.id}
        else:
            ids = set(ids)
            ids.add(self.id)
        self.aggregate_ids |= ids
        for child in self.children:
            child.set_aggregate_ids(self.aggregate_ids)

    def store_aggregate_ids(self, conn, curs):
        """
        And here's where we store those aggregate IDs in the database, once we've
        walked the whole tree and generated it.  Note that there's not really much
        call to store this in the DB -- we use the information in this script to
        generate the huge and actually-useful `object_show_class_ids` class, but
        probably nothing in OE will actually query this table.  Still, compared to
        the size of the rest of the DB, this is pretty small potatoes, so we may
        as well store it anyway.
        """
        for idnum in sorted(self.aggregate_ids):
            curs.execute('insert into class_aggregate (id, aggregate) values (?, ?)',
                    (self.id, idnum))

    def store_subclasses(self, conn, curs, from_class=None):
        """
        This table is sort of the inverse of `class_aggregate` -- it lets us know
        (recursively) all subclasses of this class.
        """
        if from_class is None:
            from_class = self.id
        curs.execute('insert into class_subclass (class, subclass) values (?, ?)',
                (from_class, self.id))
        for child in self.children:
            child.store_subclasses(conn, curs, from_class)


class ClassRegistry:
    """
    Class to hold info about all the UE Classes we know about.
    Basically just a glorified dict.
    """

    def __init__(self):
        self.classes = {}

    def __getitem__(self, key):
        """
        Act like a dict
        """
        return self.classes[key]

    def get_or_add(self, name, cat_reg):
        """
        This is here to support dynamically building out the tree from arbitrary
        starting locations; this way we can request parent entries and if they
        don't already exist, they'll get created -- if they *do* already exist,
        they'll just get returned, so we can link up parents/children properly.
        """
        if name.strip() == 'None':
            return None
        category = cat_reg.get_by_classname(name)
        if name not in self.classes:
            self.classes[name] = UEClass(name, category)
        return self.classes[name]

    def populate_db(self, conn, curs):
        """
        Kick off populating the database, once we have the entire tree.  We
        assume that `Object` is the single top-level entry.
        """
        self['Object'].populate_db(conn, curs)
        conn.commit()

    def fix_total_children_and_datafiles(self, conn, curs):
        """
        Once our `total_children` metric has been populated in all the Class
        objects (which happens as we build out the Object Registry), this will
        update the database with all those totals.

        This method now also updates the num_datafiles count as well, since
        that's another thing we can only know after processing objects.
        """
        for class_obj in self.classes.values():
            class_obj.fix_total_children_and_datafiles(conn, curs)
        conn.commit()

    def set_aggregate_ids(self):
        """
        This kicks off calculating the "aggregate" IDs which lets us have a
        shortcut to the whole object inheritance structure.  See the docs
        inside `Class` for a bit more info on that.  We assume that `Object`
        is the single top-level entry.
        """
        self.classes['Object'].set_aggregate_ids()

    def store_aggregate_ids(self, conn, curs):
        """
        Once all our aggregate IDs have been computed, this updates the database
        with the freshly-populated values.
        """
        for class_obj in self.classes.values():
            class_obj.store_aggregate_ids(conn, curs)
        conn.commit()

    def store_subclasses(self, conn, curs):
        """
        Store our subclass mapping information.
        """
        for class_obj in self.classes.values():
            class_obj.store_subclasses(conn, curs)
        conn.commit()


class UEObject:
    """
    Class to hold info about a single UE Object
    """

    def __init__(self, name, short_name,
            separator=None,
            parent=None,
            class_obj=None,
            file_index=None,
            file_position=None,
            ):
        self.name = name
        self.short_name = short_name
        self.separator = separator
        self.parent = parent
        if self.parent is not None:
            self.parent.children.append(self)
        self.class_obj = class_obj
        self.file_index = file_index
        self.file_position = file_position
        self.bytes = None
        self.id = None
        self.children = []
        self.total_children = 0
        self.show_class_ids = set()
        self.has_class_children = set()

    def __lt__(self, other):
        return self.name.casefold() < other.name.casefold()

    def inc_children(self):
        """
        Recursively keep track of how many child objects exist here.  This
        number's primarily just used so we know whether the entry in the
        tree needs to be expandable or not.
        """
        self.total_children += 1
        if self.parent is not None:
            self.parent.inc_children()

    def populate_db(self, conn, curs):
        """
        Recursively inserts ourself and all children into the database, once
        the whole tree structure's been built in memory.
        """
        fields = [
                'name',
                'short_name',
                'num_children',
                'total_children',
                ]
        values = [
                self.name,
                self.short_name,
                len(self.children),
                self.total_children,
                ]
        if self.class_obj is not None:
            fields.append('class')
            values.append(self.class_obj.id)
        if self.parent is not None:
            fields.append('parent')
            values.append(self.parent.id)
        if self.separator is not None:
            fields.append('separator')
            values.append(self.separator)
        if self.file_index is not None:
            fields.append('file_index')
            values.append(self.file_index)
        if self.file_position is not None:
            fields.append('file_position')
            values.append(self.file_position)
            fields.append('bytes')
            values.append(self.bytes)
        curs.execute('insert into object ({}) values ({})'.format(
            ', '.join(fields),
            ', '.join(['?']*len(fields)),
            ), values)
        self.id = curs.lastrowid
        for child in sorted(self.children):
            child.populate_db(conn, curs)
            curs.execute('insert into object_children (parent, child) values (?, ?)',
                    (self.id, child.id))

    def set_show_class_ids(self, ids=None):
        """
        Calculate what Class IDs result in showing this object.  For instance, if
        the user clicks on the top-level `Object`, we'd be showing basically
        everything.  If they click on `ItemPoolDefinition`, we'd want to mark
        all `CrossDLCItemPoolDefinition` and `KeyedItemPoolDefinition` as shown
        as well, since those classes inherit from `ItemPoolDefinition`.  This is
        basically just a big ol' denormalization which we're using to increase
        performance -- it lets us find valid children based on class with a single
        SELECT statement (with just a single indexed join) which should be pretty
        fast even in the worst-case scenario.

        It does come at the cost of database size, though!  During development on
        the BL2 dataset, this increases the uncompressed database size by over
        200MB.

        The has_class_children field is used to assist with the tree rendering
        in BLCMM -- a simple boolean so that the tree-building routines know
        right away whether a UEObject is a leaf or not, so it can skip adding
        a "dummy" entry where one isn't needed.
        """
        if ids is None:
            if self.class_obj is None:
                return
            ids = self.class_obj.aggregate_ids
        else:
            # The only way to get here is if we're a recursive call to a parent,
            # which means that this object has children for this class.  So,
            # mark that down
            self.has_class_children |= ids
        self.show_class_ids |= ids
        if self.parent is not None:
            self.parent.set_show_class_ids(ids)

    def store_show_class_ids(self, conn, curs):
        """
        Once all our shown class IDs have been populated, insert that into the
        database.  Note that for BL2 data, this results in over seven million
        rows in the table!
        """
        for idnum in sorted(self.show_class_ids):
            if idnum in self.has_class_children:
                has_children = 1
            else:
                has_children = 0
            curs.execute('insert into object_show_class_ids (id, class, has_children) values (?, ?, ?)',
                    (self.id, idnum, has_children))


class ObjectRegistry:
    """
    Class to hold information about *all* of our UE Objects
    """

    def __init__(self):
        self.objects = {}

    def get_or_add(self, name,
            class_obj=None,
            index=None,
            position=None,
            ):
        """
        Much like in ClassRegistry, this method assists us in building out the
        tree from arbitrary starting points, so we can re-use parent objects
        when necessary, to keep the tree structure clean.
        """
        if name in self.objects:
            # Fill in some data that could have been left out by building
            # our parent/child tree while looping
            if class_obj is not None:
                obj = self.objects[name]
                obj.class_obj = class_obj
                obj.file_position = position
                obj.file_index = index
                class_obj.inc_children()
        else:
            # Otherwise, we're adding a new object
            split_idx = max(name.rfind('.'), name.rfind(':'))
            if split_idx == -1:
                self.objects[name] = UEObject(name, name,
                        class_obj=class_obj,
                        file_index=index,
                        file_position=position,
                        )
            else:
                parent = self.get_or_add(name[:split_idx])
                parent.inc_children()
                if class_obj is not None:
                    class_obj.inc_children()
                self.objects[name] = UEObject(name, name[split_idx+1:],
                        separator=name[split_idx],
                        parent=parent,
                        class_obj=class_obj,
                        file_index=index,
                        file_position=position,
                        )

        return self.objects[name]

    def get_top_levels(self):
        """
        Returns all top-level objects
        """
        for obj in self.objects.values():
            if obj.parent is None:
                yield obj

    def populate_db(self, args, conn, curs):
        """
        Populates the database once the tree has been constructed
        """
        for obj in sorted(self.get_top_levels()):
            if args.verbose:
                print(f"\r > {obj.name:60}", end='')
            obj.populate_db(conn, curs)
            conn.commit()
        if args.verbose:
            print("\r   {:50}".format('Done!'))

    def set_show_class_ids(self):
        """
        Kicks off the process of deciding which class IDs trigger showing
        which objects.  See the docs in `UEObject` for some more info on
        all that.
        """
        for obj in self.objects.values():
            obj.set_show_class_ids()

    def store_show_class_ids(self, conn, curs):
        """
        Once we have those shown-class-ID attributes set properly, add them
        into the database.
        """
        for obj in self.objects.values():
            obj.store_show_class_ids(conn, curs)
        conn.commit()


def get_category_registry(categories):
    """
    Populate a CategoryRegistry object
    """

    cat_reg = CategoryRegistry()
    for key, values in sorted(categories.items(), key=lambda t: t[0].casefold()):
        cat_reg.add(key, values)
    return cat_reg


def get_class_registry(categorized_dir, cat_reg):
    """
    Populate a ClassRegistry object using the `Default__*` dumps at the beginning
    of our already-categorized dump files.
    """

    cr = ClassRegistry()
    for filename in sorted(os.listdir(categorized_dir)):
        if not filename.endswith('.dump.xz'):
            continue
        class_obj = cr.get_or_add(filename[:-8], cat_reg)
        with lzma.open(os.path.join(categorized_dir, filename), 'rt', encoding='latin1') as df:
            for line in df:
                if line.startswith('  ObjectArchetype='):
                    parent_name = cr.get_or_add(line.split('=', 1)[1].split("'", 1)[0], cat_reg)
                    if parent_name is not None:
                        class_obj.set_parent(parent_name)
                    break

    return cr


def get_object_registry(args, cr):
    """
    Creates our object registry
    """

    max_bytes = args.max_dump_size*1024*1024

    obj_reg = ObjectRegistry()
    for filename in sorted(os.listdir(args.categorized_dir)):
        if not filename.endswith('.dump.xz'):
            continue
        class_obj = cr[filename[:-8]]
        with lzma.open(os.path.join(args.categorized_dir, filename), 'rt', encoding='latin1') as df:
            pos = 0
            cur_index = 1
            odf = None
            new_obj = None
            for line in df:
                if line.startswith('*** Property dump for object'):
                    if new_obj is not None:
                        new_obj.bytes = pos-new_obj.file_position
                    obj_name = line.split("'")[1].split(' ')[-1]
                    new_obj = obj_reg.get_or_add(obj_name, class_obj, cur_index, pos)
                    if odf is None or pos >= max_bytes:
                        if odf is not None:
                            odf.close()
                            cur_index += 1
                        if args.verbose:
                            print("\r > {:60}".format(
                                f'{class_obj.name}.{cur_index}'), end='')
                        odf = open(os.path.join(args.obj_dir, f'{class_obj.name}.dump.{cur_index}'), 'wt', encoding='latin1')
                        pos = 0
                        class_obj.num_datafiles += 1
                odf.write(line)
                pos = odf.tell()
            if new_obj is not None:
                new_obj.bytes = odf.tell()-new_obj.file_position
            odf.close()
        # Break here to only process the first of the dump files
        #break
    if args.verbose:
        print("\r   {:60}".format('Done!'))
    return obj_reg


def write_schema(conn, curs):
    """
    Given a database object `conn` and cursor `curs`, initialize our schema.

    Show all top-level object entries which should be shown for class ID 1683:
        select o.* from object o, object_show_class_ids i where o.id=i.id and i.class=1683 and parent is null;

    Then drill down to a specific entry:
        select o.* from object o, object_show_class_ids i where o.id=i.id and i.class=1683 and parent=604797;
    """

    # Class categories
    curs.execute("""
        create table category (
            id integer primary key autoincrement,
            name text not null collate nocase,
            unique (name collate nocase)
        )
        """)
    # Info about a particular class
    curs.execute("""
        create table class (
            id integer primary key autoincrement,
            name text not null collate nocase,
            category integer not null references category (id),
            parent integer references class (id),
            num_children int not null default 0,
            total_children int not null default 0,
            num_datafiles int not null default 0,
            unique (name collate nocase)
        )
        """)
    # Direct class children, for generating the GUI tree
    curs.execute("""
        create table class_children (
            parent integer not null references class (id),
            child integer not null references class (id),
            unique (parent, child)
        )
        """)
    # "Aggregate" class IDs, allowing us to know with a single query what
    # the whole inheritance tree is.  (For instance, the aggregates for
    # the `AIBehaviorProviderDefinition` class will also include the IDs
    # for `BehaviorProviderDefinition`, `GBXDefinition`, and `Object`.
    curs.execute("""
        create table class_aggregate (
            id integer not null references class (id),
            aggregate integer not null references class (id),
            unique (id, aggregate)
        )
        """)
    # Subclass info -- sort of the opposite of class_aggregate.  Starting
    # from the primary-key class, it lets us know all subclass types as well.
    curs.execute("""
        create table class_subclass (
            class integer not null references class (id),
            subclass integer not null references class (id),
            unique (class, subclass)
        )
        """)
    # Info about a particular object (may not *actually* be an object;
    # this also includes folder-only elements of the tree)
    curs.execute("""
        create table object (
            id integer primary key autoincrement,
            name text not null collate nocase,
            short_name text not null collate nocase,
            class integer references class (id),
            parent integer references object (id),
            separator character(1),
            file_index int,
            file_position int,
            bytes int,
            num_children int not null default 0,
            total_children int not null default 0,
            unique (name collate nocase)
        )
        """)
    curs.execute('create index idx_object_parent on object(parent)')
    # Direct object children, for generating the GUI tree
    curs.execute("""
        create table object_children (
            parent integer not null references object (id),
            child integer not null references object (id),
            unique (parent, child)
        )
        """)
    # The list of Class IDs which this object should show up "under",
    # when selected by Class Explorer
    curs.execute("""
        create table object_show_class_ids (
            id integer not null references object (id),
            class integer not null references class (id),
            has_children tinyint not null default 0,
            unique (id, class)
        )
        """)
    conn.commit()

def main():

    parser = argparse.ArgumentParser(
            description="Populate new-style BLCMM data dumps (for 2023)",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            )

    parser.add_argument('-s', '--sqlite',
            type=str,
            default='data.db',
            help="SQLite database file to write to (wiping if needed, first)",
            )

    parser.add_argument('-c', '--categorized-dir',
            type=str,
            default='categorized',
            help="Directory containing categorized .dump.xz output",
            )

    parser.add_argument('-o', '--obj-dir',
            type=str,
            default='generated_2023_blcmm_data',
            help="Output directory for data dumps",
            )

    parser.add_argument('-m', '--max-dump-size',
            type=int,
            default=10,
            help="Maximum data dump file size",
            )

    parser.add_argument('-v', '--verbose',
            action='store_true',
            help="Verbose output while running.  (Does NOT imply the various --show-* options)",
            )

    parser.add_argument('--show-class-tree',
            action='store_true',
            help="Show the generated class tree after constructing it",
            )

    # Parse args
    args = parser.parse_args()

    # Wipe + recreate our sqlite DB if necessary
    if args.verbose:
        print('Database:')
    if os.path.exists(args.sqlite):
        if args.verbose:
            print(f' - Cleaning old DB: {args.sqlite}')
        os.unlink(args.sqlite)
    if args.verbose:
        print(f' - Creating new DB: {args.sqlite}')
    conn = sqlite3.connect(args.sqlite)
    curs = conn.cursor()
    write_schema(conn, curs)

    # Get category registry
    if args.verbose:
        print('Category Registry:')
        print(' - Generating')
    cat_reg = get_category_registry(categories)
    if args.verbose:
        print(' - Populating in DB')
    cat_reg.populate_db(conn, curs)

    # Get class registry
    if args.verbose:
        print('Class Registry:')
        print(' - Generating')
    cr = get_class_registry(args.categorized_dir, cat_reg)
    if args.verbose:
        print(' - Populating in DB')
    cr.populate_db(conn, curs)
    if args.verbose:
        print(' - Setting aggregate IDs')
    cr.set_aggregate_ids()
    if args.verbose:
        print(' - Storing aggregate IDs')
    cr.store_aggregate_ids(conn, curs)
    if args.verbose:
        print(' - Storing subclass map')
    cr.store_subclasses(conn, curs)
    if args.show_class_tree:
        print('Generated class tree:')
        cr.get_or_add('Object').display()
        print('')

    # Populate objects
    if args.verbose:
        print('Object Registry:')
        print(' - Generating')
    if not os.path.exists(args.obj_dir):
        os.makedirs(args.obj_dir, exist_ok=True)
    obj_reg = get_object_registry(args, cr)
    if args.verbose:
        print(' - Populating in DB')
    obj_reg.populate_db(args, conn, curs)
    if args.verbose:
        print(' - Setting shown class IDs')
    obj_reg.set_show_class_ids()
    if args.verbose:
        print(' - Storing shown class IDs')
    obj_reg.store_show_class_ids(conn, curs)

    # Clean up class total_children counts
    if args.verbose:
        print('Other Updates:')
        print(' - Cleaning up Class total_children counts')
    cr.fix_total_children_and_datafiles(conn, curs)

    # Close the DB
    curs.close()
    conn.close()

if __name__ == '__main__':
    main()


