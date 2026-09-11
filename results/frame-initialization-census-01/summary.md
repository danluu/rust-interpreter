The typed census does not justify an argument-only zeroing optimization. Proven
local argument copies overwrite only 4.4% of the folded frames' cleared bytes
and 9.1% of token's. Skipping those ranges would usually turn one contiguous
zero fill into nearly two gap fills. No implementation or performance claim
follows from these logical byte counts.

| Saved profile | Proven local calls | Frame bytes cleared, excluding alignment | Bytes immediately overwritten by arguments | Gap ranges per call |
|---|---:|---:|---:|---:|
| folded | 24,326,564 | 41,771,235,810 | 1,834,579,979 (4.4%) | 1.75 |
| token-phrase | 92,488,753 | 32,196,011,617 | 2,915,050,068 (9.1%) | 1.94 |

The analyzer decodes and validates the actual bytecode, compiles the retained
caller-local proof directly, and checks every recorded profile operation for
exact equality. It does not parse Debug strings to infer operands or pointer
roles. Argument slot intervals are merged, so overlapping slots are counted
once for zeroing and separately for the original ordered copies. Unknown source
and indirect calls are excluded from the proposed opportunity. Entry and TLS
frames and alignment padding are excluded. No guest program is changed or run.

The large total comes from repeated clearing of sizable frames. For example,
folded's production RootPrefilter::scan instantiation has an 18,224-byte frame
called 755,097 times in this profile. The presence of a test closure in its
generic arguments does not turn that production callee into test code. The
next diagnostic should inspect MIR local allocation and distinguish unused
storage from live aggregates, ABI slots, addresses and temporary storage.
Existing scalar coloring and inline scratch-bank reuse already cover some
cases, so their savings must not be counted again.

The profiles were recorded on the measured af9 production binaries, identical
to retained 57a5. Folded has 4,138,403,285 logical instructions; token has
13,369,380,010 and retains its original RNG. These profile totals describe those
executions, not all future inputs or wall-clock costs. Memory initialization,
checks and original assertions remain unchanged.
