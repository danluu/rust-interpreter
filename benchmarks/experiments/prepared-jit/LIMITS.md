# Record effective suite limits

The fre catalog follow-up omitted the established allocation limit and initially
looked like a lowering failure. The same bytecode passes at the reference limit.
Record the actual per-test instruction, live-allocation, memory and frame limits
in the VM suite report on success and test failure. Record the code budget
separately because prepared tests share one JIT owner. Do not change any limits,
guest semantics or the existing report version; these are additive fields.

The launcher checks present effective limits against its CLI options. Workflow
verification compares them against the independent report configuration. Preserve
support for older immutable VMs without this receipt, while new qualification
requires it explicitly. Test the omitted-150,000/default-100,000 mismatch and
per-test budget failures. Qualify workspace debug/release and Python tests, then
replay existing pgrust/fre/Ruff catalogs with expected numeric limits. Use the
current catalog exporter/wrapper unchanged for the runtime-only tool composition.
Run one actual pgrust edit to verify launcher/report integration. No timing gate
or performance claim is appropriate for these diagnostic fields.
