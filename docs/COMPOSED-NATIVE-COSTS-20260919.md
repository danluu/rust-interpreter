# Current-composition native code diagnostics

The session/runtime composition remains parked after its unmeasurable full
incremental parser gate. Two new, normal-entropy fre captures use its actual
normal VM (`78378e47`), persistent/resumable/scalar/indirect calls, original tests
and limits, and a fresh standalone owner. Each guest ran once and passed with
zero JIT declines. These partial, perturbed three-second sample windows describe
generated-code costs; they do not measure persistent-session latency or speedup.

| Generated self-PC category | Block | Exhaustive |
| --- | ---: | ---: |
| Copy | 414 | 243 |
| Direct call transition | 284 | 317 |
| Load | 186 | 84 |
| Switch | 116 | 78 |
| Budget | 102 | 75 |
| Scalar body | 74 | 113 |
| Return transition | 70 | 159 |
| Flush | 16 | 13 |
| Indirect call transition | 7 | 10 |
| All generated self PCs | 1,514 | 1,306 |

All generated samples are assigned. Host and post-execution diagnostic samples
remain separately reported. Scalar spans identify whole bodies. The older dynamic
profiles supply function/opcode identity only; their dynamic counts are not mixed
with current captures. Same-process reconstruction verified every emitted byte
and the complete operation-span partition.

The first analysis successfully wrote the block summary, then failed because
its older reader did not accept `resumable_indirect_call`. The failure is retained
in `results/composed-fre-runtime-sampling-01-analysis-01`. A separate reader passed
five controls and verified both retained code dumps, including their 30/28 indirect
regions. It requires Boolean mode agreement, one original CallIndirect PC, a
matching transition, and all earlier code/hash/extent/coverage checks. A separate
continuation reused the block summary and produced only the missing exhaustive
summary and both attributions. No guest or sampling command was repeated.

The final evidence is independently closed in
`results/composed-fre-runtime-sampling-01/closure.json` (supervisor 94441), with
238 archived VM source bindings and the original capture/failed-analysis records.
Sampler option qualification is closed separately in
`results/composed-native-sampler-protocol-01`; reader qualification is in
`results/composed-native-attribution-protocol-01` (supervisor 73875).

Next inspect small switch comparisons in the retained captures. The current
emitter compares both 64-bit halves separately for every case. A whole-128-bit
zero comparison or one shared high-half guard for narrow cases may remove work
without assuming Rust types or changing first-match semantics. Establish the
affected captured sites before implementing. Do not repeat the previously failed
general address-selector, capacity or frame-base variants.
