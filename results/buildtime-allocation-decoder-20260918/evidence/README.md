# Allocation trace decoder reuse

Reusing one lazily constructed JSONDecoder per validation reduced CPU in the measured opt-in verification component by **20.27–28.09%**, with **20/20 paired CPU wins in each of eight cases**. All **64 predeclared gates** passed. This supports allocation-diagnostic verification; it makes no whole-build, exporter, default-launcher, guest-runtime or unknown-holdout speedup claim.

| Fixture / public API | Component CPU reduction | Median component CPU, µs | Process CPU C/B | Process wall C/B |
|---|---:|---:|---:|---:|
| caller / validate | 27.34% | 354.5 → 260.5 | 0.992873 | 0.990614 |
| caller / selected | 20.55% | 479.0 → 383.5 | 1.004106 | 1.006318 |
| scalar_constant / validate | 27.54% | 419.5 → 308.5 | 0.996892 | 0.996905 |
| scalar_constant / selected | 20.27% | 564.0 → 452.5 | 0.995958 | 0.995807 |
| static / validate | 28.02% | 873.0 → 624.0 | 0.988731 | 0.989810 |
| static / selected | 24.04% | 1046.0 → 793.5 | 0.995081 | 0.991884 |
| tls / validate | 28.09% | 4135.0 → 2953.0 | 0.952074 | 0.958865 |
| tls / selected | 24.65% | 4645.5 → 3489.5 | 0.952129 | 0.959859 |

Reductions use each case's geometric mean paired candidate/baseline ratio. Complete-process costs include startup/imports, setup, one API call and reporting. The caller selected_trace process used 0.41% more CPU and 0.63% more wall time, within the frozen 1%/2% guards. RSS guards also passed. Unlike cases are not pooled.

All four retained real exports were used: caller 147 events, scalar_constant 174, static 369 and TLS 1,845; trace sizes span 25,870–416,039 bytes. validate_trace times one validation of preloaded bytes. selected_trace includes actual artifact/sidecar reads, identity checks, hashing and validation. Imports and input setup precede component clocks; wait4 measures the whole fresh process.

The fixed schedule retained 16 parity, 32 warmup and 320 measured calls: 20 balanced AB/BA pairs per case, plus 368 separate memory checks. All 368 reports and 736 child records are included. Warmups alone populate the private bytecode cache; measurement reads its frozen 30 files / 624,372 bytes with -B. Results describe a warm-cache local component screen over this finite real trace panel.

Correctness passed 52 unit tests across both implementations; 33 transport rejections per arm; exact real counts/full receipts; and 12,360 finite paired outcomes (7,308 nesting, 4,872 caller-stack/BOM, 144 hook-error and 36 ordinary-overflow cases), each followed by successful shallow recovery in both arms. Both the C scanner and Python fallback were checked with limits 200/1000. This does not establish every possible recursion boundary or caller stack.

The first unit attempt remains a recorded failure. A new test incorrectly expected the unchanged baseline C scanner to reject depth 4096; candidate tests and timing had not run. V4 corrected only that test, checking malformed nesting/recovery in both scanners and deep RecursionError only in the Python fallback. Production bytes, seven-test count and frozen semantic/performance gates remained unchanged. The failed raw receipt and all seven exact attempt01 source/controller/plan files are included.

The production change preserves the original hooks, caller-level BOM handling, wrapper frame, validation order, bounds and sidecar integrity checks. First decoder construction stays after event and UTF-8 checks. There is no global or cross-validation decoder cache. Source copies and patch are included.

`summary.json` retains all 800 unrounded ratios; its `timing.summary` and `timing.gates` equal the raw timing result members exactly. `artifact-manifest.json` maps every stored file to its original path or generated sources, raw size/SHA256, stored size/SHA256 and encoding; only the manifest excludes itself. Gzip uses mtime 0 and no filename. Decompression restores exact original bytes, including the full timing result and all four complete recursion logs. The lossless `raw/all-child-logs.jsonl.gz` archive contains all 1,520 stdout/stderr files across timing, semantic qualification, successful units and failed attempt01. Decode each row's `data_base64` to recover its exact original log and verify the included SHA.

The bundle also includes the eight private fixture files, frozen decision/protocol, timing/unit/semantic controllers and drivers, source descriptors, dependency/cache/input proofs, and both root raw audits. Original absolute paths remain provenance. Reproduction requires reviewed rebinding to fresh owned paths and receipts; historical output directories are not reusable.

Packaging only read, hashed, copied and compressed immutable evidence. No tests, target APIs or timings were rerun, and measured roots/original evidence were unchanged. Pinned Python 3.14 exactly recomputed all 800 ratios and geometric aggregates for packaging; a preliminary system-Python check stopped before writing because of last-bit math differences. Parent review controls publication.
