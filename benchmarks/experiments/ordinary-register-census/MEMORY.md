# Recognize the ordinary emitter's integer memory effects

The scalar-origin decoder makes paired stack restores opaque. Add only the
ordinary emitter's unsigned-offset byte/half/word/doubleword transfers and its
64-bit integer pairs with offset, pre-index or post-index addressing. All memory
operations remain nonremovable. Loads define destination registers; stores read
their payload registers; every form reads its base, and indexed pairs also write
the base/SP. Reject unpredictable overlapping writeback or identical load targets.
Leave signed, SIMD, atomics and other memory forms opaque.

Before saved-code analysis, assemble a 14-instruction independent host fixture
using the system assembler and compare its Mach-O text words with explicit
expected encodings and register effects. No fixture is linked or executed. The
host assembler is solely a test oracle, not a guest compiler/backend. Limit its
new object to 512 KiB. Run four new memory controls and all 21 existing controls;
repeat both return policies on both exact captures. Earlier all-register CFG
candidate sets must remain subsets. Retain all memory/branch effects and the
bounded fixed-point allowance; no runtime patch or timing follows from the census.

The emitted forms come from the exact adopted `jit.rs` and `jit/values.rs` inputs.
Arm's [A64 description](https://developer.arm.com/community/arm-community-blogs/b/architectures-and-processors-blog/posts/the-a64-isa-and-compilers)
and [instruction reference](https://documentation-service.arm.com/static/6245c734b059dc5ff9a8bdab)
describe uniform addressing and pair transfers. Concrete numeric spellings are
checked by the independent fixture, rather than inferred from mnemonic strings.
