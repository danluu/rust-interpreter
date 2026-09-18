# Initial publication qualification stopped at test compilation

Source 370aacf0 fails before any native control executes: the new test helper
returns u64 but the existing ABI probe returns a usize array. This is a helper
signature mismatch; no executable append/patch operation is exercised in this
attempt. The one failed Cargo command and both logs are retained. The closure
verifies 309 source/input bindings and two output artifacts.

Correct the helper to use usize consistently, then start a fresh run ID. No
success, transaction correctness or performance claim follows from this attempt.
