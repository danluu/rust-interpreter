The isolated exporter inventory preserves both freshly exported folded/token
bytecode artifacts exactly, with original tests passing. Its VM binary is
identical to retained 57a5, and all 11 exporter tests pass. The observer changes
no slots or bytecode. These instrumented compilations are not timing evidence.

After weighting by recorded direct calls, semantically unreferenced MIR local
ranges account for only 1.46% of folded frame bytes and 1.78% of token frame
bytes. This does not justify a frame-layout rewrite as the next speed experiment.

| Recorded direct-call frame bytes | Folded | Token |
|---|---:|---:|
| Total frame bytes, excluding alignment padding | 42,455,137,117 | 33,555,722,191 |
| MIR ranges without a semantic use | 620,076,843 (1.46%) | 597,260,201 (1.78%) |
| Non-ABI ranges without a named local address | 327,809,690 (0.77%) | 1,466,671,820 (4.37%) |
| Bytes after declared locals and caller-location storage | 2,356,446,822 (5.55%) | 3,481,361,815 (10.37%) |
| Additional inline-bank extent | 1,647,711,816 (3.88%) | 3,935,478,072 (11.73%) |

Unreferenced and unnamed ranges overlap and must not be added. Neither proves
that omission or relocation preserves pointer behavior. Later temporary storage
and alignment contribute to the post-declaration extent. Existing scalar
coloring and inline-bank reuse already apply. Indirect targets, entry/TLS frames
and alignment padding are excluded from these weighted counts.

The first report attempt rejected duplicate display names: distinct compiler
shims can share the rendered function name while having different frames.
There is one such name in folded and eleven in token. The corrected report
keeps those inventories separate and excludes ambiguous matches. None of those
shims has an observed direct call in these profiles, so every weighted callee
has an unambiguous inventory. The failed uniqueness assertion is preserved.

Keep the current frame layout. The remaining call-transition costs warrant a
larger experiment, preceded by a typed census of fully native leaf callees and
their rejection reasons. Benchmark reproducibility and repeated per-edit
controls should also be improved before the next performance decision.
