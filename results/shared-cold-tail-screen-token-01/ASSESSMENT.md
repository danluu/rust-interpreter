# Shared fault tails do not pass the primary

All40 commands have their expected original/wrong/edited/restored outcomes.
Every original test assertion and paired bytecode/catalog identity is preserved,
and source restoration is verified. The closure retains1,674 evidence files and
56 artifacts. No larger comparison or held-out command was started.

| Quantity | Result |
| --- | ---: |
| Median paired candidate/adopted wall |1.025596964|
| Median paired candidate/adopted child CPU |1.014945602|
| Maximum individual A/A wall deviation |0.036077669|
| Maximum individual A/A CPU deviation |0.033753731|
| Wall ratio plus A/A |1.061674633|
| CPU ratio plus A/A |1.048699333|
| Candidate/ordinary-native wall |1.534462852|

The wall gain requirement and CPU ratio<=1 requirement both fail. The result
establishes no useful end-to-end improvement; this small comparison does not
prove a stable regression. Park the implementation and cancel larger histories.
Do not retry unchanged timing or relax the gate.

The code-size hypothesis was real: two exact captures shrink by6.37%/6.09%, and
all615-test workspace profiles,121 strict/cache commands and exact original
profiles pass. Footprint alone did not establish lower development latency.
Descriptive execution is69.66ms higher and Cargo20.90ms higher; these nested
stage medians are not additive and do not establish the source of the difference.

Next inspect actual hot host-frame metadata access sequences in the existing
adopted captures. A bounded static/sample census will decide whether paired
loads/stores remove material work without extra guards, frame-layout changes or
cached continuations. No runtime implementation or timing is admitted yet.
Keep main on the adopted VM, preserve peer work and keep the saved goal paused.
