# Completed published build caches

Only the three exact successful builds in `catalog.json` are eligible. Failed
builds, arbitrary targets, guest caches and private work are excluded. Sources,
installed executables, capability receipts and build/test logs remain outside
the archived Cargo target. These are host caches, never benchmark artifacts.

`check.py` verifies the three real source/publication chains and exercises
incorrect ownership, command targets, completion, qualification and catalogue
selection. Run it before preparation. Every action holds the benchmark lock;
wait for every owned supervisor/child to finish before the next action.

Use `archive.py prepare --name ID --build BUILD`, review the resulting
`results/ID/plan.json` inventory and commit that exact file. Then use
`archive.py apply --name ID` and `archive.py verify --name ID`, each under the
experiment supervisor. Applying requires the exact committed inventory and
rechecks all external evidence before and after retirement. No benchmark space
floor is changed. Shared selectors stay frozen.

The archive is the existing `rust-interp-cache-zip-v1` format. Each payload is
decoded and hashed before originals are retired. To recover, use
`cache_archive.restore(archive_path, plan['manifest'], new_owned_directory)`;
it refuses an existing destination and verifies bytes, modes, times and internal
hardlinks. Filesystem identities and future Cargo cache reuse are not promised.
