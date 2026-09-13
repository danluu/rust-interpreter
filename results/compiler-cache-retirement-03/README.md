# Owned compiler and screen cache retirement

The parent retired nine completed, task-owned generated directories after
revalidating 110,619 entries and checking active paths/inodes under the canonical
workload lock. Observed free disk space increased from 15,407,161,344 to
41,737,994,240 bytes. These are volume observations, not a benchmark or exact
attribution of APFS shared-extent reclamation.

The selected set comprises the three completed stable-CGU screen targets, three
completed macro screen targets, and the old compiler's `stage1-rustc`,
`stage1-tools`, and `stage2-rustc` outputs. The screen archives and saved artifacts
were independently verified before retirement and rechecked afterward. Source,
compiler installations/packages, LLVM/stage0 inputs, macro build05 and all raw
result evidence were retained. No benchmark was rerun or sample replaced.

`evidence.tar.xz` contains the exact saved plans, inspectors, candidate inventories,
ownership receipts, retirement runner and supervisor/result receipts. Every
member is indexed by SHA256 in `members.json`; the archive identity is in
`summary.json`. The archive builder replays the saved candidate filter, checks
all archived member hashes, and verifies original source bytes remained equal.

The inspection history is retained rather than collapsed into its successful
attempt. Inspection01 completed. Inspection02's filename `inspect.py` shadowed
Python's standard-library module through an indirect import, re-entering the
script and trying to reacquire its own lock. Only its exact owned PID43063 was
signaled after revalidating identity, cwd, lock descriptors and absence of
children. It exited130; the nested and subsequent exception-time receipts remain
in the archive. Inspection03 was corrected but never launched, then superseded
by inspection04's narrower candidate set. Inspection04 completed; the parent
performed fresh checks immediately before retirement03.

Complete host `ps`/`lsof` output remains local and is excluded from publication.
The published derived quiescence records contain only candidate matches (empty),
raw-output hashes and byte/line counts, command receipts and exit status. The
filter source is included. Inspection02's process evidence is scoped to its own
PID and identifies no unrelated process. Visibility is limited to what the
current user could inspect; this is a point-in-time observation, not a permanent
proof that no process can ever acquire a path.

This retirement supports disk admission for a future compiler build. It provides
no speedup, correctness qualification or final 0.5-second result.
