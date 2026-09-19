# Independent C9 correctness and fixture audit

PASS. This review read source and retained execution records, recomputed hashes and identities, and checked raw logs. It did not rerun tests, production APIs, compiler queries, fixture preparation, or measurements. The only file written by the reviewer is this note.

The frozen decision is `a10f461883b1b3d68416b23c863d304a3c7f3b65edba2fc35fe8f5beb630c76b`. V3 preserves production `6a66c05ddb948a6dfdf3082991aaadc1ad8800340e40ce05568df0a4cfc4e58d`; the shared test file is `930db457e6933bec87feaefcb9625633a0980ece77a2e97c8944c059eb16f570`. Its two corrected fault tests reach both direct stat calls and Python 3.9's cached pathlib accessor using the same fault closure. All twelve test names and original test behavior remain intact. Numerical gates and measurement schedules are unchanged.

## Unit evidence

- Primary result: `unit-screen-01/result.json`, SHA256 `26d9bb17cd6abf6839c22a7e795af39c868e0c8657ae032b98f0c3206dc29a9a`.
- Compatibility result: `compatibility-screen-01/result.json`, SHA256 `3157f8de282d7af4d43cc218557341273d9a331b7a007158fef341628923a843`.

Each result contains twelve successful tests per production arm, 24 executions per interpreter and 48 total. The reviewer verified every discovered/successful test ID, canonical matching-arm production import, common test source, and absence of failures or skips. Actual runtimes are CPython 3.14.7 and directly invoked installed Xcode CPython 3.9.6. The candidate guard is true on 3.14 and false on 3.9; the baseline has no guard.

All eight child processes have matching planned/start/terminal records, successful exits and sixteen intact logs. All 400 primary and 413 compatibility input proofs match before/after records and current content/identity. Source inventories match; four private temporary directories are empty. Minimum recorded free disk was 24,854,478,848 bytes for primary and 24,764,182,528 bytes for compatibility; minimum memory was 63% in both. Audit execution reference: `5825ec`.

## Fixture qualification

Result: `fixture-qualification-01/result.json`, SHA256 `759b5a85fa7e40e5a8e126dc87c070e93a52ce4e68ccff9b4d8ec0498321ab0a`.

Fixture descriptor: `fixture-qualification-01/fixtures.json`, SHA256 `05e1b708626d285a1186730d3813ac5273c3cbbc89ba1992d07e48c288fcd656`.

All 403 input proofs remain current and match before/after records, including both successful unit receipts. The memory child and preparation child have exact successful settlements and four intact logs. The pinned Python command, sanitized environment, private cache, configuration hash, source bindings and admission records match the reviewed controller.

The three recorded actual baseline calls are matching saved stamps, creation of a device-readmission receipt, and reuse of that receipt. Each returned None without output or error. The reviewer independently checked every payload recipe, saved/current stamp, ready-manifest byte sequence and hash, receipt filename, and full parsed receipt fields. Both sealed trees contain 52 synthetic 1 KiB artifacts, two ready manifests and one receipt: 68 total entries and 76,962 file bytes. Every entry's type, identity, mode and content matches the complete retained inventories. All 48 loaded dependency files and 52 module mappings match; the qualification bytecode cache and temporary directory are empty.

Minimum recorded free disk was 24,585,293,824 bytes and memory was 63%. Audit execution reference: `3879be`.

These are correctness and fixture-preparation results, not performance evidence. Fixtures preserve the retained 26-path shape using small synthetic payloads; they are not real Rust metadata, and no retained metadata payload was read or copied for this review.
