#!/usr/bin/env python3
"""Qualify exact stopped-history ownership without modifying a compiler cache."""
import argparse
from copy import deepcopy
import fcntl
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import stopped_workflow_cache_evidence as stopped
from archive_workflow_cache import selected_cache
from reclaim_workflow_objects import sha, identifier
from verify_repeated_workflow import require
from workflow_io import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    identifier(args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        registry = ROOT / '.work/workflow-cache-archives/targets.json'
        before = sha(registry)
        failure = json.loads((ROOT / stopped.REPORT).read_text())
        workflow = stopped.CORPUS + '-' + stopped.LABEL
        actual = []
        for mode in ['check', 'baseline', 'candidate', 'native']:
            target, proofs, verified = selected_cache(workflow, stopped.CORPUS, mode, 'stopped-workflow')
            require(verified['completed_workflows'] == 0 and verified['measured_successful_edit_pairs'] == 0,
                    'cache proof claimed benchmark completion')
            actual.append(dict(mode=mode, target=str(target), proofs=proofs, verification=verified))
        require(len({row['target'] for row in actual}) == 4, 'stopped modes share a target')
        rejected = []

        def rejects(name, callback):
            try:
                callback()
            except (RuntimeError, FileNotFoundError):
                rejected.append(name)
            else:
                raise RuntimeError('invalid evidence accepted: ' + name)

        for field, value in [('run_id', 'another'), ('status', 'finished'), ('completed_workflows', 1),
            ('measured_successful_edit_pairs', 1), ('primary_records', 4), ('check_records', 2),
            ('source_restored', False), ('retained', True), ('original_records_unchanged', False),
            ('cache_cleanup_performed', True), ('process_signals_sent', True), ('snapshots', {})]:
            altered = deepcopy(failure)
            altered[field] = value
            rejects('assessment-' + field, lambda: stopped.validate(altered, stopped.CORPUS, workflow, 'native'))
        for label, corpus, run, mode in [
            ('unknown-corpus', 'unknown', workflow, 'native'),
            ('another-workflow', stopped.CORPUS, workflow + '-other', 'native'),
            ('private-workflow', stopped.CORPUS, stopped.CORPUS + '-rg-aot', 'native'),
            ('host-mode', stopped.CORPUS, workflow, 'host')]:
            rejects(label, lambda: stopped.validate(failure, corpus, run, mode))
        for name in actual[0]['proofs']:
            def bad_hash(path, selected=ROOT / name):
                return '0' * 64 if path == selected else sha(path)
            rejects('hash-' + name, lambda: stopped.cache(ROOT, workflow, stopped.CORPUS, 'native', bad_hash))
        rejects('ordinary-success-proof', lambda: selected_cache(workflow, stopped.CORPUS, 'native'))
        require(sha(registry) == before, 'read-only qualification modified archive reservations')
        out = ROOT / 'results' / args.run_id
        out.mkdir(exist_ok=False)
        sources = [Path(__file__), ROOT / 'scripts/stopped_workflow_cache_evidence.py',
                   ROOT / 'scripts/archive_workflow_cache.py', ROOT / 'scripts/workflow_cache_evidence.py']
        write_json(out / 'summary.json', dict(status='passed', actual_targets=actual, rejected=rejected,
            archive_registry_unchanged=True, compiler_caches_modified=False,
            sources={str(p.relative_to(ROOT)): sha(p) for p in sources}))
        (out / 'assessment.md').write_text(
            '# Cache ownership after a between-command stop\n\n'
            'All four exact public cache targets pass. Their recorded compiler children '
            'finished, the stop assessment is terminal, source is restored, and all preserved '
            'receipts and executed snapshots match. The proof retains zero completed workflows '
            'and zero successful-edit pairs.\n\n'
            f'{len(rejected)} altered assessments, hashes, scopes and success-proof substitutions '
            'are rejected. No compiler cache or archive reservation changed.\n')
        print(json.dumps(dict(status='passed', targets=len(actual), rejections=len(rejected))))


if __name__ == '__main__':
    main()
