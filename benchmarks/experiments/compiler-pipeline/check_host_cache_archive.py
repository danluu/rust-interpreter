#!/usr/bin/env python3
"""Qualify host-cache selection with preserved real evidence and owned fixtures."""
import argparse
from copy import deepcopy
import fcntl
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import archive_workflow_cache as coordinator
import cache_archive as archive
from host_cache_evidence import debug_workspace_cache, validate_debug_cache
from workspace_check_evidence import validate_identity
from reclaim_workflow_objects import sha
from verify_repeated_workflow import require
from workflow_io import write_json
from check_cache_archive import fixture, replace


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    coordinator.identifier(args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        raw, out = ROOT / '.work/runs' / args.run_id, ROOT / 'results' / args.run_id
        require(not raw.exists() and not out.exists(), 'qualification identity exists')
        raw.mkdir()
        rejected = []

        def rejects(label, operation):
            try:
                operation()
            except RuntimeError as error:
                rejected.append(dict(label=label, error=str(error)))
            else:
                raise RuntimeError('invalid host selection succeeded: ' + label)

        real = []
        for run in ['allocation-trace-debug-01', 'resumable-bulk-debug-01', 'bounded-native-vm-03']:
            target, proofs, verified = debug_workspace_cache(ROOT, run, sha)
            real.append(dict(run=run, target=str(target), evidence_hashes=len(proofs), verification=verified))
        run = 'allocation-trace-debug-01'
        target, proofs, verified = debug_workspace_cache(ROOT, run, sha)
        original_plan = read(ROOT / '.work' / run / 'plan.json')
        original_status = read(ROOT / '.work' / run / 'status.json')
        original_report = read(ROOT / 'results' / run / 'summary.json')

        def validate(plan, status, report, selected=target, external=proofs, verification=verified):
            validate_identity(run, plan, status, report)
            validate_debug_cache(ROOT, run, selected, external, verification, report, status)

        mutations = [
            ('unfinished check', 'status', 'status', 'running'),
            ('failed check', 'status', 'returncode', 1),
            ('changed owner', 'status', 'owner', '/another-owner'),
            ('failed report', 'report', 'returncode', 1),
            ('not frozen', 'report', 'frozen_sources_unchanged', False),
            ('performance measurement', 'report', 'performance_measurement', True),
            ('wrong source archive', 'plan', 'source_archive', '.work/other/source'),
            ('wrong target', 'plan', 'target', '.work/diagnostic-builds/other'),
            ('published tool report', 'report', 'installed_tool', {'tool_key': 'not-eligible'}),
            ('empty publication record', 'report', 'installed_tool', {}),
        ]
        for label, where, key, value in mutations:
            records = dict(plan=deepcopy(original_plan), status=deepcopy(original_status), report=deepcopy(original_report))
            records[where][key] = value
            rejects(label, lambda: validate(**records))
        for label, extra in [('release profile', ['--release']), ('custom profile', ['--profile', 'test']),
                             ('joined custom profile', ['--profile=test'])]:
            records = dict(plan=deepcopy(original_plan), status=deepcopy(original_status), report=deepcopy(original_report))
            for record in records.values():
                record['command'] += extra
            rejects(label, lambda: validate(**records))
        rejects('published verification', lambda: validate(original_plan, original_status, original_report,
            verification=dict(verified, installed_tool={'tool_key': 'not-eligible'})))
        rejects('target of another check', lambda: validate(original_plan, original_status, original_report,
            selected=ROOT / '.work/diagnostic-builds/resumable-bulk-debug-01'))
        inside = next(p for p in target.rglob('*') if p.is_file())
        rejects('evidence inside retired target', lambda: validate(original_plan, original_status, original_report,
            external={str(inside.relative_to(ROOT)): sha(inside)}))
        rejects('no external evidence', lambda: validate(original_plan, original_status, original_report, external={}))
        rejects('absolute evidence path', lambda: validate(original_plan, original_status, original_report,
            external={str(ROOT / 'Cargo.toml'): sha(ROOT / 'Cargo.toml')}))
        rejects('real installed release build', lambda: debug_workspace_cache(ROOT, 'allocation-trace-release-01', sha))
        for label, mode, kind, corpus in [
            ('unknown provenance', 'native', 'unknown', None),
            ('host with guest mode', 'native', 'workspace-check', None),
            ('host with corpus', 'host', 'workspace-check', 'corpus'),
            ('workflow with host mode', 'host', 'workflow', None),
        ]:
            rejects(label, lambda: coordinator.selected_cache('unused-fixture', corpus, mode, kind))

        legacy = []
        for mode in ['native', 'check', 'baseline', 'candidate']:
            selected, external, verification = coordinator.selected_cache('worker-count-nushell-cold-01', None, mode)
            legacy.append(dict(mode=mode, target=str(selected), evidence_hashes=len(external), verification=verification))

        cli = []
        for arguments, diagnostic in [
            (['--prepare', 'unused-host-qualification'], 'supply exactly one completed source'),
            (['--prepare', 'unused-host-qualification', '--workflow', run, '--workspace-check', run], 'not allowed with argument'),
            (['--prepare', 'unused-host-qualification', '--workspace-check', run, '--mode', 'native'], 'cannot have --mode or --corpus'),
            (['--prepare', 'unused-host-qualification', '--workspace-check', run, '--corpus', 'unused'], 'cannot have --mode or --corpus'),
            (['--apply', 'unused-host-qualification', '--workspace-check', run], 'supply exactly one completed source'),
            (['--apply', 'unused-host-qualification', '--mode', 'native'], 'supply --mode only when preparing'),
        ]:
            command = [sys.executable, str(ROOT / 'scripts/archive_workflow_cache.py'), *arguments]
            result = subprocess.run(command, capture_output=True, text=True)
            require(result.returncode in [1, 2] and diagnostic in result.stderr and
                    'BlockingIOError' not in result.stderr, 'CLI did not reject before the held benchmark lock')
            cli.append(dict(command=command, returncode=result.returncode, stderr=result.stderr))
        require(not (coordinator.BASE / 'unused-host-qualification').exists(), 'CLI rejection created an inventory')

        root = raw / 'host-coordinator'
        target = root / '.work/diagnostic-builds/fixture'
        manifest = fixture(target)
        (root / 'results').mkdir()
        external = root / 'evidence.json'
        external.write_bytes(b'original host qualification evidence\n')
        before = sha(external)

        def fixture_evidence(selected_root, name, digest):
            require(selected_root == root and name == 'fixture', 'host selector identity changed')
            return target, {'evidence.json': sha(external)}, {'kind': 'completed host workspace check', 'installed_tool': None}

        with replace(coordinator, 'ROOT', root), replace(coordinator, 'BASE', root / '.work/workflow-cache-archives'), \
             replace(coordinator, 'debug_workspace_cache', fixture_evidence), \
             replace(coordinator, 'sources', lambda: {'fixture': 'fixed'}):
            coordinator.owned_root()
            coordinator.prepare('archive', 'fixture', None, 'host', 'workspace-check')
            prepared = read(coordinator.BASE / 'archive/plan.json')
            require(prepared['proof_kind'] == 'workspace-check' and prepared['mode'] == 'host', 'host provenance was not recorded')
            archive.unchanged(target, manifest)
            external.write_bytes(b'changed host qualification evidence\n')
            rejects('changed host evidence before application', lambda: coordinator.apply('archive'))
            require(read(coordinator.BASE / 'archive/status.json')['status'] == 'prepared' and
                    not (coordinator.BASE / 'archive/cache.partial.zip').exists(), 'evidence rejection began archival')
            external.write_bytes(b'original host qualification evidence\n')
            coordinator.apply('archive')
            require(not any(target.iterdir()) and sha(external) == before, 'host retirement changed external evidence')
            packed = coordinator.BASE / 'archive/cache.zip'
            manifest = prepared['manifest']
            require(archive.read_file(packed, manifest, 'metadata.json', 1024) == b'{"owned":true}\n', 'host archive inspection differs')
            archive.restore(packed, manifest, root / 'restored')
            archive.unchanged(root / 'restored', manifest, restored=True)
            rejects('repeat host application', lambda: coordinator.apply('archive'))
            rejects('new identity for retired host target', lambda: coordinator.prepare('again', 'fixture', None, 'host', 'workspace-check'))

        out.mkdir()
        write_json(out / 'summary.json', dict(status='passed', rejected=rejected, cli_rejections=cli,
            real_host_checks=real, real_workflow_modes=legacy, host_fixture_archived_restored=True,
            external_host_evidence_preserved=True, real_compiler_cache_modified=False,
            sources={str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), *coordinator.SOURCES]},
            raw=str(raw.relative_to(ROOT))))
        print(json.dumps(dict(status='passed', selection_rejections=len(rejected), cli_rejections=len(cli),
            real_host_checks=len(real), real_workflow_modes=len(legacy))))


if __name__ == '__main__':
    main()
