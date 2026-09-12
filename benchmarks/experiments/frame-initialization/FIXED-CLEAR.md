# Specialize exact small frame clears

Source baseline: `0189a06` (runtime unchanged from `8faae61`). This is independent
of the parked initialization-elision proof. Every byte currently cleared remains
cleared, before copying call arguments and after the existing budget/fault guards.

When caller frame alignment is at least callee alignment, both validated powers
of two, caller base alignment makes the interframe padding a compile-time
constant. The exact length is `align_up(max(caller_size, 1), callee_align) -
max(caller_size, 1) + max(callee_size, 1)`. For lengths at most 256 bytes emit
bounded pair stores and exact 8/4/2/1-byte tail stores. Preserve the existing loop
for larger or dynamically aligned ranges. Do not alter register clearing, call
charging, copying, live extents, limits, TLS or bytecode encoding. No runtime flag
is needed for this isolated source candidate; baseline and candidate executables
will be separately frozen and compared before promotion.

The exact es8 sample/call metadata in `frame-initialization-proof-01` attributes
1,041 of 7,662 samples to clearing at eligible layouts (13.59%). In particular,
small byte tails currently repeat a loop that the bounded stores can avoid.
This is enough opportunity for a screen, not a performance prediction.

Validation: execute emitted stores on dirty host buffers across every length
0..256 and misalignment 0..63, checking the entire buffer including both guard
regions. Exercise layout calculation across caller/callee alignment and zero-size
boundaries. Differentially execute dirty reused guest frames, read their padding
through valid guest pointers, and test instruction/frame/memory limits. Run the
complete bytecode suite in debug and release; retain failures and terminal logs.

Then run one alternating six-pair saved-artifact JIT screen on the unchanged es8
artifact (one excluded warm pair). Compare the newly merged baseline runtime and
this candidate built with identical flags. Require identical results, instruction
counts and peak memory, and at least 10.3% median paired runtime wall improvement
to justify an 8% whole-command gain given the observed 78% execution share.
Do not repeat a failed screen to cross this threshold. If it passes, run five
real es8 production edits with baseline/candidate/native/check in rotating order,
including original, wrong and restored controls. Require at least 8% paired
custom command improvement before extending the real-project regression gates.
