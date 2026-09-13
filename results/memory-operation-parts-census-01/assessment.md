# Address-space selection is a distinct remaining cost

The observer reconstructs both adopted unprofiled captures exactly: all 1,101
and 1,305 functions, every original machine word and operation span, and all
assertion and resume identities. It partitions 306,586 and 400,795 small-memory
spans. All 412 bytecode tests pass in debug and release. Two explicit offline
reconstructions and one attribution command run, with no new guest execution or
executable-code publication.

| Generated self-PC samples | Block | Exhaustive |
| --- | ---: | ---: |
| All generated code | 1,651 | 1,439 |
| Selected Load/Store and Copy up to 16 bytes | 721 | 348 |
| Address-space selection | 188 | 66 |
| Bounds checks | 65 | 18 |
| Readonly checks | 2 | 4 |
| Data loads, including odd-width assembly | 340 | 178 |
| Data stores, including odd-width extraction | 96 | 65 |
| Register publication/input materialization | 5 | 13 |
| Known frame/shared/guarded address formation | 13 | 2 |
| Forwarded-value materialization | 7 | 0 |
| Other address value/host-base formation | 5 | 2 |

Every selected sample reconciles with the original coarse attribution. There
are no ambiguous selected samples and no omitted functions with native execution
in the retained exact profiles. Large copies, dynamic transfers, fused fills and
native call/return operations remain outside this finer partition.

Address-space selection is 11.39% of generated block samples and 4.59% on
exhaustive. The block count includes 153 source-address and 35 destination-address
samples; exhaustive splits 51/15. This is substantially more than the bounds
checks themselves. The current selector emits eight words: materialize the heap
tag, compare/subtract, and select address, backing base, extent and readonly limit.
The tag is `1 << 62`. A one-bit classification would be wrong for some larger
unsigned addresses; keep the complete current rule.

Next prototype a branch-based fixed-address selector that retains exact unsigned
classification and subtraction, all complete bounds/readonly checks, source-first
copy validation, zero-size behavior and scratch/register contracts. A new
composition can include the qualified successor-only flush mechanism, whose
standalone full gate failed. Do not reintroduce the prior rejected CCMP/range
rewrite or wider-copy bundle. Branch prediction, code-size and capacity effects
must be measured with fresh original-test and edit-command qualification.

These two short, perturbed sample windows are not timing measurements. Weighted
emitted counts are 3.088B/1.326B selection words; they are not retired instruction
counts. No speedup or arena redesign is established by this diagnostic.
The final audit verifies 240 distinct frozen inputs and 190 Git source bindings.

[Attribution](attribution.json), [closure](closure.json),
[plan](../../benchmarks/experiments/memory-operation-parts/PLAN.md).
