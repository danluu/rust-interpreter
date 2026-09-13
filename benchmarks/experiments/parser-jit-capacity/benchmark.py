"""Compare bounded JIT capacities in complete changed-source parser commands."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'pgrust-parser-probe'))
from probe import PIN, fingerprint, native_inventory, native_target
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools
from suite_reports import read_report, validate_report, validate_runtime_limits
from workflow_io import SourceEdit, capture, require_space, write_json as write
from workflow_measurements import child_usage, child_cpu_since
from workflow_controls import exporter_seconds
from bench_e2e_workflow import build_metrics
from protocol import MODES, LIMITS, selected_states, schedule, measurement, runtime_statistics, validate_prefix
from states import native_outcomes, custom_export_ran, artifact_state_key


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--cycles', type=int, choices=[1, 3], default=1)
    parser.add_argument('--harness', type=Path, required=True)
    parser.add_argument('--screen-proof', type=Path)
    parser.add_argument('--prefix-proof', type=Path)
    args = parser.parse_args()
    assert __debug__ and args.run_id.startswith('parser-jit-capacity-') and Path(args.run_id).name == args.run_id
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 24)
        harness_path = args.harness.resolve(strict=True)
        harness = json.loads(harness_path.read_text())
        assert harness['status'] == 'passed' and harness['tests'] == 9
        inputs = ROOT / harness['raw'] / 'inputs.json'
        assert sha(inputs) == harness['inputs_sha256']
        assert all(sha(ROOT / p) == h for p, h in json.loads(inputs.read_text()).items())
        proof_paths = [ROOT / 'results' / name / 'summary.json' for name in [
            'parser-jit-capacity-build-01', 'parser-jit-capacity-qualification-01',
            'parser-jit-capacity-boundaries-01', 'environment-main-parser-01']]
        build, strict, boundaries, baseline = [json.loads(p.read_text()) for p in proof_paths]
        assert all(p['status'] == 'passed' for p in [build, strict, boundaries, baseline])
        assert strict['commands'] == 119 and boundaries['commands'] == 16
        assert build['tool_key'] == strict['tool_key'] == boundaries['tool_key']
        for proof in [strict, boundaries, baseline]:
            for name in ['plan', 'records']:
                assert sha(ROOT / proof['raw'] / (name + '.json')) == proof[name + '_sha256']
        tool, key = installed_tools(build['tool_key'])
        binaries = build['binaries']
        assert all(sha(tool / n) == h for n, h in binaries.items())
        paths = [harness_path, inputs, *proof_paths]
        if args.cycles == 3:
            assert args.screen_proof is not None
            screen = json.loads(args.screen_proof.read_text())
            assert screen['status'] == 'passed' and screen['cycles'] == 1 and screen['commands'] == 32
            assert screen['measurement']['gate']['passed'] and screen['tool_key'] == key
            screen_plan = ROOT / screen['raw'] / 'plan.json'
            assert sha(screen_plan) == screen['plan_sha256']
            for name in ['benchmark.py', 'protocol.py', 'PLAN.md']:
                path = Path(__file__).with_name(name)
                assert fingerprint(path) == json.loads(screen_plan.read_text())['frozen'][str(path.relative_to(ROOT))]
            paths += [args.screen_proof, screen_plan]
        else:
            assert args.screen_proof is None
        prefix, rows, cache_scope = None, [], args.run_id
        if args.prefix_proof:
            assert args.cycles == 1
            prefix_path = args.prefix_proof.resolve(strict=True)
            prefix = json.loads(prefix_path.read_text())
            assert prefix['status'] == 'five-command prefix verified; harness failure retained' and prefix['commands'] == 5
            assert prefix['source_restored'] and prefix['edited_timing_commands'] == 0
            assert prefix['old_raw'] == '.work/parser-jit-capacity-screen-01'
            old_work = ROOT / prefix['old_raw']; cache_scope = old_work.name
            old_plan = json.loads((old_work / 'plan.json').read_text())
            assert sha(old_work / 'plan.json') == prefix['plan_sha256']
            assert sha(old_work / 'records.json') == prefix['original_records_sha256']
            amended = ROOT / prefix['raw'] / 'records.json'
            assert sha(amended) == prefix['audited_records_sha256']
            assert old_plan['tool_key'] == key and old_plan['binaries'] == binaries
            rows = json.loads(amended.read_text())
            for row in rows:
                row['outcomes'] = [tuple(x) for x in row['outcomes']]
                for stream in ['stdout', 'stderr']:
                    path = old_work / f"{row['index']}.{stream}"
                    assert sha(path) == row[stream + '_sha256']; paths.append(path)
                if row['mode'] != 'native':
                    path = old_work / f"{row['index']}-suite.json"
                    assert sha(path) == row['suite_sha256']; paths.append(path)
                for kind in ['executable'] if row['mode'] == 'native' else ['artifact', 'entry_catalog']:
                    path = ROOT / row[kind]['path']
                    assert sha(path) == row[kind]['sha256']; paths.append(path)
            paths += [prefix_path, amended, old_work / 'plan.json', old_work / 'records.json']
        prior = ROOT / baseline['raw']
        prior_plan = json.loads((prior / 'plan.json').read_text())
        native_raw = ROOT / '.work/pgrust-parser-support-01'
        native_rows = json.loads((native_raw / 'records.json').read_text())
        assert sha(native_raw / 'native.stdout') == native_rows[0]['stdout_sha256']
        names = native_inventory((native_raw / 'native.stdout').read_text())
        assert len(names) == 114
        source = ROOT / '.work/sources/pgrust'
        owner = json.loads((source / '.rust-interp-owned.json').read_text())
        assert owner['owner'] == str(ROOT) and owner['revision'] == PIN
        assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == PIN
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source).strip()
        changed = source / 'crates/backend/parser/gram_core/src/parse.rs'
        original = changed.read_bytes()
        states = selected_states(original, args.cycles)
        planned = schedule(states)
        for row in planned:
            state, = [s for s in states if (s['cycle'], s['state']) == (row['cycle'], row['state'])]
            row['source_sha256'] = hashlib.sha256(state['source']).hexdigest()
        if prefix:
            validate_prefix(rows, planned)
            assert old_plan['schedule'] == planned and old_plan['original_source_sha256'] == sha(changed)
        paths += [prior / 'plan.json', prior / 'records.json', native_raw / 'native.stdout',
                  native_raw / 'records.json', source / '.rust-interp-owned.json']
        paths += list(Path(__file__).parent.glob('*.py')) + [Path(__file__).with_name('PLAN.md')]
        paths += [Path(__file__).parent.parent / p for p in ['pgrust-parser-probe/probe.py', 'pgrust-parser-edits/states.py']]
        paths += list((ROOT / 'scripts').glob('*.py')) + [tool / n for n in binaries]
        paths += [source / p for p in subprocess.check_output(['git', 'ls-files', '-z'], cwd=source).decode().split('\0')
                  if p and source / p != changed]
        frozen = {str(p.relative_to(ROOT)): fingerprint(p) for p in paths}
        for p, h in prior_plan['frozen'].items():
            if p.startswith('.work/sources/pgrust/'):
                assert fingerprint(ROOT / p) == h
        work = ROOT / '.work' / args.run_id
        assert not work.exists()
        work.mkdir(); artifacts = work / 'artifacts'; artifacts.mkdir()
        for row in rows:
            for kind, suffix in ([('executable', 'native')] if row['mode'] == 'native' else [('artifact', 'rbc'), ('entry_catalog', 'json')]):
                saved = artifacts / (row[kind]['sha256'] + '.' + suffix)
                if not saved.exists(): shutil.copy2(ROOT / row[kind]['path'], saved)
                assert sha(saved) == row[kind]['sha256']
                row[kind]['path'] = str(saved.relative_to(ROOT))
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                             'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR',
                             'CARGO_BUILD_TARGET', 'CARGO_BUILD_BUILD_DIR', 'RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never', PYTHONDONTWRITEBYTECODE='1', CARGO_INCREMENTAL='1')
        native = native_rows[0]['command'].copy()
        assert native.count('--target-dir') == 1
        native_root = ROOT / '.work' / cache_scope / 'native'
        native[native.index('--target-dir') + 1] = str(native_root)
        custom = prior_plan['command'].copy()
        assert [custom[i + 1] for i, value in enumerate(custom) if value == '--entry'] == names
        assert custom[custom.index('--function-cache') + 1] == 'auto'
        assert '--jit-code-limit' not in custom
        custom[custom.index('--tool-key') + 1] = key
        if prefix:
            for row in rows:
                expected = native.copy() if row['mode'] == 'native' else custom.copy()
                if row['mode'] != 'native':
                    for option, value in [('--suite-report', str(old_work / f"{row['index']}-suite.json")),
                                          ('--cache-namespace', cache_scope + ':' + row['mode'])]:
                        expected[expected.index(option) + 1] = value
                    expected += ['--jit-code-limit', str(LIMITS[row['mode']])]
                assert expected == row['command']
        write(work / 'plan.json', dict(owner=str(ROOT), revision=PIN, tool_key=key, binaries=binaries,
            source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            frozen=frozen, original_source_sha256=sha(changed), schedule=planned, code_limits=LIMITS,
            prefix=prefix, retained_commands=len(rows), new_commands=len(planned)-len(rows), cache_scope=cache_scope,
            native_command_template=native, custom_command_template=custom, commands=len(planned),
            cycles=args.cycles, cargo_incremental=1, original_tests=114, cargo_jobs=2, custom_workers=2,
            native_threads='libtest default', initial_free_bytes=shutil.disk_usage(ROOT).free,
            minimum_child_gib=8, initial_minimum_gib=24, performance_measurement=True,
            gate='median candidate/baseline + max absolute per-edit median A/A deviation: wall < 1, CPU <= 1.03',
            memory_bounds='32 MiB generated code per owner; unchanged 64 MiB guest memory and 150k allocations; host RSS unmeasured'))
        records, identities = rows, {}
        for row in rows:
            if row['mode'] != 'native':
                for kind in ['artifact', 'entry_catalog']:
                    history = artifact_state_key(row['cycle'], row['state'], kind, 'paired-cycle')
                    assert identities.setdefault(history, row[kind]['sha256']) == row[kind]['sha256']
        with SourceEdit(changed, original) as edit:
            for state in states:
                selected = [s for s in planned if (s['cycle'], s['state']) == (state['cycle'], state['state'])]
                current = [r for r in records if (r['cycle'], r['state']) == (state['cycle'], state['state'])]
                if len(current) == 4:
                    assert all(r['outcomes'] == current[0]['outcomes'] for r in current)
                    continue
                edit.replace(state['source'])
                for scheduled in selected[len(current):]:
                    index = len(records); mode = scheduled['mode']
                    assert sha(changed) == scheduled['source_sha256']
                    require_space(ROOT, 8)
                    suite = work / f'{index}-suite.json'
                    command = native.copy() if mode == 'native' else custom.copy()
                    selected_env = env.copy()
                    if mode != 'native':
                        for option, value in [('--suite-report', str(suite)), ('--cache-namespace', cache_scope + ':' + mode)]:
                            assert command.count(option) == 1
                            command[command.index(option) + 1] = value
                        command += ['--jit-code-limit', str(LIMITS[mode])]
                        selected_env['RUST_INTERP_LAUNCH_STATS'] = '1'
                    usage = child_usage(); start = time.perf_counter()
                    child, out, err = capture(command, cwd=source, env=selected_env,
                        receipt_path=work / 'active.json', receipt=dict(index=index, **scheduled))
                    wall = time.perf_counter() - start; cpu = child_cpu_since(usage)
                    (work / f'{index}.stdout').write_text(out); (work / f'{index}.stderr').write_text(err)
                    row = dict(scheduled, index=index, pid=child.pid, command=command, log_raw=str(work.relative_to(ROOT)),
                        returncode=child.returncode, wall_seconds=wall, cpu_seconds=cpu['total_seconds'], cpu=cpu,
                        stdout_sha256=sha(work / f'{index}.stdout'), stderr_sha256=sha(work / f'{index}.stderr'))
                    records.append(row); write(work / 'records.json', records)
                    success = state['state'] != -1
                    assert child.returncode == (0 if success else (101 if mode == 'native' else 1)), 'unexpected build/test exit'
                    if mode == 'native':
                        row['outcomes'] = native_outcomes(out, names, success)
                        exe = native_target(out, source / 'crates/backend/parser/gram_core/src/lib.rs').resolve(strict=True)
                        assert exe.is_relative_to(native_root.resolve())
                        digest = sha(exe); saved = artifacts / (digest + '.native')
                        if not saved.exists(): shutil.copy2(exe, saved)
                        assert sha(saved) == digest
                        row['native_build_executable'] = str(exe.relative_to(ROOT))
                        row['executable'] = dict(path=str(saved.relative_to(ROOT)), sha256=digest)
                        assert 'Compiling gram_core ' in err, 'selected native source was not rebuilt'
                    else:
                        launch, = [json.loads(l.split(': ', 1)[1]) for l in err.splitlines() if l.startswith('rust-interp-launch: ')]
                        assert launch['tool_key'] == key and launch['borrowck_cache'] == 'off'
                        assert launch['function_cache'] == 'auto' and launch['toolchain_lookup']['mode'] == 'cached'
                        assert launch['suite_workers'] == launch['suite_workers_requested'] == 2
                        assert launch['jit_code_limit_bytes'] == LIMITS[mode]
                        report, digest = read_report(suite, launch['suite_report_sha256'])
                        row['outcomes'] = validate_report(report, names, 'prepared', success)
                        validate_runtime_limits(report, 100000000000, 150000, jit_code_limit=LIMITS[mode], required=True)
                        assert custom_export_ran(err), 'selected custom source did not run the exporter'
                        assert report['workers'] == report['requested_workers'] == 2
                        stats = runtime_statistics(report, LIMITS[mode])
                        if mode == 'custom-32' and success: assert stats['maximum_owner_code_bytes'] > 16777216
                        row.update(suite_sha256=digest, launch=launch, stages=exporter_seconds(err), build=build_metrics(launch),
                            **stats)
                        for kind, suffix in [('artifact', 'rbc'), ('entry_catalog', 'json')]:
                            path = Path(launch[kind + '_path']); digest = launch[kind + '_sha256']
                            assert sha(path) == digest
                            saved = artifacts / (digest + '.' + suffix)
                            if not saved.exists(): shutil.copy2(path, saved)
                            assert sha(saved) == digest
                            row[kind] = dict(path=str(saved.relative_to(ROOT)), sha256=digest)
                            history = artifact_state_key(state['cycle'], state['state'], kind, 'paired-cycle')
                            assert identities.setdefault(history, digest) == digest, 'within-state custom artifacts differ'
                    assert sha(changed) == scheduled['source_sha256']
                    current.append(row); write(work / 'records.json', records)
                    print(index + 1, mode, state['cycle'], state['label'], 'validated', flush=True)
                assert all(r['outcomes'] == current[0]['outcomes'] for r in current), 'native/custom outcomes differ'
        assert changed.read_bytes() == original
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source).strip()
        assert all(fingerprint(ROOT / p) == h for p, h in frozen.items())
        for cycle in range(args.cycles):
            assert len({r['artifact']['sha256'] for r in records if r['cycle'] == cycle and r['state'] > 0 and r['mode'] == 'custom-a'}) == 5
        result = ROOT / 'results' / args.run_id; result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', commands=len(records), cycles=args.cycles,
            retained_commands=5 if prefix else 0, new_commands=len(records)-(5 if prefix else 0), prefix=prefix,
            original_tests=114, tool_key=key, source_restored=True, frozen_inputs_verified=len(frozen),
            original_assertions_unchanged=True, exact_native_test_outcomes=True, within_state_artifact_identity=True,
            raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'),
            records_sha256=sha(work / 'records.json'), measurement=measurement(records, args.cycles), performance_measurement=True))
        print('PASS: complete original/wrong/edited/restored parser controls; see the separate performance gate', flush=True)


if __name__ == '__main__':
    main()
