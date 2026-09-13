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
