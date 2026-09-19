# Exact local-copy payload residency scope

Standalone byte-equality elision covered only26/7 generated self samples; it is
parked. This tests a different mechanism: eight reserved SIMD payload registers
holding write-through local Copy data independently of x9 clobbers. It creates no
native code and makes no claim that the future ABI/clobber contract is proved.

Use the closed loop census's exact data. Recognize ONLY complete three-word
unprofiled eight-byte Copy spans: add x11,x2,x1; ldr x9,[x11,#source];
str x9,[x11,#destination]. Decode the aligned offsets and require both complete
ranges within the frame. No inference from arbitrary address expressions or
rendered operands. Model a bounded LRU bank of8 values and at most4 exact local
aliases/value. Snapshot before overlapping writes; invalidate overlapping aliases.
Every native region starts empty. All stores, nonmatching copies, calls, and
unreviewed/effectful operations discard residency; only listed simple integer and
read-only operations preserve it under the prospective reserved-register contract.

For modeled hits, count PCs at the actual middle payload-load instruction.
Whole-copy and cyclic-copy sample totals remain separately reported. Require all
addresses of an aggregated sample to match an eligible load; otherwise report
ambiguity. Reconcile complete1933/1429 generated sample totals. Fixed-entropy
logical operation counts remain separate. Static sites or whole-copy samples
must not be represented as eliminated time. Changed-emitter cascading effects
are not modeled. No runtime candidate is authorized by the diagnostic itself.

Run10 model/decoder controls, including independent concrete payload storage over
20000 seeded operations, eviction/alias bounds, overlapping/disjoint writes,
source/destination aliases, reset, invalid encodings and range bounds. Sources
and closed evidence are hash bound. Shared lock45s;12GiB admission and8GiB child/
case checks. Freeze through independent closure and preserve any failure.

If measured scope merits a typed prototype: consume actual emitter frame facts,
reserve/register-audit SIMD slots, preserve guest memory write-through, avoid
claiming stale x9 facts after vector copies, check every alias/effect/native exit,
and run native ABI/budget/fault differential controls before real edit benchmarks.
