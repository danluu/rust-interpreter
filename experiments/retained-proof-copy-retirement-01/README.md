# Exact historical proof-copy retirement draft

Source only. No preparation, imports, recovery payload reads, probes or removal
have run through these files. This directory belongs to the independently
reviewed continuation; it does not modify any prior packet or source.

## Phase order and narrow APIs

The following additions are source drafts only. Unset values are missing actual
evidence bindings, not requests for new user approval.

1. `prepare_recovery.py` will freeze the exact recovery source and metadata,
   archive identity, 61-copy inventory, current originals and 21 prior-catalog
   witnesses. It does not require retirement or a post-retirement Reader. Its
   future explicit wrapper preserves admission/source/raw/PID/exit records.
2. `execute_recovery.py` will run one `recover.py` child under canonical admission
   with fresh 16 GiB entry/live 9 GiB, bounded CPU/time/read/output limits and no
   signals. `recover.py` loads only the pinned recovery source, calls
   `recovery.verify(guard)`, and retains its exact report. It cannot retire files.
3. Runtime04 independently qualifies its current-or-historical Reader and
   collector using a strict-callback rehearsal while all 61 copies still exist.
   Its reference context is the original 109,343 rows minus exactly 21, while
   all physical operations remain strict. The predecessor catalog is built
   before the Reader; the successful hash02 extension follows Reader checking.
   Neither this rehearsal nor recovery requires a retirement result.
4. A separate retirement packet binds actual40, actual closed recovery, actual
   Reader rehearsal, protected files and explicit consumer acknowledgments.
   No recovery packet or completed audit is rewritten to create this packet.
5. `no_consumer.verify(packet, proposal, output, canonical_fd, admitted_at, guard)`
   runs only inside the actual retirement admission. It reads exact acknowledged
   consumer metadata and runs fixed read-only lsof queries for the 21 paths plus
   ps queries for explicitly bound historical owner PIDs. It performs no host-wide
   process listing, process control, signals or guessed ownership checks. All
   probe source/raw/PIDs/times/exits are retained; unresolved children refuse.
6. `retire.py` requires all actual evidence, rechecks current bytes and invokes
   the qualified file-only remover. Independent final ledger verification and
   the subsequent runtime discovery follow actual removal. Only this last
   discovery may require the exact 21 paths absent.

The future no-consumer adapter must return the complete proof checked by
`retire.py`, including the exact proposal/path set, admission PID and fresh
timestamps. Its packet supplies exact closed-owner receipt/identity references,
explicit currently prepared/active consumer records and task-owner acknowledgments;
absence is not inferred from PID age, process names or a missing packet alone.
No phase may call the original full-live auditor after retiring its copies.

The outer dispatcher's source is retained in each explicit execution capsule.
It is excluded from the recovery packet's executable-source table because its
later actual packet-digest binding must not change one of that packet's inputs.
Before binding the actual recovery phase, preserve the unbound dispatcher and
its exact source diff; separately review the final bound dispatcher. The three
reader/preparer sources remain unchanged once their packet is prepared.

The immutable proposal is X's `runtime04-retained-copy-retirement-proposal-01.json`
(`e0599d87...`). Scope is exactly 21 non-executable, single-link ordinary files
under O's closed run-make `retained` directory. Its 61-entry manifest remains
unchanged; all 40 other files and the directory remain. The selected files total
25,677,060 bytes. This is an evidence-cap measure, not a claim that global free
space meets the separate 24 GiB compiler-entry gate.

`recovery.py` is a read-only library. A later reviewed bounded wrapper must own
its one actual invocation, canonical lock, source/raw/PID/exit records and CPU
limits. Its `verify(guard)` authenticates proposal/design, complete original
109,343-row typed file table, the closed run-make and successful hash02 records,
and exact archive/member mappings. It checks all 61 current copy bytes, all 21
still-live original sources, and all 21 compressed witnesses through complete
gzip/logical EOF and digest. The old archive is consumed through its gzip
trailer and every one of its 1,191 ordinary members; nothing is extracted.

The archive bounds retain the existing run-make archive's 64 MiB compressed,
384 MiB logical and 1,536-member limits. A finite 392 MiB expanded-stream bound,
64 MiB individual input bound, 1 GiB cumulative read bound, 600-second checked
wall bound, and 300-second CPU bound apply to recovery. These are recovery-read
limits, not permission for new archive production or increased runtime evidence.
The earlier design note mentioning 256 MiB archive recovery was superseded by
the actual archived producer's unchanged 384 MiB logical limit before execution.

The nonrecursive bootstrap is concrete: all 21 witnesses are exact reused rows
in the already completed stage03 plan's 464-record predecessor catalog. The
helper's reference context is the original full table minus exactly 21 copies
(109,322 current rows), independent of future runtime source additions. A future
qualified runtime Reader must then perform its normal current-file check and
successful hash02 catalog extension and reproduce the same witnesses.

`retire.py` is deliberately fail-closed. Eight future source/report pins
are `None`; the exact packet SHA is supplied through `--inputs-sha256`; running it now refuses before importing helpers or creating work.
It requires the actual40 independent audit `c803f6e6...`, a separately qualified
runtime04 Reader/collector rehearsal, actual closed recovery, and a separately
reviewed no-consumer adapter. A rehearsal must explicitly say copies still
exist: it grants neither runtime admission nor retirement authority. The
proposed reader report route is
`ROOT/.work/runtime04-historical-copy-reader-independent-verification-02.json`.
Its exact status/schema and digest remain to be qualified and reviewed with X.

The no-consumer adapter is drafted but unqualified. Its future pinned source must inspect exact
selected paths and explicit closed producer identities, authenticate acknowledgments
and prepared/active consumer scope, and retain full read-only probe receipts and
raw streams under the same canonical admission. No signals are allowed. A stale
generic report cannot satisfy this gate. Before binding it, review the exact
source, expected process identities, probe commands, finite bounds and independent
verification. No current or pending consumer may be silently treated as absent.

After all gates, the wrapper rechecks current copies/source/witness bytes and
invokes only the original qualified `fd_remove.remove_files` (`83413590...`),
bound to its six passed controls. It does not copy/edit that helper, change modes,
remove directories or recreate missing paths. The 21 ordered removals require
exactly 63 durable intent/unlinked/validated events, including held-file link
transitions and directory identity/membership transitions. Partial failures
retain the original ledger, uncertain intents and terminal error without retry.
All 40 preserved files and source/witness bytes are read again afterwards.

The retirement envelope keeps canonical wait 600 seconds and 9 GiB live checks,
with an explicit 16 MiB entry/output reserve, 16 MiB per-file/aggregate retained
bound, CPU 300 seconds and checked wall 600 seconds. Fresh `prepare_retirement.py`, `execute_retirement.py`, and
`verify_retirement.py` now implement the remaining packet/outer/audit source
drafts. They have not been imported or executed. The no-consumer observations
and removal remain unrun, with future evidence pins unset.
The existing directory and outer-parent identities are preserved as history;
the retained directory's legitimate post-unlink stamp is reported separately.

The final runtime representation must leave ordinary `file`, `identity` and
`file_record` APIs strict. Historical copies never satisfy current-path reads.
Original full-live audits remain immutable completed history and cannot be
rerun against missing copies. Fresh actual allocation is the only source of
space credit after separately approved removal and independent audit.


Current readback and remaining draft interfaces
-----------------------------------------------

Recovery preparation and readback have now passed once under the reviewed
16/9 GiB canonical envelope. The exact packet is `f27de377...`, the report is
`ROOT/.work/retained-proof-copy-recovery-01.json` (`b671db7b...`), and the
explicitly closed recovery execution record is `85ce36c2...`. All 61 copies
were still present; no file was removed. These concrete recovery bindings are
used by the new retirement preparer and independent audit. The executed
`recovery.py`, `prepare_recovery.py`, `recover.py`, and `execute_recovery.py`
remain unchanged by the new drafts.

The actual52 runtime adapter controls and independent audit have passed
(`4cb7aa61...`). A separate real strict-callback rehearsal is still required.
Its future digest remains `None`; pure controls cannot supply that digest.

`prepare_retirement.py` reads an explicit, pinned declaration document with
`status`, `proposal_sha256`, `owned_consumer_roots`, and `no_consumer`. The last
field contains exactly the adapter's acknowledgments, current consumer packets,
closed owner receipts with actual start observations, pending exact absences,
two executable records, and environment. The four task-owner acknowledgments
must already exist as real evidence. The preparer creates none of them and
does not perform the two process observations. Its finite closure is at most
512 ordinary protected files and 384 MiB of declared immutable bytes; the
existing read budget stays 1 GiB. Target copy rows are excluded from the
protected current-file table and remain solely in the historical inventory.
Current consumer tables can be flat or use the qualified, disjoint two-field
`file_table_base` reference. Broader `base_inputs` proof envelopes fail closed
until their separate schema is reviewed.

`execute_retirement.py --phase prepare` and `--phase audit` own canonical
admission for one read-only child at fresh16/live9. `--phase retire` enforces
fresh9 GiB plus the existing16 MiB reserve and then observes the controller,
which owns canonical itself. It waits at most1250 seconds for the controller's
600-second lock wait plus600-second admitted work; no timeout sends a signal.
Every phase has a distinct fresh execution directory. The retirement's16 MiB
retained cap covers both WORK and its outer execution evidence. The explicit
Popen request time bounds actual child start, without pretending that the
parent's post-Popen observation necessarily precedes the child's clock.

The packet digest is passed through `retire.py --inputs-sha256` and bound by
the outer after preparation. This avoids freezing a source that must later
change to contain its own packet's digest. Preserve each unbound outer and
its constants-only binding diff; the outer itself is retained as execution
evidence, not an input whose digest creates that cycle.

`verify_retirement.py` accepts exact `--inputs-sha256`, `--receipt-sha256`,
and `--execution-sha256` values only after actual passed closure. It imports
only the pinned, actually exercised recovery reader, never the controller,
consumer adapter, or remover. It independently replays all63 durable events,
checks all40 preserved current files, all21 live originals and full gzip
witness EOF, both saved exact-path/PID probes and their closed receipts, the
complete WORK/outer membership, and immutable source/proof bytes. Its report
route is `ROOT/.work/retained-proof-copy-retirement-independent-verification-01.json`,
with status `verified-exact-proof-copy-retirement`. This is the distinct
post-retirement proof required by production runtime04 admission. The report
records actual free-space samples and no inferred capacity credit.


Closure and environment correction (source only)
------------------------------------------------

The original reviewed drafts are retained under O's
`.work/retained-proof-copy-before-closure-environment-01/`, with per-file diffs.
The rehearsal01 preparation failed closed before packet outputs; its immutable
execution has an actual finished nonzero child and no recorded canonical release
time. Successor02's independent report route is now explicit above, still with
a future digest. No missing PS row or release timestamp is synthesized.

`closed_owners` uses exactly two typed PS-child schemas. `normal-child-v1`
requires its actual `finished_at`, return code, and saved `identity.ps`.
`driver-wait-v1` preserves the driver receipt's `wait`, `child_finished_at`,
and `controller_finished_at`; passed status, zero wait return code, empty
errors, and false child/probe-live flags are required. Only these explicit
saved PID/start observations feed the bounded PID query.

`closed_metadata` is a separate list. Supervised owners bind terminal, actual
outer, launch declaration, independent audit, and launcher. The old run-make
launcher-finished schema stays distinct from later terminal-observed wrappers.
Direct read-only readers bind their result to a zero-return closed execution.
The original rehearsal01 failure instead binds its exact failed execution,
stdout/stderr, and four absent packet outputs; an absent release timestamp
stays absent. None of these metadata records requires a root interpreter to
disappear or is rewritten into a synthetic PS-child receipt.

The installation worktree is
`/Users/danluu/dev/rust-interp-runtime-installation-r-20260918`, as specified by
runtime04 `entry.R`. It is the fifth permitted task-owned root for explicitly
listed future runtime WORK/outer paths. There are still four task actors, and
all four final acknowledgments remain unbound until rehearsal/current consumers
are settled. This expands no process or directory scan.

The preparer no longer requires an unobserved CF key. Every observation retains
complete `passed`, `observed`, and `additions` maps plus empty `changed` and
`removed` maps. The only permitted additions are none or the exact previously
validated macOS `__CF_USER_TEXT_ENCODING=0x1F5:0x0:0x52` value, bound to the saved
read-only startup diagnostic `edc973c0...`. This diagnostic permits that value;
it does not claim every program adds it. Initial, pre-helper, and post-helper
preparation environments are saved in the packet. Controller observations
include before and after helper imports and before and after removal. The
independent audit checks every complete map and records its own observations.
Any other added, changed, or removed key refuses without normalization.
