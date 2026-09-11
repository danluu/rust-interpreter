"""Cache ownership for one assessed history stopped between commands.

This is deliberately separate from successful workflow verification. It never
publishes a completed benchmark report or converts partial records into pairs.
"""
import json
from pathlib import Path
import subprocess

from verify_repeated_workflow import require
from workflow_cache_evidence import derive

CORPUS = 'resumable-copy-heldout-01-case-01'
LABEL = 'nushell-type-relations'
REPORT = 'results/resumable-copy-heldout-01-case-01-stop/summary.json'
REPORT_SHA = '30f3e9ce848af9225cd5a945ccb38fe6271972d74a7f7e59cbd1bff575326eb8'
ASSESSMENT = 'resumable-copy-heldout-01-case-01-stop-assess-02'
ASSESSMENT_STATUS_SHA = '7753faa351fff0bdb2fc6d320acd2ca65b92c389b2de4034ffc0df0721e1b8fc'
ASSESSOR = 'benchmarks/experiments/resumable-native-calls/assess_copy_heldout_stop.py'
STD_KEY = 'bd27cc0f910e0c93a9a6cf088789ef526d36a8697a7717e08d7585f5d19467ef'


def validate(failure, corpus_id, run_id, mode):
    require(corpus_id == CORPUS and run_id == CORPUS + '-' + LABEL,
            'stopped cache is not in the explicit assessed catalog')
    require(mode in ['native', 'check', 'baseline', 'candidate'], 'invalid stopped cache mode')
    require(failure['run_id'] == CORPUS and failure['status'] == 'incomplete: pre-command disk guard' and
            failure['completed_workflows'] == 0 and failure['measured_successful_edit_pairs'] == 0 and
            failure['primary_records'] == 5 and failure['check_records'] == 1 and
            failure['source_restored'] is True and failure['retained'] is False and
            failure['original_records_unchanged'] is True and failure['cache_cleanup_performed'] is False and
            failure['process_signals_sent'] is False and len(failure['snapshots']) == 4,
            'stopped-history assessment differs')


def cache(root, run_id, corpus_id, mode, sha):
    require(corpus_id == CORPUS, 'unknown stopped corpus')
    report_path = root / REPORT
    require(sha(report_path) == REPORT_SHA, 'stopped assessment changed')
    read = lambda path: json.loads(path.read_text())
    failure = read(report_path)
    validate(failure, corpus_id, run_id, mode)
    proofs = {REPORT: REPORT_SHA}
    for name, saved in failure['evidence'].items():
        original, snapshot = root / name, report_path.parent / saved['snapshot']
        require(original.resolve(strict=True) == original and snapshot.resolve(strict=True) == snapshot and
                snapshot.parent == report_path.parent and
                sha(original) == sha(snapshot) == saved['sha256'] and
                original.stat().st_size == snapshot.stat().st_size == saved['bytes'],
                'preserved stopped evidence changed')
        proofs[name] = saved['sha256']
        proofs[str(snapshot.relative_to(root))] = saved['sha256']
    for name, digest in failure['snapshots'].items():
        path = root / name
        require(path.resolve(strict=True) == path and sha(path) == digest,
                'stopped executed snapshot changed')
        proofs[name] = digest
    assessment_root = root / '.work/experiments' / ASSESSMENT
    require(sha(assessment_root / 'status.json') == ASSESSMENT_STATUS_SHA,
            'terminal stop assessment receipt changed')
    assessment = read(assessment_root / 'status.json')
    require(assessment['status'] == 'finished' and assessment['returncode'] == 0 and
            assessment['owner'] == str(root) and assessment['cwd'] == str(root) and
            assessment['command'] == ['python3', ASSESSOR] and
            sha(root / ASSESSOR) == failure['assessor_sha256'] and
            sha(assessment_root / 'plan.json') == assessment['plan_sha256'] and
            sha(assessment_root / 'command.log') == assessment['log_sha256'],
            'stopped assessment was not completed by the recorded assessor')
    for path in [root / ASSESSOR, *[assessment_root / name for name in
                                  ['status.json', 'plan.json', 'command.log']]]:
        proofs[str(path.relative_to(root))] = sha(path)
    experiment = read(root / '.work/experiments' / CORPUS / 'status.json')
    controller = read(root / '.work/corpus-runs' / CORPUS / 'status.json')
    raw = root / '.work/runs' / run_id
    active = read(raw / 'active-command.json')
    pids = [experiment['supervisor_pid'], experiment['child_pid'], controller['child_pid'], active['pid']]
    process = subprocess.run(['ps', '-p', ','.join(map(str, pids)), '-o',
                              'pid,ppid,lstart,tty,command'], capture_output=True, text=True)
    require(process.returncode in [0, 1] and not process.stderr and
            not any(CORPUS in line for line in process.stdout.splitlines()[1:]),
            'stopped history is still live or process inspection failed')
    source = root / '.work/sources/nushell'
    marker = read(source / '.rust-interp-owned.json')
    require(marker['owner'] == str(root) and marker['revision'] == failure['source_pin'] and
            subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == failure['source_pin'] and
            not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source, text=True).strip() and
            sha(source / 'crates/nu-protocol/src/ty.rs') == failure['restored_source_sha256'],
            'stopped source ownership or restoration differs')
    plan = read(root / '.work/corpus-runs' / CORPUS / 'plan.json')
    options = plan['options']
    # Only an in-memory descriptor for the existing cache-identity derivation.
    # No successful-workflow schema, pair count, or published result is invented.
    descriptor = dict(project='nushell', raw=str(raw.relative_to(root)), batch=True,
        comparison={}, check_floor=True, std_mir=dict(key=STD_KEY),
        tool_builds={name: dict(tool_key=options[name + '_tool_key'], engine='jit')
                     for name in ['baseline', 'candidate']})
    target, selection, _ = derive(root, run_id, descriptor, read(raw / 'records.json'),
                                  read(raw / 'check-records.json'), 'check' if mode == 'native' else mode)
    if mode == 'native':
        target, selection = raw / 'native', dict(mode='native')
    require(target.resolve(strict=True) == target and target.is_dir(), 'stopped target is not canonical')
    verified = dict(history_status=failure['status'], completed_workflows=0,
        measured_successful_edit_pairs=0, preserved_primary_records=5, preserved_check_records=1,
        preserved_executed_snapshots=4, source_restored=True, cache_selection=selection)
    return target, proofs, verified
