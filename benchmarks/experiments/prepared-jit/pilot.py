#!/usr/bin/env python3
"""Qualify isolated real test entries against native and retained VM controls."""
import argparse
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools
from workflow_io import capture, require_space, write_json as write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--build', type=Path, required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'prepared-suite-pilot-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        build_path = args.build.resolve()
        build = json.loads(build_path.read_text())
        assert build['status'] == 'passed'
        assert build['tests']['test-debug'] == build['tests']['test-release'] == dict(passed=320, ignored=1)
        candidate, key = installed_tools(build['tool_key'])
        control, _ = installed_tools(build['composition']['exporter_and_wrapper_key'])
        history = ROOT / '.work/runs/export-reuse-screen-token-01/records.json'
        rows = json.loads(history.read_text())
        latest = {m: [r for r in rows if r['mode'] == m][-1] for m in ['native', 'baseline', 'candidate']}
        assert all(r['state'] == 5 and r['calls'][0]['returncode'] == 0 for r in latest.values())
        assert len({r['source_sha256'] for r in latest.values()}) == 1
        assert latest['baseline']['artifacts'] == [dict(path='.work/runs/export-reuse-screen-token-01/artifacts/baseline/5-0.rbc',
            sha256='9a7929f5b61e8da843645ea1bfadbfb5e706cb5133e4d0f37dd1bfdd2d827df4', bytes=28810629)]
        artifact = ROOT / latest['baseline']['artifacts'][0]['path']
        assert sha(artifact) == latest['baseline']['artifacts'][0]['sha256']
        matches = re.findall(r'Running unittests src/lib.rs \(([^)]+)\)', latest['native']['calls'][0]['stderr'])
        assert len(matches) == 1
        native = Path(matches[0])
        assert native.is_relative_to(ROOT / '.work/runs/export-reuse-screen-token-01/native')
        names = latest['native']['tests']
        assert len(names) == 3 and all(r['tests'] == names for r in latest.values())
        supervisor_path = ROOT / '.work/experiments/export-reuse-screen-token-01/status.json'
        supervisor = json.loads(supervisor_path.read_text())
        assert supervisor['status'] == 'finished' and supervisor['returncode'] == 0 and supervisor['owner'] == str(ROOT)
        assert native.stat().st_mtime <= supervisor['finished_at'], 'native target changed after its completed history'
        entropy_path = ROOT / 'results/fixed-frame-clear-entropy-check-01/summary.json'
        entropy = json.loads(entropy_path.read_text())
        assert entropy['status'] == 'passed' and entropy['commands'] == 17 and entropy['expected_rejections'] == 10
        library = ROOT / entropy['library']
        assert sha(library) == entropy['library_sha256']
        work = ROOT / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        paths = [Path(__file__).resolve(), Path(__file__).with_name('PLAN.md').resolve(), build_path, history,
                 supervisor_path, artifact, native, entropy_path, library, candidate / 'rust-interp-vm', control / 'rust-interp-vm']
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        write(work / 'plan.json', dict(frozen=frozen, tests=names, state=5, source_sha256=latest['native']['source_sha256'],
            tool_key=key, commands=8, native_control='each exact original test in a new process',
            native_provenance='retained target from the final successful native command in the owned completed source-edit history',
            performance_measurement=False, instruction_limit=100_000_000_000, allocation_limit=150_000))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env), 'existing loader instrumentation is out of scope'
        records = []
        def invoke(label, command, selected_env):
            require_space(ROOT, 8)
            process, stdout, stderr = capture(command, cwd=ROOT, env=selected_env,
                receipt_path=work / 'active.json', receipt=dict(label=label))
            (work / (label + '.stdout')).write_text(stdout)
            (work / (label + '.stderr')).write_text(stderr)
            record = dict(label=label, command=command, pid=process.pid, returncode=process.returncode,
                statistics={k: int(v) for k, v in re.findall(r'\b([a-z_]+)=(\d+)\b', stderr)})
            records.append(record); write(work / 'records.json', records)
            assert process.returncode == 0, label + ' failed'
            return stdout, record
        for index, name in enumerate(names):
            stdout, _ = invoke('native-' + str(index), [str(native), '--exact', name, '--test-threads=1'], env)
            assert 'test result: ok. 1 passed; 0 failed; 0 ignored;' in stdout and 'test ' + name + ' ... ok' in stdout
        def vm_command(tool):
            return [str(tool / 'rust-interp-vm'), '--engine', 'jit', '--jit-resumable-calls', '--jit-persistent-registers',
                    '--instruction-limit', '100000000000', '--allocation-limit', '150000']
        replay_env = dict(env, DYLD_INSERT_LIBRARIES=str(library), RUST_INTERP_VM_STATS='1')
        normal = []
        for label, tool, action in [('retained-batch', control, 'record'), ('current-batch', candidate, 'replay')]:
            stdout, row = invoke(label, vm_command(tool) + [str(artifact)],
                dict(replay_env, RUST_INTERP_ENTROPY_MODE=action, RUST_INTERP_ENTROPY_TAPE=str(work / 'batch.tape')))
            assert stdout == '0\n'
            normal.append({k: row['statistics'][k] for k in ['instructions', 'peak_guest_memory', 'entropy_calls', 'entropy_bytes']})
        assert normal[0] == normal[1]
        isolated, consumption = [], []
        for label, mode, action in [('fresh-record', 'fresh', 'record'), ('fresh-replay', 'fresh', 'replay'),
                                    ('prepared-replay', 'prepared', 'replay')]:
            report_path = work / (label + '.json')
            stdout, row = invoke(label, vm_command(candidate) + ['--isolated-batch', mode, '--suite-report', str(report_path), str(artifact)],
                dict(replay_env, RUST_INTERP_ENTROPY_MODE=action, RUST_INTERP_ENTROPY_TAPE=str(work / 'isolated.tape')))
            assert stdout == '0\n'
            report = json.loads(report_path.read_text())
            assert report['passed'] == 3 and report['failed'] == 0 and [t['name'] for t in report['tests']] == names
            assert all(t['jit_declined_functions'] == 0 for t in report['tests'])
            isolated.append([{k: t[k] for k in ['name', 'function', 'status', 'instructions', 'peak_guest_memory']}
                             for t in report['tests']])
            consumption.append({k: row['statistics'][k] for k in ['entropy_calls', 'entropy_bytes']})
        assert isolated[0] == isolated[1] == isolated[2] and consumption[0] == consumption[1] == consumption[2]
        assert consumption[0]['entropy_calls'] > 0
        assert len(records) == 8 and all(sha(ROOT / p) == h for p, h in frozen.items())
        out = ROOT / 'results' / args.run_id
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', dict(status='passed', commands=8, native_tests=names, tool_key=key,
            unchanged_one_shot=normal[0], isolated_tests=isolated[0], entropy=consumption[0],
            performance_measurement=False, raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'),
            records_sha256=sha(work / 'records.json'),
            scope='Original assertions and exact prepared/fresh execution equality under the same recorded inputs; no latency or full-libtest claim.'))
        print('PASS: three native tests, unchanged one-shot control and isolated fresh/prepared equality', flush=True)


if __name__ == '__main__':
    main()
