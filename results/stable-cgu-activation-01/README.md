# Retained stable-CGU activation evidence

The fixed-bucket policy **did activate** for the native `nu_protocol` build in the completed stable-module screen. Both retained candidate sessions contain exactly all 256 independently reconstructed bucket names; baseline and duplicate sessions match zero. This rules out an inactive module-count threshold as the explanation for that screen's negative result. This analysis runs no compiler, test, or benchmark and makes no new timing claim.

The saved screen reported baseline/candidate/duplicate medians of approximately 5.1584/5.1673/5.1701 seconds and no improvement. Its unchanged raw summary is in the archive; that earlier screen used an assertions-enabled compiler and preliminary diagnostic comparison, so it does not establish production strict-diagnostic qualification or the 0.5-second target.

| Retained native objects | Baseline | Candidate | Duplicate |
| --- | ---: | ---: | ---: |
| Objects in each session | 256 | 256 | 256 |
| Fixed bucket matches in each session | 0 | 256 | 0 |
| Exactly 808-byte objects in each session | 0 | 35 | 0 |
| Names shared between retained sessions | 238 | 256 | 238 |
| Shared names with the same inode | 232 | 249 | 232 |

Physical inode reuse describes these retained files; it is not a count of green compiler queries or backend invocations. The two largest candidate objects still contain 2,673 and 1,255 distinct text-symbol addresses. Their largest function extents are 3.25% and 0.52% of text, respectively. The larger object's 2,569 external function addresses include 1,525 with a literal `9drop_glue` symbol marker. This supports investigating finer placement of many small functions; it does not prove their `MonoItem` ownership or compilation cost. Thirty-five 808-byte objects are consistent with empty buckets; their full contents were not inspected.

The independent Python reconstruction reads the crate disambiguator from a retained Rust v0 symbol, decodes it to `aeb53990d42cb515`, and applies the pinned CGU name builder's SipHash1-3 128-bit hash and base36 encoding to `nu_protocol.<stable-id>-stable-cgu-v1.256-<index>`. It compares that complete set against both the saved work-product names and object filenames. It reads only Mach-O header/symbol/string slices for three selected objects, retaining their hashes, file stamps and raw drop-glue examples. It does not compare relocations, DWARF, whole-object hashes or disassembled instructions; function extents include alignment.

`summary.json` records the exact identities and compact findings. `evidence.tar.xz` retains all three analysis scripts, admission receipts, both completed reports and the original screen summary. Attempt01 failed admission before reading inputs and did not capture its PID. Attempt02 completed but searched the wrong drop-glue marker; preserve its report as superseded classification evidence. Attempt03 corrected the marker and completed under the canonical lock (owned PID46844, exit0, no compiler/tool children). The scripts are exact evidence with historical absolute input paths, not a public general-purpose analyzer. No cache files were modified.
