# C9 actual CPython3.9 compatibility stage

Source-only, independently review before root execution. run-compatibility-tests.py uses the same candidate twelve-test module against each matching production arm:24 additional correctness tests in two work children plus two memory children. It writes exclusively to compatibility-screen-01/. It requires the explicit --execute-python39-compatibility-unit-tests argument. The primary24 tests and this24-test stage are both required before timing, with no performance samples or adoption gates in either stage.

The invoked binary is the canonical existing /Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/bin/python3.9, not a developer dispatcher. The inspected /usr/bin/python3 shim is provenance only. The installed plist/header declare3.9.6; no standalone version query was run. The driver confirms actual CPython3.9.6 and either the bound framework bin/python3.9 or framework Resources/Python.app/Contents/MacOS/Python resolved executable before production/test imports. It records the full runtime identity in its result. No version is simulated and the production optimization flag is never assigned: the candidate must naturally report single_stat_guard=false; the baseline has no flag and reports null.

python39-runtime-source-proof.json binds17 named installed files totaling6,671,771B: the Apple shim, canonical native executable/framework/app executable, version metadata/header and relevant pathlib/json/unittest sources/extension. Three dispatch/provenance symlink identities are recorded. Their contents and file identities, and all link texts/targets/identities, are checked before and after the stage. The environment also pins DEVELOPER_DIR to the existing selected Xcode tree, while preserving the same HOME, private TMPDIR and other minimal unit environment controls. No installation, developer selection, SDK change, service activation, download or fallback is performed.

The runtime source inspection exposed that Python3.9 pathlib retains _NormalAccessor.stat=os.stat at import; this caused the v2 os.stat-only test injection defect to be found before executing tests. The bound v3 test helper faults both entrypoints. Missing, permission and I/O errors use that runtime's actual public Path.is_file policy as the oracle, then test the matching arm's unchanged old-runtime branch. This stage provides actual older-interpreter coverage, not proof of every Python implementation/version.

Canonical module preload, common candidate test selection, exact twelve IDs and success/no-skip requirements match the primary driver. All seven resource and settlement helpers remain literally identical to C8. Shared lock,16GiB/30% admission, private outputs/TMPDIR, five-second read-only observations, finally settlement and no signals/retries remain unchanged. All413 before/after proofs must match. Full success schema matches the primary receipt: status="passed",24 successful tests/two suites/four completed zero-exit children, null error/post_binding_error, equal bindings/bindings_after, and actual3.9 runtime plus candidate guardfalse in both reports. See UNIT-SCREEN.md for exact IDs and semantic coverage.

Source identities:

- `run-compatibility-tests.py`: `e6f7c87cbb9d0c086d05b66c84601410f52e12c3a170bcbee28e9a1b5b6e2d12`
- `compatibility-driver.py`: `0799450651df7325471465a12af0ab0bacafabf933634e08537fb8739625ad56`
- `python39-runtime-source-proof.json`: `15772780278f43b7df71dfbd76700fe344279cf533d5dad1fec51a025b3dd09d`
- `compatibility-source-review.json`: `1a58fbe019780e88514b41aeb9537cfb3b80427f3b56f4ecb4d9607d7dbcb322`
- `unit-source-manifest.json`: `ba5be5480862b6c2fa9b31c3838db182dba43055300444d3f797ff20b0817980`
