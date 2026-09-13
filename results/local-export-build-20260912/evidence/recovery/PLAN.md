# Recover the wholly unstarted adoption protocol

This prospective recovery is prepared after the original screen controller
timed out at its first admission, before launching any workload. Root reported
the outer session terminal with exit1. The retained controller independently
records status stopped, calls=[], admissions=[], and the exact admission-lock
timeout traceback. Its SHA-256 is
`ad0668a39b0ba0b3219562264152a4370bdd907c8651baee264f4d98651551b7`.
The original frozen protocol remains unchanged at
`a54ddd20bb73748a1243ca48eceaf672f91c72ae55095f636aa371604dc0f54c`.

Preparation checked only the named raw/report/custom-workspace roots and found
all32 absent: four roots per planned history across the original eight
histories. No cache contents were inspected or inventoried. This exact absent
path list and the stopped controller's empty call/admission lists are recorded
in unstarted-evidence.json. Seven original files, including the frozen protocol,
stopped controller, runner, assessor, plan, commands and inputs, are copied
byte-for-byte into preserved/. Original files and all qualified evidence stay
untouched.

The original workload names can be reused **only because all32 roots are
absent**. The recovery runner revalidates that complete absence immediately
before starting its screen. Every original per-history fresh-path and source
check remains. This is not continuation of a started history and does not
replace, discard, retime or splice any measurement; there are no measurements
from the stopped attempt.

The sole scheduling change is the parent controller's admission-lock wait,
from300 to3600 seconds. It still acquires the original shared benchmark lock
only for admission, spawns the original self-locking harness, then releases
admission before waiting for child output. **Every frozen harness/verifier argv
is unchanged**, including its own300-second lock wait. Cargo jobs18, all source
pins, selected binaries, std-MIR, original/wrong/edited/restored controls, all
eight histories, all48 edited pairs and every performance gate remain exactly
as frozen. No process or other session is signaled or changed.

The new runner/assessor live only in this recovery directory. They use the
original frozen input file; there is no new freeze command or changed benchmark
plan. The copied runner's original freeze function is unreachable from its CLI.
The recovery manifest binds both original hashes, preserved files, source
adaptations, this plan and the exact absence record before execution. The runner
checks those bindings before starting and at every history admission, and the
assessor verifies the same bindings against the new controller receipt.

All new controller receipts, logs and assessments stay here:

- screen-controller.json and screen-assessment.json;
- confirmation-controller.json and confirmation-assessment.json;
- the original history labels' `-controller.log` files.

The original stopped B/local-export-adoption-screen-controller.json is never
overwritten, and original B/local-export-adoption-*-assessment.json paths are
not used. Raw/report/custom-workspace paths retain their original planned
names. The independent original verifier therefore still consumes the exact
same original planned report path after each history.

After root and independent source review, root may use the original frozen
Python executable, from the root worktree, to invoke these modes sequentially:

1. `run_local_export_adoption_recovery.py screen`
2. `assess_local_export_adoption_recovery.py screen`
3. Only after its complete screen PASS,
   `run_local_export_adoption_recovery.py confirmation`
4. `assess_local_export_adoption_recovery.py confirmation`

Do not wrap the runner or verifier in run_locked.py. Root owns all execution.
This package was prepared without imports, builds, tests, freeze commands,
workload execution, lock acquisition or process inspection/control. If recovery
stops again, preserve its terminal evidence. This package offers no automatic
retry or overwrite path. Any further recovery requires its own prospective
decision against the actual completed/unstarted state, without changing gates.
