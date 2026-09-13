# Qualified opt-in Darwin getcwd primitive

Source `c176cc5cd8228bdb2911a3438b51455b9acd5695` passed the full default
release workspace: 540 Rust tests, 10 ignored, zero failed/filtered, 49 suites.
All four required getcwd controls passed. Fresh exporter and VM builds then
passed both native comparison histories, with all 33 child receipts retained.
The primitive remains opt-in; this is not complete build-script support or a
performance result.

The controls cover caller-buffer and NULL allocation forms, including Darwin's
ignored NULL size, byte-exact cwd comparison, return-pointer relationships,
native errno, guest free/realloc, count/byte/register allocation budgets, host
errno preservation, invalid pointers/sizes/errno destinations, and default-off
admission before guest instructions. Both execution engines matched native
results in a cwd containing spaces and UTF-8. A wrong expected path cleared the
exact byte-match bit; four incompatible foreign ABIs failed during export.

The metadata stage completed 34 commands under supervisor/helper `46968/46971`
and froze 207 source snapshots. Plan SHA:
`10f414b4d290e79e764ca93f9d25e415d3794ad7deffce22ce58513e32d8ffb1`.
Qualification supervisor/helper `53545/53548` finished at
`1789337776.843849`. Its 13 outer children comprise the three qualification
commands and ten actual tool-loader inspections. The run receipt is
`007d9e9afc61c703f13e186415b347cb680db96e77c23b47d41a106cfc7f0d3e`.

Actual exporter SHA:
`3070c85bfc7ac227e4dad9898b74083db7a897fefe3502213385e18b2ba891ee`.
Actual VM SHA:
`f305425352073a31633b68a8627d32da93ab0d07112ee027062e5ce70ab2121c`.
The public compiler is `cea272fa356e94bd2ee2cadf376630aa0683867a`; prepared
std key is `bd27cc0f910e0c93a9a6cf088789ef526d36a8697a7717e08d7585f5d19467ef`.
Full compiler/tool/std/dependency/loader identities remain in the retained plan
and result records; installed toolchain binaries are not duplicated here.

Archive supervisor/helper `30685/30688` passed at `1789338204.413183` after
fresh source/runtime/std/configuration checks and pure replay of all native
receipt associations. The archive has 1,865 logical members, 1,427 physical
payloads and 5,418,294 bytes, all verified by readback:
`fae8161b9122039afdd9ffe577749232d7e25dcfe78f0d610a309d0c0a300c3b`.
The manifest uses original absolute paths without the leading slash. The
source documentation inside the archive correctly retains its pre-run status;
this report records the subsequent actual qualification.
