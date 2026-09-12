# Complete-command constant-folding screen

Freeze this recipe before timing. Compare `constant-fold-compose-02` with
`suite-profiling-build-02` (c013f239); VM and wrapper bytes are identical.
The candidate changes only the checked exporter, applying the bounded folder
and another CFG cleanup after the retained pipeline. It has passed 366 Rust
tests per profile and the nine-test standalone native/custom fixture. Validate
fixture tool identities and the saved-artifact diagnostic before launching.

Run `screen.py --case token --run-id constant-fold-screen-token-01` with all twelve
`token_phrase::tests::` tests from pinned fre e0df0b0. Use the same five cumulative
production-body edits in workflow_cases.py: name the literal-finder result, reuse
short-count input length, reuse short-span input length, orient the short-route
width comparison, and match the short-route event bound. Keep all assertions and
the wrong-edit control. The shared source-state generator rotates mode order;
original/wrong/restored states remain outside the five measured pairs.

Use two Cargo workers and repository profiles in every mode. Native runs one
process per test. Custom modes use strict checked MIR, MIR level 3 and inline
scale 8, existing leaf inlining, prepared test isolation, resumable calls,
persistent registers, 100 billion instructions and 150,000 allocations per test.
Create separate fresh native/check/control/candidate caches. Every measured
command must follow a source content change. Record whole-command wall/CPU,
stages, selected outcomes, source transitions and artifact/catalog/selection hashes.

The compiler can change instruction count, PCs and branches. After each source
state, outside timing, require complete candidate bytes to equal typed folding
and CFG cleanup of the control artifact. Preserve all layouts/data and retain
checks required for the resulting artifact. A verification mismatch stops the
screen. All original native and custom assertion outcomes must match.

Require the median of five paired candidate/control wall ratios <=0.90 and CPU
ratios <=1.00. Otherwise park without retiming. Only after a pass, run separate
folded and pgrust five-edit guards with established limits, requiring both ratios
<=1.05. Broader projects follow only after these gates; this screen alone is not
an adoption result.

Hold the global lock with a 45-second wait. Admit fre at 9.5 GiB free, pgrust at
8.3 GiB, and require 8 GiB before each child. The 7 GiB allowance used by tiny
host/standalone correctness fixtures does not apply to these real projects.
Restore source on every ordinary exit and preserve raw evidence. Resource or
harness stops remain incomplete screens, never performance passes.
