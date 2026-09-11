# Bounded leaf inlining: structural screen

No bytecode has been transformed or executed by this analyzer. It checks the retained program against every saved profile operation, then applies static eligibility and growth limits without using observed hit counts to choose sites.

| Workload | Max leaf instructions | Eligible dynamic calls | Direct-call share | Added bytecode instructions (upper bound) |
|---|---:|---:|---:|---:|
| word64-inline8 | 64 | 641,704 | 3.7% | 1,119 |
| word64-inline8 | 128 | 6,734,266 | 38.8% | 5,729 |
| word64-inline8 | 192 | 8,074,030 | 46.5% | 7,710 |
| sha1-inline8 | 64 | 500 | 0.0% | 759 |
| sha1-inline8 | 128 | 4,457,795 | 80.5% | 4,634 |
| sha1-inline8 | 192 | 4,457,795 | 80.5% | 4,634 |

Every selected call has proven caller-local argument/result extents, a scalar leaf with explicit terminal control flow, and the existing conservative proof that its registers need no initial zeroing. Leaf frames are at most 512 bytes and 256 registers; argument/result copies are at most 32 bytes. Callee alignment cannot exceed caller alignment.

The proposed transform reuses one disjoint inline storage bank per caller and explicitly zeros the active callee frame on every invocation. The estimate includes argument copies, that reset, and a common result copy. Bytecode growth is capped at 4,096 operations per caller and 50% across the program. Aggregate storage growth is not peak live memory.

At a 192-instruction limit, word64 adds at most 7,710 instructions to 55,081, and SHA-1 at most 4,634 to 16,094. This screen motivates a prototype; it does not establish semantic equivalence, runtime improvement, or complete-command performance.
