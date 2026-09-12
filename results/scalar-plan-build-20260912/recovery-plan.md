# Storage interruption and fixed replacement protocol

The original scalar-screen controller stopped during token history03 before its
state3 Cargo-check command: only1,047,363,584 bytes were free, below the declared
1GiB floor. Fifteen primary commands, four Cargo-check commands, ten retained
artifacts and three edited pairs remain in that interrupted history. No child
was started for the rejected check. Source restoration ran and both public
source modules equal their pins, but no final restored-original build/execution
completed in that history. No performance gate has been assessed.

Keep the failed original controller and all partial artifacts/logs unchanged.
Preserve four fully completed histories as the first two histories per project.
After bounded task-owned cache reclamation and sufficient space, run a fresh
token04 with the SAME declared third order candidate/native/baseline, followed
by the previously unstarted pgrust03 with that order. Use new namespaces and
empty targets, unchanged compiler/VM/wrapper, common scripts, source pins, tests,
limits, flags, jobs, edit sequence, checks and restoration. Require at least3GiB
free before admitting token04 (the per-command1GiB floor remains unchanged).

The complete-history performance unit is token01,02,04 and pgrust01,02,03,
15 edited pairs per project. Keep interrupted token03's three pairs separately
as incomplete evidence; do not splice them into replacements, hide them, subtract
A/A variation, or select histories by timings. The original5% aggregate token
wall/improving CPU gate and individual/aggregate5% regression guards stand.
A separate recovery receipt binds the failed and replacement controller hashes.

Independent benchmark review approved this infrastructure-only replacement and
verified the exact failure, paired artifact identity in all reached states,
source restoration, and absence of final restoration-build evidence. It is not
a retry of a performance-rejected candidate. Subsequent planned confirmations
still require their original guards and adequate task-owned storage.
