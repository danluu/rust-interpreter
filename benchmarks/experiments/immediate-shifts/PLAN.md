# Direct immediate shifts and rotations

Start from adopted main fb0b363. Current same-process samples place92.86% of
the dominant block window in generated code; SipHash rounds and regex
determinization are hot regions. Rotates already run natively, but known
counts still use the register-count masking/negation path. This candidate
selects direct AArch64 immediate shifts/rotates when the existing fact table
proves the count. No broader constant propagation or memory-model change.

Preserve the full count's modulo-width behavior, input/output masking, signed
right shift, zero overflow and value-before-overflow assignment under aliasing.
Use immediate shifts at validated widths through64, and immediate rotates
only at32/64; retain the existing narrow-rotate and128-bit paths. Immediate
facts remain higher priority than assigned native registers. Do not drop
logical bytecode steps, budget checks, full register writes or fault guards.

Qualify exact encodings, all count residues/upper count bits, signed values,
aliased destinations, full-width output initialization, ordinary/resumable
modes, persistent registers and instruction-budget tails. Expect432 workspace
tests per profile (one ignored), including four new boundary tests. Build with two Cargo
workers under the45-second shared lock and8GiB floor, preserving the exact
adopted exporter/wrapper e729a493 for runtime comparison. Reuse owned host
build caches. Then verify saved real selections/suites and exact per-PC counts,
memory and entropy before any timing. Freeze source and protocol inputs.

The next timing step is a40-command screen: one original/wrong/five valid/
restored token history, five modes (ordinary native, adopted custom baseline,
A/A duplicate, candidate, retained fixed custom anchor). Two Cargo workers,
two prepared custom workers, original12 assertions/guest flags/limits, matched
cache policy and toolchain lookup for baseline/duplicate/candidate. Rotate
custom order and alternate native placement, with every command retained.
Only the five valid edits contribute to paired wall/CPU medians. Record the
maximum absolute duplicate/baseline deviation as this screen's descriptive
A/A envelope. Freeze executable schedule and stopping rule before running.

Admission to a full comparison requires candidate/baseline paired wall ratio
below1 minus the observed wall envelope, candidate/baseline CPU ratio<=1, and
CPU ratio plus its envelope<=1.05. Report fixed-anchor and native ratios,
but do not credit already-adopted gains as this candidate's improvement.
Failure or inconclusive noise stops unstarted guards; do not repeat the screen.
A passing screen is only a reason for a prospective full adoption comparison
with all declared guards. There is no adoption verdict from this screen.

This may be a small component. A later compatible bundle is allowed with an
explicit new source manifest, without adding historical ratios or reviving an
unchanged failed candidate. The binding observer showed only4.83ms immediate
indexing, so the cache positions-table rewrite is not part of this candidate.
