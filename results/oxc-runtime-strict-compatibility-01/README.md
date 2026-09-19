# Strict Oxc interpreter/JIT qualification

The complete fixed Oxc plugin-normalization history passed through the ordinary interpreter and JIT launcher with both unsupported-call trapping and try-callback emulation disabled. All three unchanged tests passed on the original source, after all three production refactors, and after restoration. Each test independently reached its expected assertion failure under the wrong-prefix negative in both engines: 16 calls in total, including six negatives.

This qualifies the selected case under strict lowering. It does not establish full Oxc or general Rust compatibility, and the 0.5-second build target remains unmet.

Every launch reported `trap_unsupported_calls=false` and `run_try_callbacks=false`. Each selected crate's retained dep-info independently recorded both exporter policy variables as unset and recorded the exact single or batch test selection. No diagnostic call sidecar was present or synthesized. The selected library-test crate was freshly compiled on every call. All 16 retained bytecode artifacts were also compared directly against their diagnostic counterparts; every byte array and SHA-256 matched. That equivalence is limited to this selected test/edit history.

The source remains Oxc `4d5c812d6b16c23fa71d106cf87f7f20ddee69b1`, with unchanged profiles, default features and tests. The test selections and six source hashes match the [native](../oxc-native-compatibility-02/README.md) and [diagnostic](../oxc-runtime-compatibility-01/README.md) histories. Both engines used separate fresh caches, MIR optimization level 3, HIR capture/reuse disabled, function/borrow-check caches off, and two Cargo jobs. The qualified runtime/tool/shared-std keys remained `eca3d131…`, `7610e295…` and `e4d1cd29…`; complete identities and publication provenance are retained in the frozen plan. JIT retained resumable calls and persistent registers.

Single-history diagnostic build-to-ready observations for the three production edits were 5.759–6.265 seconds; their guest execution took 4.24–8.58 milliseconds. These are correctness-run observations, not a repeated benchmark distribution, controlled speedup measurement or optimized result. No no-change cache hit is presented as an edit result.

The controller held the canonical lock with 600-second admission and unchanged 24/9/8 GiB entry/stop/floor limits. It admitted with 26,033,643,520 free bytes and finished with 22,704,377,856. Recorded allocation was 2,876,588,032 bytes of cache and 120,524,800 bytes of evidence. Source restoration and final source/runtime/std/tool/provider/all-323-registry-package guards passed. No strip or loader failure was reported.

`evidence.tar.gz` retains the complete 16-call history, raw outputs and supervisor receipts, all actual compiler argument records, all 16 dep-info files, selected bytecode and batch catalogs, all 234 frozen inputs, exact source/plan/launch, independent audit and selected-bytecode equivalence proof. Build caches and temporary payloads remain at their recorded owner. The independent audit reconciled every child command/environment/cwd/raw hash/parent/time interval, policy/entry dep-info, bytecode/catalog, compiler route/flags, negative assertion and source restoration.

- Terminal SHA-256: `284ae6e21719cf6e045e93b1c0caab61acc60c63ce5ecae9d4df8e48c7ddf339`.
- Independent audit SHA-256: `e6a9e9d5c8254a3e3c016c4cb5f502f98cb290280578d664e81789e2adbcfce8`.
- Selected bytecode equivalence proof SHA-256: `14af06fb6da3c5fd34e90297fc5cc26d12accbe854b31ca1f6698553b5865a66`.
- Archive: 859 regular members, 118,259,487 uncompressed bytes, 32,772,541 compressed bytes; SHA-256 `fde2fb2598ec995dadd338582ccec3b78646862cc0899c2d0c95e73b9e7b10a2`.
- Manifest SHA-256: `7910312415625040855dd0e142f6df1a3047bef2d0e32cd14a12fb095d28f517`.

Every archive member hash and the full gzip CRC/EOF were verified. Extraction recreates paths relative to the experiment worktree; absolute paths inside records identify the original execution environment.
