# Per-item compiler integration qualification

Status: source implementation only; not built, executed or qualified.

The existing 36-command custom-compiler fixture can select the per-item policy
with `--partitioning-policy stable-mono-cgu`, both explicit prepared std-v2 keys,
and strict diagnostics. Module partitioning stays off in both modes. The same
host build script, host procedural macro, native/public reference, guest result,
uncalled errors, source edits, bytecode comparisons and restoration remain.
No benchmark command enables the recording or diagnostic mappings below.

`--compiler-argv-record-dir` enables optional compiler-call evidence. The
lightweight wrapper records the actual native argv immediately before exec;
the exporter records the actual final driver argv. Each role/process creates
one exclusive file containing a versioned, UTF-8, NUL-delimited envelope:
version, route role, compiled sysroot, cwd, and individual arguments, including
the executable. A missing or invalid destination fails before compilation.
No shared append file or shell quoting reconstruction is used.

Qualification retains both the raw envelope and its lossless JSON decoding.
The flag proof binds those files to both off/on modes and to actual host and
selected-guest roles. Every compiler record must contain exactly one module=no
and mono=no/yes flag, without mixed worker policies or response files. Ordinary
Cargo verbose output remains additional route evidence, but does not substitute
for the actual post-routing arguments.

The standard diagnostic mapping helper verifies identical source bytes and
configures the compiler's diagnostics-only remapping consistently for public,
host and guest roles. Saved raw JSON is checked for actual standard source text
and compared using the existing strict structured comparator. The preliminary
source-derived comparison is not permitted. Successful fixture qualification
can mark presentation qualified for this integration only; adoption, final
latency and holdout claims still require their separate protocol gates.

The result binds its original plan and all completed child receipts, raw
fingerprint diagnostics in commands.json, compiler argv evidence, bytecode
snapshots, fixture/configuration and exact Python producer sources. This source
checkpoint provides no successful compiler, integration or performance result.
