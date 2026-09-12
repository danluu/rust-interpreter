#!/usr/bin/env python3
"""Replay two real token entropy streams on both unchanged VMs and engines."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/tuned-native'))
from compare_saved_runtime import acquire_lock
from timing import environment, invoke, sha, require
from workflow_io import write_json as write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    run = parser.parse_args().run_id
    require(re.fullmatch(r'fixed-frame-clear-entropy-token-\d{2}', run), 'invalid run ID')
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        work = ROOT / '.work' / run
        work.mkdir(exist_ok=False)
        status = dict(owner=str(ROOT), status='preflight', pid=os.getpid(), started_at=time.time())
        write(work / 'status.json', status)
        try:
            qualification_path = ROOT / 'results/fixed-frame-clear-entropy-check-01/summary.json'
            qualification = json.loads(qualification_path.read_text())
            require(qualification['status'] == 'passed' and qualification['commands'] == 17 and
                qualification['expected_rejections'] == 10, 'entropy fixture qualification differs')
            require(all(sha(ROOT / p) == h for p, h in qualification['frozen'].items()), 'entropy implementation changed')
            library = ROOT / qualification['library']
            vms = dict(baseline=ROOT / '.work/fixed-frame-clear-01/candidate-vm',
                candidate=ROOT / '.work/fixed-frame-clear-combined-build-01/candidate-vm')
            require(sha(vms['baseline']) == 'effc588d6d486a5ac0d443d0014516cf71d1de02ce7b37c57ab5dfaac2487a33' and
                sha(vms['candidate']) == 'f64c086b500e4ac6ce7bbedf89b686a6c397c674aacf22a9b6f31fd83ec46aec', 'VM differs')
            manifest = ROOT / '.work/fixed-frame-clear-combined-runtime-inputs-02/manifest.json'
            case = next(c for c in json.loads(manifest.read_text()) if c['name'] == 'token-phrase')
            artifact = Path(case['artifact'])
            require(sha(artifact) == case['artifact_sha256'], 'original artifact differs')
            paths = [Path(__file__), HERE / 'ENTROPY.md', qualification_path, manifest, artifact, library, *vms.values()]
            frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
            env = environment('repository')
            require(not any(k.startswith('DYLD_') for k in env), 'existing loader instrumentation is out of scope')
            env.update(DYLD_INSERT_LIBRARIES=str(library), RUST_INTERP_VM_STATS='1')
            write(work / 'plan.json', dict(owner=str(ROOT), frozen=frozen, streams=2, commands=10,
                engines=['interpreter', 'jit'], mode='record real inputs once; replay exact requests on both VMs',
                performance_measurement=False, instruction_limit=case['instruction_limit'], allocation_limit=case['allocation_limit']))
            records, streams = [], []
            compared = ['instructions', 'peak_guest_memory', 'entropy_calls', 'entropy_bytes']
            for stream in range(2):
                tape = work / (str(stream) + '.tape')
                order = [('baseline', 'jit', 'record'), ('baseline', 'interpreter', 'replay'),
                    ('candidate', 'interpreter', 'replay'), ('baseline', 'jit', 'replay'), ('candidate', 'jit', 'replay')]
                expected, tape_hash = None, None
                for mode, engine, action in order:
                    label = f'{stream}-{action}-{mode}-{engine}'
                    command = [str(vms[mode]), '--engine', engine, '--instruction-limit', str(case['instruction_limit']),
                        '--allocation-limit', str(case['allocation_limit'])]
                    if engine == 'jit':
                        command += ['--jit-resumable-calls', '--jit-persistent-registers']
                    command.append(str(artifact))
                    status.update(status='running', stream=stream, label=label)
                    write(work / 'status.json', status)
                    selected = dict(env, RUST_INTERP_ENTROPY_MODE=action, RUST_INTERP_ENTROPY_TAPE=str(tape))
                    row, stdout, stderr = invoke(work, label, command, ROOT, selected)
                    row.update(mode=mode, engine=engine, action=action, stream=stream, tape=str(tape.relative_to(ROOT)))
                    row['statistics'] = {k: int(v) for k, v in re.findall(r'\b([a-z_]+)=(\d+)\b', stderr)}
                    records.append(row)
                    write(work / 'records.json', records)
                    require(row['returncode'] == 0 and stdout == case['stdout'], 'replayed original assertions failed')
                    values = {k: row['statistics'][k] for k in compared}
                    require(values['entropy_calls'] == 3 and values['entropy_bytes'] > 0, 'expected entropy path did not execute')
                    if action == 'record':
                        expected, tape_hash = values, sha(tape)
                    require(values == expected and sha(tape) == tape_hash, 'controlled input/output/statistics mismatch')
                    require(all(sha(ROOT / p) == h for p, h in frozen.items()), 'diagnostic input changed')
                    print('PASS', label, values, flush=True)
                streams.append(dict(stream=stream, tape_sha256=tape_hash, values=expected, replays=4))
                write(work / 'streams.json', streams)
            result = dict(status='passed', performance_measurement=False, commands=len(records), streams=streams,
                unchanged_vms={m: sha(p) for m, p in vms.items()}, artifact_sha256=sha(artifact),
                raw=str(work.relative_to(ROOT)), all_replay_requests_consumed=True,
                evidence={str(p.relative_to(ROOT)): sha(p) for p in [work / 'plan.json', work / 'records.json', work / 'streams.json']},
                scope='Two independent recorded entropy streams; exact output/instruction/peak-memory equality across both unchanged VMs and engines. Diagnostic, not a timing result.')
            write(work / 'summary.json', result)
            out = ROOT / 'results' / run
            out.mkdir(exist_ok=False)
            write(out / 'summary.json', result)
            status.update(status='finished', returncode=0, finished_at=time.time())
            write(work / 'status.json', status)
        except BaseException as error:
            status.update(status='failed', error=repr(error), finished_at=time.time())
            write(work / 'status.json', status)
            raise


if __name__ == '__main__':
    main()
