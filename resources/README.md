As part of data generation for the 2023 opensource fork of BLCMM, we're
loading in all valid Enum values, for autocompleting while writing
mods.  The best way to pull this out of the engine is using the [Enum
PythonSDK library](https://bl-sdk.github.io/mods/Enums/).

At time of writing, though, that library (v1.1, or maybe it's the current
version of PythonSDK that's the problem (v0.7.11)) doesn't fully handle
Enum values which have numeric suffixes.  For instance, for the
`EPacketSizeMultiplier` enum, you'd end up with a bunch of consecutive
`EPSM` values, which should really be `EPSM_4`, `EPSM_8`, etc.

There's no public fix for that yet, though, so instead the new BLCMM
data-generation script just uses an export given to me by apple1417.
Eventually I'd like to get the enum generation done inside DataDumper
itself, alongside everything else, but for now that'll be how it is.

From apple1417, btw, I believe this is the C code which generated
the dump:

    std::wofstream out{"enums.dat"};
    const auto NONE = L"None"_fn;
    auto enum_class = find_class(L"Enum"_fn);
    auto func = enum_class->get<UFunction, BoundFunction>(L"GetEnum"_fn);

    for (const auto& obj : unrealsdk::gobjects()) {
        if (!obj->is_instance(enum_class)) {
            continue;
        }

        out << L"================================\n";
        out << obj->get_path_name() << L'\n';

        for (int32_t i = 0; i < std::numeric_limits<int32_t>::max(); i++) {
            auto name = func.call<UNameProperty, UObjectProperty, UIntProperty>(obj, i);
            if (name == NONE) {
                break;
            }
            out << name << L'\n';
        }
    }


