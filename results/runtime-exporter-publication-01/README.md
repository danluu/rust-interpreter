# Installed-runtime exporter publication

The exporter and Cargo wrapper built at source checkpoint `185efda9403389fcb408100e5765306179be2cbe` are published under installed runtime R, tool key `7610e295912b132303c95db6a587f9288c03a7f84b691de8ea60093e2829622a`. The adopted VM bytes are unchanged. Actual final-path probes and the runtime owner's ordinary installed-tool readers passed; application agents received the verified composition before archival.

| Stage | Actual children | Result |
| --- | ---: | --- |
| Metadata | 53 | Passed |
| Exporter/wrapper build | 19 | Passed; one Cargo build, 44 D compiler invocations, zero stripping-helper failures |
| Original direct frontend attempt | 32 | Preserved harness failure after all 18 compiler controls ran |
| Saved-output continuation | 8 | Passed; nine exact diagnostic comparisons and bytecode parity, no completed compiler command repeated |
| Publication attempts 01 and 02 | 0 each | Preserved 600-second canonical-admission timeouts |
| Publication attempt 03 | 23 | Passed; independently verified |

The four focused control stages passed 5, 6, 4 and 8 tests. The original frontend harness compared compiler stderr with exporter telemetry mixed in. The continuation retains raw bytes and offsets, admits only exact source-bound telemetry grammars, and rejects unknown lines. It executes only the missing postguards.

`manifest.json` lists every logical proof/source file in `evidence.tar.gz`; duplicate content uses tar hardlinks. Retention verifies all member bytes and the complete gzip EOF/CRC, and checks source identities and evidence membership before and after. Live compiler and tool payloads are excluded; their exact hashes, identities and actual source/build provenance are retained.

`summary.json` records retention scope and all stage/receipt hashes. This result qualifies frontend composition and native tool publication. It does not qualify guest/application behavior, edited-build timing, holdout performance, or the 0.5-second target. See [the experiment sources](../../experiments/runtime-exporter/README.md) for the fixed compiler roles and reproduction records.
