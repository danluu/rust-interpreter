# Retain programs from a lowering audit

The audit checks each selected test body independently, after ordinary Rust
frontend checking. With `--retain-audit-bodies`, it saves every successfully
validated program for separate execution diagnostics. Collection executes no
guest code and does not establish that a test passes.

The optional `--trap-unsupported-calls` retains strict checking while representing
unavailable direct foreign calls and `catch_unwind` as explicit terminal stops.
Per-body call-site metadata is retained and verified with the artifact. Replay
reports `runtime-unsupported-call` when such a boundary is reached; this is not a
pass. Known supported primitive signatures still require validation, and other
unsupported Rust operations still reject export.

This option raises fre's retained execution evidence to **242/389** bodies:
231 reused with identical bytecode and VM hashes, 11 fresh native/JIT passes,
78 runtime refusals (62 CPU-feature queries, 16 TLS registration), 7 ignored and
62 lowering-blocked. All 11 new passes also run together after real production
edits, including their exhaustive differential test.
[Combined current evidence](results/unavailable-calls-capability-01/summary.md).

```sh
python3 scripts/interpreter.py \
  --manifest-path /absolute/path/to/project/Cargo.toml \
  --package my-crate --test-body --audit-entries names.json \
  --retain-audit-bodies --std-mir
```

`names.json` is a JSON list of distinct function paths. Omit `--std-mir` when the
installed standard-library metadata supplies the needed bodies. The corpus
wrapper `scripts/audit_test_lowering.py` accepts the retention flag too.

Each audit export owns its function/allocation graph. Files have numeric names,
writer-recorded SHA-256 digests, a 64 MiB per-body limit, and a 1 GiB aggregate
limit. An exclusively created pack is referenced only after its files have been
written. The manifest is published beside Cargo's exact metadata artifact.
The launcher verifies the selected pack's names, sizes, hashes, and contents,
including when Cargo reuses cached metadata after a configuration revert.
Incomplete packs are never published as successful results.

Reports include the pack, individual artifact records, selection hash, tool
binary hashes, and selected audit sidecar's hash. Lowering and artifact-retention
time are recorded separately. The launcher reports verification time when
`RUST_INTERP_LAUNCH_STATS=1` is set. Dry audits retain their existing behavior.

The implementation passes 79 focused commands comparing native Rust and both
custom engines, plus all 99 launcher checks and 23,502 native regression commands.
The focused checks cover retained success, panic and Result failure, independent
mutable state, feature/selection/source changes and reverts, uncalled type errors,
damaged or missing files, invalid artifact names, and incompatible options.
The VM binary is identical to the qualified block-linking build.
[Validation](results/audit-builtin-metadata-validation-02.json).

The real Nushell collection retained 162 validated programs totaling
208,783,957 bytes (about 199 MiB); 117 of 279 selected bodies remain blocked.
Artifact retention took 0.532 s and verification 0.081 s within a fresh 68.305 s
command. Compiler-tool bootstrap and reusable metadata-sysroot setup are separate.
These are one collection's measurements, not an execution speedup.
[Collection report](results/lowering-audit-nushell-retained-01/summary.md).

Retained reports classify built-in test descriptors using compiler markers and
resolved attributes. Ignored tests and expected panics are identified, including
cfg-dependent attributes. Unknown/custom harnesses remain unclassified. An
arbitrary VM error cannot substitute for native unwinding. Focused tests cover
these distinctions and confirm that classification itself executes no bodies.

For a retained corpus collection, run the ordinary-test execution survey with:

```sh
python3 scripts/survey_audit_execution.py \
  --collection results/lowering-audit-fre-retained-01/summary.json \
  --run-id my-fresh-execution-survey
```

Use `--entries names.json` to select a subset of the verified collection, or
`--vm-tool-key <64-character-key>` to execute it through a different installed
immutable VM. The original collection's tool hashes, sidecar and bytecode pack
are verified independently of the execution build. Reports record both tool
identities; replay does not perform lowering with the alternate exporter.
Two real fre bodies pass with the original and alternate VM, and malformed
tool keys are refused before native builds or execution.
[Replay validation](results/audit-vm-override-validation-01.json).

The fre collection classified all 389 entries and retained 198 ordinary tests.
All 198 passed against fresh native controls: 189 at 100 million instructions,
eight more at 10 billion, and the last at 100 billion. The last actually used
17 billion instructions and took 11.084 s in the JIT versus 0.541 s natively.
191 bodies remain blocked; these include all seven ignored tests, none of which
executed. This is partial suite coverage, not an edit/build speedup claim.
[Combined execution evidence](results/audit-execution-fre-combined-01/summary.md).

Subsequent SIMD lowering changes raise retained execution evidence to **231**
ordinary fre tests, with **158** bodies still blocked. All new or changed programs
were compared again with fresh native controls; programs reused from prior runs
have identical bytecode and VM hashes. Each phase distinguishes fresh execution
from verified reuse. [Current capability evidence](results/simd-ordered-capability-01/summary.md).

`audit_test_lowering.py --inline-leaves` collects programs with the experimental
leaf inliner enabled. Collection and execution reports record that choice.
All **231** supported ordinary fre tests were freshly compared with native
executions using transformed bytecode; **158** remain lowering-blocked. The
survey used an explicit 100-billion-instruction limit. This is correctness
coverage for the option, not a full-suite or performance claim.
[Transformed collection](results/lowering-audit-fre-leaf-inline-01/summary.md),
[fresh execution](results/audit-execution-fre-leaf-inline-01/summary.md).

The native-fill and deterministic-export build repeats the collection and all
231 native/JIT comparisons freshly, again leaving 158 lowering blockers. The
collection and execution identities are recorded separately.
[Fresh collection](results/lowering-audit-fre-export-order-01/summary.md),
[fresh execution](results/audit-execution-fre-export-order-01/summary.md).

Nushell's older 162-body pack lacks built-in metadata. Its custom harness supplies
environment, experimental-option, and dependency settings. Those need an explicit
adapter; no claim is made that the 162 retained bodies pass.

The explicit `--run-try-callbacks` option requires `--trap-unsupported-calls` and
allows the normal-return path of `catch_unwind` to execute. Actual panic, unwinding,
and VM faults still fail; this is not support for expected-panic tests. Collection,
artifact sidecars and execution reports record this option independently. It is
needed by the current guest std TLS cleanup path. The fresh complete fre survey
passes 320 bodies with 62 lowering blocks and 7 ignored tests.
