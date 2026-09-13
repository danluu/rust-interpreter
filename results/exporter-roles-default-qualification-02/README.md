# Default exporter-role qualification

The default build at source `98aba1effa37b7028fe18df185589167797525f8`
passed the release workspace: **544 Rust tests passed, 10 ignored, zero failed
or filtered**, across 50 suites. All eight compiler-role controls passed once.
The explicit standalone build produced the exporter, wrapper and VM. The
exporter reported its original public sysroot without `compiler_roles`; the
wrapper's new role probe returned exactly `null\n`.

This qualifies the existing default route and the pure binding/identity
controls. It does **not** establish that an exporter built with the beta
compiler can embed the newer frontend. No split-role ABI qualification,
publication or performance result is claimed.

The run used the actual pinned public compiler
`cea272fa356e94bd2ee2cadf376630aa0683867a`, a fixed sanitized environment,
offline/locked Cargo, two Cargo jobs, two test threads, and the canonical
workload lock. The metadata stage retained 34 commands. The passed run
retained four qualification commands and 12 loader inspections. Its admission
was 16 GiB with a 9 GiB stop guard and 8 GiB floor.

The archive retains the exact plan, all 50 raw child receipts/stdout/stderr,
both outer supervisors, 205 original source inputs and their passing
snapshots, Cargo metadata and the 30-package dependency source/checksum
closure, public compiler/SDK/loader inventories, and actual binary hashes and
capability outputs. Registry source archives are retained; installed compiler,
standard-library and produced tool binaries, Cargo build targets and build caches are not.
SDK selection and tool identities are recorded; this is not a hermetic SDK
distribution. Every tar member is checked against `manifest.json` after
compression. Archive-level counts and hashes are in `summary.json`.

The earlier helper/manifest/launch draft 01 is retained as
**superseded and unexecuted**. It has no test result. The executed successor is
`qualify_exporter_roles_default_02.py`, SHA-256
`aa045d96d4bb0beb67b5da268074f52138cd0d18887634e34b6994c68047a912`.

Exact qualification bindings:

- Plan: `0599098c2a5b81db33c61cfa69965ddea8162cca87cf1be10c14d0390101acd5`.
- Metadata receipt: `890058ddbab2f2d2a3263e77abd61ea89071afc3f2aeabcab23ced2115f202d4`.
- Passed run receipt: `4d092643500ca13cb492642df39c0058dff297bb68b270282af743062c376415`.
- Actual tools inventory: `8bcfda28268cc728f92cf4f2f44e8e88c71082542d85473f856e8aaf378db1d9`.

Original receipts, binaries and source trees remain in their owned locations.
