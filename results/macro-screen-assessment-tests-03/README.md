# Macro publication and saved-assessment controls

All 21 focused tests passed under the explicit canonical workload lock: 11 saved-screen assessment controls, five shared public-tool provenance controls, and five publication boundary tests. The test runner reported 0.120 seconds. No Rust, Cargo, or VM workload was executed by these tests.

The archive retains exact tested Python sources, the runner, supervisor and child receipts, and both output streams. Every archived member was reopened and byte-verified. These tests cover immutable publication failures, source/configuration drift, complete standard-library identities, and preservation of the original screen workload and command timing. They do not qualify actual package installation or performance.

The subsequent real plan03 setup exposed a registry-layout assumption that these controls did not cover: the current registry stores archives without `.cargo-checksum.json`. That failed setup is retained separately; a revised inventory and its tests require fresh qualification.
