# Build and qualify an immutable aggregate-result candidate

Prerequisites: closed aggregate native ABI and complete Call controls (374
bytecode tests/profile), plus the exact 132-function census retaining all32
memory-admitted native bodies and all66 exhaustive samples. None of these is
an end-to-end performance result.

Run the complete workspace in debug/release, requiring 637 passed /18 ignored
per profile and the named native/boundary controls. Run all429 launcher/Python
tests, with the existing22 declared skips. Build the release VM and install it
under a fresh composition hash with the adopted df4006e0 exporter and wrapper
unchanged. Record all commands, exact tool hashes and total setup time.

Only the shared owned build target is used. Hold the global lock; use two Cargo
workers, two test threads, offline/locked dependencies and ordinary entropy.
Require max(14 GiB,8 GiB+twice allocated target) before builds and an8 GiB child
floor. Freeze all Rust, launcher, test and controller inputs. Close any failure
before editing. No original-project guest or performance command occurs here.

After success require the unchanged121 strict/cache commands and three exact
original profiles/reconstructions. The prospective primary remains the complete
changed-source exhaustive test history specified in NATIVE-NEXT.md; full project
and parser guards precede adoption. Main remains the adopted runtime.
