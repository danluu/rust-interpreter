# Matched-profile demand-retention release

The final immutable tool is
`785432b3792154eb8df8d56fdd044fa1861b8e2652fa71414fcd9c9a9160f5ef`, built from
implementation commit `355f12ad83f1140625482f526e2541ac7ce92f4e`.
Its **six direct compiler histories and one Cargo history passed**, including
ordinary native output, export-byte comparisons, VM execution, strict checking,
failed-edit restoration and host/dependency edits. Source hashes remained fixed.

Release-02 matches baseline tool `923ad6d94c365365f15322ee65d32dca6ba9ccc4fd07a8147111329ea1955c86`:
`CARGO_INCREMENTAL=0`, `CARGO_PROFILE_DEV_DEBUG=0`,
`CARGO_PROFILE_TEST_DEBUG=0`, `CARGO_PROFILE_RELEASE_DEBUG=1`, with
`cargo +nightly-2026-09-08 build --release --locked --offline --jobs 2` for the
exporter and wrapper binaries. The full command and environment are in the exact
receipt. The separate release-01 build omitted the release debug override; its
passing correctness results are preserved, but it is **not a matched-profile
performance control**.

Both attempts use the unchanged retained VM
`83ca5b7882debeae37af8099c99c5cfb1a3829ed969444ee350eee12aa72b4df`.
All 110 bytecode/workspace Cargo input hashes matched its saved source manifest.
The VM was not rebuilt. `summary.json` records final binary/compiler/capability
hashes and the explicit tool-key composition. `evidence.tar.gz` preserves exact
receipts, build/test logs, fixture commands, installed manifests and retained-VM
provenance; its internal `MANIFEST.json` hashes every member.

The shared lock was held for builds and compiler tests. No benchmark was run.
All observed successful saves took one pass with zero serializer query jobs, so
**positive runtime coverage of serialization retry remains missing**. These
results make **no performance claim and do not establish the 0.5-second target**.
