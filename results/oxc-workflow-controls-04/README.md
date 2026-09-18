# Oxc workflow registration and native compiler controls

All 30 focused Python controls passed. The final run completed without resource
warnings, using canonical workload admission and one supervised test child.
It verifies opt-in Oxc registration, the exact case pin, explicit native Cargo
and compiler routing, configuration conflict rejection, compiler/loader identity
inputs, post-history compiler validation, and lock release on a preflight error.
Native-suite execution is mocked; no Oxc acquisition, compilation or benchmark
was performed.

The preceding 30-test run also passed but exposed an unclosed benchmark-lock
warning on its expected failure path. Its original output and source inputs are
retained. The final implementation scopes the entire workflow with `ExitStack`;
the adjusted test retains the descriptor, verifies explicit closure, and obtains
a competing lock afterward. The final rerun uses the same complete test set.

`evidence.tar.gz` contains 86 regular members (715,090 input bytes), including
both complete runs, frozen source copies, raw outputs, child and outer process
receipts, launch environments, independent verification, and the archive helper.
The earlier unrun preparation manifests remain explicitly labeled unrun.
Every member was read back and hashed, including a complete gzip CRC/EOF read.

- Archive SHA-256: `08d6491fd31458ac69ef5c7740a2c4c4ed09262ff0df5d72ea3ca79e9d52604a`
- Final run: supervisor 11409, helper 11412, test process 11414.
- Final summary SHA-256: `90e25906f52db190b73a40b29115b1565f1ef841de568ab0698ede6c05c610e7`
- Raw final stderr SHA-256: `2f6aa918aca1c404028196873a9408da5bf5530aa9aaca67dddd4dfc00251aec`

See [the staged setup plan](../../experiments/oxc-plugin-normalization/SETUP.md)
for the remaining upstream 1.98.1 acquisition and native compatibility work.
This result supplies no build-time improvement or interpreter-compatibility claim.
