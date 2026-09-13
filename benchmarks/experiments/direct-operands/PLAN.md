# Direct operands for modular operations

Base: adopted runtime at main3fef4b8. The immediate-shift candidate remains on
its experimental branch after its complete40-command screen found no gain.
This candidate does not contain that emitter change. Current adopted-code
samples place most token runtime inside generated native regions. SipHash
rounds and regex determinization contain many Binary operations.

Use the existing native source registers directly for Add/Sub/Mul and
And/Or/Xor at8/16/32/64bits. Arithmetic qualifies only when the existing read
analysis already treats its overflow output as unobserved. For these modular
operations the low result bits depend only on low input bits, so keep the
final width mask and omit the two input masks. Bitwise overflow remains zero.
Preserve fact precedence over assigned registers, live-in bookkeeping and
cache recency. Known zero low words use the zero register; all other facts
materialize normally. Fetch both operands before computing into x9 and
publishing outputs in the original value-then-overflow order.

No change to register allocation, value storage, full register writes,
fault checks, logical guest steps or budget tails. Observed arithmetic,
comparisons, shifts, division and128bit operations retain the original path.
Qualify exact encodings and no-side-effect rejection; fact/cache/physical
operand selection; native Rust integer oracles with dirty upper bits;
source/destination/overflow aliases and checked arithmetic fallback; source
preservation across loop backedges and native calls; every small instruction
budget with exact per-PC counts. Use ordinary/resumable modes and persistent
registers on/off, plus an interpreter-only zero-code-capacity control.

Expect433 workspace tests per profile, one ignored. Build runtime only with
the adopted e729a493 exporter/wrapper, two Cargo workers,45-second shared lock
admission and8GiB free-space floor. Freeze source and protocol before building.
Run seven saved real selections, nine suites,203 strict native/cache checks
and three current profiles with unchanged per-PC logical work, peak memory
and entropy before performance. Require smaller primary generated code and
no code growth on the three real profiles as the mechanism check.

Use a fresh40-command token screen with the same first-history protocol as
immediate-shifts/WORKFLOW.md: baseline/duplicate/candidate share automatic
function caching and cached lookup; retain fixed anchor and ordinary native;
two Cargo and two prepared custom workers; all12 original assertions and
unchanged guest settings. Only five valid source edits enter paired medians.
Gate: candidate/baseline wall<1-AA wall, CPU<=1 and CPU+AA CPU<=1.05; A/A is
maximum absolute individual duplicate/baseline deviation, not a confidence
interval. Freeze the adapted executable schedule and storage admission before
running. A screen is not adoption. Failure cancels unstarted guards with no
repeat; passing requires a prospectively declared full comparison including
all mandatory held-out projects before adoption.
