# Scoped identity and original native-code pools

Five controls and133saved chronological comparisons pass; no guest, build or
artifact decoding was repeated. Closure binds295inputs,223source files and79
evidence files to83470/83473. The code map comparison validates two complete
original token arenas (11,313,812and13,757,056bytes), exact names/IDs and options.

| History | Median stable body plus direct callees | Median stable bytecode operations, also preserving heap mode/count |
| --- | ---: | ---: |
| fre token | 48.68% | 13.49% |
| fre folded | 51.81% | 12.31% |
| pgrust selected tests | 91.11% | 85.59% |
| rg-aot | 4.59% | 0% |
| Nushell type relations | 4.60% | 0% |
| pgrust full parser | 99.91% | 99.28% |
| Recent token primary | 42.96% | 9.15% |

No valid edit changes heap mode. Numeric function-count changes exclude3pgrust,
12private and9type-relation transitions under this conservative scope. The raw
body/direct-callee columns retain those transitions without treating them as
safe code reuse. Omitted global/admission/relocation inputs remain unresolved.

Against each edited token state, the original block/exhaustive arenas have
median11.60%/11.13%of bytes in functions whose bodies and direct callees still
match the original numeric bindings. These are original-to-edited comparisons,
not chronological cache hits. In particular, adjacent edits2and3are highly
stable even though both differ substantially from the original state. Original
code byte weights do not measure edited compilation work or hot execution.

This weakens the case for a first persistent native cache aimed at token. The
parser remains more promising, but this study has no matching edited parser
code arenas. A simpler independent opportunity is sharing immutable emission
templates between the two workers of one prepared suite: both see the exact
same checked Program, so cross-edit hashing, global rebinding and disk I/O are
absent. PreparedJit currently retains code separately per worker. Any sharing
must still give each owner its own arena, scalar-address/assertion relocations,
admission accounting, continuation tables and fresh guest state. Start with
bounded template correctness before claiming a speedup or changing defaults.

Dataset-label correction: the retained internal case label
`nushell-parser-incremental` in the preparation and identity summaries actually
refers to pgrust's `gram_core`, selected by the original command's manifest
`.work/sources/pgrust/Cargo.toml` and package `gram_core`. The historical labels
and their closed hashes are retained; all parser prose and future plans must
use pgrust. The separate `nushell` case is the type-relations history.
