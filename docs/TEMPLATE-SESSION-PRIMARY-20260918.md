# First complete cross-command template session comparison

The candidate fails the prospective warm-edit gate. Keep the adopted runtime.
The closed40-command comparison uses pgrust's114 original parser tests, five
execution modes and source states[0,-1,1,2,3,4,5,0]. Every command rebuilt changed
source in its own compiler-cache history. Two additional type/borrow-error
controls returned101 without submitting a session request. All original test
outcomes, current artifact/catalog identities and restored source matched.

| Valid-edit paired median | Wall | CPU |
| --- | ---: | ---: |
| Cached session / adopted VM | 1.0110 | 0.9869 |
| Cached session / session without history | 0.9472 | 0.9656 |
| Session without history / adopted VM | 1.0674 | 1.0107 |
| Cached session / ordinary native | 1.3576 | 1.2760 |
| Maximum adopted A/A deviation | 0.0388 | 0.0285 |
| Candidate/adopted plus A/A margin | 1.0498 | 1.0153 |

The wall gate requires a ratio plus margin below1. CPU meets its thresholds;
wall does not. The result is failed, not unmeasurable: noise is below the8%
classification threshold. Do not retime the unchanged candidate or change gates.
The cache-on/off difference is an observed paired result on this workload, not a
general speedup claim or proof that every per-request cost is attributable.

Accounting includes all kernel server CPU, with request snapshots reconciled at
exit. Remaining server CPU plus parent/helper startup/teardown CPU is allocated
across the five valid edits. Complete startup/teardown wall is also charged:
25.1ms total for the cached session and30.4ms for session without history. Those
lifecycle costs alone cannot explain the full session/adopted gap. Both owned
sessions exit by ownerEOF and are reaped. No background daemon work is omitted.
Verification mode is off for timing; the preceding independent-client replay
checked1,824 real test invocations and17,076 exact cache hits with verification on.

Source756f304d ran under8562/8796; closure90499/90502 verifies5,309 frozen inputs
and175 evidence files. Results:
results/cross-program-template-parser-screen-incremental-01/summary.json.
Candidate tool9f7aa601253a6817745070cf16a5122282d4fd9f70b33a14b625ee7a09a4a30b;
VMd84f7bc7b125ff5eaa15407ec2e5f80edb4180ca07ac8caf52a2132bad05a7e7;
serverc17f9eeb1b022f62ba5149cc425a2bbc9a67d0edca1f7e2bbc7aa8cfe6b8110b.
Exporter/wrapper are byte-identical to the adopted build. No larger comparisons
or runtime adoption follow this failed primary.

Next inspect the retained per-command build, execution, server-request and worker
preparation intervals without rerunning the workload. The implementation currently
reads/hashes the artifact in both client and server, performs repeated structural
Program validation, and syncs report/receipt files. These are candidates for
investigation, not established explanations for the measured difference. Preserve
strict Rust checking, exact current artifact binding, pre-execution report
reservation, fresh guest state and no automatic retry in any follow-up.
