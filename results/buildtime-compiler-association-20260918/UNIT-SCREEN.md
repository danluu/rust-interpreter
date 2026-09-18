# Association Python correctness controller

Source-only preparation; no controller/test/production import or workload ran.
The script uses the separately owned launcher-association tree C3 at 2ba26966,
with exact proposal-v2 patch 932e88bd and source bindings 5770f3a8. The active C
and C2 trees and all timing-controller files are untouched.

Eight source-audited modules, each with one direct unittest.TestCase class:

| Module | Expected test methods |
| --- | ---: |
| compiler_association | 3 |
| custom_compiler | 13 |
| custom_compiler_launcher | 6 |
| runtime_tools | 10 |
| custom_cargo | 7 |
| std_mir_source_paths | 18 |
| interpreter_tools | 5 |
| interpreter_build_metrics | 19 |
| Total | 81 |

These are expected source counts, not passes. No selected class inherits another
test class. runtime_tools borrows only fixture setup, launch and process-stub
methods, so it does not inherit the fixture's six tests. Imported fixture modules
are module objects or helper functions, not imported TestCase class aliases.
No selected module defines load_tests or a skip/expected-failure decorator.
The controller checks source counts before execution and requires exact observed
unittest totals, an individual `... ok` line for every expected test, final OK,
and exit zero. Skips, expected failures, incomplete modules and errors cannot pass.

Fixture process-boundary audit:

- compiler_association uses only temporary manifests, real file guards and one
  patched read failure. The oversized manifest is sparse and rejected before read.
- custom_compiler.fake_install patches all compiler check_output probes and the
  macOS library audit. Its direct Mach-O audit tests patch check_output themselves.
- custom_compiler_launcher uses fake_install, a setUp subprocess.run stub for
  Cargo/VM, patched std Popen and custom-tools capture/capability probes.
- runtime_tools borrows that same stubbed launcher setup, replaces selected runtime
  lookup and rejects fallback to stage2. Its prepared-std calls are patched.
- custom_cargo creates synthetic qualified reports/binaries; library closure is
  patched at installation, Mach-O probes are patched, launcher run is patched,
  and std fetch/Popen/compiler identity are patched.
- std_mir_source_paths uses fake source/metadata trees and patched compiler/Cargo
  identities, acquisition/space checks and capture. Native preflight and metadata
  compilation are synthetic capture return values with retained fixture receipts.
- interpreter_tools substitutes subprocess.run at setUp, writes synthetic installed
  files and returns synthetic capability output.
- interpreter_build_metrics patches launcher subprocess.run before launch and uses
  fake CPU/wall values only to test metric boundaries. Its new stock-import guard
  rejects custom implementation imports even when already cached. No fixture clock
  value or test process timing is performance evidence.

No existing workflow test directly asserts bench_e2e_workflow's frozen script
inventory, so unrelated workflow tests are not added. The controller statically
checks that the exact script_paths AST includes scripts/compiler_association.py;
it neither imports nor invokes the benchmark workflow.

All 186 top-level scripts/tests Python sources, six exact proposal copies,
proposal README/patch/bindings, pinned Homebrew Python3.14 executable/framework,
source manifest and controller are bound before and after. Each module runs in a
fresh isolated Python child with -I -S -B, no user site or bytecode writes, fixed
HOME and an exclusive private TMPDIR. Every module receives a fresh memory probe.
Expected controller children are eight memory probes and eight unittest processes.
No extra compiler/Cargo/VM process is authorized by this controller.

Resource/process controls are reused from reviewed tool-bin unit controller
227f239f: shared benchmark lock, 16 GiB synthetic-Python-only disk floor and30%
memory threshold, fresh per-child checks, file logs with1 MiB readers, exact PID/
argv/cwd/env/start/terminal records, read-only five-second disk observations while
waiting, and finally-path sole-wait4 settlement. No signals or shared cleanup.
The separate32 GiB Rust workload gate is unchanged. Source preparation uses a
fresh >16 GiB check before writes. Failure preserves the fresh attempt without
retry; future root execution requires independent source review and admission.

Future command (not executed):
 /usr/bin/python3 run-unit-tests.py --execute-synthetic-unit-tests
