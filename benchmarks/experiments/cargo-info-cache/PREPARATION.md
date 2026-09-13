# Cargo-only setup and later screen

`setup_screen.py` imports the already qualified matched Cargo pair into the
current worktree, validates one public-compiler exporter/VM tool key, and runs
standard-library setup separately for both Cargo identities. It records exact
child receipts, namespace initial state, source/harness hashes and validated std
identities. It acquires the canonical shared workload lock with a bounded wait.
No source edit or project command occurs during this setup.

Allow roughly 8 GiB of additional cache storage for the three later project
arms and separate std metadata. Setup requires at least 16 GiB free, retaining
the ordinary 8 GiB floor beneath that estimate. This is a planning estimate;
each actual command still checks free space. Existing valid std metadata is
recorded as reuse; an incomplete prior std namespace fails explicitly.

After the custom-compiler integration/stable-CGU screen has released the lock:

```sh
python3 benchmarks/experiments/cargo-info-cache/setup_screen.py \
  --run-id cargo-info-cache-setup-01 \
  --screen-run-id strict-warm-cargo-info-cache-screen-01 \
  --source .work/sources/nushell-cargo-info-cache \
  --qualified-report /absolute/owned/cargo-worktree/.work/cargo-info-cache-build-01/summary.json \
  --tool-key PUBLIC_EXPORTER_VM_KEY --lock-wait-seconds 45
```

Setup emits `.work/cargo-info-cache-setup-01/screen-command.json` with the exact
27-command screen invocation and each prepared std path. It does **not** launch
the screen. Invoke that saved argument array under a separate coordinated lock
admission after reviewing setup success; the screen acquires its own lock.
Do not hold a parent benchmark lock while starting the screen child.

The prepared PRIMARY source is a separate pinned Nushell snapshot with
independent Git objects, so another comparison's body edits cannot affect it.
The stock/candidate Cargo inputs are independent copies of the qualified pair,
and A/A′ share stock Cargo while keeping separate fresh project caches. This
setup plan does not report performance or claim that any target has passed.
