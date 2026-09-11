#!/usr/bin/env python3
"""Check worker-count integration, early CLI failures and historical receipts."""
import argparse
from copy import deepcopy
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_repeated_workflow import require, verify
from workflow_io import write_json


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qualify(run_id):
    corpus = read(ROOT / 'results/native-controls-corpus-01/summary.json')
    paths = [ROOT / row['report'] for row in corpus['workflows']]
    for row, path in zip(corpus['workflows'], paths):
        require(sha(path) == row['report_sha256'], 'historical corpus report changed')
    paths += [ROOT / 'results' / name / 'summary.json' for name in [
        'interface-pgrust-repeated-01', 'interface-nushell-repeated-01',
        'lightweight-wrapper-pgrust-repeated-01', 'lightweight-wrapper-nushell-repeated-01',
        *[f'lightweight-wrapper-nushell-cold-{i:02d}' for i in range(1, 5)]]]
    histories = []
    for path in paths:
        report, expected = read(path), read(path.with_name('verification.json'))
        reference = None
        if expected['reference_bytecode'] is not None:
            require(path.parent.name.endswith('-repeated-01'), 'unresolved historical reference')
            reference = read(ROOT / 'results' / path.parent.name.replace('-repeated-01', '-qualification-01') / 'summary.json')
        actual = verify(report, reference)
        require(actual == expected, 'historical workflow verification changed')
        histories.append(dict(report=str(path.relative_to(ROOT)), sha256=sha(path), verification=actual))

    base = read(paths[-1])
    false_receipts = 0
    for check_floor in [True, False]:
        altered = deepcopy(base)
        altered['custom_build_jobs'] = dict(baseline=4, candidate=18)
        if not check_floor:
            altered['check_floor'] = None
        try:
            verify(altered)
        except ValueError as error:
            require('job count differs' in str(error), 'false worker receipt failed for another reason')
        else:
            raise RuntimeError('false candidate worker count accepted')
        false_receipts += 1
    matching = deepcopy(base)
    matching['custom_build_jobs'] = dict(baseline=4, candidate=4)
    require(verify(matching) == verify(base), 'explicit matching worker receipt changes semantics')

    # Nonexistent installed keys ensure a missed early parser check cannot
    # fall through to an implicit host-tool build or project execution.
    paired = ['--baseline-tool-key', '0' * 64, '--candidate-tool-key', '0' * 64]
    unpaired = ['--candidate-tool-key', '0' * 64]
    malformed = []
    for option in ['--jobs', '--native-jobs', '--baseline-jobs', '--candidate-jobs']:
        malformed += [(paired + [option, '0'], 'integer in 1..256'),
                      (paired + [option, '257'], 'integer in 1..256'),
                      (paired + [option, '4', option + '=18'], 'specified more than once')]
    for option in ['--baseline-jobs', '--candidate-jobs']:
        malformed.append((unpaired + [option, '18'], 'baseline/candidate jobs require a paired comparison'))
    cli = []
    for index, (arguments, diagnostic) in enumerate(malformed):
        name = run_id + '-reject-' + str(index)
        command = [sys.executable, str(ROOT / 'scripts/bench_e2e_workflow.py'), '--run-id', name, *arguments]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        require(result.returncode == 2 and diagnostic in result.stderr and not result.stdout,
                'workflow CLI did not reject before resolving tools')
        require(not (ROOT / '.work/runs' / name).exists(), 'invalid CLI created a project workflow')
        cli.append(dict(arguments=arguments, returncode=result.returncode, diagnostic=diagnostic))
    corpus_cli = []
    for option in ['--jobs', '--native-jobs', '--baseline-jobs', '--candidate-jobs']:
        name = run_id + '-corpus-reject-' + option.removeprefix('--')
        command = [sys.executable, str(ROOT / 'scripts/bench_workflow_corpus.py'), '--run-id', name,
                   *paired, option, '4', option + '=18']
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        require(result.returncode == 2 and 'specified more than once' in result.stderr and not result.stdout,
                'corpus CLI did not reject repeated worker counts')
        require(not (ROOT / '.work/corpus-runs' / name).exists(), 'invalid CLI created a corpus')
        corpus_cli.append(dict(option=option, returncode=result.returncode))
    return dict(status='passed', histories=histories, false_worker_receipts_rejected=false_receipts,
                matching_explicit_receipt_verified=True, workflow_cli_rejections=cli,
                corpus_cli_rejections=corpus_cli, project_compiled_or_executed=False,
                note='Historical workflows were reverified, not rerun. New valid worker commands still require project qualification.')


def same_tool_guards(run_id):
    """Exercise the late comparison guard and stop at an exclusive run directory.

    The real harness takes its own benchmark lock. Do not hold the parent lock
    across these calls. Its existing mkdir without exist_ok stops an accepted
    configuration before source edits or any project compiler command.
    """
    key = '78e60cdd76195c55583651bac6a7f7d349314dd1ea582b6a86335adbee48049d'
    case_path = ROOT / 'benchmarks/experiments/interface-edits/pgrust-generic-input.json'
    case = read(case_path)
    source = ROOT / '.work/sources/pgrust' / case['case']['file']
    observations = []
    for jobs in [4, 18]:
        name = run_id + '-same-tool-' + str(jobs)
        sentinel = ROOT / '.work/runs' / name
        marker = sentinel / 'prebuild-sentinel.json'
        with (ROOT / '.work/benchmark.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            source_before = sha(source)
            sentinel.mkdir(exist_ok=False)
            write_json(marker, dict(owner=str(ROOT), purpose='Stop comparison guard probe before project execution'))
            marker_before = sha(marker)
        command = [sys.executable, str(ROOT / 'scripts/bench_e2e_workflow.py'), '--run-id', name,
                   '--project', 'pgrust', '--case-file', str(case_path),
                   '--baseline-tool-key', key, '--candidate-tool-key', key,
                   '--baseline-jobs', '4', '--candidate-jobs', str(jobs)]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        with (ROOT / '.work/benchmark.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            require(sha(source) == source_before and list(sentinel.iterdir()) == [marker] and
                    sha(marker) == marker_before, 'guard probe changed source or sentinel')
        if jobs == 4:
            require(result.returncode == 2 and 'must differ' in result.stderr,
                    'identical settings no longer rejected')
        else:
            require(result.returncode == 1 and 'FileExistsError' in result.stderr and
                    str(sentinel) in result.stderr, 'different workers did not reach prebuild sentinel')
        require(not result.stdout, 'guard probe unexpectedly produced workflow output')
        observations.append(dict(candidate_jobs=jobs, returncode=result.returncode,
                                 source_unchanged=True, sentinel_sha256=marker_before,
                                 identical_rejected=jobs == 4, reached_prebuild_sentinel=jobs == 18))
    return observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['', '.', '..'], 'invalid ID')
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        out = ROOT / 'results' / args.run_id
        require(not out.exists(), 'qualification output exists')
        result = qualify(args.run_id)
    result['same_tool_guard_probes'] = same_tool_guards(args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(not out.exists(), 'qualification output appeared during guard probes')
        sources = [Path(__file__), ROOT / 'scripts/workflow_jobs.py', ROOT / 'scripts/bench_e2e_workflow.py',
                   ROOT / 'scripts/verify_repeated_workflow.py', ROOT / 'scripts/bench_workflow_corpus.py',
                   ROOT / 'scripts/archive_workflow_cache.py']
        result['sources'] = {str(p.relative_to(ROOT)): sha(p) for p in sources}
        out.mkdir()
        write_json(out / 'summary.json', result)
        print(json.dumps(dict(status='passed', histories=len(result['histories']),
                              false_receipts=result['false_worker_receipts_rejected'],
                              workflow_cli=len(result['workflow_cli_rejections']),
                              corpus_cli=len(result['corpus_cli_rejections']))))


if __name__ == '__main__':
    main()
