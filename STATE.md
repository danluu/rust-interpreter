# Current state — September 18, 2026

Manual optimization continues indefinitely. The saved goal remains paused.
The task is a general custom Rust interpreter/direct AArch64 JIT, guided by
real changed-source build/test commands across small and large projects.
Private repository: `danluu/rust-interpreter`. Qualified changes go to main.

The scratch-value/scalar-call composition is adopted with the current compiler.
It combines bounded scalar native calls and private value transfers with reuse
of checked memory values still held in x9. Writes, aliases and register clobbers
invalidate reuse conservatively. Type and borrow checking finish before guest
execution; partial-demand artifacts cannot use the scalar calling path.

Use explicit `--jit-scalar-calls --jit-resumable-calls
--jit-persistent-registers`, prepared isolation and the measured two-worker
configuration. The 16 MiB default arena remains. There is no LLVM, Cranelift or
foreign-interpreter fallback for guest execution.

All five predeclared performance guards pass across 726 complete commands:

| Selected workload | Wall / previous custom | Wall / ordinary native |
| --- | ---: | ---: |
| fre token | 0.9370 | 1.5714 |
| fre folded matching | 0.9689 | 0.9181 |
| pgrust hashfn | 0.9939 | 0.8466 |
| private rg-aot | 1.0048 | 0.4097 |
| Nushell type-relations | 1.0000 | 0.6363 |

Token improves 6.30% wall and 6.51% child CPU, beyond 1.41% wall A/A variation.
Folded improves 3.11% wall. Differences for pgrust, rg-aot and Nushell establish
no speedup over the previous custom runtime. These are complete changed-source
commands, with 15 valid edited pairs per case. Wrong edits and restoration
retain their original assertions. The two independent 88-command full-parser
histories also pass: 114 original tests, no established parser speedup, and
1.140× native wall under the repository profile / 1.263× matched incremental.
[Full results and limits](results/scratch-memory-values-full-01/ASSESSMENT.md).

Qualified tool `df4006e0` preserves measured VM `6ac4dd9e`, exporter `cf4b3499`
and wrapper `45bca4f2`. All Rust/Cargo/configuration inputs match the measured
candidate. The integration retains main's optional runtime-compiler validation
and restores the scalar launcher test; 407 merged Python tests pass, 22 declared
compiler/native tests are skipped. The closure binds 1,460 source files.
Prior 608 workspace tests per profile (13 ignored), 121 strict/cache commands,
six exact profiles, 13 original selected/prepared controls, the full-parser
compatibility and performance histories are reused through exact source/binary
and closed-evidence bindings. The integration repeats no guest timing.
[Integration](results/scratch-scalar-main-qualification-01/assessment.md).

This is still a selected-function/test-body engine. Complete Rust application,
libtest, thread/OS/FFI and real unwinding support remain open. The parser and
token native gaps still guide optimization; no complete database/shell coverage
or isolated scratch-cache speedup is claimed.

The current manual branch is `experiment/runtime-composition-20260918`.
Main still adopts df4006e0; the new runtime remains experimental. Main4b6ec8bf
published only the separately qualified std-MIR device-readmission repair,
preserving peer compiler work. Re-fetch main when integration is actually admitted.

The prospective composition combines native indirect transitions, checked readonly
scalar leaves and successor-only spilling on the adopted scratch/scalar runtime.
Its immutable tool45a1529e / VMfd21a46f keeps exporter cf4b3499 and wrapper45bca4f2.
Qualification passes666 Rust tests per profile (25 ignored),421 Python tests
(22 declared skips),122 strict/cache commands, six fresh matched profiles,
26 fresh selected/prepared compatibility commands and25 full-protocol controls.
Strict type/borrow checking remains mandatory, including unreachable errors and
rejection of partially checked artifacts before scalar/indirect execution.

The original std-MIR manifest is unchanged. Its26 artifact hashes matched after
a device-number change; separate readmission receipts verify current identities.
The historical profile comparison failed on18 extra CPU-feature-detection
instructions. A fresh adopted VM reproduced the exact same path as candidate;
six fresh profiles then matched every original PC, memory peak and entropy count.
Preserve the original failure; never mask counts or use entropy replay for timing.

The40-command primary passes: wall0.96398368, CPU0.95353329, wall A/A2.221367%.
No primary pair is reused in the full campaign. The fresh full comparison now
has five closed passing project cases and726 commands, with15 valid edited pairs per case:

| Case | Commands | Wall / adopted | CPU / adopted | Wall A/A | Wall / native |
| --- | ---: | ---: | ---: | ---: | ---: |
| token |154|0.96769033|0.96381150|2.728848%|1.59822459|
| folded |154|0.97865347|0.98459988|1.057504%|0.98477876|
| pgrust hashfn |154|1.00313849|1.00271664|1.826877%|1.04813587|
| private rg-aot |132|1.00143096|1.00207350|2.353175%|0.56640976|
| Nushell type-relations |132|0.99990634|0.99738674|1.674626%|0.62010914|

Token passes narrowly. Pgrust/private differences are within control variation
and establish no incremental gain. Current native ratios are from these matched
histories; do not substitute older, more favorable hardware/run ratios. All
original assertions, wrong-edit outcomes, paired bytecode/catalog identities,
frozen inputs and source restoration pass. The first full setup failed after
two original-state commands due to a copied scalar-option assertion; it had no
edited pairs and remains archived. All02 case namespaces are independent of it.

The five-project campaign is complete. Nushell supervisor82525, child82528,
started September18 at15:36 and finished normally at16:01 with132 commands.
Its wall ratio0.99990634 and CPU0.99738674 establish no incremental speedup;
wall/CPU noise-inclusive margins1.01665260/1.00274318 pass the1.05 limits.
The full726-command final audit passes9,290 unique frozen inputs. A separate
project closure binds122 source inputs and explicitly leaves parser guards
pending and runtime adoption false. No final-audit recovery was needed.

Parser compatibility passes all114 original tests under supervisor9983,
child10069 (runtime-composition-parser-admission-02), with6,798 frozen inputs.
Its closure verifies6,801 bindings including three original admission records.
The first supervisor83909/child83912 expired at45seconds before preflight or any
guest. Retain that admission failure and the two no-mutation closure failures.
Batched audit runtime-composition-pending-evidence-01 (supervisor57715/child57718,
source60d6a01e) closed compatibility and current Nushell cache retirement;
it ran no new guest or deletion. Both checks passed normally.

The16 parser protocol controls pass and are closed with120 source inputs
(source7e10588f; supervisor60793). The first88-command parser history is launched:
runtime-composition-parser-edits-incremental-01, supervisor87894/child87897,
September18 at16:13:49. Its benchmark sources are unchanged and committed in
93ab825c. Check actual status/records; do not infer completion. Repository-profile
history remains unstarted and requires the completed passing incremental guard.
Fresh free space is28.64GiB at16:14. Require24GiB initially and8GiB before every
command, with two Cargo/prepared workers and normal entropy.
Preserve all scripts and frozen runtime-composition-full/parser inputs through
histories and final closure;840eee0c binds the unchanged full controller sources.

Token/rg-aot supervisors ended normally. Folded/pgrust case controllers also
finished normally, but their outer post-case audits timed out on the shared lock.
Audit-only recovery verified all existing measurements and repeated none.
Checkpoints2/3 originally included a reference to the growing live campaign ledger;
their immutable ledger copies were intact. The closed supplemental repair resolves
those references through exact original hashes, preserving all original receipts.
Use each case's checkpoint-evidence-repair.json when auditing those older closures.
Checkpoint4 remains historical evidence; the final project closure supersedes
its next-case state. No peer process was altered.

Current Nushell custom caches were retired only after project closure and actual
free space fell below parser admission. Supervisor96627/child96630 completed
normally:33,924 files,12,730,891,710 logical bytes removed;20,095 protected hashes
unchanged. Observed free space rose from23,032,410,112 to31,306,891,264bytes.
The batched closure rechecked every removed path and protected hash. Source
ac3618f3 binds the deletion controller; never repeat this retirement. All native,
parser, private, shared-target and peer caches remain untouched. Neither cleanup
nor project closure admits adoption. Final-audit recovery remains unused.

Both separate88-command parser histories, incremental first and repository
second, remain required after the passing compatibility/protocol. Stop the
unstarted successor on any failed guard. The three terminal-parser-decision
controls already pass and are closed. The final closure handles a failed parser
guard without relabeling the project result and binds its own helper sources.
Final close_campaign.py and current-main integration still require the parser
results. Last inspected main237510c3 includes2ba26966 (bounded leaf scans, shared
call-graph facts and exporter summary CFG), plus091f9ea9 (runtime collision
ancestor scans). Preserve those Rust/launcher changes and qualify the merged
binaries, full contracts, strict/cache paths and a newly declared matched
changed-source comparison; frozen timings do not qualify that new combination.
[Integration plan](docs/RUNTIME-COMPOSITION-INTEGRATION-20260918.md).

Disk cleanup is complete and closed for the current Nushell group above and
three earlier exact public cache groups:
old scratch/scalar Nushell custom namespaces (33,924 nonexecutable files;
20,002 protected hashes unchanged), current full-token caches (13,304 files;
3,389 protected hashes unchanged), and current full-folded caches (13,304 files;
3,392 protected hashes unchanged). Never repeat those retirements. An old
repository-parser attempt found zero eligible files and removed nothing; its
failed/no-removal receipt is retained. All executables, installed tools, bytecode,
suites and recorded evidence remain. Shared target, private and peer caches
were excluded. Cleanup's logical bytes differ from observed free-space changes.
The independent monitor is reporting fresh five-second samples again; its
latest status warns below32GiB. Use fresh admission checks without controlling it.

Previous isolated indirect, readonly and successor-flush candidates remain parked
under their original failed gates; the new composition does not relabel them or
establish additive gains. Recent disabled censuses also remain deferred: ordinary
code generation is66–114ms; immutable reads and guarded-value forwarding have
little sampled coverage; smaller range guards cover14/0/0 samples; confined scalar
call chains cover no selected Call/Return samples; four external capture slots
cover15/0/0 samples before their own costs. Do not repeat these unchanged probes.
After qualified adoption, fresh owned native-PC sampling should choose the next
runtime target. The sampler needs explicit indirect-option forwarding and the
current observation validator before it can profile the new configuration.

[Primary](results/runtime-composition-screen-token-01/ASSESSMENT.md),
[token](results/runtime-composition-edit-token-02/ASSESSMENT.md),
[folded](results/runtime-composition-edit-folded-02/ASSESSMENT.md),
[pgrust](results/runtime-composition-edit-pgrust-02/ASSESSMENT.md),
[private aggregate](results/runtime-composition-edit-rg-aot-02/ASSESSMENT.md),
[Nushell](results/runtime-composition-edit-nushell-02/ASSESSMENT.md),
[all five projects](results/runtime-composition-full-02/ASSESSMENT.md).

The compiler/Cargo/parser-exporter investigation belongs to the other session.
Preserve its worktrees and all user-owned processes. Keep the global benchmark
lock, two Cargo workers, the shared owned build target, conservative reservations
and the 8 GiB child floor. The disk monitor is read-only for this task; do not
start a competing repair or cleaner. The saved goal stays paused while manual
optimization continues.

The September 13 12:45 suggestions were re-read on September 18 and their SHA
remains unchanged: 4d74b3dc8b79ad7655a153c8aaf7485677e4bbe677b5a7bc7bec683a3da80c2f.
[Review and dispositions](docs/SUGGESTIONS-REVIEW-20260913-1245.md).
