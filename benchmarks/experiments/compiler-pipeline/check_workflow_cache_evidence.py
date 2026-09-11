#!/usr/bin/env python3
"""Qualify completed cache selection without modifying any compiler cache."""
import argparse
from copy import deepcopy
import fcntl
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from reclaim_workflow_objects import identifier, sha, workflow
from verify_repeated_workflow import require
from workflow_cache_evidence import cache_guard, derive, workflow_cache
from workflow_io import write_json
import archive_workflow_cache as coordinator


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    run_id = identifier(args.run_id)
    raw = ROOT / '.work/runs' / run_id
    output = ROOT / 'results' / run_id
    require(not raw.exists() and not output.exists(), 'qualification identity already exists')
    read = lambda path: json.loads(path.read_text())
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        raw.mkdir()
        real = []
        for name in ['lightweight-wrapper-nushell-qualification-01',
                     'lightweight-wrapper-pgrust-repeated-01', 'interface-nushell-repeated-01']:
            for mode in ['check', 'baseline', 'candidate']:
                target, proofs, verification = workflow_cache(ROOT, name, None, mode, workflow, sha)
                with cache_guard(target, mode):
                    require(all(sha(ROOT / p) == h for p, h in proofs.items()), 'preserved proof changed')
                real.append(dict(workflow=name, mode=mode, target=str(target.relative_to(ROOT)),
                    proofs=len(proofs), artifacts=verification['exact_artifact_hashes_verified'],
                    selection=verification['cache_selection']))
        name = 'lightweight-wrapper-nushell-qualification-01'
        source = ROOT / '.work/runs' / name
        report = read(ROOT / 'results' / name / 'summary.json')
        rows = read(source / 'records.json')
        checks = read(source / 'check-records.json')
        custom_index = next(i for i, r in enumerate(rows) if r['mode'] == 'candidate')
        rejected = []

        def rejects(label, operation):
            try:
                operation()
            except (RuntimeError, BlockingIOError) as error:
                rejected.append(dict(label=label, error=str(error)))
            else:
                raise RuntimeError('accepted ' + label)

        def changed(label, mutate, mode='candidate'):
            r, rs, cs = deepcopy(report), deepcopy(rows), deepcopy(checks)
            mutate(r, rs, cs)
            rejects(label, lambda: derive(ROOT, name, r, rs, cs, mode))

        def command_change(flag, value, append=False):
            def change(r, rs, cs):
                cmd = rs[custom_index]['calls'][0]['command']
                if append:
                    cmd.extend([flag, value])
                else:
                    cmd[cmd.index(flag) + 1] = value
            return change

        changed('private project', lambda r, rs, cs: r.update(project='rg-aot'))
        changed('foreign workflow root', lambda r, rs, cs: r.update(raw='.work/runs/another-run'))
        changed('unbatched export', lambda r, rs, cs: r.update(batch=False))
        changed('foreign source manifest', command_change('--manifest-path', '/tmp/Cargo.toml'))
        changed('different package', command_change('--package', 'another-package'))
        changed('shared namespace', command_change('--cache-namespace', name + ':baseline'))
        changed('empty namespace', command_change('--cache-namespace', ''))
        changed('duplicate namespace', command_change('--cache-namespace', name + ':candidate', True))
        changed('missing namespace', lambda r, rs, cs: rs[custom_index]['calls'][0]['command'].remove('--cache-namespace'))
        changed('other tool key', command_change('--tool-key', '0' * 64))
        changed('invalid recorded key', lambda r, rs, cs: r['tool_builds']['candidate'].update(tool_key='../invalid'))
        changed('foreign launcher', lambda r, rs, cs: rs[custom_index]['calls'][0]['command'].__setitem__(1, '/tmp/interpreter.py'))
        changed('missing test selection', lambda r, rs, cs: rs[custom_index]['calls'][0]['command'].remove('--test-body'))
        changed('missing standard MIR', lambda r, rs, cs: rs[custom_index]['calls'][0]['command'].remove('--std-mir'))
        changed('other standard MIR identity', lambda r, rs, cs: r['std_mir'].update(key='0' * 64))
        changed('changed launch receipt', lambda r, rs, cs: rs[custom_index]['calls'][0]['launch'].update(tool_key='0' * 64))
        changed('missing launch trace', lambda r, rs, cs: rs[custom_index]['calls'][0].update(stderr=''))

        def trace_change(field, value):
            def change(r, rs, cs):
                call = rs[custom_index]['calls'][0]
                call['launch'][field] = value
                call['stderr'] = 'rust-interp-launch: ' + json.dumps(call['launch'])
            return change

        changed('foreign artifact cache', trace_change('artifact_path', '/tmp/program.rbc'))
        changed('artifact parent traversal', trace_change('artifact_path', str(ROOT / '.work/../program.rbc')))
        changed('different executed engine', trace_change('engine', 'interpreter'))
        changed('different executed hash', trace_change('artifact_sha256', '0' * 64))
        changed('missing snapshot', lambda r, rs, cs: rs[custom_index].update(artifacts=[]))
        changed('snapshot outside evidence', lambda r, rs, cs: rs[custom_index]['artifacts'][0].update(path='Cargo.toml'))
        changed('snapshot byte count changed', lambda r, rs, cs: rs[custom_index]['artifacts'][0].update(bytes=1))
        changed('missing check history', lambda r, rs, cs: cs.clear(), 'check')
        changed('foreign check target', lambda r, rs, cs: cs[0]['command'].__setitem__(cs[0]['command'].index('--target-dir') + 1, '/tmp/target'), 'check')
        changed('executing check command', lambda r, rs, cs: cs[0]['command'].__setitem__(2, 'test'), 'check')
        changed('missing comparison mode', lambda r, rs, cs: rs.__setitem__(slice(None), [x for x in rs if x['mode'] != 'baseline']))
        rejects('arbitrary cache mode', lambda: derive(ROOT, name, report, rows, checks, '../native'))

        fixture = raw / 'workspace'
        fixture.mkdir()
        target = fixture / 'target'
        target.mkdir()
        marker = fixture / 'invocation.lock'
        marker.touch()
        with marker.open('r') as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            def held_guard():
                with cache_guard(target, 'candidate'):
                    pass
            rejects('busy invocation lock', held_guard)
        with cache_guard(target, 'candidate'):
            pass
        marker.unlink()
        marker.symlink_to(ROOT / 'Cargo.toml')
        rejects('symlink invocation lock', held_guard)
        require(len(rejected) == 31 and len(real) == 9, 'unexpected qualification counts')
        output.mkdir()
        write_json(output / 'summary.json', dict(status='passed', rejected=rejected, real_targets=real,
            invocation_lock_verified=True, compiler_caches_modified=False,
            sources={str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), *coordinator.SOURCES]},
            raw=str(raw.relative_to(ROOT))))
        print(json.dumps(dict(status='passed', rejected=len(rejected), real_targets=len(real))))


if __name__ == '__main__':
    main()
