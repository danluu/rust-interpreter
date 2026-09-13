# Scalar Copy memory operands

Base: main dd1f55f, qualified operation-map runtime d4a6ff9a (436 tests per
profile), with the adopted e729a493 exporter/wrapper. Direct operands and
immediate shifts remain parked. The latest suggestion review and same-process
operation samples identify scalar Copy as a bounded next target.

For Copy widths1/2/4/8/16, reuse the existing proven local-frame scaled
memory operands. Share the host frame base when both endpoints qualify.
Retain source-before-destination checks and validate both complete ranges
before loading or writing. Load all bytes before any store for memmove
semantics, including both words of a16-byte value. Omit the unused high-word
clear for narrow copies. Preserve forwarding, live values, cache replacement
order and exact overlap invalidation. Zero, irregular widths and larger copy
paths retain their code. No allocation/address cache or memory-model change.

Expect441 workspace tests per profile, one ignored. New checks cover exact
encodings at immediate boundaries, unchanged checked/irregular fallback code,
full stack/heap bytes across local/unknown endpoints and overlap directions,
faults without partial writes, live wide values across calls, every small
budget, exact logical PC counts and zero-code-capacity fallback. Existing
forwarding and unknown-alias tests remain mandatory. Build runtime only,
two Cargo workers,45-second shared lock admission,8GiB floor. Freeze source
before building and do not change it during qualification or comparison.

Run seven saved real selections, nine suites,203 strict native/cache checks
and three current profiles with identical logical work, peak memory and
entropy. Require smaller primary generated code and no code growth on the
three profiles. The optional map must still reconstruct emitted bytes exactly.

Before timing, freeze an adapted40-command token screen against d4a6ff9a and
its duplicate, plus fixed anchor fe9dcae0 and ordinary native. Retain all12
original assertions, strict type/borrow checks, cached lookup, automatic
function reuse and two prepared workers. Five valid changed-source pairs
enter medians; initial and restored controls do not. Gate: candidate/baseline
wall<1-AA wall, CPU<=1, CPU+AA CPU<=1.05. A/A is maximum absolute individual
duplicate/baseline deviation. No repeat or splicing of screens. Failure parks
the candidate and cancels unstarted guards. Success requires a separately
frozen full primary-first comparison of token, folded, pgrust, private rg-aot
and Nushell, with all five gates required. Retain same-session native and
line-tables controls, fixed anchor and per-case storage admission. A smaller
instruction sequence or passing screen is not adoption evidence.
