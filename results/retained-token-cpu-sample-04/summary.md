Three separate executions of the exact retained `57a54edd` VM passed the original
token-phrase tests with their original RNG and assertions. Every sampled
generated PC was checked against the live arena of that same owned process.
Host call sites were checked against this binary's disassembly. All three
executions completed with zero JIT declines. These are diagnostic windows,
not complete-command timings or before/after speedup measurements.

| Disjoint category | Window 1 | Window 2 | Window 3 | Combined share |
|---|---:|---:|---:|---:|
| generated code | 986 | 923 | 945 | 37.0% |
| dispatcher self unresolved | 748 | 717 | 775 | 29.0% |
| frame reservation inclusive | 252 | 301 | 262 | 10.6% |
| local argument copies | 196 | 219 | 205 | 8.0% |
| return result copies | 127 | 142 | 139 | 5.3% |
| heap management | 109 | 93 | 81 | 3.7% |
| general argument copies | 70 | 70 | 87 | 2.9% |
| other memory copies | 59 | 57 | 56 | 2.2% |
| switch lookup | 8 | 24 | 11 | 0.6% |
| memory store | 13 | 11 | 15 | 0.5% |
| jit compilation | 2 | 8 | 4 | 0.2% |

Nested memset and memcpy samples remain inside their parent category, so they
are not counted twice. Frame reservation and argument/result copying remain
substantial. Dispatcher self combines several instruction addresses; its share
does not identify a single operation. Original RNG can vary work between runs.

The next candidate needs a typed count of calls and initialization requirements
before implementation. In particular, examine whether callee argument stores
immediately overwrite a useful part of freshly zeroed frames. Preserve argument
ordering, overlapping slots, frame alignment, initialization semantics, memory
limits, fault ordering and original tests. A census is a screening step; any
implementation must improve real source-edit/build/test commands to advance.
