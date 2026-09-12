Basic pgrust passes its 5% retention gate: paired candidate/baseline wall ratio **0.999165**, CPU ratio **0.997328**. There is no meaningful measured regression or gain from fixed clearing on this short workload.

Across three cycles and five edits, complete-command medians are native **0.648s**, baseline **0.476s**, candidate **0.472s**. All 63 primary commands, 21 Cargo checks, 15 edited pairs and 42 artifact hashes verify. Paired bytecode is identical; original assertions, wrong production edits and source restoration are retained.

The first attempt refused the shared benchmark lock before commands or edits. The completed attempt used the same benchmark protocol and an independently bound estimate of the four full pgrust caches, including native object files, 20% growth, the 8 GiB floor and archive/evidence reserves. No timing sample was discarded or retried.
