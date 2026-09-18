# Exporter bound to the installed native runtime

This experiment builds the exporter and Cargo wrapper at source checkpoint `185efda9403389fcb408100e5765306179be2cbe` with the admitted beta compiler D and auxiliary build sysroot B2. The resulting tools bind application compilation to installed runtime R, key `eca3d1317ba4c852d64de435aa0f0e5d87ae63bd4eb96cfafacc7b0a85841d03`. Runtime installation and tool publication belong to `/Users/danluu/dev/rust-interp-runtime-installation-r-20260918`.

The adopted VM remains the exact `df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62` tool's binary, SHA256 `6ac4dd9e964e0ebb0a050f8412c8ec8877bd197e8ad7876832db378ed03ca7cf`. Its existing source qualification and the explicit 24-path source-difference assessment are retained in the metadata plan. This experiment builds only the exporter and wrapper.

The single actual Cargo build completed 44 D compiler invocations with B2 and the installed R native-library route. Cargo emitted zero stripping/helper failures. Actual loader and role probes confirmed the R driver and matching exporter/wrapper compiler roles. The resulting hashes are:

| Binary | SHA256 |
| --- | --- |
| `rust-interp-mir-export` | `863bd33873255e8b60027525218ab7b700f143b2e7621024382413026613129c` |
| `rust-interp-rustc-wrapper` | `8f6d4bcf34e6298e7c7f19240fde03629ad942b002f93e2be51b8b7a999bc851` |

The direct frontend run completed all 18 planned compiler controls. Its original controller then failed because whole-stderr equality included the exporter's ordinary timing and optimization telemetry. That failed 32-child history remains unchanged. The reviewed continuation losslessly separates six source-bound telemetry grammars, rejects unknown lines, compares compiler diagnostic bytes exactly, rechecks all saved controls and bytecode sidecars, and executes only the eight missing source postguards. It passed all nine diagnostic comparisons and explicit/default/wrapper/restored bytecode parity. Eight saved-output controls cover the separator, including warning preservation and malformed/unknown-line rejection. No completed compiler command was repeated.

`metadata-02`, `build-02`, `frontend-01`, `frontend-continue-01`, and `publication-03` contain the exact sources, plans, freezes and supervised launch proposals. Earlier unrun metadata/build proposals remain present. The first two publication attempts each reached the 600-second canonical-lock admission timeout with zero children and no installed output. Their source and failed histories remain unchanged in `publication-01` and `publication-02`; the distinct successor binds both failures explicitly. Every actual stage uses the existing canonical workload lock with a 600-second admission bound, 16 GiB entry threshold, 9 GiB running stop threshold and 8 GiB floor. Four separate focused control stages passed 5, 6, 4 and 8 tests respectively.

Publication03 passed all 23 planned children and installed tool key `7610e295912b132303c95db6a587f9288c03a7f84b691de8ea60093e2829622a`. The tools are ordinary readonly copies in the R owner's `interpreter-tools` namespace. Actual final-path exporter/wrapper probes and the R owner's installed-tool readers verified their runtime association. Independent verification checked every command, raw stream, copied binary and complete frozen compiler/source record before handing the installed composition to the application agents. Guest/application correctness and edited-build performance are subsequent qualification stages; this record makes no build-latency target claim.
