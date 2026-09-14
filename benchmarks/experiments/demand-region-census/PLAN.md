# Demand-driven ordinary region compilation: feasibility first

The register-file census did not justify repeating parked register/cache/flush
variants. Before changing compilation granularity, join the three closed adopted
original-test profiles to their own exact profiled native region maps and code.
Validate complete coverage, boundaries and counters; keep scalar bodies separate.
Partition ordinary emitted bytes into regions with charged native entries, only
interpreted work, or neither. A zero charged count does not prove the region was
never entered: preflight/budget declines run before that counter. Preserve this
limitation and report interpreted work separately. No execution-order claim is
possible from aggregate counters.

Report whole-function versus region counts, charged operations, code bytes and
per-function concentration. Keep existing measured JIT preparation durations as
context only; neither cold bytes nor extra first visits estimate time saved.
Preparation includes whole-function analyses that finer emission may retain.
A later prototype must measure additional VM exits, analysis/emission cost and
patching overhead inside the complete changed-source command, with the same
strict frontend, scalar fallback, exact faults/budgets, original assertions and
primary/full guards. No machine-code or analysis cache is assumed safe.

A prospective emitter would need immutable per-function analysis and bounded
region publication; missing internal/resume targets must return through existing
VM state publication. Any native edge patch must happen only on the owning
thread outside native execution, with checked displacement, macOS write
protection and instruction-cache publication. No code generation executes while
a frame borrows guest storage. Existing arbitrary-entry and code-capacity refusal
semantics remain requirements. The census authorizes no runtime adoption.

Use shared lock/45-second admission, 8 GiB offline floor and two workers for later
builds. Retire only nonexecutable compiler intermediates in the five exact caches
of the closed failed read-only-native 40-command screen. Keep all evidence,
executables, shared ROOT target, private and peer work; record exact inventory,
process/open-file checks and protected hashes. The saved goal stays paused.
