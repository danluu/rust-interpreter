# Reduced session request costs: correct, below the adoption margin

The materially changed session candidate fails the same prospective warm-edit
wall gate. Keep the adopted runtime; no unchanged retry or larger comparisons.
This is a failed result, not unmeasurable: A/A noise remains below8%.

| Valid-edit paired median | Wall | CPU |
| --- | ---: | ---: |
| Cached session / adopted VM |0.982134|0.961514|
| Maximum adopted A/A deviation |0.036901|0.021485|
| Candidate/adopted plus A/A margin |1.019036|0.983000|
| Cached session / session without history |0.999368|0.974262|
| Session without history / adopted VM |1.014124|0.996795|
| Cached session / ordinary native |1.306254|1.273764|

The result is a1.8% observed wall reduction against a3.7% noise allowance; CPU
meets both thresholds. Ratios compare modes within this run. Differences from
the earlier run do not independently establish the size of this change's effect.
Cached/off wall is near parity in this run despite lower CPU. Retained stage
intervals will guide further attribution; no isolated fsync attribution is claimed.

The implementation53268501 removes client artifact hashing and post-execution
launcher rehash, retaining server validation of actual bytes and a pre-execution
launcher digest when available. One owned immutable ValidatedProgram is shared
across request workers; each still admits current limits, creates private native
owners and fresh guest/environment state. Completed report/receipt writes match
ordinary suite semantics; no power-loss persistence is promised. Reservation,
exact report hashes and no automatic replay remain.

Qualification passes442Python tests/22skip and651Rust tests/16ignored per profile,
plus a feature-off VM build.24 owned session processes and46 VM fixture clients
are reaped. The independent actual-parser replay matches1,824 invocations with
16,322 verified hits and reconciled kernel CPU. Results are closed:
results/session-request-costs-qualification-01 and
results/session-request-costs-parser-client-01.

Primary4533aa53 ran60442/60445,40 source-build commands across five modes and source
states[0,-1,1,2,3,4,5,0]. All114 original parser outcomes, selected artifacts and
restoration match. Two additional type/borrow controls returned101 without any
session submission. Both servers exited by ownerEOF and were reaped. Complete
kernel CPU plus startup/teardown is included; cached lifecycle wall20.7ms total,
off20.0ms, each fully charged to five valid edits. Cold anchors are excluded from
warm ratios. Results:results/cross-program-template-parser-screen-incremental-02.

Candidate tool d3c57bceeadb0d79f44848d9f8ab8c559be27659a073347eab9f3b4f5c585096;
VM200148cd93a412b9b323121d67632e335b94f1a5917763e1a1d3dee489baad4c;
servere39cda827ba050869370e93500a281c543d248778c0128efd7fb4422931920a0.
Exporter and wrapper remain byte-identical to the adopted build. The runtime
candidate is retained on experiment/session-request-costs-20260918, unadopted.
