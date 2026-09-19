# Remaining JIT preparation across real edits

The adopted VM already retains native code within each prepared-suite worker.
The remaining opportunity is reuse between processes after a source edit.
An offline audit of 95 retained adopted-baseline edit receipts finds materially
more compilation work in fre and the parser than in the smaller selected tests.
No application, compiler or guest was rerun for this audit.

| History | Complete command, s | Compiler interval sum, ms | Largest worker compiler interval, ms | Constructor sum, ms |
| --- | ---: | ---: | ---: | ---: |
| fre token | 3.888 | 258.06 | 149.59 | 68.67 |
| fre folded | 1.600 | 72.76 | 52.27 | 15.59 |
| pgrust selected tests | 0.546 | 4.70 | 2.40 | 0.45 |
| rg-aot selected test | 0.280 | 2.48 | 2.48 | 0.31 |
| Nushell type relations | 5.650 | 15.07 | 7.75 | 2.05 |
| Full parser, incremental edits | 1.690 | 213.92 | 124.63 | 45.06 |
| Most recent fre token primary | 3.766 | 255.00 | 147.51 | 65.61 |

Each cell is a median of its own per-command quantity. Worker intervals overlap;
they are not CPU time, critical-path attribution, or promised savings. In the
type-relations case the summed compilation intervals exceed the execution wall
time. Constructor time includes validation that a native cache must preserve.
The original single-worker private history remains single-worker throughout
the audit; the other receipts retain their original two-worker configuration.

Code counters are cumulative within an owner. Counting each owner's final
counter once gives median totals of 26.7 MB for token and 24.6 MB for the parser.
The parser has a median two declined function owners under the 16 MiB per-worker
limit. A reuse design must retain finite admission and interpreter fallback.

The next bounded diagnostic compares typed function identities across saved
source edits, failing-test edits and reversions. It separates local bodies,
direct-callee inputs and global program inputs. Stable bytecode alone does not
prove native reuse: scalar target relocations, assertion identities, compiler
budgets, available arena capacity, entry tables, backend/options identity,
corruption handling and bounded storage also need a complete contract. Cache
key construction, reading, population and invalidation must all be charged to
the eventual real edit/build/test comparison. No native cache is implemented
or admitted by this cost audit.

Seven observer controls pass. The first observer rejected the legitimate
single-worker history; its failure is retained and the corrected control was
added. The successful audit is closed against its original terminal, verifying
141 frozen inputs, 12 source bindings and 136 evidence files. Two closure
attempts timed out waiting for the shared lock; closure then completed without
repeating controls or receipts.

[Audit data](../results/jit-preparation-costs-02/summary.json),
[closure](../results/jit-preparation-costs-02/closure.json),
[analysis and limitations](../results/jit-preparation-costs-02/ASSESSMENT.md).
