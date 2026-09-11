#!/usr/bin/env python3
"""Qualify interrupted-corpus cache provenance without preparing or retiring caches."""
import argparse
import copy
import fcntl
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import archive_workflow_cache as archive
import recovered_corpus_cache_evidence as recovery
from reclaim_workflow_objects import sha
from verify_repeated_workflow import require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['', '.', '..'], 'invalid run ID')
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        paths = [recovery.RECOVERY, recovery.FAILURE,
            '.work/corpus-runs/' + recovery.ORIGINAL + '/status.json',
            '.work/corpus-runs/' + recovery.ORIGINAL + '/plan.json',
            recovery.ASSESSMENT + '/status.json', recovery.ASSESSMENT + '/plan.json']
        bundle = [json.loads((ROOT / p).read_text()) for p in paths]
        run = recovery.ORIGINAL + '-nushell'
        recovery.validate(bundle, ROOT, run)
        mutations = []
        def field(index, key, value):
            b = copy.deepcopy(bundle); b[index][key] = value
            mutations.append((str(index) + ':' + key, b))
        for index, key, value in [
            (0, 'status', 'incomplete'), (0, 'original_run_status', 'finished'),
            (0, 'failure_report', 'results/other/summary.json'), (0, 'assessor_sha256', '0' * 64),
            (0, 'counts', dict(primary_commands=440, check_commands=147, edited_pairs=105, artifacts=294)),
            (1, 'run_id', 'another-run'), (1, 'status', 'passed'), (1, 'source_restored', False),
            (1, 'no_matching_processes', False), (1, 'stale_original_status_receipts_preserved', False),
            (1, 'incomplete_workflow', 'ruff'), (1, 'completed_workflows', 5),
            (2, 'cwd', '/wrong-owner'), (2, 'status', 'finished'), (2, 'case', 'ruff'),
            (2, 'completed', bundle[2]['completed'][:-1]),
            (4, 'status', 'running'), (4, 'returncode', 1), (4, 'owner', '/wrong-owner'),
            (4, 'command', ['python3', 'wrong-assessor.py']), (5, 'owner', '/wrong-owner'),
            (5, 'command', ['python3', 'wrong-assessor.py']),
        ]:
            field(index, key, value)
        for key in ['run_id', 'candidate_tool_key', 'baseline_tool_key']:
            b = copy.deepcopy(bundle); b[3]['options'][key] = 'wrong'
            mutations.append(('plan-option:' + key, b))
        b = copy.deepcopy(bundle); b[3]['frozen'] = {}; mutations.append(('frozen-inputs', b))
        for key in ['report', 'report_sha256']:
            b = copy.deepcopy(bundle)
            next(r for r in b[0]['workflows'] if r['workflow'] == 'nushell')[key] = 'wrong'
            mutations.append(('assessment:' + key, b))
        b = copy.deepcopy(bundle); b[0]['workflows'] += [next(r for r in b[0]['workflows'] if r['workflow'] == 'nushell')]
        mutations.append(('duplicate-assessed-case', b))
        b = copy.deepcopy(bundle); b[2]['completed'][1]['report'] = 'results/wrong/summary.json'
        mutations.append(('ledger-report', b))
        rejected = []
        for label, changed in mutations:
            try:
                recovery.validate(changed, ROOT, run)
            except RuntimeError:
                rejected.append(label)
            else:
                raise RuntimeError('accepted altered recovery: ' + label)
        for label in ['rg-aot', 'nushell-type-relations', 'unknown']:
            try:
                recovery.validate(bundle, ROOT, recovery.ORIGINAL + '-' + label)
            except RuntimeError:
                rejected.append('ineligible-case:' + label)
            else:
                raise RuntimeError('accepted ineligible case: ' + label)
        _, proofs, _ = recovery.evidence(ROOT, recovery.ORIGINAL, run, sha)
        tampered = [ROOT / recovery.FAILURE, ROOT / recovery.ASSESSOR,
                    ROOT / (recovery.ASSESSMENT + '/plan.json'), ROOT / (recovery.ASSESSMENT + '/command.log'),
                    ROOT / '.work/corpus-runs' / recovery.ORIGINAL / 'status.json',
                    ROOT / 'results/resumable-bulk-heldout-failure-01/evidence-03.json']
        for target in tampered:
            try:
                recovery.evidence(ROOT, recovery.ORIGINAL, run, lambda path: '0' * 64 if path == target else sha(path))
            except RuntimeError:
                rejected.append('hash:' + str(target.relative_to(ROOT)))
            else:
                raise RuntimeError('accepted altered evidence hash')
        targets = []
        registry = ROOT / '.work/workflow-cache-archives/targets.json'
        registry_hash = sha(registry)
        for label in ['nushell', 'ruff']:
            for mode in ['check', 'baseline', 'candidate', 'native']:
                target, checked, verification = archive.selected_cache(recovery.ORIGINAL + '-' + label,
                    recovery.ORIGINAL, mode, 'recovered-workflow')
                require(verification['commands'] == 63 and verification['check_commands'] == 21 and
                        verification['exact_artifact_hashes_verified'] == 42, 'completed case count differs')
                targets.append(dict(workflow=recovery.ORIGINAL + '-' + label, mode=mode, target=str(target),
                                    evidence=checked, verification=verification))
        try:
            archive.selected_cache(run, recovery.ORIGINAL, 'native')
        except RuntimeError:
            rejected.append('ordinary-path-still-rejects-interrupted-parent')
        else:
            raise RuntimeError('ordinary archival silently accepted interrupted parent')
        require(sha(registry) == registry_hash, 'read-only qualification changed archive registry')
        out = ROOT / 'results' / args.run_id
        out.mkdir(exist_ok=False)
        source_paths = [Path(__file__), *[ROOT / p for p in archive.sources()],
                        ROOT / 'benchmarks/experiments/compiler-pipeline/archive_batch.py']
        record = dict(status='passed', targets=targets, rejected=rejected,
            sources={str(p.relative_to(ROOT)): sha(p) for p in source_paths},
            recovery_evidence={str(p.relative_to(ROOT)): sha(p) for p in proofs},
            archive_registry_unchanged=True, caches_prepared=0, caches_retired=0,
            original_failure_status_unchanged=True, performance_measurement=False)
        (out / 'summary.json').write_text(json.dumps(record, indent=2) + '\n')
        print(json.dumps(dict(status='passed', targets=len(targets), rejections=len(rejected))))


if __name__ == '__main__':
    main()
