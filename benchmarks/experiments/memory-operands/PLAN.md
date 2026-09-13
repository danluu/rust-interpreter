# Simpler memory operand generation

The typed address-check census finds zero fully reusable checks in all three
current profiles, without reaching an analysis limit. Do not implement that
cache. The supplementary operation census finds 1.002/0.908/0.354 billion
narrow stores in the same tests and conservative lower bounds of
0.805/0.878/0.358 billion known-local common-size stores. Counts are logical
operations, not hardware traffic or timing; local loads can already forward.

Start from the exact wide-operation emitter/assignment sources at 0f1d6f3,
qualified tool f8713aaa. Exclude the failed paired-register runtime. Keep the
new bounded offline census tools, with no role in execution. Retain the wide
exporter and wrapper bytes; strict compiler checks, VM layout and limits stay
unchanged.

This candidate makes three related instruction-selection changes:

1. Common-width loads overwrite their entire low temporary; 16-byte loads
   also overwrite the high temporary. Drop those dead clears. Retain a zero
   high temporary for widths <=8 and both accumulator clears for unusual
   byte-assembled widths, including zero.
2. Store never uses its high source temporary for widths <=8. Omit that read,
   retaining the low read's liveness bookkeeping. Do not omit any VM-register
   high-word write or change reused native-callee register initialization.
3. For an existing Fact::Local range wholly inside the active frame, encode
   aligned offsets in the existing unsigned scaled Load/Store immediate when
   every access fits its 12 bits. Compute current memory base + logical frame
   base once per access. A 16-byte access needs two 64-bit offsets and both must
   fit. Preserve original addressing for unknown, unaligned, unusual-width,
   out-of-frame and oversized-offset cases. No new pinned register or memory
   model, guard removal, check reordering or cross-entry proof is introduced.

The load encodings are the existing AArch64 scalar forms. Byte/halfword/word
loads zero-extend; unsigned immediates scale by access width. See Arm's
[instruction reference](https://documentation-service.arm.com/static/6245c734b059dc5ff9a8bdab)
and [A64 compiler overview](https://developer.arm.com/community/arm-community-blogs/b/architectures-and-processors-blog/posts/the-a64-isa-and-compilers).

Four focused tests cover encodings/high-word contracts, displacement/alignment
and full-range boundaries with identical fallback checks, unused Store source
reads, and actual interpreter/JIT agreement for every width 0..16, offsets
through 32768, frame alignments 1/2/16, narrow and full-width reads preserving
neighboring bytes, ordinary/resumable and persistent on/off, VM exits and every
instruction-budget tail. Provisional host count: 428 per debug/release profile
(wide419 + census5 + memory4). Build under the shared lock with 45-second
admission, two Cargo workers and the existing 8GiB host floor.

Qualify seven exact saved real tests, nine suite commands, 203 strict
native/cache commands and three exact logical profile comparisons before
performance sampling. Freeze a prospective complete-command comparison after
qualification. The same fifteen edited pairs, fresh A/A controls, fixed anchor,
ordinary native libtest and mandatory folded/pgrust guards as the paired
experiment apply. No completed candidate is retimed to seek acceptance.
Generated code size only confirms a mechanism; edited end-to-end latency
determines whether the resulting development engine is useful.
