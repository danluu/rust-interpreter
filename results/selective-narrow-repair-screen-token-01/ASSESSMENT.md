# Park selective full-width interpreter repair

All40 expected outcomes pass, including deliberately wrong edits, twelve
original test assertions, bytecode identity across current arms and source
restoration. Median paired wall ratio1.011454947 is1.15% slower than adopted;
CPU0.998580341 is nearly unchanged. A/A wall1.7815%/CPU1.0864%; the wall
margin1.029269619 fails, while CPUmargin1.009444555 passes. Candidate/native
wall ratio1.609743254. Retain every pair; do not retry this candidate unchanged.

Supervisor9299/child9303 completed normally. The closure verifies1,674evidence
files and56artifacts. All larger five-project and parser histories remain
unstarted and cancelled. No runtime change is adopted.

Descriptive nested stage medians are Cargo+7.92ms, build-to-ready+7.73ms and
execution+19.31ms. They are not additive or a causal explanation. The earlier
conservative repair candidate ran in a separate history; comparing those two
point estimates does not isolate the effect of selective repair.

Tool6c26c1c8 /VM610a3574 retains the adopted compiler components. It passes
634Rust tests/profile,427Python tests,121strict/cache commands and three distinct
original profiles. Checked address relocation proves native code and execution
distribution unchanged from3e53b127. One observer label bug is retained, and
its successful first capture was reused rather than repeated.

Next audit actual JIT preparation costs in saved changed-source suite receipts.
PreparedJit already retains native code within each suite worker; distinguish
that existing reuse from possible cross-process reuse before proposing another
cache. No new guest or compiler-workstream change is needed for that audit.
