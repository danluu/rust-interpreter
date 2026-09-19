# Native behavior qualification and preserved failures

The saved native03 commands are qualified by a separate, read-only reconciliation. The original native03 terminal remains failed, and its original result file remains absent. Reconciliation launched no compiler or native program. This is instrumented correctness evidence, with no latency qualification.

| Evidence owner | Actual commands | Original outcome | Retained interpretation |
| --- | ---: | --- | --- |
| native01 | 5 | Failed after stock-wrapper lint warning | Unqualified; all raw evidence preserved |
| native02 | 6 | Failed at lexical provider-route validation | Unqualified; all raw evidence preserved |
| native03 | 20 | Failed at the final wrong-B3 diagnostic parser | All commands had their expected return codes; original failure preserved |
| native reconciliation01 | 0 new | Passed; independent audit passed | The 20 saved native03 commands are qualified; 31 actual historical commands remain accounted for |

The corrected wrong-B3 parser admits the observed `compiler_builtins` E0514 diagnostic only with exact frozen B3 provider and version associations. It preserves the primary `std`/`core` requirement, raw diagnostic parity, and foreign-provider/unknown-error rejection. Eleven focused parser controls passed before reconciliation. The complete readback also verified the native loader and linker proofs, diagnostics, cache-hit accounting, retained executed artifacts, and restored fixture.

`evidence.tar.gz` contains 875 logical members, deduplicated to 512 physical members using backward tar aliases. Full member hashing and gzip EOF/CRC checks passed. It retains all 31 command receipt/stdout/stderr triples; all 376 original compressed snapshot files from the three attempts; the reconciliation's 125 logical delta proofs (89 physical payloads); all failed and successful audit attempts; rejected unrun controls; and the actual 4, 9, and 11 source-control histories. The four qualified generated outputs and four retained executed artifacts are included. Older unqualified stock-wrapper payloads and live compiler/provider libraries are excluded.

The archive is 60,159,235 bytes, SHA-256 `e18c654558f389dd4bc01e9e0791f7b09288c896290dc70d99c2becbf8778a58`. Its logical readback totals 267,307,947 bytes. The independent publication audit is `034983d233a97b494d15943830a12587223da8d111d894605acf7d526c615b82`; the separate native reconciliation audit is `6e95c8845fd761757d6db80e375673e126208466fa54ed678a32d3a2a036685e`.

The archive references the already retained B308 prerequisite archive `ec80d1339228b02917612a1002b90228c03a4182eb5da7b39ef2731c4b771e14` from commit `9d7ecf3a`; that archive is not duplicated here. Each retained archive member keeps its original absolute source path in `manifest.json`. Reconstruct it into a separate directory using that mapping; do not overwrite the original evidence owners.

The [source bundle](../../experiments/native-qualification-source-01/source-map.json) contains 58 exact provenance copies (512,816 bytes). Their original paths remain authoritative. The publication helper's frozen README and packet preserve their historical proposal status; this README and `publication-status.json` record the completed outcome.

`publication/` contains the publication's own preparation, supervisor, dispatcher, audit, source-review, and source-copy records. `publication-manifest.json` maps and hashes all 38 exact metadata copies. These records were added after the independent auditor verified the original three-file archive output, preserving its exact checked membership. A small, read-only extras-planning failure involving access-time comparison is retained; no archive or audit was repeated.

Missing contemporaneous process observations remain explicit in the original evidence. In particular, native03's two unavailable fast cwd observations and proven numeric PID reuse are preserved. No synthetic passed native03 terminal, new command receipts, or benchmark timings were created.
