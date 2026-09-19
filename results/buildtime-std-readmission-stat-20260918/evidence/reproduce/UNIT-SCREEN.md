# C9 v3 primary paired correctness screen

This source-only packet is bound to frozen decision a10f461883b1b3d68416b23c863d304a3c7f3b65edba2fc35fe8f5beb630c76b and applied-source manifest0212e8ac3505304f5f58d2b3b50752ef57cc56a62ab0edeae76b7e0a8466da4b. No tests, project imports, compiler queries or workloads were executed by the preparer. Root owns admission and execution after independent source review.

Primary controller run-unit-tests.py uses the pinned Homebrew CPython3.14.7 executable with -I -S -B. It requires exactly twelve successful methods per arm,24 total, in two work children with two preceding memory queries. Each source arm has189 immediate scripts/tests Python files; all378 are checked before and after. The common test is the candidate's tests/test_std_mir_readmission.py (11675B,930db457e6933bec87feaefcb9625633a0980ece77a2e97c8944c059eb16f570). Baseline production remains930fa978 and candidate production6a66c05d. The old baseline test source remains part of its unchanged189-file inventory but is not substituted for the common twelve-test panel.

For each arm the driver loads that arm's exact scripts/std_mir_readmission.py as canonical std_mir_readmission before importing the candidate test module. Both test_module.recovery and sys.modules["std_mir_readmission"] must remain that object; source/test bytes and SHA256, discovered IDs and successful IDs are checked. The candidate test's scripts-path insertion cannot substitute its production module during the baseline run. Extra suites, missing methods, skips, failures, expected failures or unexpected successes fail qualification.

The seven existing tests and helpers remain unchanged. Five new tests cover actual nonregular files/broken links, regular-target symlinks through all reuse paths, stable native stat-error policy, later missing-artifact precedence and one-shot transient failures. V3 corrects only fault injection for actual older Python: stat_fault uses ExitStack to patch both direct os.stat and an optional cached pathlib accessor with the same callable. Oracle and validation one-shot faults get independent fresh state. All fixtures are bounded private TemporaryDirectory metadata/receipt files; production validate and its real hash/stamp/receipt logic execute, with no compiler, Cargo, VM or external service.

Exact IDs required once per arm:

- `test_std_mir_readmission.Readmission.test_complete_hash_readmission_preserves_manifest_and_reuses_exact_receipt`
- `test_std_mir_readmission.Readmission.test_content_change_with_preserved_stamp_is_rejected`
- `test_std_mir_readmission.Readmission.test_invalid_receipt_and_mutation_during_hash_are_rejected`
- `test_std_mir_readmission.Readmission.test_later_missing_artifact_precedes_earlier_stamp_mismatch`
- `test_std_mir_readmission.Readmission.test_nonregular_paths_preserve_exact_artifact_error`
- `test_std_mir_readmission.Readmission.test_other_stamp_changes_and_mixed_devices_are_rejected`
- `test_std_mir_readmission.Readmission.test_receipt_does_not_admit_different_manifest`
- `test_std_mir_readmission.Readmission.test_replaced_or_missing_artifact_after_readmission_is_rejected`
- `test_std_mir_readmission.Readmission.test_stat_failures_preserve_native_pathlib_error_policy`
- `test_std_mir_readmission.Readmission.test_symlink_to_regular_artifact_retains_all_reuse_paths`
- `test_std_mir_readmission.Readmission.test_transient_stat_failure_is_not_hidden_by_retry`
- `test_std_mir_readmission.Readmission.test_unchanged_device_needs_no_readmission`

The seven require/free_bytes/identity/proof/write/run_child/admission helper bodies are byte-for-byte and AST-identical to the executed C8 controller. The new diffs and source review record those checks. Shared blocking benchmark lock and inode revalidation,16 GiB direct disk checks,>=30% memory admission fresher than20 seconds, private TMPDIR, five-second read-only disk observations and exact wait4 settlement in finally are preserved. No signal, process timeout, retry, cleanup, service repair or peer mutation is introduced. The1MiB log reader limit is a post-exit reader bound, not a live disk quota.

All400 primary binding proofs must match before and after, including complete sources, canonical proposal copies, final decision/applied record, v3 source/test/patch/policy evidence, driver, source manifest, pinned runtime files and immutable executed-C8 provenance. The C8 receipt establishes controller lineage only; it is not C9 test evidence.

A successful future unit-screen-01/result.json requires status="passed", error/post_binding_error null, expected_tests=passed_tests=24, two successful suite rows, four completed child/terminal records with zero returncodes and real wait4 usage, and equal bindings/bindings_after. Each driver report additionally captures the actual executable, version, version_info and implementation. Primary requires actual CPython3.14 and reports candidate single_stat_guard=true, baseline null, without modifying that production flag.

A separate mandatory24-test actual Python3.9 compatibility stage is described in COMPATIBILITY-SCREEN.md. Both stage receipts must pass before fixture qualification/timing; the two stages remain separate results. Neither stage is performance evidence. The frozen timing cases/counts/gates are not changed by these controls.

Unexecuted runner drafts were retained in pre-v3-runner-bindings/. Earlier dispatcher draft/runtime proofs remain in pre-canonical-python39-draft/. Root separately retained the unapplied/rejected proposal history and pre-v3 decision/applied-source records. No failed experiment is relabeled.

Frozen source identities:

- `run-unit-tests.py`: `811185773c18b11f8aafe4c7aa051da12c8a6de480c63bd5e50843b561ca8657`
- `unit-driver.py`: `b6f927e41a54af097fc1307ed5cbea815cd6d42e6d942bc8cc814c7187c52c00`
- `unit-source-manifest.json`: `ba5be5480862b6c2fa9b31c3838db182dba43055300444d3f797ff20b0817980`
- `unit-source-review.json`: `cf9d0725b004adb5a6b92e6ccea1b3321d86c3c1ee68fe1f844de7e8c19b7da2`
