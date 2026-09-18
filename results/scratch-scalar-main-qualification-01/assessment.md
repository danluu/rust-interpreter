The scratch-value/scalar-call composition is qualified for adoption on main.
The integration preserves main's optional runtime-compiler prepublication
validation and its newer tests. The scalar-option launcher test omitted from
the initial integration commit was restored before running the merged suite.
All 407 executed Python tests pass; 22 declared compiler/native tests require
explicit tool fixtures and were skipped. The suite discovered 429 tests.

Every Rust/Cargo/configuration input matches candidate `b462d9e6`; the build
manifest's 214 Rust/Cargo inputs are unchanged. The stock launcher and all
production Python scripts match that candidate except `runtime_compiler.py`,
which matches main `701cc006` and is not imported by the stock route. Installed
tool `df4006e0` retains VM `6ac4dd9e`, exporter `cf4b3499`, and wrapper `45bca4f2`.
The closure binds 1,460 current source files to integration revision `7082378a`.

The source and binary equality permit reuse of the closed 608 Rust tests per
profile (13 ignored), 121 strict/cache commands including type/borrow errors and
scalar rejection of a partial-demand artifact, six exact original profiles,
13 selected/prepared controls, 114 original parser tests, 726 performance
commands and two 88-command parser histories. Their summaries, terminals, raw
records and source/evidence manifests were checked. These are retained prior
executions; this integration adds one Python-suite command and no guest timing.
The complete retained histories were audited at their original closures; this
integration does not claim to rehash every multi-gigabyte guest artifact again.

The [full comparison](../scratch-memory-values-full-01/ASSESSMENT.md) improves
token wall/CPU by 6.30%/6.51% and folded wall by 3.11%. Pgrust hashfn, rg-aot and
Nushell differences remain within observed variation. Token still takes 1.571×
ordinary native wall time; full-parser wall remains 1.140× native in the
repository profile and 1.263× with matched incremental compilation. These
results cover selected subsystems and test bodies, not arbitrary Rust programs
or complete database/shell compatibility. They measure the scalar-call and
scratch-value composition together, not the isolated scratch-cache effect.

Use explicit `--jit-scalar-calls --jit-resumable-calls
--jit-persistent-registers` with the qualified prepared-worker configuration.
Keep ordinary type/borrow checking, normal entropy, two Cargo workers and the
16 MiB arena. Unsupported guest code has no foreign interpreter/JIT fallback.
Next collect owned samples on this exact VM before choosing another mechanism.
