# Darwin fstat

Source `a8b93b65` passed 551 release workspace tests (10 ignored, none failed
or filtered), all 15 required controls and both native tests with 49 child
commands. This qualifies the narrow primitive; complete filesystem, stdio and
Cargo build-script support remain unestablished.
[Qualification evidence](../results/fstat-native-qualification-03/README.md).

The archive preserves metadata attempt01's C compiler/SDK selection failure
and attempt02's compiler API failure, before any tests ran. Attempt03 normalizes
the field type through the existing rustc API and passed using a fresh target.

`DescriptorStat` is appended as V5 opcode 39 after CurrentDirectory 38. It uses
the existing, default-disabled `guest_descriptor_io` capability and the same
complete-program/AArch64 Darwin admission. Only descriptors owned by the fresh
guest table are usable. Inherited 0/1/2 and arbitrary host numbers remain absent.

The lowerer accepts the exact C non-unwind `fstat(i32, *mut stat) -> i32`
contract. The pointee must have the pinned Darwin 144-byte, eight-byte-aligned
C layout, all 22 declared field offsets/types (the final field is two i64s).
Other signatures/layouts/targets fail during export. This first implementation
supports the ordinary libc stat declaration; arbitrary void-pointer declarations
are not accepted as substitutes for the qualified layout.

Runtime validates the complete writable 144-byte result and four-byte guest
errno before a native call or guest change. It resolves the guest descriptor,
seeds all bytes of private eight-byte-aligned storage from the guest, calls
native fstat once, preserves actual result/errno and copies all bytes back.
Padding and native failure writes are retained. No Rust stat value with
uninitialized padding is copied; no host pointer crosses the boundary. Missing
or closed guest handles return -1/EBADF and leave the output unchanged. Host
errno is restored. Interpreter and JIT use the same checked fallback.

Three new Rust controls cover opcode/each-register/default/partial/target
admission, full native bytes/independent MetadataExt fields/size changes/errno,
and invalid memory/unowned or closed descriptors. Existing generic register and
memory-barrier cases include the new operation.

The opt-in `tests/test_fstat_native.py` suite contains two controls and 49 recorded
child commands: 42 for SDK/native/engine histories and 7 incompatible signatures.
The caller must provide the existing explicit Rust tools/std/evidence variables,
plus `RUST_INTERP_TEST_CC` and `RUST_INTERP_TEST_SDK`. The qualification helper
must bind the actual C compiler/loader and SDK header closure, including the
new C source (source enumerators that select only .rs/.py must add it explicitly).
The actual oracle compile retains oracle.d with -MD/-MF, including transitive
SDK and compiler-resource headers, for comparison with the frozen closure.

Before fixture compilation, the C oracle compiles against actual SDK stat.h with
static assertions for sizeof/alignof and 23 scalar offsets/widths (flattening
qspare). A union gives fstat a declared SDK stat object and exposes its fully
seeded character representation, including padding. Its actual raw stat bytes and separately read named fields supply the
retained generated expected.rs table. A stable owned file is shared by the C,
native Rust and both VM engines; a second size phase refreshes the actual oracle
and creates fresh source/artifact paths. Content reads are deferred until all
comparisons finish, preserving access times. Every stat byte and named field is
compared, without inode/time normalization. Closed/-1 native failures,
default refusal, invalid guest pointers and two actual byte/field expectation
tamper executions are retained. The suite never runs invalid native pointers.

Qualification03 used a frozen supervised plan and canonical workload admission.
Its actual C depfile matched all 133 frozen SDK and compiler-resource headers.
Census03's fstat blocker motivated this scope; remaining build-script blockers
require a renewed strict export with the qualified tools.
