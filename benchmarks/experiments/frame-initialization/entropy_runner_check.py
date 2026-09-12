#!/usr/bin/env python3
"""Qualify the optional replay comparison path on existing small Rust fixtures."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    run = parser.parse_args().run_id
    assert re.fullmatch(r'entropy-runner-check-\d{2}', run)
    work = ROOT / '.work' / run
    qualification = ROOT / 'results/fixed-frame-clear-entropy-check-01/summary.json'
    qualified = json.loads(qualification.read_text())
    library = ROOT / qualified['library']
    vm = ROOT / '.work/fixed-frame-clear-combined-build-01/candidate-vm'
    sources = [Path(__file__), ROOT / 'scripts/compare_saved_runtime.py', qualification, library, vm]
    fixtures = [
        ('random-state', ROOT / '.work/runs/allocation-trace-fixtures-01/tls/baseline/program.rbc',
         '0778d5c21af8197f488f7a7bf01bb83eea97a60d1a54d7f8d7b72ba27528936b',
         ROOT / '.work/runs/allocation-trace-fixtures-01/tls/native', ['0'], True),
        ('destructors', ROOT / '.work/fixed-frame-clear-combined-tls-01/mir0-inline0-tls.rbc',
         'ca642d429036ad6ca43fd24c72f1dec94182e46d37dd1ac86a11f3ed5f861997',
         ROOT / '.work/fixed-frame-clear-combined-tls-01/native-mir0', ['tls', '0'], False),
    ]
    sources += [p for _, artifact, _, native, _, _ in fixtures for p in (artifact, native)]
    frozen = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    assert sha(vm) == 'f64c086b500e4ac6ce7bbedf89b686a6c397c674aacf22a9b6f31fd83ec46aec'
    assert sha(library) == qualified['library_sha256']
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(frozen=frozen, performance_measurement=False,
              same_vm_both_sides=True, native_commands=2, recordings=4, replay_commands=56))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        records, cases = [], []
        def invoke(command, selected):
            child = subprocess.Popen(command, env=selected, cwd=ROOT, stdin=subprocess.DEVNULL,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            write(work / 'active.json', dict(pid=child.pid, parent_pid=os.getpid(), command=command, cwd=str(ROOT)))
            stdout, stderr = child.communicate()
            records.append(dict(command=command, pid=child.pid, returncode=child.returncode, stdout=stdout, stderr=stderr))
            write(work / 'records.json', records)
            assert child.returncode == 0 and stdout == '79\n'
            return {k: int(v) for k, v in re.findall(r'\b([a-z_]+)=(\d+)\b', stderr)}
        for name, artifact, expected_hash, native, native_args, random in fixtures:
            assert sha(artifact) == expected_hash
            invoke([str(native), *native_args], env)
            case = dict(name=name, artifact=str(artifact), artifact_sha256=expected_hash,
                        args=['0'], stdout='79\n', instruction_limit=100_000_000,
                        allocation_limit=100_000, entropy_tapes=[])
            for index in range(2):
                tape = work / f'{name}-{index}.tape'
                selected = dict(env, DYLD_INSERT_LIBRARIES=str(library), RUST_INTERP_VM_STATS='1',
                                RUST_INTERP_ENTROPY_MODE='record', RUST_INTERP_ENTROPY_TAPE=str(tape))
                stats = invoke([str(vm), '--engine', 'jit', '--jit-resumable-calls', '--jit-persistent-registers',
                                '--instruction-limit', str(case['instruction_limit']), '--allocation-limit',
                                str(case['allocation_limit']), str(artifact), '0'], selected)
                assert (stats['entropy_calls'] > 0 and stats['entropy_bytes'] > 0) if random else stats['entropy_calls'] == stats['entropy_bytes'] == 0
                case['entropy_tapes'].append(dict(path=str(tape), sha256=sha(tape),
                    calls=stats['entropy_calls'], bytes=stats['entropy_bytes']))
            cases.append(case)
        write(work / 'manifest.json', cases)
    command = [sys.executable, str(ROOT / 'scripts/compare_saved_runtime.py'), '--baseline', str(vm),
               '--candidate', str(vm), '--manifest', str(work / 'manifest.json'), '--output', str(work / 'replay'),
               '--lock', str(ROOT / '.work/benchmark.lock'), '--lock-wait-seconds', '45',
               '--entropy-qualification', str(qualification)]
    with (work / 'replay.log').open('x') as log:
        child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        write(work / 'active.json', dict(pid=child.pid, parent_pid=os.getpid(), command=command, cwd=str(ROOT)))
        assert child.wait() == 0, 'comparison runner failed; inspect replay.log'
    result = json.loads((work / 'replay/summary.json').read_text())
    assert result['status'] == 'passed' and result['commands'] == 56
    assert all(sha(ROOT / p) == h for p, h in frozen.items())
    out = ROOT / 'results' / run
    out.mkdir(exist_ok=False)
    write(out / 'summary.json', dict(status='passed', performance_measurement=False, same_vm_both_sides=True,
          native_commands=2, recordings=4, replay_commands=56, cases=[c['name'] for c in cases],
          frozen=frozen, raw=str(work.relative_to(ROOT)), entropy_replay=result['entropy_replay'],
          evidence={str(p.relative_to(ROOT)): sha(p) for p in [work / 'plan.json', work / 'records.json',
                    work / 'manifest.json', work / 'replay/plan.json', work / 'replay/commands.jsonl', work / 'replay/summary.json']},
          scope='Comparison-runner correctness only: positive and zero-request entropy, two streams, both engines. No timing claim.'))
    write(work / 'active.json', dict(status='finished', returncode=0))
    print('PASS: 2 native controls, 4 recordings, 56 exact replay commands')


if __name__ == '__main__':
    main()
