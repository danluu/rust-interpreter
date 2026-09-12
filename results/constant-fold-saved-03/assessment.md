# Corrected folder artifact verification

Build10 passes368Rust tests in each profile and fixture02 passes18 native/custom
commands over nine original tests plus uncalled borrow/type error controls.
Compose03 retains the exact control VM. Three saved transformations and three
whole-artifact verifications pass after the null-read fix.

The final token, folded-trie and pgrust artifacts are byte-for-byte identical to
the programs already checked in the34test replay. The token folder's intermediate
counts change because18 invalid constant reads and two switches are no longer
folded; the later CFG cleanup makes the final artifact unchanged. The explicit
replay-binding.json validates saved input, result, fixture, VM and raw record
hashes. No replay timings are repeated or fabricated.

The old compiler remains disqualified for general use. These exact corrected
programs inherit the prior selected-test coverage. Corrected full-workflow
performance remains unmeasured; the weak standalone runtime gain does not justify
adopting the global folding pass.
