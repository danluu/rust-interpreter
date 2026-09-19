# C13 timing raw audit

PASS. The complete fixed screen and all eight predeclared gates reproduce exactly. This audit used pinned CPython3.14.7 with -I -S -B for matching floating-point arithmetic; it imported no project/controller/driver module and ran no CLI, test, preparation, compiler or timing workload. No process was controlled and no retained stage record was changed.

Raw result: `screen-01/result.json`, 2,372,176 bytes, SHA256 `c7185d5ee410e22976dbbbb8a6161c92c03824f8d5a795dd4fcd8a05c50a72f0`. Bound controller d9945755, descriptor ef5530a7, driver 06ad506b, decision c432cb2d, unit 8cc032cc, preparation 9cb2f476 and fixture 41e0cd50 remain exact. The scope/result fields and frozen copied stage inputs agree with their originals.

Independently reconstructed the exact 46-row schedule: one AB parity pair, four ABBA warmups, then 20 alternating AB/BA measured pairs. All 92 direct children are unique, parent 92186, zero-exit, error-free and fully settled; every planned/start/terminal receipt, all 184 stdout/stderr proofs, empty observation journals and CPU/wall/RSS records reconcile. Planned PID/start placeholders remain null until their actual start records. Child intervals do not overlap. Every memory query and its following driver are in the correct order, with fresh admission within 20 seconds and the exact pinned flags/environment/config. Minimum memory admission was 50%; minimum recorded disk was 25.572544 GiB. No sample was replaced, retried, omitted or excluded.

All 46 raw stdout JSON reports equal their retained report wrappers and embedded sample rows; samples.jsonl equals the result rows exactly. Every config matches the actual immutable source/fixture/stage identities and phase. Each actual main returned None, made exactly one setup and one fresh discovery-stub call, emitted the exact same six-field CLI stdout, and recorded zero process attempts. All stderr files are empty. Both arms load actual toolchain_lookup/tempfile/readmission; baseline alone adds the four intended optional modules. Per-arm module maps are stable throughout all phases (102 baseline/98 candidate), and every module source is bound to its correct arm or runtime. Preclock module inventories are common and exclude target/optional/test imports.

All 2,448 before/after input records are equal and current: 2,440 regular-file proofs (77,066,587 bytes) plus 8 exact runtime links, covering 2,061 fixed files and 379 source files. Both source filename inventories remain exact. All 47 fixture entries and 36,370 bytes match the before/after/preparation inventories. The 101 dependency proofs match the actual warmup union and current files. The private bytecode cache matches both frozen and final inventories: 72 pyc files, 1,843,874 bytes, 28 directories, exact source proofs/headers/magic/flags, with every reported cached module covered. Only the four warmup commands permit writes; all parity/measured commands use -B. Empty private TMP remains empty. Immutable pyc/header/stamp evidence and the controller's per-sample checks show no measured cache change.

Using the raw measured rows, all 100 C/B ratios and every summary field were recomputed without tolerance, including medians, strict wins, paired differences and separate order strata. All eight numerical gate values exactly match the frozen decision and raw result. Component CPU geomean is 0.9611748859388262, 18/20 strict wins; AB 0.9549053149930463, BA 0.967485620672499. Component CPU medians are 16.1465→15.5575 ms. Whole-driver CPU/wall/RSS geometric ratios are 0.981114850411019, 0.9796900833178188, and 0.9937866684821178. The complete raw 100 ratios remain in the result; no rounded value was used for gate evaluation.

This supports the declared instrumented stock standalone std CLI prepared-reuse component, using synthetic metadata and stubbed compiler discovery. The global process-rejection hook is in the component clock and receives different import-event counts across arms. It is not evidence for real compiler-query, full std/build/export, selected-tool, interpreter-launcher, guest-runtime or unknown-holdout improvement.

Exact recomputed headline metrics:

```json
{
  "component_cpu_ns": {
    "geometric_mean_ratio": 0.9611748859388262,
    "median_baseline": 16146500.0,
    "median_candidate": 15557500.0,
    "strict_wins": 18
  },
  "component_wall_ns": {
    "geometric_mean_ratio": 0.9608166871415679,
    "median_baseline": 16158229.0,
    "median_candidate": 15580146.0,
    "strict_wins": 18
  },
  "cpu_seconds": {
    "geometric_mean_ratio": 0.981114850411019,
    "median_baseline": 0.0352685,
    "median_candidate": 0.0348045,
    "strict_wins": 17
  },
  "peak_rss_bytes": {
    "geometric_mean_ratio": 0.9937866684821178,
    "median_baseline": 25174016.0,
    "median_candidate": 25018368.0,
    "strict_wins": 20
  },
  "wall_seconds": {
    "geometric_mean_ratio": 0.9796900833178188,
    "median_baseline": 0.03752656299911905,
    "median_candidate": 0.03691533349046949,
    "strict_wins": 17
  }
}
```
