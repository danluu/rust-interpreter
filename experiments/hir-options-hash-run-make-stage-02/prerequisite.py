"""Read-only binding of the three actual compiler controller histories."""
from pathlib import Path

from . import adapter
from . import support as s


def completed(frozen=None):
    frozen = frozen or (lambda path: (s.ordinary(path), Path(path))[1])
    tests = adapter.external('compiler_test_source',
        s.X / 'experiments/hir-options-hash/compiler-build-continuation-01/test_source.py')
    actual = adapter.compiler_history().validate(owner=s.X, source=s.S, evidence=s.BUILT,
        source_directory=s.BHERE, frozen=frozen, sha=s.sha, derive_tests=tests.derive)
    assert actual['compiled']['candidate_revision'] == '4de35bdacef0e3cd18a66bc30b5459c19e09b118'
    # Bind each owning supervisor as well as the complete child records already
    # validated by the shared verifier. No failed owner becomes successful.
    for work, outer, terminal, expected in [
        (s.X / '.work/hir-options-hash-compiler-build-02',
         s.X / '.work/experiments/hir-options-hash-compiler-build-supervisor-02',
         actual['failed_terminal'], 1),
        (s.X / '.work/hir-options-hash-compiler-build-continuation-01',
         s.X / '.work/experiments/hir-options-hash-compiler-build-continuation-supervisor-01',
         actual['failed_support_terminal'], 1),
        (s.BUILT, s.X / '.work/experiments/hir-options-hash-compiler-build-continuation-supervisor-03',
         actual['terminal'], 0),
    ]:
        status = s.read(frozen(outer / 'status.json'))
        plan = s.read(frozen(outer / 'plan.json'))
        log = frozen(outer / 'command.log')
        assert status['status'] == 'finished' and status['returncode'] == expected
        assert status['child_pid'] == terminal['pid'] and status['supervisor_pid'] == terminal['parent_pid']
        assert status['plan_sha256'] == s.sha(outer / 'plan.json') and status['log_sha256'] == s.sha(log)
        assert status['child_started_at'] <= terminal['started_at'] <= terminal['admitted_at'] <= terminal['finished_at'] <= status['finished_at']
        assert status['cwd'] == str(s.X) and status['command'] == plan['command']
    return actual


def audit(actual, path, sha256, frozen=None):
    path = Path(path)
    if frozen is not None:
        frozen(path)
    s.ordinary(path)
    assert s.sha(path) == sha256
    proof = s.read(path)
    assert path == s.X / '.work/hir-options-hash-compiler-build-continuation-verification-03.json'
    assert proof['status'] == 'verified' and proof['receipt_sha256'] == s.sha(s.BUILT / 'receipt.json')
    assert proof['compiled_sha256'] == s.sha(s.BUILT / 'compiled.json')
    assert [proof[key] for key in ['children','saved_children','saved_actual_children','combined_children','combined_actual_children']] == [3,22,23,25,26]
    # The independent audit is required in addition to our complete 26-record
    # replay; it cannot replace the explicit 25-success / one-failure mapping.
    assert len(actual['compiled']['command_history']) == 25
    assert len(actual['compiled']['actual_command_history']) == 26
    return dict(path=str(path), sha256=sha256)


def reference(actual, audit_ref):
    return dict(policy='run-make-three-compiler-histories-v1',
        receipt=dict(path=str(s.BUILT / 'receipt.json'), sha256=s.sha(s.BUILT / 'receipt.json')),
        compiled=dict(path=str(s.BUILT / 'compiled.json'), sha256=s.sha(s.BUILT / 'compiled.json')),
        independent_audit=audit_ref, source_identity=actual['compiled']['source_identity'],
        successful_logical_children=25, complete_actual_children=26,
        failed_support_attempt=actual['compiled']['failed_support_attempt'],
        original_failed_build_sha256=actual['compiled']['prior_failed_build_sha256'],
        original_failed_continuation_sha256=actual['compiled']['prior_failed_continuation_sha256'],
        unavailable_contemporaneous_cwd_children=actual['unavailable_contemporaneous_cwd_children'])
