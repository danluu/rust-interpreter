# Shared cold fault-tail experiment: not adopted

The September18 custom-runtime experiment shares identical complete terminal
fault-return sequences within a resumable native function. It retains local
fault labels and all original operations, budgets, assertions and scalar bodies.
The isolated VM93b75492 preserves adopted exporter cf4b3499 and wrapper45bca4f2.
No compiler checking or guest semantics are relaxed.

Exact reconstruction of two saved captures removes720,192/837,504bytes
(6.37%/6.09%) while preserving all entries, resumes and logical operations.
Five focused controls pass in debug/release, including complete native state
and callee-saved ABI equality. Workspace checks pass615 Rust tests/profile,
427 Python tests (22 declared skips),121 strict/cache commands and three exact
original-workload profiles. The earlier two incorrect fixture assumptions and
first lock-admission failure remain archived.

The complete40-command changed-source primary preserves original assertions,
wrong-edit failures, source restoration and candidate/control bytecode identity.
Only five valid edited pairs enter ratios. Candidate/adopted median paired wall
is1.025596964 and CPU1.014945602; A/A deviations are3.607767% wall and3.375373% CPU.
The original wall-gain and CPU<=1 requirements fail. Candidate/native wall is
1.534462852. This establishes no useful latency improvement; the small comparison
does not prove a stable regression. Smaller code alone did not earn adoption.

The implementation is parked, all larger histories are cancelled/unstarted, and
main retains the adopted scratch/scalar runtime. No unchanged retry or gate
adjustment is planned. The closure verifies1,674 evidence files and56 artifacts.
The source, controls, raw receipts and result are retained on
`experiment/shared-cold-tails-20260918` at a401548a, including
`results/shared-cold-tail-screen-token-01/ASSESSMENT.md`.

Next inspect exact private host-frame memory accesses using the already closed
adopted captures. This is an offline coverage census; no replacement runtime or
speedup follows without separate correctness and end-to-end evidence. Preserve
parallel compiler/application investigations and conservative shared-host limits.
