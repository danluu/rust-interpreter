# Runtime source qualification

Source `b7c2ba4f1f47dff32331ec5b2815b6d823740a65` passed all four focused
expectation controls and the existing-runtime source preflight. The controls
reject wrong virtual prefixes, missing standard-library expansions, missing or
forged snippets, and changed source bytes; they also verify that validation
leaves raw diagnostic records unchanged. Supervisor 95472, helper 95475 and test
process 95477 are bound by the retained command, environment and timestamps.

The native preflight completed twelve children: five source Git guards, two
compiler probes, and the same five guards again. Supervisor 3549 and helper
3552 ran from canonical admission 1789350183.323735 through 1789350197.057533.
Both compiler processes exited normally with the expected E0080 error for the
unchanged uncalled constant-panic probe. Process 3778 exposed real standard
source paths and matching snippets. Process 3868, with local-path translation
disabled, exposed the exact `/rustc/7efc0d9484da82cd327deb3b48616f8ec81eaf8d/library`
prefix. Its absent snippets are accepted only for this virtual-identity control.
Both probes exposed `core/src/panic.rs` and `std/src/macros.rs`.

The complete source, runtime and standard-source provider guards passed before
and after the probes. The final receipt is
`8bd341a23550e0d77c0bf7f6472811bb1586cad1af9a214a7be1d5684a7af4dc`.
All 170 native-preflight inputs and retained copies, all 63 control inputs and
copies, actual child arguments/environment/process associations, and raw streams
were independently checked after completion.

`evidence.tar.gz` preserves complete run directories, source snapshots, plans,
launches, supervisors and the archive source. Its 302 logical members resolve to
196 distinct payloads; full member readback and gzip EOF/CRC validation passed.
`manifest.json` binds every member's source path, size and SHA-256. The archive's
own nine execution records are separately retained and bound by
`archive-execution.json`, including supervisor 42287 and helper 42290.

This qualifies the existing E runtime's observed standard-source behavior. It
does not install or publish a runtime, add a source capability, qualify the final
installation callback, prepare std MIR, or establish application compatibility
or a build-time improvement. The original metadata candidate is unchanged.
