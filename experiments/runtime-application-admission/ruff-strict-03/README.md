# Strict Ruff platform-identity successor03

Source-only proposal. No preparation freeze or workload has run. Earlier01 and02
are preserved exactly as unrun proposals whose complete-uname guard is unstable:
the observed nodename changed from MacBook-Pro-2.local to Mac and back while the
kernel fields, file identities and bytes remained unchanged.

The new runtime_platform.py policy binds sysname, release, version and machine
under an explicit policy tag. It rejects missing/extra identity keys, malformed
observations and any change in those four fields. Nodename is retained as context
in the preparation plan and every actual guard observation in the supervised
receipt. It is not passed to the compiler or rewritten to a preferred value.
The copied runtime_admission_v3.py changes only this platform comparison and
context recording; all frozen-source, executor, provider, configuration,
runtime/std/tool byte checks and owned supervision remain.

The exact six tests are registry::tests::{documentation, rule_naming_convention,
check_code_serialization, linter_parse_code, rule_size, linter_sorting}. They
iterate source-defined registry values, static documentation strings, compiled
naming patterns, code conversions, type size and sorted names. No assertion
consumes a hostname. Generated explanation functions return static doc literals.
The explicit launch environment contains no HOSTNAME variable and the selected
launcher/runtime/shared-std routing does not query uname or hostname. Exact
reviewed sources and limitations are recorded in hostname-review.json. This is
not a proof that arbitrary dependencies, compilers or other applications never
observe hostnames; actual strict behavior remains necessary.

The recipe remains the same sixteen HIR-off/on calls, five cumulative real
edits, wrong-edit assertions, restored source and six unchanged tests. Both
compatibility switches remain absent; source/dep-info/argv/bytecode and missing
.calls.json checks remain. Each mode has a fresh owned cache under
.work/ruff-runtime-strict-03. Admission remains16/9/8 GiB, canonical600 seconds,
6GiB total owned work. Incremental-info instrumentation remains, so this is
correctness and diagnostic evidence, not timing qualification.

The preparer rejects any changed prior frozen input or provider
stamp, revalidates full R/std/tools and Ruff source inventory, then would create
a distinct exact proposal. It has not been invoked. Five pure policy controls
in ../test_runtime_platform.py passed under exact launch11d4205f; their actual
receipt, raw streams, source closure and independent readback are required inputs
to this proposal. No Ruff workload has run.
