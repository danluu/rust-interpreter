#!/usr/bin/env python3
"""Check legacy cache ownership and reject changed scope or incomplete commands."""
import argparse
from copy import deepcopy
import fcntl
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import legacy_native_cache_evidence as legacy
from archive_workflow_cache import selected_cache
from reclaim_workflow_objects import identifier, sha
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
        catalog = json.loads((ROOT / legacy.CATALOG).read_text())
        actual, rejected = [], []
        for group in catalog['groups']:
            for variant in group['variants']:
                identity = group['run'] + '-' + group['project'] + '-' + variant
                target, proofs, verified = selected_cache(identity, group['run'], 'native', 'legacy-native')
                require(verified['completed_commands'] == 2 + 3 * group['repeats'], 'legacy command total differs')
                actual.append(dict(identity=identity, target=str(target), evidence_files=len(proofs), verification=verified))
        require(len(actual) == 20 and len({row['target'] for row in actual}) == 20,
                'legacy catalog did not select twenty independent targets')

        def reject(label, callback):
            try:
                callback()
            except RuntimeError:
                rejected.append(label)
            else:
                raise RuntimeError('accepted invalid legacy evidence: ' + label)

        group = catalog['groups'][0]
        identity = group['run'] + '-' + group['project'] + '-llvm'
        for field, value in [('owner', '/wrong'), ('schema_version', 2), ('groups', [])]:
            changed = deepcopy(catalog)
            changed[field] = value
            reject('catalog-' + field, lambda: legacy.select(changed, ROOT, identity, group['run'], 'native'))
        for field, value in [('project', 'rg-aot'), ('run', '../outside'), ('repeats', 1), ('variants', ['llvm'])]:
            changed = deepcopy(catalog)
            changed['groups'][0][field] = value
            reject('group-' + field, lambda: legacy.select(changed, ROOT, identity, group['run'], 'native'))
        for label, run, corpus, mode in [('unknown-identity', 'unknown', group['run'], 'native'),
            ('wrong-corpus', identity, 'unknown', 'native'), ('wrong-mode', identity, group['run'], 'candidate')]:
            reject(label, lambda: legacy.select(catalog, ROOT, run, corpus, mode))
        raw = ROOT / '.work/runs' / group['run'] / group['project']
        provenance = json.loads((raw / 'provenance.json').read_text())
        rows = [json.loads(line) for line in (raw / 'results.jsonl').read_text().splitlines()]
        summary = json.loads((ROOT / 'results' / group['run'] / 'summary.json').read_text())
        for label, changed in [('missing-final', rows[:-1]), ('duplicate', rows + rows[:1]), ('reordered', rows[::-1])]:
            reject(label, lambda: legacy.validate_records(ROOT, group, provenance, changed, summary))
        for field, value in [('project', 'rg-aot'), ('status', 'running'), ('exit_code', 1), ('pid', None),
            ('target_dir', '/outside'), ('binary', '/outside/binary'), ('build_seconds', 0),
            ('runtime_seconds', 0), ('runtime_stdout_sha256', ''), ('source_sha256', 'changed'), ('ordinal', 1000)]:
            changed = deepcopy(rows)
            changed[0][field] = value
            reject('record-' + field, lambda: legacy.validate_records(ROOT, group, provenance, changed, summary))
        changed = deepcopy(rows)
        changed[0]['binary'] = str(Path(rows[0]['target_dir']) / '..' / 'outside')
        reject('binary-parent-traversal', lambda: legacy.validate_records(ROOT, group, provenance, changed, summary))
        for field, value in [('compiler', 'wrong'), ('variants', ['llvm']), ('jobs', 999)]:
            changed = deepcopy(provenance)
            changed[field] = value
            reject('provenance-' + field, lambda: legacy.validate_records(ROOT, group, changed, rows, summary))
        changed = deepcopy(summary)
        changed['summary'] = []
        reject('missing-summary', lambda: legacy.validate_records(ROOT, group, provenance, rows, changed))
        paths = [ROOT / 'results' / group['run'] / 'summary.json', raw / 'provenance.json',
                 raw / 'results.jsonl', ROOT / group['archived_harness'], raw / '000-llvm-cold.json']
        for path in paths:
            def altered_hash(current, selected=path):
                return '0' * 64 if current == selected else sha(current)
            reject('hash-' + str(path.relative_to(ROOT)),
                   lambda: legacy.cache(ROOT, identity, group['run'], 'native', altered_hash))
        require(sha(registry) == before, 'qualification modified archive reservations')
        out = ROOT / 'results' / args.run_id
        out.mkdir(exist_ok=False)
        sources = [Path(__file__), ROOT / 'scripts/legacy_native_cache_evidence.py', ROOT / legacy.CATALOG,
                   ROOT / 'scripts/archive_workflow_cache.py']
        write_json(out / 'summary.json', dict(status='passed', actual_targets=actual, rejected=rejected,
            archive_registry_unchanged=True, compiler_caches_modified=False,
            sources={str(path.relative_to(ROOT)): sha(path) for path in sources}))
        (out / 'assessment.md').write_text(
            'Twenty exact caches across seven completed public legacy histories pass ownership checks. '
            f'{len(rejected)} altered scopes, command histories and hashes are rejected. '
            'Source pins and restoration verify. No compiler cache or archive reservation changed.\n\n'
            'This checks cache ownership and recorded completion, without reassessing historical '
            'performance or invoking an old compiler backend.\n')
        print(json.dumps(dict(status='passed', targets=len(actual), rejections=len(rejected))))


if __name__ == '__main__':
    main()
