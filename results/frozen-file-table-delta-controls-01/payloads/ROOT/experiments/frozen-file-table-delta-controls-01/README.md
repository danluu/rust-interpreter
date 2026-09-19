# Frozen file table delta controls

Source-only, unprepared proposal for 29 synthetic fixture controls. The harness
is a narrow successor of the passed snapshot22 harness: only the owner namespace,
source module, exact source selection and count change. The existing canonical
600-second lock, 16/9/8 GiB policy, 120-second alarm, 60-second CPU limit,
256 KiB file bound, 256 cumulative writable-name bound, 2048-directory bound and
2 MiB retained-output cap remain unchanged. There is one owned Python child and
no compiler, provider, network or nested process work.

Fixtures create tiny catalogs only beneath the explicit WORK/tmp root, including
symlink and mutation adversaries. The frozen helper reads these fixture catalogs
through no-follow descriptors. Source qualification does not read actual provider
payloads, perform actual hash-stage discovery, or establish workload results.

Expected publication: receipt.controls_passed=29; result.tests_run=29 and exact
AST-derived expected_names; independent audit controls=29, exact_names, raw_sha256,
receipt_sha256 and result_sha256. No inputs or launch proposal has been prepared;
preparation and actual control execution require their separate exact reviews.
