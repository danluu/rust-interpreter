# Extend the analysis within native regions

The single-operation census has only 6/4 sampled candidate words. Analyze the
same two captures again, grouping consecutive spans by function and region PC.
Include entry, budget, flush, transition and failure tails in the region's code;
exclude private scalar bodies. Every region begins and ends conservatively.
Keep all direct branch targets, calls, returns and unknown instructions as
barriers using the unchanged qualified linear recognizer. This permits liveness
to flow across adjacent ordinary bytecode operations, not across native regions.

Verify contiguous, noninterleaved grouping; all words and spans must retain their
original owner. The prior single-operation candidate offsets must be a subset of
the region candidates. Repeat the 14 recognizer/linear controls and add two
grouping controls. Reconcile original sample totals and publish only aggregate
coverage and bounded top sites; keep full details local with exact hashes.
No runtime patch, guest execution, compiler or executable publication is involved.
