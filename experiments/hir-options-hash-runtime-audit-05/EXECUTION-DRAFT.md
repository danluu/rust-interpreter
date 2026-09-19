# Phase-specific supplemental manifest and saved-audit executor

These sources are drafts. Neither has been imported or executed. The four
actual53-tested sources remain unchanged; the enclosing bootstrap and audit
core are being integrated separately with the startup owner adapter. No
runtime invocation, manifest, test run, probe, deletion or compiler call has
been performed by these sources.

The order avoids referring to a preparation's own future completion record:

1. Qualify the startup adapter with its separate actual39 controls and complete
   independent audit. Finish the enclosing bootstrap/core source review.
2. Complete the actual preparation of the chosen runtime phase, under its own
   reviewed preparer. Preserve its record, seven evidence files, invocation,
   source manifest and exact packet output identities.
3. Review a final source inventory and bind the explicit integration source
   list and actual39 chain anchors. The inventory is exactly `{policy,sources}`,
   policy `runtime05-reviewed-sources-v1`, with absolute paths mapped to SHA256.
   It includes eight audit05 Python files (core/bootstrap/four tested sources/
   these two executors) plus the explicitly listed adapter sources, including
   `environment.py` and `audit_owner.py`. No directory scan selects authority.
4. A separately authorized `execute.py prepare --phase ...` invocation supplies
   that inventory digest and the actual runtime preparation record and launcher
   source digests. The parent holds canonical and passes its descriptor to the
   manifest preparer. The preparer authenticates the complete actual53/45/39
   control chains and the already closed phase preparation before publishing
   only a fresh phase-specific supplemental manifest and summary.
5. After that runtime phase's actual workload and dispatcher have closed,
   review a distinct `execute.py audit --phase ...` invocation. It supplies the
   manifest, its completed manifest-preparation summary and observer record
   digests, plus all seven actual phase digests. The parent holds canonical and
   passes its descriptor to the bootstrap for full independent saved readback.

The manifest may be prepared before or after the phase workload, but always
**after the phase preparation has explicitly closed**. It does not admit a
runtime or create any runtime packet. Manifest preparation and independent
runtime verification have separate fresh observer evidence directories.

## Exact wire contract

The manifest has exactly seven keys:

`{policy,files,actual53,phase45,preparation,preparation_launcher,startup_controls}`

The policy remains `runtime04-saved-audit-source-manifest-v1`. Every reference is
exact `{path,sha256}`. `preparation` names the chosen phase's actual runtime
preparation record; `preparation_launcher` names its original wrapper source.
`startup_controls` names the independently verified actual39 report. The
bootstrap derives its two expected preparation references directly from these
pinned headers; there are no duplicate new bootstrap CLI bindings.

Each file row has exact `{size,sha256,identity}`, with all seven ordinary-file
identity fields. The complete supplement remains limited to 256 rows and 8MiB
of logical input bytes. Equal paths get one row; conflicting typed identities
are refused. Input reads hold nofollow ancestor descriptors through complete
payload reads and final leaf/route checks. JSON rejects duplicate keys and
nonfinite numeric constants.

The complete control closure covers each original packet, every frozen source
and tool row, actual receipt/result/child raw triple, outer plan/status/log,
dispatcher source/record/raw handoff, independent auditor/executor sources and
retained source copies, explicit execution record/raw and report, and original
control preparation record/raw/all five retained preparation sources.

The actual runtime preparation adds its seven files:
`record.json`, `stdout`, `stderr`, `launcher.py`, `invocation.json`,
`source-rows.json`, and `child-observation.json`. It also includes the original
wrapper source, original `record.invocation.path`, and adapter source-manifest
file. Its declared seven packet output identities remain preserved in the
closed record and summary. The bootstrap/core independently reread the actual
packet under the original phase scope; this preparer does not duplicate those
packet files or recursively copy the hundreds of original source/provider rows
from `source-rows.json` into the small supplement. The combined original table
and supplement authenticate those overlaps.

The existing actual53 report SHA is
`8eab665dd1cd8107ff203056decf12b54c5f0724e3332fe5f6ccdf6f61a54333`;
the actual45 report SHA is
`c86c5f2e33c0aeed5b67fd75256e20f47626b21bdbb494bcd4eb6b74af57b25d`.
Those are completed control qualifications. The actual39 report is now
`016e80b8169e8da75a82d29cecb3be9c0dd3e89cd6deae90b50522b927fa88f0`;
its passed preparation and closed audit-execution records were read back and
bound separately. The prior unbound source and exact three-value diff are
retained. `INTEGRATION_SOURCE_PATHS` remains `None`. The parent checks those literal declarations by AST before creating
execution evidence, importing the lock helper or starting a child. The final
source inventory, both runtime phase preparations, manifests and runtime invocations
remain unbound.

## Fresh routes and bounds

For each `phase` (`preflight` or `installation`), the manifest output is
`ROOT/.work/runtime05-saved-audit-{phase}-manifest-01/{manifest.json,preparation.json}`.
The observer for that manifest preparation uses
`ROOT/.work/runtime05-saved-audit-{phase}-manifest-preparation-execution-01`.
The saved-runtime auditor's separate observer uses
`ROOT/.work/runtime05-saved-audit-{phase}-execution-01`.
The original bootstrap report route remains
`R/.work/hir-options-hash-runtime-{phase}-independent-verification-04.json`.
All must be fresh. No earlier failed source, rehearsal, packet or record is
rewritten.

The parent requires 16GiB before evidence/child creation and again after the
canonical wait. Canonical timeout is 600 seconds; live floor 9GiB, declared
stop floor 8GiB, child CPU 900 seconds, child read interval 1200 seconds, parent
observation interval 1250 seconds, maximum output/report file 4MiB. Only the
exact manifest preparer or bootstrap child is spawned, with fixed unoptimized
`Python -B`, recorded clean passed environment, cwd `R`, and the inherited
canonical FD. The child does not acquire a nested lock. The startup adapter
owns the actual passed/observed environment contract; this executor invents no
macOS environment addition.

A fixed deadline is set immediately after `Popen`. Publication and disk sample
errors are collected while bounded waiting continues. The actual return code
and closure time precede raw hashing and final publication. Any observation
error prevents qualification. Deadline expiry retains `may_be_live: true` and
`unclosed-task-not-signaled`, with no signal, successful-completion claim or
workload retry. Parent/child identities come from the interpreter and `Popen`;
lack of separate contemporaneous process probes remains explicit.

The derivation is the corrected, unexecuted Reader02 auditor executor source,
SHA `effbd39c7c62f6a974c93b801a66ae172edeade3acb2ed777c0b6f762fb4f07f`.
It is a reviewed source pattern, not a claimed actual successful audit.
Handoff01 and all three prior draft files are preserved in O's
`.work/runtime05-saved-audit-before-phase-manifests-01` with exact diffs.

The seven runtime SHA bindings are launch, compact inputs, snapshot plan,
actual receipt, actual source-probe result, outer status, and dispatcher
record. Full provider bytes, logical selection, physical snapshot references,
directory membership, historical retirement and runtime children remain the
independent bootstrap/core's responsibility. The parent reads only explicitly
named small closure inputs before handing off; it never invokes a compiler or
runtime constructor.
