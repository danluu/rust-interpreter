# Custom compiler setup failures and focused checks

This archive preserves two setup failures and their narrow importer fixes. It contains no benchmark or speedup result and does not qualify a compiler/tool pair for workload timing.

- Installer attempt01 rejected an absolute `LC_ID_DYLIB` self identity. The actual library load was the system library. The corrected importer distinguishes identity from actual ordinary, weak, reexport, upward and lazy load edges. Nine focused synthetic tests passed.
- Installer attempt02 published package05 after validating its complete recorded 6,982-file inventory. The first matching tool build then failed because that package omitted `rust-objcopy`, which normal Darwin release build-script stripping requires. No matching tools were published and real integration never started. The importer now requires and audits the executable support tool; ten focused synthetic tests passed.

The original compiler/package identities, failed copy, failed build target, plans, child receipts, logs and frozen input hashes are retained. No compiler artifact, strip setting, build profile, or workload source was changed to bypass either failure. The replacement package and its real qualification are separate later steps.

`evidence.tar.xz` contains exact tested source snapshots, both synthetic test receipts, setup plans and outputs, installed/compiler-package inventories, and the observed Mach-O records. `members.json` records each payload's source, size and SHA256; `summary.json` records the archive digest. Every archived member was reopened and compared with its captured bytes. Compiler/tool binaries are retained at their recorded owned paths and are not duplicated in this compact archive.
