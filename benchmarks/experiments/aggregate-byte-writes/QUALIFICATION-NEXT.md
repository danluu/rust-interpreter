# Conditional qualification after both primary gates

Do not start this phase unless both completed primary assessments pass the
fixed criteria in RELOCATION-NEXT.md. A primary failure parks the transformation.
The candidate is isolated tool `9637b0acb1d208524c3c8b446af64cfd5e2d0d3be75e1412a8df76750ce36223`;
control is the immutable current 0e tool. No production compiler adoption yet.

First run the existing broad correctness drivers on the candidate:

- `qualify_native_execution.py`: all 47,004 commands across its two existing
  inlining modes, including 22,238 interpreter and 22,238 JIT invocations.
- `validate_tls_destructors.py`: all 245 commands and 24 artifacts; preserve
  actual panic/unsupported-call outcomes and original destructor assertions.
- `qualify_test_bodies.py`: the exact previously discovered fre list (389
  including seven ignored), fresh candidate exports and native controls.
  Compare every outcome to the prior qualified replay; differing artifact
  hashes are expected for this compiler change and must be reported.

Keep persistent registers and resumable calls on for JIT; native-tree/stub
options off. The interpreter remains the reference. Use each driver's existing
strict checks, immutable installed tools, exact source pins and original inputs.
Each child owns the benchmark lock; no competing waiter is launched. Record
exact PIDs/commands/start times and terminal receipts. Preserve any failure;
do not edit an active driver's sources or weaken an assertion to continue.

Then compare all seven existing held-outs, in the established order: Nushell
type relations, Ruff, Nushell, fre forward/TLS, pgrust SHA-1, pgrust, private
rg-aot. Use three cycles of five actual production edits, rotated mode order,
original/wrong-edit controls, source restoration and separate Cargo-check floor.
Both custom modes use the current identical runtime options and each case's
original guest flags; only the exporter differs. Native retains 18 jobs,
O0/incremental and default test concurrency; custom modes retain four jobs.
The aggregate comparison verifier must accept each independently bound case's
flags, including the empty list, while checking exact installed binaries and
executed tool keys. Qualify that extension separately before measurements.

Every held-out must stay within 5% paired wall and CPU regression. Report
absolute native/control/candidate times as well. Private output is aggregate
only. Do not pool heterogeneous cases to hide a regression. Do not adopt or
claim whole-suite support before complete correctness and held-out evidence.

Large-cache admission must use the previous verified complete-cache inventories
and include the 8 GiB running floor, growth, evidence and archive reserves.
Reuse the qualified estimators with new run identities and separately recorded
admission. Reclaim only reviewed, owned, completed public caches after all
receipts verify; never touch private, quarantine, active or unrelated workloads.
Keep failed starts and retries distinct, with a recorded reason and unchanged
measurement controls. Do not make the host idle by controlling other work.
