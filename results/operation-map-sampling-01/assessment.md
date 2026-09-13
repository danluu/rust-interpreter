# Current operation attribution

Two fresh three-second samples complete on the qualified operation-map tool
`d4a6ff9a`. All generated self-PCs map to verified same-process emitted bytes:
2,128 block-boundary and 1,857 exhaustive-test samples, with zero unassigned.
The retained profiles supply operation identities; they are not new timing
runs. Three attribution tests pass in addition to the prior103 harness tests.

| Emitted span | Block generated samples | Exhaustive generated samples |
| --- | ---: | ---: |
| Copy | 518 (24.34%) | 339 (18.26%) |
| Call, including native protocol | 400 (18.80%) | 426 (22.94%) |
| Load | 343 (16.12%) | 149 (8.02%) |
| Budget | 234 (11.00%) | 126 (6.79%) |
| Return, including native protocol | 129 (6.06%) | 199 (10.72%) |
| Flush | 125 (5.87%) | 230 (12.39%) |
| Store | 85 (3.99%) | 59 (3.18%) |
| Binary | 65 (3.05%) | 37 (1.99%) |

Copy/Load/Store together cover44.45% of block generated samples. This does
not identify all of that work as address checking. Call/Return spans are not
counts of VM exits. Static word histograms and ten hot-region tables are in
each attribution JSON; their cold tails are not retired instructions.

An offline audit of eight-byte Copy spans finds358/214 samples. Of these,
92/93 are local-to-local,182/77 checked-source-to-local-destination, and44/14
local-source-to-checked-destination. Forwarded copies account for the rest.
The audit recognizes exact current code patterns; optimization eligibility
must still use the compiler's existing active-frame range proofs.

A typical local-to-local Copy8 has two address calculations per endpoint,
an unused high-word clear, a load and a store: seven instructions. Existing
scaled memory operands could reduce this to one shared frame-base calculation,
one load and one store. Mixed checked/local copies can retain every check
while saving address and clear instructions. This is the next bounded
candidate, covering scalar widths1/2/4/8/16 with complete overlap semantics.

These partial, perturbed windows use normal entropy and establish no latency
gain. The exhaustive window includes188 recognized post-execution diagnostic
samples; the table's denominator includes only generated-code samples.
Do not interpret the entire window as pure guest execution or extrapolate a
seven-to-three instruction reduction into a whole-command speedup. Require
correctness qualification, the predeclared changed-source screen, then all
five full comparison gates for adoption.

Evidence: [block](../operation-map-sample-block-01/operation-attribution.json),
[exhaustive](../operation-map-sample-exhaustive-01/operation-attribution.json),
[saved Copy8 audit](../operation-map-copy-audit-01/summary.json),
[hash audit and controller receipt](summary.json).
