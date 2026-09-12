#!/usr/bin/env python3
"""Nushell native debuginfo comparison, with original assertions and real edits."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/composed-development'))
from workflows import native_outcomes
from compare_saved_runtime import acquire_lock, sha
from workflow_cases import WORKFLOW_VARIANTS
from workflow_controls import native_command
from workflow_measurements import source_states, child_usage, child_cpu_since
from workflow_io import SourceEdit, capture, require_space, write_json as write

NATIVE = ['repository', 'duplicate', 'line_tables']
MODES = [*NATIVE, 'check']
TOOLCHAIN = 'nightly-2026-09-08'


def assessment(rows):
    pairs = []
    for cycle in range(3):
        for state in range(1, 6):
            selected = [r for r in rows if r['cycle'] == cycle and r['state'] == state]
            assert len(selected) == 4 and {r['mode'] for r in selected} == set(MODES)
            assert len({r['source_sha256'] for r in selected}) == 1
            modes = {r['mode']: r for r in selected}
            baseline, duplicate, lines = (modes[m] for m in NATIVE)
            pairs.append(dict(cycle=cycle, state=state, source_sha256=baseline['source_sha256'],
                wall_ratio=lines['seconds']/baseline['seconds'], cpu_ratio=lines['cpu']['total_seconds']/baseline['cpu']['total_seconds'],
                aa_wall_ratio=duplicate['seconds']/baseline['seconds'], aa_cpu_ratio=duplicate['cpu']['total_seconds']/baseline['cpu']['total_seconds']))
    median = statistics.median
    envelope = {kind: max(abs(median(p['aa_'+kind+'_ratio'] for p in pairs if p['state'] == state)-1)
                         for state in range(1, 6)) for kind in ['wall', 'cpu']}
    return dict(pairs=pairs, edited_pairs=15, aa_pairs=15,
                paired_wall_ratio=median(p['wall_ratio'] for p in pairs),
                paired_cpu_ratio=median(p['cpu_ratio'] for p in pairs), aa_envelope=envelope,
                noise_acceptable=envelope['wall'] <= .04 and envelope['cpu'] <= .03,
                optimization_gate=None, interpretation='Native control calibration; no minimum improvement required.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'large-native-nushell-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        estimate_path = ROOT / 'results/aggregate-relocation-space-nu-native-01/summary.json'
        estimate = json.loads(estimate_path.read_text())
        assert estimate['status'] == 'completed' and 'nushell-type-relations' in estimate['workflow']
        needed = 8 * 1024**3 + 16 * 1024**2 + (estimate['unique_original_bytes'] * 4 * 120 + 99) // 100
        assert shutil.disk_usage(ROOT).free >= needed, 'four conservative targets do not fit; no source edit started'
        source = ROOT / '.work/sources/nushell'
        marker = source / '.rust-interp-owned.json'
        owner = json.loads(marker.read_text())
        assert owner['owner'] == str(ROOT) and owner['revision'] == '9d3157963241cf89447119d34d6e887859f5e7e8'
        assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == owner['revision']
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source).strip()
        case = WORKFLOW_VARIANTS['nushell', 'type-relations']
        changed = source / case['file']
        original = changed.read_bytes()
        states = list(source_states(original.decode(), case, 3, NATIVE, True))
        assert len(states) == 21 and len(case['tests']) == 14
        paths = [Path(__file__), Path(__file__).with_name('PLAN.md'), estimate_path, marker,
                 ROOT / 'benchmarks/experiments/composed-development/workflows.py']
        paths += [ROOT / 'scripts' / p for p in ['workflow_cases.py', 'workflow_controls.py',
            'workflow_measurements.py', 'workflow_io.py', 'compare_saved_runtime.py']]
        paths += [source / p for p in subprocess.check_output(['git', 'ls-files', '-z'], cwd=source).decode().split('\0')
                  if p and source / p != changed]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
            and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
                          'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET', 'CARGO_BUILD_BUILD_DIR', 'RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env['CARGO_TERM_COLOR'] = 'never'
        lines = dict(env, CARGO_PROFILE_DEV_DEBUG='line-tables-only', CARGO_PROFILE_TEST_DEBUG='line-tables-only',
                     CARGO_PROFILE_DEV_SPLIT_DEBUGINFO='unpacked', CARGO_PROFILE_TEST_SPLIT_DEBUGINFO='unpacked')
        envs = {m: lines if m == 'line_tables' else env for m in MODES}
        work = ROOT / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), source_revision=owner['revision'], frozen=frozen,
            required_free_bytes=needed, admitted_free_bytes=shutil.disk_usage(ROOT).free, minimum_child_gib=8,
            source_sha256=sha(changed), tests=case['tests'], cargo_workers=2, native_test_threads='libtest default',
            modes=MODES, commands=88, edits=15, aa_pairs=15, source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()))
        profiles, graphs = {}, {}
        for mode in ['repository', 'line_tables']:
            command = native_command(TOOLCHAIN, source / 'Cargo.toml', case['package'], work / mode, 2, 'default', [])
            command = command[:command.index('--')] + ['--no-run', '--unit-graph', '-Z', 'unstable-options']
            require_space(ROOT, 8)
            child, stdout, stderr = capture(command, cwd=source, env=envs[mode], receipt_path=work/'active.json',receipt=dict(mode=mode,phase='profile'))
            (work / (mode+'-unit-graph.json')).write_text(stdout)
            (work / (mode+'-unit-graph.stderr')).write_text(stderr)
            assert child.returncode == 0, stderr[-3000:]
            graph = json.loads(stdout)
            graphs[mode] = graph
            assert graph['version'] == 1 and len(graph['roots']) == 1
            root = graph['units'][graph['roots'][0]]
            assert root['mode'] == 'test' and root['target']['kind'] == ['lib']
            profiles[mode] = dict(root=root['profile'], unit_count=len(graph['units']), graph_sha256=sha(work/(mode+'-unit-graph.json')),
                                  command=list(map(str,command)), pid=child.pid, returncode=child.returncode)
        a, b = [profiles[m]['root'] for m in ['repository','line_tables']]
        assert a['debuginfo'] == 2 and b['debuginfo'] == 'line-tables-only'
        assert a['split_debuginfo'] == b['split_debuginfo'] == 'unpacked'
        assert {k:v for k,v in a.items() if k != 'debuginfo'} == {k:v for k,v in b.items() if k != 'debuginfo'}
        assert str(a['opt_level']) == '0' and a['incremental'] and a['debug_assertions'] and a['overflow_checks']
        # All unit identities, dependencies and non-debug settings must match.
        graphs = json.loads(json.dumps(graphs))
        for graph in graphs.values():
            for unit in graph['units']:
                unit['profile'].pop('debuginfo')
        assert graphs['repository'] == graphs['line_tables'], 'a non-debug unit-graph field changed'
        write(work / 'profiles.json', profiles)
        rows, transitions, space = [], [], []
        previous = dict.fromkeys(MODES)
        restored = dict(cycle=3, state=0, phase='restored', label='restored-original', source=original, modes=NATIVE)
        with SourceEdit(changed, original) as edit:
            for sample in [*states, restored]:
                before = sha(changed)
                edit.replace(sample['source'])
                digest = sha(changed)
                transitions.append(dict(cycle=sample['cycle'], state=sample['state'], before=before, after=digest))
                write(work / 'transitions.json', transitions)
                selected = {}
                for mode in [*sample['modes'], 'check']:
                    assert previous[mode] != digest, 'unchanged source entered calibration'
                    require_space(ROOT, 8)
                    space.append(dict(cycle=sample['cycle'], state=sample['state'], mode=mode,free_bytes=shutil.disk_usage(ROOT).free))
                    write(work / 'space.json', space)
                    command = list(map(str, native_command(TOOLCHAIN, source/'Cargo.toml', case['package'], work/mode,
                        2, 'default', case['tests'], check=mode=='check')))
                    started, usage = time.perf_counter(), child_usage()
                    child, stdout, stderr = capture(command, cwd=source, env=envs[mode], receipt_path=work/'active.json',
                        receipt=dict(cycle=sample['cycle'],state=sample['state'],mode=mode))
                    row = dict(cycle=sample['cycle'],state=sample['state'],phase=sample['phase'],mode=mode,command=command,
                        pid=child.pid,seconds=time.perf_counter()-started,cpu=child_cpu_since(usage),returncode=child.returncode,
                        stdout=stdout,stderr=stderr,source_sha256=digest,previous_source_sha256=previous[mode])
                    rows.append(row);write(work/'records.json',rows)
                    success = sample['state'] != -1
                    assert (child.returncode==0) == (success or mode=='check'), stderr[-3000:]
                    assert ('Checking ' if mode=='check' else 'Compiling ')+case['package'] in stderr
                    assert sha(changed)==digest
                    if mode != 'check':
                        row['outcomes']=native_outcomes(stdout,case['tests'],success)
                        duration, = re.findall(r'test result: (?:ok|FAILED)\..*?finished in ([0-9.]+)s',stdout)
                        row['native_reported_suite_seconds']=float(duration)
                        row['build_and_residual_seconds']=row['seconds']-float(duration)
                        selected[mode]=row['outcomes']
                    previous[mode]=digest;write(work/'records.json',rows)
                    print(sample['cycle'],sample['state'],mode,round(row['seconds'],3),flush=True)
                assert selected['repository']==selected['duplicate']==selected['line_tables']
        assert len(rows)==88 and changed.read_bytes()==original
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=assessment(rows)
        result.update(status='passed',commands=88,profile_queries=2,test_count=14,tests=case['tests'],source_restored=True,
            original_assertions_match=True,test_source_unchanged=True,raw=str(work.relative_to(ROOT)),
            evidence={name:sha(work/(name+'.json')) for name in ['plan','records','profiles','transitions','space']},
            median_edited_seconds={m:statistics.median(r['seconds'] for r in rows if r['mode']==m and r['state']>0) for m in MODES})
        out=ROOT/'results'/args.run_id;out.mkdir(exist_ok=False);write(out/'summary.json',result)
        print(json.dumps({k:result[k] for k in ['status','paired_wall_ratio','paired_cpu_ratio','aa_envelope','noise_acceptable']}),flush=True)


if __name__=='__main__':main()
