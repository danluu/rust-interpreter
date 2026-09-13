#!/usr/bin/env python3
"""Full scalar Copy comparison against the adopted runtime and fixed anchor."""
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
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools, require_export_option, TOOLCHAIN
from workflow_cases import WORKFLOWS, WORKFLOW_VARIANTS
from workflow_controls import native_command, exporter_seconds
from workflow_measurements import source_states, child_usage, child_cpu_since
from workflow_io import SourceEdit, capture, require_space, write_json as write
from test_discovery import read_listing, read_selection
from suite_reports import guest_test_failure, read_report, validate_report, validate_runtime_limits
from screen import BASELINE_KEY, EXPORTER_KEY, validate_baseline

CASES = {'token': ('fre', 'token-phrase-allocation', 'token_phrase::tests::', 'prepared-suite-token-01'),
         'folded': ('fre', 'folded-literal-trie', 'folded_literal_trie::tests::', 'prepared-suite-folded-01'),
         'pgrust': ('pgrust', None, '', 'prepared-catalog-pgrust-03')}
CUSTOM = ['baseline', 'duplicate', 'candidate', 'anchor']
CACHED = ['baseline', 'duplicate', 'candidate']
MODES = [*CUSTOM, 'native', 'native_lines', 'check']


def lookup_args(mode):
    assert mode in CUSTOM
    return ['--toolchain-lookup', 'cached' if mode in CACHED else 'fresh']


def validate_lookup(launch, mode, cycle, state):
    assert mode in CUSTOM
    observed = launch['toolchain_lookup']
    assert observed['mode'] == ('cached' if mode in CACHED else 'fresh')
    expected = ['miss', 'hit'] if cycle == 0 and state == 0 else ['hit']
    assert observed['outcome'] in (expected if mode in CACHED else ['fresh'])
    return True


def native_outcomes(stdout, names, success):
    found = re.findall(r'^test (.+) \.\.\. (ok|FAILED|ignored)$', stdout, re.M)
    assert len(found) == len(names) and len(dict(found)) == len(names)
    statuses = dict(found)
    assert set(statuses) == set(names) and 'ignored' not in statuses.values()
    failed = sum(status == 'FAILED' for status in statuses.values())
    summary = re.findall(r'test result: (ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored;', stdout)
    assert summary == [('ok' if success else 'FAILED', str(len(names) - failed), str(failed), '0')]
    assert (failed == 0) == success
    return [(name, 'passed' if statuses[name] == 'ok' else 'failed') for name in names]


def protocol_states(original, case):
    """Four-order Williams schedule: each mode in every position per block."""
    orders = [list('0132'), list('1203'), list('2310'), list('3021')]
    for sample in source_states(original, case, 3, CACHED, True):
        cycle, state = sample['cycle'], sample['state']
        index = cycle * 5 + state - 1 if state > 0 else cycle * 2 + (state == -1)
        sample['modes'] = [CUSTOM[int(i)] for i in orders[index % 4]]
        yield sample


def assessment(rows, case):
    pairs = []
    for cycle in range(3):
        for state in range(1, 6):
            selected = [r for r in rows if r['cycle'] == cycle and r['state'] == state]
            assert len(selected) == len(MODES)
            modes = {r['mode']: r for r in selected}
            assert set(modes) == set(MODES)
            assert len({r['source_sha256'] for r in modes.values()}) == 1
            a, b, c, anchor = (modes[m] for m in CUSTOM)
            pairs.append(dict(cycle=cycle, state=state, source_sha256=a['source_sha256'],
                wall_ratio=c['seconds'] / a['seconds'], cpu_ratio=c['cpu']['total_seconds'] / a['cpu']['total_seconds'],
                anchor_wall_ratio=c['seconds'] / anchor['seconds'], anchor_cpu_ratio=c['cpu']['total_seconds'] / anchor['cpu']['total_seconds'],
                aa_wall_ratio=b['seconds'] / a['seconds'], aa_cpu_ratio=b['cpu']['total_seconds'] / a['cpu']['total_seconds'],
                native_wall_ratio=c['seconds'] / modes['native']['seconds'],
                native_lines_wall_ratio=c['seconds'] / modes['native_lines']['seconds']))
    med = lambda key: statistics.median(p[key] for p in pairs)
    envelope = {kind: max(abs(statistics.median(p['aa_' + kind + '_ratio'] for p in pairs
                if p['state'] == state) - 1) for state in range(1, 6)) for kind in ['wall', 'cpu']}
    wall_margin = max(med('wall_ratio'), med('anchor_wall_ratio')) + envelope['wall']
    cpu_margin = max(med('cpu_ratio'), med('anchor_cpu_ratio')) + envelope['cpu']
    if case == 'token':
        wall_ok = med('anchor_wall_ratio') <= .92 and med('wall_ratio') < 1 - envelope['wall']
        cpu_ok = max(med('cpu_ratio'), med('anchor_cpu_ratio')) <= 1.0 and cpu_margin <= 1.05
    else:
        wall_ok = wall_margin <= 1.05
        cpu_ok = cpu_margin <= 1.05
    return dict(pairs=pairs, edited_pairs=15, aa_pairs=15, aa_envelope=envelope,
                wall_with_noise_margin=wall_margin, cpu_with_noise_margin=cpu_margin,
                gate_passed=wall_ok and cpu_ok,
                paired_wall_ratio=med('wall_ratio'), paired_cpu_ratio=med('cpu_ratio'),
                paired_anchor_wall_ratio=med('anchor_wall_ratio'), paired_anchor_cpu_ratio=med('anchor_cpu_ratio'),
                paired_native_wall_ratio=med('native_wall_ratio'),
                paired_native_lines_wall_ratio=med('native_lines_wall_ratio'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=CASES, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--cache-qualification', type=Path, required=True)
    parser.add_argument('--execution-qualification', type=Path, required=True)
    parser.add_argument('--serial-qualification', type=Path, required=True)
    args = parser.parse_args()
    assert re.fullmatch('scalar-copy-operands-edit-' + args.case + r'-\d{2}', args.run_id)
    project, variant, pattern, reference = CASES[args.case]
    case = WORKFLOWS[project] if variant is None else WORKFLOW_VARIANTS[project, variant]
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        admission = 14 if project == 'fre' else 10
        require_space(ROOT, admission)
        harness_path = ROOT / 'results/scalar-copy-operands-full-python-tests-01/summary.json'
        harness = json.loads(harness_path.read_text())
        assert harness['status'] == 'passed' and harness['tests'] == 125
        integration_path = ROOT / 'results/memory-lookup-main-complete-01/summary.json'
        integration = json.loads(integration_path.read_text())
        assert integration['status'] == 'passed' and integration['new_cache_cargo_commands'] == 223
        assert integration['real_project_history_commands'] == 40 and integration['all_sources_restored']
        harness_inputs = ROOT / harness['raw'] / 'inputs.json'
        assert sha(harness_inputs) == harness['inputs_sha256']
        assert all(sha(ROOT / p) == h for p, h in json.loads(harness_inputs.read_text()).items())
        source = ROOT / '.work/sources' / project
        reference_path = ROOT / 'results' / reference / 'summary.json'
        ref = json.loads(reference_path.read_text())
        marker = source / '.rust-interp-owned.json'
        owner = json.loads(marker.read_text())
        assert owner['owner'] == str(ROOT) and owner['revision'] == ref['revision']
        assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == ref['revision']
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source).strip()
        listing_path = ROOT / '.work/test-discovery-real-01' / (project + '-tests.json')
        listing, _ = read_listing(listing_path)
        names = [
            t['name'] for t in listing['tests'] if pattern in t['name'] and not t['ignored']]
        assert names and set(case['tests']) <= set(names)
        assert all(t['ordinary_test'] for t in listing['tests'] if t['name'] in names)
        build_paths = {m: args.build.resolve(strict=True) if m == 'candidate' else
                       ROOT / 'results' / ('parallel-suites-build-01' if m == 'anchor' else
                       'operation-map-build-02') / 'summary.json' for m in CUSTOM}
        builds = {m: json.loads(p.read_text()) for m, p in build_paths.items()}
        tools = {m: installed_tools(b['tool_key'])[0] for m, b in builds.items()}
        for m, build in builds.items():
            assert build['status'] == 'passed'
            assert all(sha(tools[m] / name) == digest for name, digest in build['binaries'].items())
            assert build['tests']['test-debug'] == build['tests']['test-release'] == dict(
                passed=441 if m == 'candidate' else 365 if m == 'anchor' else 436, ignored=1)
            require_export_option(tools[m], build['tool_key'], 'filtered-tests')
            if m in CACHED:
                require_export_option(tools[m], build['tool_key'], 'function-cache-auto')
        assert builds['baseline']['tool_key'] == 'd4a6ff9a73f831178a8c95e835ef5d17afce57e38c590148be8c04438dbc4a44'
        assert builds['anchor']['tool_key'] == 'fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e'
        assert builds['candidate']['binaries']['rust-interp-vm'] != builds['baseline']['binaries']['rust-interp-vm']
        for binary in ['rust-interp-mir-export', 'rust-interp-rustc-wrapper']:
            assert builds['candidate']['binaries'][binary] == builds['baseline']['binaries'][binary]
        proofs = [args.cache_qualification.resolve(strict=True), args.serial_qualification.resolve(strict=True),
                  args.execution_qualification.resolve(strict=True)]
        control_proofs = [ROOT / 'results' / name / 'summary.json' for name in
            ['memory-operands-cache-03', 'operation-map-qualification-01', 'operation-map-real-01']]
        for index, path in enumerate(proofs):
            proof = json.loads(path.read_text())
            assert proof['status'] == 'passed' and proof['commands'] == [203, 9, 7][index]
            if index == 0:
                assert proof['tool_key'] == builds['candidate']['tool_key'] and proof['automatic_cache_qualified']
            else:
                vm_hash = proof.get('vm_sha256') or proof['binaries']['candidate']
                assert vm_hash == builds['candidate']['binaries']['rust-interp-vm']
        assert validate_baseline(builds['baseline'], integration,
            *[json.loads(p.read_text()) for p in control_proofs])
        assert builds['candidate']['composition']['exporter_and_wrapper_key'] == EXPORTER_KEY
        assert builds['candidate']['tool_key'] == '185cc7b99ac7c9c0f955dd14e252f593eb758c7619b90b702f02ce71e882ccfb'
        coverage_path = ROOT / 'results/scalar-copy-operands-profile-01/summary.json'
        coverage = json.loads(coverage_path.read_text())
        assert coverage['status'] == 'passed' and coverage['tool_key'] == builds['candidate']['tool_key']
        assert coverage['vm_sha256'] == builds['candidate']['binaries']['rust-interp-vm']
        assert coverage['commands'] == 3 and coverage['exact_logical_counts_memory_and_entropy'] and coverage['exact_per_pc_counts']
        assert coverage['exact_operation_map_reconstruction']
        assert all(c['statistics']['jit_declined_functions'] == 0 for c in coverage['comparisons'])
        screen_path = ROOT / 'results/scalar-copy-operands-screen-token-01/summary.json'
        initial = json.loads(screen_path.read_text())
        assert initial['status'] == 'passed' and initial['commands'] == 40 and initial['gate_passed']
        assert initial['tool_keys']['candidate'] == builds['candidate']['tool_key']
        changed = source / case['file']
        original = changed.read_bytes()
        states = list(protocol_states(original.decode(), case))
        assert len(states) == 21 and len(case['edits']) == 5
        paths = [Path(__file__), Path(__file__).with_name('screen.py'), Path(__file__).with_name('FULL.md'), Path(__file__).with_name('PLAN.md'),
                 reference_path, marker, listing_path, coverage_path, harness_path, harness_inputs, integration_path, screen_path,
                 *build_paths.values(), *proofs, *control_proofs]
        paths += [ROOT / 'scripts' / name for name in ['interpreter.py', 'workspace_cache.py', 'std_mir.py',
            'toolchain_lookup.py', 'test_discovery.py', 'workflow_cases.py', 'workflow_controls.py', 'workflow_measurements.py',
            'workflow_io.py', 'suite_reports.py', 'native_suite.py', 'compare_saved_runtime.py']]
        paths += [tool / name for tool in tools.values() for name in builds['candidate']['binaries']]
        paths += [source / p for p in subprocess.check_output(['git', 'ls-files', '-z'], cwd=source).decode().split('\0')
                  if p and source / p != changed]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        work = ROOT / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        (work / 'artifacts').mkdir()
        plan = dict(owner=str(ROOT), case=case, revision=ref['revision'], names=names, filter=pattern,
            tools={m: b['tool_key'] for m, b in builds.items()}, frozen=frozen,
            original_source_sha256=sha(changed), admission_gib=admission, minimum_child_gib=8,
            cargo_workers=2, custom_suite_workers=2, native_test_threads='libtest default',
            custom_runner='prepared, fresh guest state per test',
            identity_lookup={m:lookup_args(m)[1] for m in CUSTOM},
            composition='scalar Copy operands; adopted baseline/duplicate/candidate share cached identity and automatic function cache',
            cycles=3, edited_pairs=15, aa_pairs=15,
            guest_rustflags=ref['guest_rustflags'], build_tool_opt_level=ref.get('build_tool_opt_level'),
            instruction_limit=ref['instruction_limit'], allocation_limit=ref['allocation_limit'],
            native_profiles=['repository', 'repository with dev/test debug=line-tables-only'],
            timings='complete commands; native suite time from rounded libtest output, residual is not pure compilation',
            gate='token anchor wall<=0.92 and adopted-baseline wall<1-AA wall; CPU versus both<=1.0 and max CPU ratio+AA CPU<=1.05; held-outs max wall ratio+AA wall<=1.05 and max CPU ratio+AA CPU<=1.05; engineering margins, not confidence intervals',
            stop='retain any failure; no partial-pair splicing, automatic retry, or repeat to cross a gate')
        write(work / 'plan.json', plan)
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                             'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.pop('RUST_TEST_THREADS', None)
        env.update(CARGO_TERM_COLOR='never', RUST_INTERP_LAUNCH_STATS='1')
        if ref.get('build_tool_opt_level') is not None:
            for profile in ['DEV', 'TEST']:
                env['CARGO_PROFILE_' + profile + '_BUILD_OVERRIDE_OPT_LEVEL'] = str(ref['build_tool_opt_level'])
        guest = env.copy()
        if ref['guest_rustflags']: guest['RUSTFLAGS'] = ' '.join(ref['guest_rustflags'])
        lines = dict(env, CARGO_PROFILE_DEV_DEBUG='line-tables-only', CARGO_PROFILE_TEST_DEBUG='line-tables-only')
        rows, transitions, space = [], [], []
        previous = dict.fromkeys(MODES)

        def snapshot(path):
            payload = path.read_bytes()
            digest = hashlib.sha256(payload).hexdigest()
            dest = work / 'artifacts' / (digest + path.suffix)
            if dest.exists(): assert dest.read_bytes() == payload
            else: dest.write_bytes(payload)
            return dict(path=str(dest.relative_to(ROOT)), sha256=digest)

        def invoke(mode, sample):
            cycle, state = sample['cycle'], sample['state']
            success = state != -1
            digest = sha(changed)
            assert previous[mode] != digest, 'an unchanged build entered the edit benchmark'
            suite_path = work / f'{cycle}-{state}-{mode}-suite.json'
            if mode in CUSTOM:
                command = [sys.executable, ROOT / 'scripts/interpreter.py', '--manifest-path', source / 'Cargo.toml',
                    '--package', case['package'], '--jobs', '2', '--tool-key', builds[mode]['tool_key'],
                    '--cache-namespace', args.run_id + ':' + mode, '--test-body', '--std-mir', '--engine', 'jit',
                    '--jit-resumable-calls', '--jit-persistent-registers',
                    '--instruction-limit', str(ref['instruction_limit'])]
                command += ['--isolated-batch', 'prepared', '--suite-workers', '2',
                            '--suite-report', suite_path, '--test-filter', pattern]
                if ref['allocation_limit'] is not None:
                    command += ['--allocation-limit', str(ref['allocation_limit'])]
                for field in ['inline_leaves', 'trap_unsupported_calls', 'run_try_callbacks']:
                    if ref.get(field): command += ['--' + field.replace('_', '-')]
                if mode in CACHED: command += ['--function-cache', 'auto']
                command += lookup_args(mode)
                selected_env = guest
            else:
                command = native_command(TOOLCHAIN, source / 'Cargo.toml', case['package'], work / mode,
                                         2, 'default', names, check=mode == 'check')
                selected_env = lines if mode == 'native_lines' else env
            command = list(map(str, command))
            space.append(dict(cycle=cycle, state=state, mode=mode, free_bytes=shutil.disk_usage(ROOT).free))
            write(work / 'space.json', space)
            require_space(ROOT, 8)
            started, before = time.perf_counter(), child_usage()
            child, stdout, stderr = capture(command, cwd=source, env=selected_env,
                receipt_path=work / 'active.json', receipt=dict(cycle=cycle, state=state, mode=mode))
            row = dict(cycle=cycle, state=state, phase=sample['phase'], label=sample['label'], mode=mode,
                command=command, pid=child.pid, seconds=time.perf_counter()-started, cpu=child_cpu_since(before),
                returncode=child.returncode, stdout=stdout, stderr=stderr, source_sha256=digest,
                previous_source_sha256=previous[mode])
            rows.append(row)
            write(work / 'records.json', rows)
            assert sha(changed) == digest and (child.returncode == 0) == (success or mode == 'check'), stderr[-3000:]
            assert ('Checking ' if mode in CUSTOM or mode == 'check' else 'Compiling ') + case['package'] in stderr
            if mode in CUSTOM:
                suite, suite_sha = read_report(suite_path)
                row['outcomes'] = validate_report(suite, names, 'prepared', success)
                validate_runtime_limits(suite, ref['instruction_limit'], ref['allocation_limit'], required=True)
                assert suite['workers'] == suite['requested_workers'] == 2
                launches = [json.loads(line.split(': ', 1)[1]) for line in stderr.splitlines()
                            if line.startswith('rust-interp-launch: ')]
                assert len(launches) == 1
                launch = launches[0]
                validate_lookup(launch, mode, cycle, state)
                assert launch['function_cache'] == ('auto' if mode in CACHED else 'off')
                artifact = Path(launch['artifact_path'])
                row.update(launch=launch, artifact=snapshot(artifact),
                           exporter_stages=exporter_seconds(stderr))
                assert row['artifact']['sha256'] == launch['artifact_sha256']
                assert launch['suite_report_sha256'] == suite_sha
                row['suite_sha256'] = suite_sha
                catalog = Path(launch['entry_catalog_path'])
                row['catalog'] = snapshot(catalog)
                assert row['catalog']['sha256'] == launch['entry_catalog_sha256']
                entries = json.loads(catalog.read_text())['entries']
                assert [e['name'] for e in entries] == names
                assert [e['function'] for e in entries] == [t['function'] for t in suite['tests']]
                selection_path = Path(launch['test_selection_path'])
                selection, selection_sha = read_selection(selection_path, artifact, pattern, False)
                assert selection['selected'] == names and selection_sha == launch['test_selection_sha256']
                row['selection'] = snapshot(selection_path)
                assert sum(line.startswith('rust-interp-export: ') for line in stderr.splitlines()) == 1
                if mode in CACHED:
                    reports = [json.loads(line.split(': ', 1)[1]) for line in stderr.splitlines()
                               if line.startswith('rust-interp-function-cache: ')]
                    assert len(reports) == 1 and reports[0]['mode'] in ['reuse', 'off']
                    if reports[0]['mode'] == 'off':
                        assert reports[0]['requested_mode'] == 'auto' and reports[0]['reason']
                        assert reports[0]['all_original_lowering_executed'] and reports[0]['skipped_functions'] == 0
                        assert not reports[0]['staged_in_incremental_session']
                    else:
                        assert reports[0]['staged_in_incremental_session']
                        assert reports[0]['skipped_functions'] == reports[0]['previous_payload_uses']
                    row['function_cache'] = reports[0]
            elif mode != 'check':
                row['outcomes'] = native_outcomes(stdout, names, success)
                duration = re.findall(r'test result: (?:ok|FAILED)\..*?finished in ([0-9.]+)s', stdout)
                assert len(duration) == 1
                row['native_reported_suite_seconds'] = float(duration[0])
                row['native_build_and_residual_seconds'] = row['seconds'] - float(duration[0])
            previous[mode] = digest
            write(work / 'records.json', rows)
            print(cycle, state, mode, round(row['seconds'], 3), flush=True)
            return row

        with SourceEdit(changed, original) as edit:
            restored = dict(cycle=3, state=0, phase='restored', label='restored-original', source=original, modes=CUSTOM)
            for sample in [*states, restored]:
                before = sha(changed)
                edit.replace(sample['source'])
                transitions.append(dict(cycle=sample['cycle'], state=sample['state'], before=before, after=sha(changed)))
                write(work / 'transitions.json', transitions)
                order = list(sample['modes'])
                native = ['native', 'native_lines'] if (sample['state'] + sample['cycle']) % 2 else ['native_lines', 'native']
                order = [native[0], *order, native[1], 'check']
                selected = {m: invoke(m, sample) for m in order}
                assert len({tuple(map(tuple, row['outcomes'])) for m, row in selected.items() if m != 'check'}) == 1
                for mode in ['duplicate', 'candidate']:
                    assert selected['baseline']['artifact'] == selected[mode]['artifact']
                    assert selected['baseline']['catalog'] == selected[mode]['catalog']
        assert changed.read_bytes() == original and all(sha(ROOT / p) == h for p, h in frozen.items())
        assert len(rows) == 154
        result = assessment(rows, args.case)
        result.update(status='passed', case=args.case, commands=len(rows), test_count=len(names), tests=names,
            source_restored=True, test_source_unchanged=True,
            native_assertion_outcomes_match=True, candidate_control_bytecode_matches=True,
            tool_keys=plan['tools'], raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'),
            records_sha256=sha(work / 'records.json'), transitions_sha256=sha(work / 'transitions.json'),
            space_sha256=sha(work / 'space.json'), minimum_recorded_free_bytes=min(s['free_bytes'] for s in space),
            median_edited_seconds={m: statistics.median(r['seconds'] for r in rows if r['mode'] == m and r['state'] > 0) for m in MODES})
        out = ROOT / 'results' / args.run_id
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', result)
        print('PASS original assertions, wrong edits and restoration; performance gate', result['gate_passed'], flush=True)


if __name__ == '__main__':
    main()
