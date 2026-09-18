# Owned native sampling recognizes this host's anonymous arena label

The retained failed block capture contains twelve successful vmmap reports.
Each labels the owned VM's actual emitted arena `Untagged`, so the old
`VM_ALLOCATE`-only readiness expression never started sample. The guest itself
passed. The failed capture is closed, and its exhaustive successor is unstarted.

Capture readiness and summary now share a parser accepting these two observed
labels with the exact owned-VM PID header, complete positive address bounds and
`rwx/rwx` permissions. Invalid and overlapping ranges are rejected. Attribution
still binds each captured process's own emitted-code map and arena containment.

All 427 Python tests pass, with 22 declared skips; the nine attribution controls
also pass against the changed summary dependency. All 14 retained real reports
(twelve current and two historical) contain their independently recorded emitted
arenas under the new parser. The closed check binds 495 source files and 29
evidence files. It executes no guest and establishes no runtime speedup.

Fresh diagnostic capture will use new02 namespaces. This fixes a demonstrated
format mismatch; it does not repeat the rejected composition's timing study.
