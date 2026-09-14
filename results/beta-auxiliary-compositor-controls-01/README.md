# Synthetic B2 compositor controls

All ten controls passed with no skips at source `95d9501b`. The two new controls assemble one tiny archive member into two independently hashed ordinary files with distinct inodes, and reject collisions, chained copies and unrecorded repeated members before output. All eight original controls passed.

The archive preserves all tested source bytes and snapshots, exact ten passing names, raw stdout/stderr, child command/environment/PIDs/times, original supervisor and saved launcher/admission/helper association. Every member was read back and verified.

No real compiler archives, private artifacts or B334 contents were inspected by these controls. No B2 assembly, compiler build, runtime compatibility probe or benchmark ran. The source proposal remains unqualified for those later steps.
