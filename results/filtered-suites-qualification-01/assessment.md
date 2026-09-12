# Automatically selected suites qualification

The launcher can now select ordinary libtest bodies with `--test-filter PATTERN`
and optional `--test-exact`. Selection and MIR export happen in the same fully
checked compiler invocation. The bounded selection report binds the filter,
compiler-derived attributes and chosen names to the exact bytecode; the entry
catalog also verifies executed function IDs. No native listing build is needed.

Ignored tests are skipped. Selected expected-panic tests, zero runnable matches
and more than 256 runnable matches are rejected before guest execution. Single
unit/Result tests use the same isolated runner through a one-entry catalog.
This remains an explicit subset runner; general unwinding, threads and full
Cargo/libtest semantics are still open.

All 329 Rust tests pass in each profile (one ignored), as do 48 Python tests.
The 44-command Cargo fixture covers exact/substring matching, a duplicate short
name, single Result success/failure, ignored expected-panic tests, unsupported
selections, feature/target changes, an unused borrow error, bounds, a wrong
production edit, a valid refactor and source restoration. Its first attempt
caught a verifier omission: Result failure already produced the correct VM
guest-assertion error, which the verifier had not recognized. That classifier
fix has a regression test and still rejects resource/compiler errors.

Each real workflow passes 32 commands: original/wrong/five valid edits/restored
source, each through native, explicit-name and filtered suites plus an independent
Cargo check. Automatic and explicit bytecode is identical in all 24 state pairs;
every test outcome matches native. Original test code stays unchanged.

| Case | Tests | Native edited command | Explicit names | Automatic filter | Paired automatic/explicit |
| --- | ---: | ---: | ---: | ---: | ---: |
| pgrust | 4 | 0.673 s | 0.525 s | 0.533 s | 1.0164 |
| folded | 18 | 1.711 s | 1.686 s | 1.726 s | 1.0130 |
| token | 12 | 3.059 s | 8.330 s | 8.267 s | 0.9946 |

These are descriptive medians from five different source edits in one cycle,
using repository profiles and two workers. Native isolation is one process per
test; custom isolation is fresh guest state with shared prepared JIT code.
The token filter includes all twelve ordinary module tests, so its timings do
not represent the older three-test benchmark. The first token attempt stopped
on the 8 GiB disk floor after cold/wrong controls and no valid-edit samples; the
complete retry used fresh caches with over 10 GiB available at admission. Both
histories remain preserved.

Filtering has a small observed overhead and removes manual name enumeration.
Token execution remains the larger performance problem. Next investigate
conservative narrower persistent-register assignments, measuring their actual
coverage before implementing or timing a candidate. Parked candidates remain
parked; this qualification does not change their decisions.
