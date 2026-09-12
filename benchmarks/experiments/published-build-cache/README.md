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

`runtime.py` supplies a separate read-only evidence selector to that unchanged
archive lifecycle. Its exact catalogue is the four completed guarded-Call
histories and four target modes. It recomputes the qualified workflow assessment,
checks the fixed parked decision, process ownership and every saved evidence hash,
then uses the existing namespace/artifact derivation. The original cache selector
and all original benchmark helpers remain unchanged. Run `runtime.py --check`
first; its four real target derivations and invalid selections must pass.

For this adapter, `--build` is the selection ID `WORKFLOW:MODE`; otherwise the
prepare/review/commit/apply/verify procedure is identical. Use `runtime.py` for
all actions on those identities. Native/check/custom targets remain distinct;
executed bytecode snapshots and timing records stay outside each target.
