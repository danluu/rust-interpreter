# Completed proof snapshot catalog controls

Source-only, unprepared proposal for 33 synthetic in-memory controls. This is a
narrow successor of the passed file-table29 harness: only namespace, source
module/selection and count change. The canonical600 wait, 16/9/8 GiB policy,
120-second alarm, 60-second CPU bound, 256 KiB file bound, 256 cumulative writable
name bound, 2048-directory bound and 2 MiB retained-output cap remain unchanged.
There is one owned Python test child and no compiler, provider, network or nested
process work.

The catalog callbacks and file/directory/gzip descriptors in the tests are
synthetic dictionaries. No test creates real filesystem fixtures, reads provider
payloads or invokes gzip. The unchanged child audit policy and module closure
checks remain in force. The proposed result has tests_run=33 and exact AST-derived
expected_names; the receipt has controls_passed=33. The independent audit will
bind controls=33, exact_names, raw_sha256, receipt_sha256 and result_sha256.

No packet preparation or test execution has occurred. Exact source review,
read-only packet preparation, bound dispatcher/auditor review and explicit
once-only control authorization remain separate steps.
