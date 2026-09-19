# Verified options-hash plus packed-sidecars source

This publication retains the source composition and independent byte verification for candidate identity `e4d112c506f7b091c0e471c56ce25a1a8f62725ffa5676f7c977e105a1e450c0`. The exact generated patch, 29 base files, 30 candidate files, provenance, and six historical generator sources are under `../../experiments/hir-options-hash-packed-sidecars/`. Read that directory's STATUS.md for the current qualification boundary.

`execution/` preserves the two actual source-program histories, dispatcher and independent source readback; `reviews/` retains the two independent source reviews. `manifest.json` maps each published source/evidence byte to its original path and SHA-256. The original source and all prior compiler evidence remain unchanged.

No compiler, test, provider probe, benchmark, installation or combined-source checkout was executed as part of generation or this publication. The source processes recorded Popen child/parent identities, argv, cwd, environment, times, exit statuses and kernel session/group IDs. No separate ps or cwd probe was run. The historical allocation-failure statement is limited by infallible Arc and BTreeMap allocation, as STATUS.md records.
