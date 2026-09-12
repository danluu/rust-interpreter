# Keep null reads observable

Review after the 34-test real-artifact replay found a missing transfer condition:
the VM rejects every nonempty read at address zero, while both constant analyses
treated data[0..size] as readable. The folder could therefore replace a faulting
null load with an immediate. The offline call census could report argument bytes
from an invalid null argument address. Neither conclusion follows from the
existence of padding bytes in Program.data.

Add regressions before fixing the transfer functions. Exercise scalar loads of
1/2/4/8/16 bytes at zero, valid nonzero data addresses, the exact last valid
start, the end of data and usize::MAX. Preserve interpreter results/faults and
the existing per-artifact JIT/budget comparisons. Check a null call argument
beside a valid immutable argument so the diagnostic keeps useful nonzero facts.

Qualify this narrow change with the existing host dependency cache, two workers,
offline locked Cargo and the already used zero-debug/incremental-off host
profiles. A focused bytecode-library test child requires 4 GiB free: it rebuilds
one library test executable, fetches nothing, creates no project/dependency
benchmark cache and publishes no tool. Record command, source hashes, outcome
and free space; retain the expected failing run. Full tool publication and the
actual-edit screen remain separate qualifications with their declared rules.

Until the fix is qualified, the existing folder binaries are disqualified for
adoption even though all 34 selected real tests passed. Preserve those results
as coverage evidence, not proof that all valid bytecode semantics are preserved.
