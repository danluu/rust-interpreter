# Compiler association launcher component screen

Prepared without importing the candidate/driver/controller or running a workload.
The separately owned decision-plan.json is frozen at
f4fc89ff9c419a748db281d0c946770c8d909249bfdc2f80cf8f187d86d97c3b.
Only QUALIFICATION_SHA remains UNBOUND until root supplies the completed successful
81-test receipt. The controller never changes gates or retries/discards a sample.

Baseline: /Users/danluu/dev/rust-interp-buildtime-fallthrough-baseline-20260918.
Candidate: /Users/danluu/dev/rust-interp-launcher-association-20260918.
Both derive from 2ba2696675cfd275ea9a9ef4c937bc8579f618f2; candidate is the exact six-file
v2 patch 932e88bde51e4233825d8c0bc8a20076edcb7da94ace1ec2889d289f729dc508.
screen-bindings.json binds all immediate scripts/*.py and tests/*.py (184 baseline,
186 candidate), driver/proposal, Python launcher/framework/Resources executable,
and all five actual retained tool-bundle files. Imported source/extension dependencies
and cache headers are frozen after prescribed warmups, before measurement.

The single case invokes actual main with --inline-leaves. installed_tools binary
hashing, require_export_option capability validation and compiler association checks
run normally. ROOT points to old R only to locate immutable eb91912d... tools.
Every invocation has its own explicit workspace-cache-root under screen-01, so real
ownership markers/locking/directory creation run without writing old R.

Exactly the expected Cargo and VM subprocess.run boundaries are stubbed, with full
argv/kwargs/environment assertions. An audit hook rejects actual process launches.
Cargo returns one deterministic compiler-artifact event; VM returns success. The
common sidecar contains an explicit stub marker, NOT validated RBC. No compiler,
Cargo, exporter, VM, guest, decoder or capability subprocess runs. Both compiler.json
and runtime.json remain absent, including broken symlinks. No other project function,
file integrity check, lock, resource counter or timer is replaced.

Fixed schedule: four warmups AB/BA, then 12 measured pairs alternating AB/BA,
28 fresh Python processes total, one main call each. Shared absolute fixture/bundle/
driver/cwd/environment and one new task-owned PYTHONPYCACHEPREFIX. -I -S excludes
user/site state; -X pycache_prefix repeats the prefix because -I ignores PYTHON*
environment settings. Four warmups can populate the cache. Measured24 use -B and
must not alter cache contents/headers/source identity/directory count.

Cache bound: 512 regular files, 256 directories, 64 MiB total, 4 MiB each. Headers
must match pinned Python magic and actual source timestamp/size or PEP552 hash.
All file-backed loaded source/native-extension modules are bound, up to384 files/
64MiB. Frozen/builtin modules can have no runtime pyc. This proves cache eligibility,
not a private import-hook trace of each cache read; no import hooks alter the path.
Transitive macOS shared libraries are not exhaustively walked: pinned Python binaries
and observed native extensions plus the host environment are the explicit scope.

Before component timing the driver imports only json/os/pathlib/subprocess/sys/time,
also needed by the launcher. It rejects preloaded implementation/feature modules,
dataclasses and unittest; no unittest.mock/test helper. Both CPU/wall clocks start
before importing interpreter and end after actual main returns. Stub assertions and
audit-hook overhead are included. Provenance formatting is afterwards; parent wait4
CPU/wall/RSS cover the complete driver, including that reporting. Candidate stock
must leave custom_compiler absent and import compiler_association; baseline must
import custom_compiler. Captured boundaries match exactly after replacing each
sample's work-directory prefix with <WORK>.

The shared benchmark flock is exclusive/nonblocking; busy means no child. Fresh
memory_pressure -Q >=30% and statvfs >16GiB precede every launcher child. Admission
queries themselves have exact process/log/terminal receipts. A read-only controller
thread samples disk every5s during each child. It never signals anything. wait4
blocks without polling quantization; finally settles the exact child even if start
recording fails. All logs/raw rows are preserved. Size caps apply when reading logs,
not by truncating child writes; ordinary bounded Python outputs are expected.
A resource/identity/child failure stops before further samples without replacement.

This 16GiB category authorizes only tiny Python work, never the32GiB Rust builds.
No full-build/export/guest/holdout speed claim follows. Historical invalid-key and
parked streaming-hash measurements are not pooled with this independent screen.

Root must bind QUALIFICATION_SHA and review the final controller hash. Invocation:
the pinned Python launcher, run-screen.py, --execute-frozen-startup-screen.
screen-01 must be absent. No execution occurred while authoring this packet.
