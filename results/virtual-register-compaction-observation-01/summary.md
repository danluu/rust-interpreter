A typed census supports trying a small register-numbering pass. The current exporter leaves unused virtual-register IDs after its transformations. Removing only those gaps preserves a separate slot for every referenced identity, including unread outputs; this proposal does not reuse slots across different registers.

| Original workload | Total declared slots | Referenced slots | Predicted address-generation instructions removed | Predicted native bytes removed |
|---|---:|---:|---:|---:|
| Token-phrase | 1,051,586 | 978,460 | 666,158 | 4,688 |
| Folded trie | 234,644 | 221,700 | 539,082,440 | 9,280 |

Slot counts are totals across all artifact functions, not peak working memory. Address counts are generated instructions weighted by the matching retained profile, not hardware traffic or elapsed-time estimates. Both bytecode artifacts remain exactly unchanged by this diagnostic.

The folded estimate is overwhelmingly concentrated in one original differential-test routine: 2,197 declared registers become 2,031 referenced registers. Its hot accesses would then fit the existing unsigned-offset addressing range, removing 539,067,438 modeled address-generation instructions. This concentration limits generalization; token-phrase predicts little address benefit.

The next prototype must use a strictly monotone map over all referenced IDs, preserve aliases and initial-zero semantics, and run after established inlining and control-flow decisions. Existing raw-bytecode and native ABI tests remain untouched. Before retention, require original assertions, explicit inverse-map trace checks, fresh source-edit/export comparisons, broad correctness gates and binary reproduction. No transformation or speedup has yet been demonstrated.
