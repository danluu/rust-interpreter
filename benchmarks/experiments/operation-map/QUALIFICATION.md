# Exact real-code qualification and sampling protocol

Runtime build operation-map-build-02: 436 checks per profile, one ignored,
source 7b92125; tool d4a6ff9a and VM 83ca5b78. Exporter and wrapper are the
exact adopted e729a493 binaries. The first build stopped at new test-fixture
field names before running tests; its failure is retained.

Run seven uninstrumented exact saved selections using the established entropy
replay and instruction/memory/selection checks. Then run three current
profiled map qualifications (block, exhaustive, folded), each with the new
operation map. Their purpose is to prove complete generated-byte identity
against the retained adopted memory-operands-profile-01 code dumps, including
the profile-enabled path, and to validate every operation span against those
same retained profiles. New profile files are equality evidence, not a new
cost census. All per-PC counters, original assertions, native boundaries,
memory, entropy and source/artifact identities must match. Ten guest commands
total; no performance verdict. Both stages require the current 103 Python
harness checks, an 8 GiB floor, the 45-second benchmark lock, and serialized
execution. Failures are retained and corrected without discarding a sample.

After qualification, sample block and exhaustive once each for three seconds
under normal OS entropy using unprofiled selected-test execution and the new
same-process map. Use the existing owned-process identity/cwd/mapping checks,
two commands in order and no concurrent own workload. The sampler never
signals the VM. The map is reconstructed after guest execution, so a window
may include diagnostic host work. The primary attribution is the distribution
of sampled generated PCs; do not present total-thread shares as pure guest
time or compare them directly with older windows lacking reconstruction.
Native PCs cannot be executed by the reconstruction itself.

Join by exact function index and PC, retaining zero-word operations, explicit
overhead and whole Call/Return transition spans. Reject changed code/map
hashes, PIDs, options or native boundaries. Preserve ambiguous sampled frames
as unassigned. Report static emitted words separately from sampled counts;
neither is a count of retired instructions. Do not rerun either parked runtime
candidate or infer an end-to-end speedup from these diagnostic windows.
