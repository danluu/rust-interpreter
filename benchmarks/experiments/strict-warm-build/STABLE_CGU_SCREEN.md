# Stable codegen-unit grouping mechanism screen

The `stable-cgu` policy compares one complete installed custom compiler and one
matching exporter/wrapper/VM build with grouping off, on, and off in the three
independent cache arms. A public compiler versus a differently built custom
compiler is not the baseline for this experiment. Compiler build profiles and
actual tool identities belong in the retained installation/build receipts.

Prepare standard-library MIR in both `stable-cgu:off` and `stable-cgu:on`
namespaces before the screen. These use the same compiler and existing metadata
flags; native CGU grouping is not applied during that metadata preparation.
The launcher records the actual std key, sysroot and target, and the screen
checks that each command used its prepared namespace. Project compiler policy
goes through the wrapper to both native host and explicit guest invocations.

Use `screen.py --candidate-policy stable-cgu`, the same value for
`--baseline-tool-key` and `--candidate-tool-key`, the installed `--compiler-key`,
`--std-mir-ready` for the off namespace, and `--candidate-std-mir-ready` for the
on namespace. Custom compiler arguments are rejected for the older policies,
whose distinct-tool requirement remains unchanged. Installed-tool/compiler
association and immutable compiler provenance are verified before any source
mutation and again by the timed launcher.

The existing protocol, all 27 commands, all 14 original tests, five fresh
cumulative edits, wrong-result control, recovery and final restoration remain
unchanged. Complete command wall time includes launcher validation, Cargo, all
required compiler/build-script work, VM preparation and test execution. Native
partitioning should leave interpreted bytecode and catalogs identical, which
the screen continues to require. No Cargo optimization is enabled in this
comparison. This is a mechanism screen, not final latency or holdout evidence.
