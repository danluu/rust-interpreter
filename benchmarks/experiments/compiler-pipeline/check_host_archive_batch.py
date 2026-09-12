#!/usr/bin/env python3
"""Check batch routing and early rejection without running archive children."""
import argparse
from contextlib import redirect_stdout
from copy import deepcopy
import fcntl
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import archive_batch as batch
from check_cache_archive import replace
from reclaim_workflow_objects import sha
from verify_repeated_workflow import require
from workflow_io import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    batch.identifier(args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        raw, out = ROOT / '.work/runs' / args.run_id, ROOT / 'results' / args.run_id
        require(not raw.exists() and not out.exists(), 'qualification identity exists')
        raw.mkdir()
        host = dict(archive='host', workflow='completed-check', mode='host', proof_kind='workspace-check')
        guest = dict(archive='guest', workflow='completed-workflow', mode='candidate', corpus='completed-corpus')
        recovered = dict(archive='recovered', workflow='completed-recovered-case', mode='candidate',
                         corpus='assessed-interrupted-corpus', proof_kind='recovered-workflow')
        stopped = dict(archive='stopped', workflow='assessed-stopped-case', mode='native',
                       corpus='assessed-stopped-corpus', proof_kind='stopped-workflow')
        legacy = dict(archive='legacy', workflow='legacy-complete-case', mode='native',
                      corpus='legacy-complete-corpus', proof_kind='legacy-native')
        compiler = dict(archive='compiler', workflow='completed-compiler-case', mode='candidate',
                        proof_kind='compiler-comparison')
        rejected, routes = [], []

        def invoke(label, entries, action='prepare', altered=None, should_fail=False):
            root = raw / label
            root.mkdir()
            plan = root / 'batch.json'
            write_json(plan, dict(owner=str(root), schema_version=1, entries=entries))
            if action == 'apply':
                for entry in entries:
                    work = root / '.work/workflow-cache-archives' / entry['archive']
                    work.mkdir(parents=True)
                    prepared = {k: v for k, v in entry.items() if k != 'archive'}
                    prepared['corpus'] = entry.get('corpus')
                    if altered:
                        prepared.update(altered)
                    write_json(work / 'plan.json', prepared)
                    write_json(work / 'status.json', dict(status='prepared'))
            calls = []

            class SimulatedChild:
                pid = None

                def __init__(self, command, cwd):
                    require(cwd == root, 'child working directory differs')
                    calls.append(command)

                def wait(self):
                    return 0

            command = ['archive_batch.py', '--plan', str(plan), '--plan-sha256', sha(plan), '--action', action]
            error = None
            with replace(batch, 'ROOT', root), replace(sys, 'argv', command), \
                 replace(batch.subprocess, 'Popen', SimulatedChild), redirect_stdout(io.StringIO()):
                try:
                    batch.main()
                except RuntimeError as failure:
                    error = str(failure)
            if should_fail:
                require(error is not None and calls == [], 'invalid batch reached a child')
                rejected.append(dict(label=label, error=error))
            else:
                require(error is None and len(calls) == len(entries), 'valid batch routing failed')
                routes.append(dict(label=label, commands=calls))
            return calls

        calls = invoke('mixed-prepare', [host, guest, recovered, stopped, legacy, compiler])
        require(calls[0][2:] == ['--prepare', 'host', '--workspace-check', 'completed-check'] and
                calls[1][2:] == ['--prepare', 'guest', '--workflow', 'completed-workflow',
                                '--mode', 'candidate', '--corpus', 'completed-corpus'] and
                calls[2][2:] == ['--prepare', 'recovered', '--workflow', 'completed-recovered-case', '--mode',
                                'candidate', '--corpus', 'assessed-interrupted-corpus', '--recovered-corpus'] and
                calls[3][2:] == ['--prepare', 'stopped', '--workflow', 'assessed-stopped-case', '--mode',
                                'native', '--corpus', 'assessed-stopped-corpus', '--stopped-corpus'] and
                calls[4][2:] == ['--prepare', 'legacy', '--workflow', 'legacy-complete-case', '--mode',
                                'native', '--corpus', 'legacy-complete-corpus', '--legacy-native'] and
                calls[5][2:] == ['--prepare', 'compiler', '--workflow', 'completed-compiler-case', '--mode',
                                'candidate', '--compiler-comparison'],
                'selector arguments differ')
        calls = invoke('mixed-apply', [host, guest, recovered, stopped, legacy, compiler], action='apply')
        require([call[2:] for call in calls] == [['--apply', name] for name in ['host', 'guest', 'recovered', 'stopped', 'legacy', 'compiler']],
                'apply arguments differ')
        for label, changed in [
            ('host-with-guest-mode', dict(host, mode='native')),
            ('host-with-corpus', dict(host, corpus='unexpected')),
            ('unknown-provenance', dict(host, proof_kind='unknown')),
            ('workflow-with-host-mode', {k: v for k, v in host.items() if k != 'proof_kind'}),
            ('explicit-workflow-kind', dict(guest, proof_kind='workflow')),
            ('legacy-with-candidate-mode', dict(legacy, mode='candidate')),
            ('legacy-without-corpus', {k: v for k, v in legacy.items() if k != 'corpus'}),
            ('stopped-with-host-mode', dict(stopped, mode='host')),
            ('stopped-without-corpus', {k: v for k, v in stopped.items() if k != 'corpus'}),
            ('recovered-with-host-mode', dict(recovered, mode='host')),
            ('recovered-without-corpus', {k: v for k, v in recovered.items() if k != 'corpus'}),
            ('compiler-with-host-mode', dict(compiler, mode='host')),
            ('compiler-with-corpus', dict(compiler, corpus='unexpected')),
        ]:
            # Invalid later entries must prevent even the valid prefix running.
            invoke(label, [dict(guest, archive='valid-prefix'), changed], should_fail=True)
        invoke('duplicate-host-target', [host, dict(host, archive='second')], should_fail=True)
        invoke('duplicate-archive-id', [host, dict(guest, archive='host')], should_fail=True)
        invoke('same-target-different-proof-kind', [guest, dict(recovered, workflow=guest['workflow'])], should_fail=True)
        invoke('changed-legacy-kind', [legacy], action='apply', altered={'proof_kind': 'workflow'}, should_fail=True)
        invoke('duplicate-legacy-target', [legacy, dict(legacy, archive='second')], should_fail=True)
        invoke('changed-stopped-kind', [stopped], action='apply', altered={'proof_kind': 'workflow'}, should_fail=True)
        invoke('duplicate-stopped-target', [stopped, dict(stopped, archive='second')], should_fail=True)
        invoke('changed-recovered-kind', [recovered], action='apply', altered={'proof_kind': 'workflow'}, should_fail=True)
        invoke('changed-compiler-kind', [compiler], action='apply', altered={'proof_kind': 'workflow'}, should_fail=True)
        invoke('duplicate-compiler-target', [compiler, dict(compiler, archive='second')], should_fail=True)
        for label, altered in [('changed-kind', {'proof_kind': 'workflow'}),
                               ('changed-mode', {'mode': 'native'}),
                               ('changed-corpus', {'corpus': 'unexpected'}),
                               ('changed-run', {'workflow': 'another-check'})]:
            invoke(label, [host], action='apply', altered=altered, should_fail=True)
        out.mkdir()
        write_json(out / 'summary.json', dict(status='passed', rejected=rejected, simulated_routes=routes,
            real_archive_children=0, real_compiler_cache_modified=False,
            note='Only coordinator routing is simulated here. A separately reviewed real host pilot must still pass preparation, application and final receipt assessment.',
            sources={str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), Path(batch.__file__)]}))
        print(json.dumps(dict(status='passed', rejections=len(rejected), simulated_routes=len(routes))))


if __name__ == '__main__':
    main()
