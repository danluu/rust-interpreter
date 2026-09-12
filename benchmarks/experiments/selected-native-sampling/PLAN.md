# Select real tests without changing generated code instrumentation

Add --select-test EXACT_NAME with --suite-catalog to the VM, independently of
--profile. Retain --profile-test's existing requirement for --profile. Both use
the validated artifact-bound catalog, preserve the bytecode file, and change
only the in-memory entry before starting fresh guest state and JIT. Reject
duplicate/mixed selections, missing or stale catalogs, unknown names, entry
arguments and isolated batches. Preserve selected test failures.

Two CLI regressions cover exact selection in both engines, uninstrumented code
dump provenance, byte preservation, rejected combinations and test failures.
This starts from main with358tests, so require360tests per host profile (one
ignored). Existing instrumentation and full-suite behavior remain compatible.

Host qualification floor: 4 GiB. Reuse the populated debug/release host cache,
two workers and locked offline dependencies. Completed profile JSON and parked
artifact copies now use transparent filesystem compression; original logical
bytes, pathnames and metadata were verified unchanged. No cache was removed.

Then validate all seven current selected token/folded/pgrust entries against
the recorded instruction-profile receipts using the same qualified entropy
tapes. Require exact instructions, outputs, memory peaks and entropy use.
This verifies the CLI's execution path; it is not a performance comparison.

Finally capture three two-second native sample windows for each of the two
dominant token tests. Use ordinary entropy, fresh owned VM processes, exact
PID/parent/cwd checks, no signaling, and code dumps from those same processes.
The sampler must record and verify the selected name, function and original
artifact/catalog hashes. The dumped code must be uninstrumented. Attribute
captured PCs to actual emitted ranges; do not infer cost from bytecode counts.
Sampling perturbs execution, so no latency or speedup claim comes from it.

Sampling uses the bounded offline3GiB reserve, at most six16MiB arenas and their
metadata, with512MiB extra at initial admission. It creates no Cargo workspace
cache and does not alter real-edit benchmark admission or adoption gates.
