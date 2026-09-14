The scalar dead-register candidate is parked. All 40 complete commands preserved
original assertions, deliberate wrong-result failure, source restoration, and
candidate/control bytecode identity. The median edited-pair wall ratio was
0.949959 and CPU ratio 0.956743. The maximum A/A wall deviation was 0.060657;
wall plus this margin was 1.010617, failing the unchanged primary gate. The CPU
margin was 1.000401. No later comparisons were started and no runtime adoption
follows from the point estimate.

Qualification passed 20 focused controls and 596 workspace tests in each build
profile (12 ignored), 121 strict Cargo/cache commands, six exact original-test
profiles, and 13 protocol / 3 observation / 419 launcher controls (22 skipped).
The scalar bodies shrank from 19,548 to 16,712 bytes in token block, 16,932 to
14,984 in exhaustive token, and 1,440 to 1,304 in folded prefilter. Original
per-PC counts, peak guest memory, entropy and reconstructed code maps matched.

The screen's descriptive median Cargo, build-to-ready and execution deltas were
-161.7 ms, -162.2 ms and -87.0 ms. These stages overlap and are not additive;
they do not establish causal attribution. In particular, the runtime-only
change does not justify attributing the Cargo difference to the candidate.
Candidate/native median paired wall ratio was 1.64845 for this selected workflow.

Keep the candidate and its exact evidence on the experiment branch. The next
mechanism should first quantify avoidable scalar computations, including
constant-only arithmetic and duplicated value/overflow calculations, on the
saved real hot leaf bodies. Preserve full checking, original Call transaction
semantics and logical accounting, and run a new primary only for a qualified
materially different runtime revision.
