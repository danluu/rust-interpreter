"""Measure complete original parser tests after real production-source edits."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
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
from workflow_measurements import child_usage, child_cpu_since, mode_order
from workflow_controls import exporter_seconds
from bench_e2e_workflow import build_metrics
from states import source_states, native_outcomes, custom_export_ran, check_prefix_schedule, artifact_state_key

MODES = ['native', 'custom-a', 'custom-b']


def ratios(records):
    pairs = []
    for cycle in range(3):
        for state in range(1, 6):
            matching = [r for r in records if r['cycle'] == cycle and r['state'] == state]
            assert len(matching) == 3, 'missing or duplicate timing observation'
            chosen = {r['mode']: r for r in matching}
            assert set(chosen) == set(MODES)
            pair = dict(cycle=cycle, state=state)
            for metric in ['wall_seconds', 'cpu_seconds']:
                pair[metric] = dict(custom_native=chosen['custom-a'][metric] / chosen['native'][metric],
                    aa=chosen['custom-b'][metric] / chosen['custom-a'][metric],
                    **{m: chosen[m][metric] for m in MODES})
            pairs.append(pair)
    result = {}
    for metric in ['wall_seconds', 'cpu_seconds']:
        result[metric] = dict(custom_native=statistics.median(p[metric]['custom_native'] for p in pairs),
            aa=statistics.median(p[metric]['aa'] for p in pairs),
            aa_max_absolute_per_edit_median=max(abs(statistics.median(p[metric]['aa'] for p in pairs if p['state'] == state) - 1)
                                               for state in range(1, 6)))
    return dict(pairs=pairs, medians=result, edited_pairs=15)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--profile', choices=['repository', 'incremental'], required=True)
    parser.add_argument('--harness', type=Path, required=True)
    parser.add_argument('--prefix-proof', type=Path)
    parser.add_argument('--artifact-history', choices=['cross-cycle', 'paired-cycle'], default='cross-cycle')
    args = parser.parse_args()
    assert __debug__ and args.run_id.startswith('pgrust-parser-edits-') and Path(args.run_id).name == args.run_id
    initial_gib = 16 if args.prefix_proof and args.profile == 'incremental' and args.artifact_history == 'paired-cycle' else 18
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, initial_gib)
        harness_path = args.harness.resolve(strict=True)
        harness = json.loads(harness_path.read_text())
        assert harness['status'] == 'passed' and harness['tests'] == 10
        inputs_path = ROOT / harness['raw'] / 'inputs.json'
        assert sha(inputs_path) == harness['inputs_sha256']
        assert all(sha(ROOT / p) == h for p, h in json.loads(inputs_path.read_text()).items())
        proof_path = ROOT / 'results/pgrust-parser-support-04/summary.json'
        proof = json.loads(proof_path.read_text())
        assert proof['status'] == 'passed' and proof['custom_tests_passed'] == proof['native_tests_reused'] == 114
        prior = ROOT / proof['raw']
        assert sha(prior / 'plan.json') == proof['plan_sha256']
        assert sha(prior / 'records.json') == proof['records_sha256']
        prior_plan = json.loads((prior / 'plan.json').read_text())
        tool, key = installed_tools(proof['tool_key'])
        binaries = json.loads((tool / 'ready.json').read_text())
        assert binaries == prior_plan['binaries']
        native_raw = ROOT / '.work/pgrust-parser-support-01'
        assert fingerprint(native_raw / 'records.json') == prior_plan['frozen'][str((native_raw / 'records.json').relative_to(ROOT))]
        native_rows = json.loads((native_raw / 'records.json').read_text())
        assert sha(native_raw / 'native.stdout') == native_rows[0]['stdout_sha256']
        names = native_inventory((native_raw / 'native.stdout').read_text())
        source = ROOT / '.work/sources/pgrust'
        owner = json.loads((source / '.rust-interp-owned.json').read_text())
        assert owner['owner'] == str(ROOT) and owner['revision'] == PIN
        assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == PIN
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source).strip()
        changed = source / 'crates/backend/parser/gram_core/src/parse.rs'
        original = changed.read_bytes()
        states = source_states(original)
        paths = [harness_path, inputs_path, proof_path, prior / 'plan.json', prior / 'records.json',
                 native_raw / 'native.stdout', native_raw / 'records.json', source / '.rust-interp-owned.json']
        paths += list(Path(__file__).parent.glob('*.py')) + [Path(__file__).with_name('PLAN.md')]
        paths += [Path(__file__).parent.parent / 'pgrust-parser-probe/probe.py']
        paths += list((ROOT / 'scripts').glob('*.py')) + [tool / n for n in binaries]
        paths += [source / p for p in subprocess.check_output(['git', 'ls-files', '-z'], cwd=source).decode().split('\0')
                  if p and source / p != changed]
        frozen = {str(p.relative_to(ROOT)): fingerprint(p) for p in paths}
        for p, h in prior_plan['frozen'].items():
            if p.startswith('.work/sources/pgrust/'):
                assert fingerprint(ROOT / p) == h
        work = ROOT / '.work' / args.run_id
        cache_scope = args.run_id
        prefix_rows, prefix_details = [], None
        if args.prefix_proof:
            prefix_path = args.prefix_proof.resolve(strict=True)
            prefix = json.loads(prefix_path.read_text())
            expected_status = {'repository': 'two-command prefix verified; validator mismatch retained',
                               'incremental': 'repeated-original artifact mismatch'}[args.profile]
            expected_count = {'repository': 2, 'incremental': 22}[args.profile]
            assert prefix['status'] == expected_status and prefix['commands'] == expected_count and prefix['source_restored']
            assert (args.profile == 'incremental') == (args.artifact_history == 'paired-cycle')
            old = ROOT / prefix['raw']
            assert sha(old / 'plan.json') == prefix['plan_sha256']
            assert sha(old / 'records.json') == prefix.get('original_records_sha256', prefix.get('records_sha256'))
            assert sha(old / 'audited-prefix.json') == prefix['audited_prefix_sha256']
            old_plan = json.loads((old / 'plan.json').read_text())
            assert old_plan['tool_key'] == key and old_plan['profile'] == args.profile
            assert (old / 'native').is_dir(), 'retained native cache is absent'
            allowed = {str(Path(__file__).relative_to(ROOT)),
                       *[str(Path(__file__).with_name(n).relative_to(ROOT)) for n in ['states.py', 'test_protocol.py', 'check.py', 'PLAN.md']]}
            for path, expected in old_plan['frozen'].items():
                actual = fingerprint(ROOT / path)
                if actual != expected:
                    assert path in allowed and expected['kind'] == 'file'
                    old_bytes = subprocess.check_output(['git', 'show', old_plan['source_commit'] + ':' + path], cwd=ROOT)
                    assert hashlib.sha256(old_bytes).hexdigest() == expected['sha256']
            prefix_rows = json.loads((old / 'audited-prefix.json').read_text())
            for row in prefix_rows:
                for stream in ['stdout', 'stderr']:
                    assert sha(old / f"{row['index']}.{stream}") == row[stream + '_sha256']
                for kind in ['artifact', 'entry_catalog', 'executable']:
                    if kind in row: assert sha(ROOT / row[kind]['path']) == row[kind]['sha256']
                row['log_raw'] = prefix['raw']
                row['outcomes'] = [tuple(outcome) for outcome in row['outcomes']]
                if row['mode'] != 'native':
                    row['stages'] = exporter_seconds((old / f"{row['index']}.stderr").read_text())
                    row['build'] = build_metrics(row['launch'])
                    assert Path(row['launch']['workspace_path']).is_dir(), 'retained custom cache is absent'
            cache_scope = old.name
            prefix_details = dict(proof=str(prefix_path.relative_to(ROOT)), proof_sha256=sha(prefix_path),
                                  retained_commands=len(prefix_rows), old_raw=prefix['raw'], old_plan_sha256=prefix['plan_sha256'])
            frozen.update({str(p.relative_to(ROOT)): fingerprint(p) for p in
                           [prefix_path, old / 'plan.json', old / 'records.json', old / 'audited-prefix.json']})
        if args.artifact_history == 'paired-cycle':
            assert args.profile == 'incremental' and prefix_details and len(prefix_rows) == 22
            origins_path = ROOT / 'results/parser-allocation-origins-01/summary.json'
            origins = json.loads(origins_path.read_text())
            assert origins['status'] == 'passed' and origins['guest_commands'] == 0
            assert [s['exact_literal_allocations'] for s in origins['states']] == [1, 1, 2, 2]
            assert origins['states'][0]['artifact_sha256'] == prefix_rows[1]['artifact']['sha256']
            assert origins['states'][3]['artifact_sha256'] == prefix_rows[21]['artifact']['sha256']
            trace_path = ROOT / 'results/parser-allocation-history-01/summary.json'
            trace = json.loads(trace_path.read_text())
            assert trace['status'] == 'passed' and trace['commands'] == 8 and trace['observer_byte_identity']
            for state in origins['states']: assert sha(ROOT / state['report']) == state['report_sha256']
            frozen.update({str(p.relative_to(ROOT)): fingerprint(p) for p in [origins_path, trace_path]})
        work.mkdir(exist_ok=False)
        artifacts = work / 'artifacts'; artifacts.mkdir()
        for row in prefix_rows:
            if row['mode'] == 'native':
                exe = row['executable']; saved = artifacts / (exe['sha256'] + '.native')
                shutil.copy2(ROOT / exe['path'], saved)
                assert sha(saved) == exe['sha256']
                row['native_build_executable'] = exe['path']
                row['executable'] = dict(path=str(saved.relative_to(ROOT)), sha256=exe['sha256'])
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                             'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR',
                             'CARGO_BUILD_TARGET', 'CARGO_BUILD_BUILD_DIR', 'RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never', PYTHONDONTWRITEBYTECODE='1')
        if args.profile == 'incremental': env['CARGO_INCREMENTAL'] = '1'
        native = native_rows[0]['command'].copy()
        assert native.count('--target-dir') == 1
        native[native.index('--target-dir') + 1] = str(ROOT / '.work' / cache_scope / 'native')
        custom = prior_plan['command'].copy()
        assert [custom[i + 1] for i, value in enumerate(custom) if value == '--entry'] == names
        assert custom[custom.index('--tool-key') + 1] == key
        assert custom[custom.index('--function-cache') + 1] == 'auto'
        schedule = []
        for state in states:
            order = mode_order(MODES, state['cycle'], state['state'], True)
            for mode in order:
                schedule.append(dict(cycle=state['cycle'], state=state['state'], mode=mode,
                    label=state['label'], source_sha256=hashlib.sha256(state['source']).hexdigest()))
        assert len(schedule) == 66
        if prefix_rows:
            check_prefix_schedule(prefix_rows, schedule, args.profile)
            for row in prefix_rows:
                expected = native.copy() if row['mode'] == 'native' else custom.copy()
                if row['mode'] != 'native':
                    for option, value in [('--suite-report', str(ROOT / prefix_details['old_raw'] / f"{row['index']}-suite.json")),
                                          ('--cache-namespace', cache_scope + ':' + row['mode'])]:
                        assert expected.count(option) == 1
                        expected[expected.index(option) + 1] = value
                assert row['command'] == expected, 'retained command differs'
        write(work / 'plan.json', dict(owner=str(ROOT), revision=PIN, tool_key=key, binaries=binaries,
            source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            profile=args.profile, cargo_incremental=env.get('CARGO_INCREMENTAL', 'project defaults'),
            frozen=frozen, original_source_sha256=hashlib.sha256(original).hexdigest(),
            schedule=schedule, native_command_template=native, custom_command_template=custom,
            commands=66, new_commands=66-len(prefix_rows), prefix=prefix_details, cache_scope=cache_scope,
            artifact_history=args.artifact_history,
            cycles=3, original_tests=114, cargo_jobs=2, custom_workers=2,
            native_threads='libtest default', initial_free_bytes=shutil.disk_usage(ROOT).free,
            minimum_child_gib=8, initial_minimum_gib=initial_gib, performance_measurement=True))
        records, by_state = prefix_rows, {}
        for row in prefix_rows:
            if row['mode'] != 'native':
                for kind in ['artifact', 'entry_catalog']:
                    history_key = artifact_state_key(row['cycle'], row['state'], kind, args.artifact_history)
                    prior_digest = by_state.setdefault(history_key, row[kind]['sha256'])
                    assert prior_digest == row[kind]['sha256'], 'retained paired artifact differs'
        with SourceEdit(changed, original) as edit:
            for state in states:
                selected = [s for s in schedule if (s['cycle'], s['state']) == (state['cycle'], state['state'])]
                current = [r for r in records if (r['cycle'], r['state']) == (state['cycle'], state['state'])]
                if len(current) == 3:
                    assert current[0]['outcomes'] == current[1]['outcomes'] == current[2]['outcomes']
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
                        assert exe.is_relative_to((ROOT / '.work' / cache_scope / 'native').resolve())
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
                        report, digest = read_report(suite, launch['suite_report_sha256'])
                        row['outcomes'] = validate_report(report, names, 'prepared', success)
                        validate_runtime_limits(report, 100000000000, 150000, required=True)
                        assert custom_export_ran(err), 'selected custom source did not run the exporter'
                        assert report['workers'] == report['requested_workers'] == 2
                        row.update(suite_sha256=digest, launch=launch, stages=exporter_seconds(err), build=build_metrics(launch))
                        for kind, suffix in [('artifact', 'rbc'), ('entry_catalog', 'json')]:
                            path = Path(launch[kind + '_path']); digest = launch[kind + '_sha256']
                            assert sha(path) == digest
                            saved = artifacts / (digest + '.' + suffix)
                            if not saved.exists(): shutil.copy2(path, saved)
                            assert sha(saved) == digest
                            row[kind] = dict(path=str(saved.relative_to(ROOT)), sha256=digest)
                            history_key = artifact_state_key(state['cycle'], state['state'], kind, args.artifact_history)
                            prior_digest = by_state.setdefault(history_key, digest)
                            assert prior_digest == digest, 'custom A/A or repeated-state artifact differs'
                    assert sha(changed) == scheduled['source_sha256']
                    current.append(row); write(work / 'records.json', records)
                    print(index + 1, args.profile, mode, state['cycle'], state['label'], 'validated', flush=True)
                assert current[0]['outcomes'] == current[1]['outcomes'] == current[2]['outcomes'], 'native/custom test outcomes differ'
        assert changed.read_bytes() == original
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source).strip()
        assert all(fingerprint(ROOT / p) == h for p, h in frozen.items())
        assert len(records) == 66
        result = ROOT / 'results' / args.run_id; result.mkdir(exist_ok=False)
        retained = prefix_details['retained_commands'] if prefix_details else 0
        histories = [dict(cycle=r['cycle'], state=r['state'], sha256=r['artifact']['sha256']) for r in records if r['mode'] == 'custom-a']
        write(result / 'summary.json', dict(status='passed', commands=66, new_commands=66-retained,
            prefix=prefix_details, original_tests=114,
            artifact_history=args.artifact_history, artifact_histories=histories,
            profile=args.profile, tool_key=key, source_restored=True, frozen_inputs_verified=len(frozen),
            original_assertions_unchanged=True, exact_native_test_outcomes=True,
            raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'),
            records_sha256=sha(work / 'records.json'), measurement=ratios(records), performance_measurement=True))
        print('PASS: 66 commands, original/wrong/edited/restored parser controls', flush=True)


if __name__ == '__main__':
    main()
