# Historical cache and superseded package retirement

The parent retired the completed profiling target and two obsolete compiler
package prefixes after fresh canonical-lock checks of ownership, saved evidence,
file identities, publication dependencies and active paths/inodes. No benchmark
was rerun and no observation was replaced.

| Retirement | Removed roots | Entries revalidated | Observed free bytes before → after |
| --- | --- | ---: | ---: |
| 04 | PRIMARY `.work/strict-warm-profile-01/target` | 14,911 | 34,141,548,544 → 37,100,527,616 |
| 05 | Old compiler build `packaged-stage2-03` and `packaged-stage2-05` | 16,773 | 36,480,458,752 → 38,931,222,528 |

These are volume observations affected by other disk activity and APFS shared
extents. They are not exact per-directory physical reclamation measurements.
The profiling target had 2,954,264,576 allocated candidate-only bytes at inspection;
the package pair had 2,448,838,656. No external hardlinks or visible active users
were found at either inspection or the parent's subsequent retirement checks.

The profiling cache was associated with seven completed states across the
original profile, self-profile and Cargo-profile runs. Their 1,951 raw evidence
files, saved artifacts and source-restoration history stayed outside the deleted
target and were rechecked afterward. The package comparison maps bind every
candidate file to the retained package06 and installed compiler60096 copies;
the 6,982-file retained union, 776 evidence files and 24 publication/plan documents
were checked before and after removal. Complete package receipts and native
control result identities are included here; native/compiler binaries and the
large original profile payloads are not duplicated in this archive.

The completed integration test target was inspected but **not deleted**: its
127,295,488 allocated bytes were insufficient for the immediate admission need.
Its prior 490-test result and 336-member evidence archive remain bound by the
inspection receipts. The old extracted CI LLVM and additional raw compiler
stage roots were also **not deleted in these attempts**. The nine-root retirement
03 is a separate, previously published action.

The original compiler prepare01 failed its 36-GiB entry requirement with
36,403,642,368 free bytes, before any child command or source creation. That
failure remains retained. After retirement05, prepare02 passed its eleven
setup commands; its receipt is included to preserve the admission sequence.
Source freezing and the later compiler build are separate steps.

`evidence.tar.xz` contains exact saved inspectors, inventories, comparison and
retention maps, retirement runners, supervisor/result receipts and the selected
ownership records. `members.json` indexes every archived member by source path,
size and SHA256. `summary.json` records the archive identity and outcomes. The
archive builder verifies all members and rechecks its source bytes after writing.

Full-host `ps`/`lsof` output was never retained by these inspections or retirement
runners and is not published. Only candidate matches (empty), raw-output hashes,
counts, exit status and filter source are present. Process visibility is limited
to the current user and to the time of each observation.

All source, latest package06, installed compiler identities, tool publication
roots, macro build05, LLVM/stage0 input archives and raw results were preserved.
This evidence supports setup disk admission; it makes no speedup or final
0.5-second qualification claim.
