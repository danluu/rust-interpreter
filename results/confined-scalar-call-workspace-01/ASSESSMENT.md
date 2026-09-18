# Test-only Call transaction qualification

The original supervisor finished with return code zero. Both full workspace
profiles passed 581 tests with ten ignored; all six new transaction controls
and 24 imported proof/scalar/native controls passed in each profile. No
production hook or original-project benchmark ran. All 231 frozen inputs,
four output logs and the supervisor log were revalidated. The focused run's
169 inputs and four logs were independently closed as well.

The run summary was initially saved under the last required test's name
because a Python loop shadowed the run-name variable. Its bytes were
preserved and moved to this directory after verifying its raw-run identity.
The runner fix changes reporting only; it does not justify rerunning 103
seconds of already-passed regressions. The closure retains the tested source
revision and raw plan, records, logs and terminal identities.

Next: native-to-native Call bridge with shared code admission, original
profiles, caller/cursor preservation and guarded transactional commit. This
Rust callback model is a correctness reference and has no speed claim.
