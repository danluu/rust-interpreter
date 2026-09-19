# Implicit-zero storage primary: gate failed

All40 command outcomes, original assertions, deliberate wrong edits, source
restoration and candidate/control bytecode identities pass. The existing
performance gate fails. Park this exact runtime and cancel all larger histories;
main retains the adopted runtime. Do not retime this unchanged candidate.

| Measure | Candidate / baseline | Maximum absolute A/A deviation | Gate |
|---|---:|---:|---|
| Median paired wall |0.978171695|0.043579437|fails: sum1.021751132 exceeds1|
| Median paired child CPU |0.986097055|0.040287040|passes: ratio≤1 and sum1.026384095≤1.05|

The observed wall improvement is2.18%, inside4.36% A/A variation. This is failure
to establish a gain under the declared protocol, not evidence of zero benefit.
The candidate/native median paired wall ratio is1.662316689. Keep all five
pairs, including the first edit's1.093552814 wall ratio.

The descriptive paired median Cargo change is−16.25ms and VM execution change
−32.16ms. These nested/overlapping stages are not additive or causal. The
code-size and exact semantic evidence remain valid but do not justify adoption.

The closure verifies1,674 evidence files and56 artifacts. Source71eac35e,
supervisor36363/child36366, completes normally. The larger five-project and
parser histories were never started. No other session was interrupted.

Next inspect the conservative interpreter repair work. The initial implementation
normalizes every classified read, including operands whose VM operations already
truncate to64bits. Use the retained current-host profiles and typed operations
to count the actually necessary full-width reads before designing another
variant. This is a different prospective mechanism; no unchanged retry or
relaxed gate is authorized by this result.
