# Unchanged build-script export support census

Four actual compiler commands completed successfully: one metadata-only helper
compile and three strict `main` lowering audits of the unchanged native-qualified
build script. Default, native-shared-helper and unsupported-build-operation
configurations all reached the same first blocker:

`libc::unix::getcwd: MIR unavailable for libc::unix::getcwd`

Each report records one requested entry, zero lowered, one blocked and
`executed: false`. No Cargo, VM, native build script or guest program ran.
This establishes the first blocker only; later support and latency are unknown.

Metadata01 completed with zero children and 21 snapshots, then remained
unexecuted. After PRIMARY advanced, metadata02 bound the original qualified
202-source inventory through its immutable archive while retaining live Python,
binary, std, dependency, configuration and fixture checks. It completed with
zero children and 224 snapshots. Plan02 is
`cb70041ada99117cb9b8f08e476347b2fbadaf3317ba4dbbd6bb22c034164587`.

Actual run supervisor/helper `14890/14893` finished at `1789336861.902641`.
The four child PIDs are `14896`, `14899`, `14903`, `14907`; all returned zero.
Raw command/environment/stdout/stderr receipts, copied fixture, helper metadata,
three audit reports and identical audit sidecars are retained. The exporter
source is `a66cdf6781ed321e93702e2c049336ad064e29f9`, actual exporter SHA
`197a70d080c7da7545544b77ee23145bef74f21ea3c1db4e5cfc557547d8a3ac`.
Public compiler, prepared std and native-baseline associations remain in the
exact qualified archive references; those archive payloads are not nested here.

Archive supervisor/helper `79538/79541` passed at `1789338079.623133` after
fresh runtime/source/fixture guards and full member readback. The archive has
328 logical members, 264 physical payloads and 997,963 bytes:
`5af71dd977d71930703c5c90f0570fa8661f52bd4092e8c10434b27640f77326`.
The manifest uses original absolute paths without the leading slash.
Initial metadata01 launcher stdout was not separately saved; its actual
supervisor identity and terminal receipt remain preserved.
