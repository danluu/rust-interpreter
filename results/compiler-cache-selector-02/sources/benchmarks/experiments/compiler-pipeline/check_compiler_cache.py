#!/usr/bin/env python3
"""Check compiler-comparison ownership and fixture archival before real retirement."""
import argparse
from contextlib import redirect_stdout
import fcntl
import io
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'scripts'))
import archive_workflow_cache as coordinator
import compiler_comparison_cache_evidence as comparison
from check_cache_archive import archive, fixture, replace
from reclaim_workflow_objects import sha, identifier
from verify_repeated_workflow import require
from workflow_io import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    identifier(args.run_id)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        raw, out = ROOT/'.work/runs'/args.run_id, ROOT/'results'/args.run_id
        require(not raw.exists() and not out.exists(), 'qualification identity already exists')
        raw.mkdir()
        registry = ROOT/'.work/workflow-cache-archives/targets.json'
        registry_before = sha(registry)
        run = comparison.PREFIX + 'nushell-type-relations'
        actual, rejected = [], []

        def rejects(name, operation):
            try:
                operation()
            except (RuntimeError, FileNotFoundError):
                rejected.append(name)
            else:
                raise RuntimeError('invalid compiler cache evidence accepted: ' + name)

        for mode in ['native', 'check', 'baseline', 'candidate']:
            target, proofs, verified = coordinator.selected_cache(run, None, mode, 'compiler-comparison')
            require(verified['compiler_comparison'] and verified['source_restored'] and
                    verified['commands'] == 63 and verified['check_commands'] == 21 and
                    verified['edited_pairs'] == 15 and verified['exact_artifact_hashes_verified'] == 42,
                    'compiler comparison coverage changed')
            actual.append(dict(mode=mode, target=str(target), proofs=proofs, verification=verified))
        require(len({r['target'] for r in actual}) == 4, 'compiler targets overlap')
        for label in sorted(comparison.PUBLIC):
            for mode in ['native', 'check', 'baseline', 'candidate']:
                require(comparison.selection(comparison.PREFIX+label, None, mode) == label,
                        'public catalog routing changed')
        for label, selected, corpus, mode in [
            ('private case', comparison.PREFIX+'rg-aot', None, 'native'),
            ('unknown case', comparison.PREFIX+'unknown', None, 'native'),
            ('other experiment', 'other-nushell-type-relations', None, 'native'),
            ('arbitrary target', '/tmp/cache', None, 'native'),
            ('invalid run type', None, None, 'native'),
            ('unexpected corpus', run, 'parent', 'native'),
            ('host mode', run, None, 'host'),
            ('unknown mode', run, None, 'unknown'),
        ]:
            rejects(label, lambda: comparison.selection(selected, corpus, mode))
        rejects('wrong workspace', lambda: comparison.cache(ROOT/'another', run, None, 'native', sha))
        rejects('unstarted public case', lambda: comparison.cache(ROOT, comparison.PREFIX+'ruff', None, 'native', sha))
        rejects('ordinary proof substitution', lambda: coordinator.selected_cache(run, None, 'native'))
        proof_names = sorted(actual[0]['proofs'])
        selected_proofs = {comparison.QUALIFICATION}
        # Corrupt only digests with an independent recorded expectation.
        # Fresh receipt-file digests are collected here, not compared to a
        # historical digest by this provider; their contents are reverified.
        pinned = json.loads((ROOT/comparison.QUALIFICATION).read_text())['evidence']
        selected_proofs.update(name for name in proof_names if name in pinned and name.endswith(
            ('plan.json', 'status.json', 'report_heldouts.py')))
        selected_proofs.add(next(name for name in proof_names if '/artifacts/' in name))
        for name in sorted(selected_proofs):
            def altered_digest(path, selected=ROOT/name):
                return '0'*64 if path == selected else sha(path)
            rejects('changed proof: '+name, lambda: comparison.cache(ROOT, run, None, 'native', altered_digest))
        invalid_cli = [
            ['--apply', 'unused', '--compiler-comparison'],
            ['--prepare', 'unused', '--workspace-check', 'check', '--compiler-comparison'],
            ['--prepare', 'unused', '--workflow', run, '--corpus', 'parent', '--compiler-comparison'],
            ['--prepare', 'unused', '--workflow', run, '--corpus', 'parent', '--recovered-corpus', '--compiler-comparison'],
            ['--prepare', 'unused', '--workflow', run, '--corpus', 'parent', '--stopped-corpus', '--compiler-comparison'],
            ['--prepare', 'unused', '--workflow', run, '--corpus', 'parent', '--legacy-native', '--compiler-comparison'],
        ]
        for index, arguments in enumerate(invalid_cli):
            result = subprocess.run([sys.executable, str(ROOT/'scripts/archive_workflow_cache.py'), *arguments],
                                    cwd=ROOT, capture_output=True, text=True)
            require(result.returncode != 0 and 'compiler-comparison requires' in result.stderr and
                    'Resource temporarily unavailable' not in result.stderr,
                    'invalid compiler selector reached archive locking or mutation')
            rejected.append('CLI '+str(index))
        # Exercise the real archive machinery on an owned fixture. The provider
        # is simulated here; the four actual target proofs above are read-only.
        root = raw/'fixture'
        target = root/'.work/runs/completed/native'
        manifest = fixture(target)
        (root/'results').mkdir()
        outside = root/'evidence.json'
        outside.write_text('preserved evidence\n')
        outside_sha = sha(outside)

        def provider(selected_root, selected_run, corpus, mode, digest):
            require(selected_root == root and selected_run == 'completed' and corpus is None and mode == 'native',
                    'compiler fixture provider received different selection')
            return target, {'evidence.json': sha(outside)}, {'compiler_comparison': True, 'performance_gate_passed': False}

        with replace(coordinator, 'compiler_cache', provider), replace(coordinator, 'ROOT', root), \
             replace(coordinator, 'BASE', root/'.work/workflow-cache-archives'), \
             replace(coordinator, 'sources', lambda: {'fixture': 'fixed'}), redirect_stdout(io.StringIO()):
            coordinator.owned_root()
            coordinator.prepare('archive', 'completed', None, 'native', 'compiler-comparison')
            work, prepared, _ = coordinator.load('archive')
            require(prepared['proof_kind'] == 'compiler-comparison' and prepared['corpus'] is None,
                    'compiler provenance was lost during preparation')
            coordinator.apply('archive')
            require(not list(target.iterdir()), 'fixture retirement incomplete')
            archive.restore(work/'cache.zip', manifest, root/'restored')
            archive.unchanged(root/'restored', manifest, restored=True)
            require(sha(outside) == outside_sha and
                    json.loads((work/'status.json').read_text())['status'] == 'completed',
                    'fixture evidence or completion changed')
            rejects('repeat fixture application', lambda: coordinator.apply('archive'))
        require(sha(registry) == registry_before, 'qualification changed real archive reservations')
        out.mkdir()
        write_json(out/'summary.json', dict(status='passed', actual_targets=actual, rejected=rejected,
            public_catalog_routes=24, fixture_archive_restored=True, completed_failed_gate_preserved=True,
            real_compiler_caches_modified=False, archive_registry_unchanged=True,
            sources={str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), *coordinator.SOURCES]}))
        print(dict(status='passed', actual_targets=4, rejected=len(rejected), fixture_archive_restored=True))


if __name__ == '__main__':
    main()
