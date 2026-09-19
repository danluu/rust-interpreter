# What causes actual parser template misses

Capacity is a secondary issue in the five valid edits of this diagnostic history.
The independently reconstructed per-worker LRU reports 12,741 hits, 3,462 changed
keys, 1,770 first attempts of a function on that worker, and only 22 evicted-key
misses. Their summed miss-emission intervals are respectively 0, 214.939, 66.085
and 1.421 ms. Worker intervals overlap; these are not command savings.

The diagnostic feature records at most 4,096 attempts per worker/request, with a
dropped counter on truncation/allocation refusal. All actual requests have zero
drops. A separate OrderedDict model verifies every lookup, insertion, byte charge,
recency transition and cumulative eviction against the runtime. Original limits,
114 outcomes, wrong-edit failure text and kernel CPU reconcile across all 16
suites / 1,824 invocations. There are 16,528 hits over the complete history.
[Actual trace](../results/template-miss-parser-01/summary.json).

The feature passes 25 template controls and 33 integrations in both profiles,
32 feature-off integrations, and seven independent history-model controls,
including malformed/missing transitions and tampered counters/storage.
[Runtime controls](../results/template-miss-history-qualification-01/summary.json),
[model controls](../results/template-miss-parser-model-01/summary.json).

Joining the exact artifacts to the existing consecutive bytecode-difference
census gives these categories over valid edited requests:

| Observed body differences since this worker's prior attempt | Misses | Summed emission ms |
| --- | ---: | ---: |
| Only immediate values | 2,563 | 152.106 |
| Immediate values and direct-call IDs | 702 | 33.826 |
| Function identity moved at this numeric ID | 189 | 16.538 |
| Body unchanged | 10 | 7.370 |
| Other body changes | 14 | 5.721 |
| Same most-recent key, no longer retained | 6 | 0.798 |
| First attempt on this worker | 1,770 | 66.085 |

These categories describe intervening bytecode differences, not isolated causes:
callee/scalar inputs can also change, and an intervening change can later revert.
The cache-history classification above also recognizes previously retained keys
older than the most recent attempt, explaining the different eviction subtotal.
[Hash-bound join](../results/template-miss-causes-01/summary.json).

The expensive tests_dump::node body is often changed only by immediate data
offsets; moving function IDs explains another group. Increasing cache capacity
or compacting metadata would address little of this measured valid-edit cost.
Next census a conservative immediate-relocation subset before implementing it.
The existing emitter propagates constants into folds, memory facts, range guards
and call-slot decisions. Never omit immediate values from identity without a
complete eligibility proof and restoration ledger. Any prototype must preserve
instruction shape, all derived dependencies, original outcomes and strict Rust
checking, then qualify on changed-source end-to-end gates. The previous digest
full guard stays unmeasurable; buffering remains parked; default runtime unchanged.
