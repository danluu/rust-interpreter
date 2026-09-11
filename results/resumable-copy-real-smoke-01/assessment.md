Both original real-workload artifacts pass in the baseline ordinary JIT and the candidate resumable/persistent JIT. Candidate instruction profiles reconcile exactly with their VM counters and contain zero interpreted Copy or CopyDynamic operations. No function declines. Folded retains its exact 4,138,403,285 logical instructions and 102,369-byte peak guest memory. Token keeps its 8,170,193-byte peak; randomized execution counts are preserved.

The candidate records 2,648,070 native entries in token, versus roughly 22.4 million in the earlier tool78 resumable captures, and 80,997 in folded versus 85,769. These are separate executions, with token randomness unchanged. This confirms the intended transition removal; the instrumented smoke timings are not end-to-end performance evidence.

[Commands and tool/artifact hashes](summary.json) · [Whole-run profile reconciliation](profile-attribution.json)
