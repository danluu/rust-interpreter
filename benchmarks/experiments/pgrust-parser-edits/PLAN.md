# Complete parser edited-source baseline

Use all 114 original gram_core library tests at pgrust revision
38d2517d3e09168a8fe222837730d435238ff358, including reference vectors.
Change only production parse.rs. Five cumulative edits refactor lookahead
dispatch and parser-table boundary conditions. A separate wrong edit reverses
the initial lookahead predicate. Require exactly the same native/custom test
names and outcomes, original assertions, and restoration on every exit.

Run each profile as its own declared experiment: repository defaults (line
tables, unpacked debug information, incremental=false) and the same profile with
CARGO_INCREMENTAL=1 for every native and custom command. Keep two Cargo workers,
native libtest default threads and two isolated prepared custom workers. Use
strict checking, automatic function reuse, cached toolchain lookup, leaf
inlining, resumable calls, persistent registers, original instruction/allocation
limits and qualified tool8c2d64bb. No profiler, entropy shim or guest backend
fallback. Both custom arms are identical and have independent fresh namespaces;
native has its own fresh target directory. Do not share mutable compiler caches.

Each profile has three cycles of original, wrong, five cumulative valid edits,
then one final executed restoration: 22 source states, three commands each,
66 complete build/test commands. Rotate the three mode orders using the existing
workflow ordering. Freeze all states, source/tool/helper digests and full command
templates before the first command. Do not restart a failed or completed cycle
to seek a preferred timing. Stop on failed correctness or admission and retain
the prefix; any continuation needs a separate audit and plan.

The predeclared timing statistic is the median of 15 per-edit custom-A/native
wall and child-tree CPU ratios. Custom-B/custom-A provides same-session A/A
variation, reported both as a paired median and as the maximum absolute per-edit
median deviation across the three cycles. Preserve all observations and the
per-edit spread. These are descriptive measurements, not confidence intervals.
Custom B is not a second independent native control. First-command costs use
fresh target namespaces but retain installed tools, standard MIR and shared
dependency downloads; label them accordingly. Exclude originals, wrong edits
and restoration from edited warm ratios. No unchanged-build performance claim.

Require 18GiB initial free space per profile, with an 8GiB per-command floor and
the shared45-second benchmark lock. This conservatively allows two parser custom
caches, one native cache and retained per-state artifacts; it is not a reservation.
Read the independent disk sampler before launching; do not create another cleaner
or control another session. Existing support and five-project checks are separate
correctness evidence. This baseline guides the next optimization; it makes no
claim that capacity/environment support itself is a speed optimization.

## Retained prefix and validator repair

Repository run01 completed native and custom-A original commands, both114/114,
then rejected Cargo's `Compiling gram_core` label. The pinned launcher actually
uses cargo check --profile test and the exporter ran successfully. The offline
prefix audit verifies every original frozen input, both logs, source restoration,
suite/artifacts, and terminal receipt before changing the validator. Accept either
Checking or Compiling for this selected target and still require exactly one
exporter completion marker. Qualify this boundary and prefix rejection controls.

Continue only those two retained commands, using the same original native cache
and custom namespaces with a fresh output directory and64 unstarted commands.
Bind repaired input files to their original Git blobs and the successful prefix
audit; reject other source changes. Keep timings and schedule unchanged, record
prefix/new command counts separately, and preserve all native executable versions
as well as bytecode/catalogs. A separate incremental profile remains a new66-command
experiment. No edited timing has been collected in the stopped prefix.

## Revised incremental comparison: preserve compiler-history differences

The original incremental experiment remains failed at command22 under its
cross-cycle byte-identity rule. A separate eight-command diagnostic reproduces
its exact cold and restored artifacts with function-template reuse disabled.
Observer-off/on byte identity holds. Four qualified origin inspections show
one/one/two/two exact initialized string allocations, with distinct compiler IDs
before exporter layout. Keep those identities; do not normalize bytecode.

The separately identified continuation uses `--artifact-history paired-cycle`
and the sealed22-command prefix. It retains every completed timing and runs44
unstarted commands in the same cache namespaces, schedule, profiles and limits.
Skip completed states without rewriting their sources. Check every retained
command against its template, logs, artifacts, source hash and frozen schedule.
Bind the revised rule to the successful allocation-origin proof and unchanged
tool. Native assertion outcomes, wrong controls and restoration remain mandatory.

Custom A/B must still produce byte-identical artifacts/catalogs at every matching
cycle and source state. Cross-cycle identities are explicitly recorded rather
than required; this models the observed compiler cache history. Original and
wrong states remain excluded from timing ratios. Keep the same15-pair statistics
and A/A variation report. This is a corrected baseline measurement protocol,
not an optimization acceptance gate or a change to the failed study's verdict.
The repository-profile result keeps its original stricter identity proof.
This continuation admits at16GiB because all three compiler namespaces already
exist and are checked before launch. It adds44 warm commands and preserved
artifacts, with no new native/custom namespace. The8GiB per-command floor stays
unchanged; fresh-profile experiments retain their18GiB admission. The preceding
audited retirement removes only completed public compiler intermediates and
preserves all evidence; its reclaimed space is not assumed to remain available.
