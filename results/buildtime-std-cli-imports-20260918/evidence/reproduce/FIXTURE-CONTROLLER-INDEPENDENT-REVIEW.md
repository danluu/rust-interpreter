# C13 fixture-preparation controller independent source review

Verdict: READY for final input binding and narrow freeze review; no source blocker found. The reviewed draft is intentionally not executable. No project/controller imports, tests, APIs, native queries, shared locks or workloads were performed in this review.

Reviewed bytes:
- run-fixture-preparation.py: fa98bdb8d3fe1759dc4e3ab0ff02de8648ebd4834807ab14fbae40016949ebf7 (24,615 bytes).
- fixture-prep-bindings.json: d91c2a137413d6b2948fdb69b553bf4e938f770a42fcb29cd463e58cfa39a548 (858,904 bytes).
- fixture-preparation-plan.json: b31828509775835a44325ee0d236e7aacb0ed3c6f0ae29441b5cc33e2a2f1be3 (1,980 bytes).
- Unmodified preparer template fixture-prep.py: 9729513d49a08a0165e65d58f743ee8109d7656f4fbc8dd89036e9d98707a90e (11,058 bytes).

## Controls and input closure

The eight stated helper bodies are literally equal to executed C9 run-fixture-qualification.py e326e7397ff39649bf8411ba19aead38653417cb77adb7c00c8ff1fd00cf6fae: require, free_bytes, stamp, proof, write, verify_expected, child and admission. Exactly one memory-pressure query and one pinned Python preparation child are planned. The common environment, private empty cache/TMP, -I -S -B, fresh strictly-above-16-GiB disk checks, at-least-30-percent memory, 20-second gate age, shared lock identity check, five-second read-only observer and exact-PID wait4/finally settlement are retained. Terminal receipts are written before bounded log proofs. No timeout, signal, cleanup or retry is introduced. Log-size limits are post-settlement validation, not proactive disk caps. Rust's separate 32-GiB admission is unchanged.

Independently rehashed all 189 baseline and 190 candidate Python sources and checked their exact inventories. Independently checked all 22 fixed-file bindings: only the three explicitly anticipated unit-freeze entries differ from this draft. Their current values are controller b1af3370ff5b81863a1197dc24ea701de0716030b66572daabd5add8f2e41fee, driver d1546542fdaa7287320468bd31e63022cfa279d9ac6588a65c5fc16f7d7a5ebf and manifest db14ba649b5f51f9533e950e731a0fe3e5ecb4bf33a6403fde6b10e5b0702755. All 1,956 named runtime files (57,932,058 bytes), eight links and two directories still have the recorded exact identities; this review did not rehash the large runtime payloads. The controller will hash that named closure before and after preparation. The declared-library and macOS shared-cache boundary remains explicit.

The prerequisite requires the exact successful 21-test candidate inventory, one unit row, both settled children, the matching canonical modules/runtime, unchanged before/after proofs, and no failures, skips or attempted real processes. All 379 source proofs must agree with that receipt. Baseline bindings are provenance, not a claim of baseline tests.

## Fixture and freeze semantics

The no-cycle freeze order is valid: successful unit receipt and procedural plan, then descriptor, then only preparer INPUTS_SHA, then the three controller constants. The actual preparer hash is pinned separately; normalization must restore exactly one input-binding literal to UNBOUND and recover template 9729513d. The descriptor does not bind its own hash or the final preparer bytes. UNBOUND hashes fail before lock acquisition, output creation or any child; existing outputs also refuse.

The preparer imports only standard-library modules, parses bound source constants with AST and never imports project code or calls its APIs. Its audit hook rejects process/network launches and mutations outside the new exclusive output. Only synthetic files are created: exact corpus, synthetic compiler source lock, empty writable std lock, ready.json and 26 deterministic 1,024-byte rmeta-named payloads. These payloads are expressly not valid Rust metadata. Bounded inventories permit at most 256 entries and 1 MiB of fixture data, with a 64-KiB ordinary file limit. Reads require canonical regular files with opening and final identity checks.

The controller independently recomputes identity/key and expected six-field CLI report, validates exact ready ownership/metadata/order, each artifact payload and saved stamp, file modes, corpus/lock bytes, full fixture inventory and descriptor hash. It repeats input and fixture verification after settlement. Loading the bound preparer's pure inventory helpers has no top-level project import or main execution. Actual std_mir.main/readmission parity remains for the fixed screen's first pair, not this preparation stage.

## Remaining freeze work

Preserve this draft, bind the actual successful unit result, refresh the three unit-source proofs and procedure proof, freeze descriptor/procedure states, apply only the preparer's input-hash literal, and bind the controller's three final hashes. Verify that narrow delta and every current proof before execution. No numerical decision, fixture semantics, workload schedule or resource gate needs changing. The fixture output was absent during this review.
