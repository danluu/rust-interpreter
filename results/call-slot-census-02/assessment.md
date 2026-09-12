# Native Call slot census

The typed census passes eight focused tests and reconciles both recorded profiles
with their original VM instruction, native Call and native Return counters.
No new guest execution or runtime change. No function hit an analysis bound.

| Workload | Native Calls | Nonempty native argument checks | Known caller-frame slots | Share |
| --- | ---: | ---: | ---: | ---: |
| folded-literal-trie | 25,913,904 | 82,536,622 | 80,948,861 | 98.08% |
| token-phrase | 112,236,119 | 326,206,317 | 324,531,401 | 99.49% |

All nonempty result destinations on these native Calls are also known caller-frame
slots. These are potential result copies per Call, not a measurement of actual
native Return copies. Indirect Calls remain separately counted and interpreted.

The input artifacts and successful original assertions match the qualified
compiler. Token executes three real randomness operations; its profile is
reconciled against its own instruction total. Dynamic frequencies are not joined
to CPU samples from a different execution.

The census resets facts at all branch targets and after terminators, kills
complete register writes, and follows only Local, immediate and bounded unsigned
64-bit Local-plus-constant facts. It is a conservative opportunity count, not
permission to trust arbitrary initialized registers at external native entries.

Next try guarded local argument addresses: compare the actual low-64-bit guest
address with the expected current-frame offset, use the proven in-frame path
only on equality, and otherwise run the existing checked path. Keep guard and
copy execution at the original argument position, after the same charging and
clearing. Return optimization remains separate. Complete edited-command gates
will determine whether this instruction reduction is useful.

The first admission failure remains preserved. It involved a receipt-path
assumption before any build or profile read; the corrected binding follows the
recorded complete smoke summary and compares its command list exactly.
