The suspected register-clearing opportunity is absent. All 1,080 block, 1,281
exhaustive, 102 folded and 2,345 parser direct-callee rows already qualify to skip
register initialization. The call-weighted current zeroing total is zero in all
four profiles. Both production decision helpers match the adopted source exactly;
only a cfg(test) diagnostic was added.

reduce_cold has 5,526 blocks and zero upward-exposed register reads. The fast
block proof already handles it despite its 102,786 registers exceeding the later
CFG proof's bound. Do not raise bounds or implement a projected CFG proof for
this workload. Its separate 372,497-byte memory frame is still initialized.

Four validated typed analyses pass in 17.74 seconds including the release test
build. The closure verifies 244 source/input bindings and 12 evidence files.
No guest code executed, runtime changed or end-to-end speedup was measured.
