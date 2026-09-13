#!/usr/bin/env python3
"""Primary-first changed-source screen for the branch-selected fixed addresses and successor-live spills."""
import argparse
import hashlib
import json
import math
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

CASES = {'token': ('fre', 'token-phrase-allocation', 'token_phrase::tests::', 'prepared-suite-token-01')}
CUSTOM = ['baseline', 'duplicate', 'candidate', 'anchor']
CACHED = ['baseline', 'duplicate', 'candidate']
MODES = [*CUSTOM, 'native']


BASELINE_KEY = '35df4077b5cfb466cf1a7155374abb867fb8fadeb4f5dbedffe766d5b3621bc1'
EXPORTER_KEY = '35df4077b5cfb466cf1a7155374abb867fb8fadeb4f5dbedffe766d5b3621bc1'


def validate_baseline(build, integration, cache, selection, parser):
    """Bind the adopted VM/current compiler to its complete integration audit."""
    assert all(p['status'] == 'passed' for p in [build, integration, cache, selection, parser])
    assert all(p['tool_key'] == BASELINE_KEY for p in [build, integration, cache, selection, parser])
    assert build['tests']['test-debug'] == build['tests']['test-release'] == dict(passed=513, ignored=5)
    assert integration['binaries'] == build['binaries']
    assert integration['all_frozen_inputs_verified'] and integration['workspace_tests_per_profile'] == 513
    assert integration['strict_commands'] == cache['commands'] == 119
    assert integration['project_commands'] == selection['commands'] == 40
    assert integration['complete_parser_tests'] == parser['custom_tests_passed'] == 114
    assert integration['remap_internal_commands'] == 130
    identities = integration['project_artifact_identity']
    assert sorted(r['case'] for r in identities) == ['folded', 'nushell', 'pgrust', 'rg-aot', 'token']
    assert all(r['exact'] is True for r in identities)
    assert cache['automatic_cache_qualified'] and cache['source_restored'] and parser['source_unchanged']
    return True


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


def native_executable(stdout, source, target):
    """Cargo --package/--lib selects one test artifact, including workspace members."""
    targets = []
    for line in stdout.splitlines():
        if not line.startswith('{'): continue
        try:
            unit = json.loads(line)
        except json.JSONDecodeError:
            continue  # ordinary captured test output is not Cargo JSON
        if unit.get('reason') == 'compiler-artifact' and unit.get('profile', {}).get('test') and unit.get('executable'):
            if unit['target']['kind'] == ['lib']:
                library = Path(unit['target']['src_path']).resolve(strict=True)
                executable = Path(unit['executable']).resolve(strict=True)
                assert library.is_relative_to(source.resolve())
                assert executable.is_relative_to(target.resolve())
                targets.append(executable)
    assert len(targets) == 1, 'missing or ambiguous library-test executable'
    return targets[0]


def protocol_states(original, case):
    """One complete edit history; rotate custom order and alternate native placement."""
    orders = ['0132', '1203', '2310', '3021']
    samples = list(source_states(original, case, 1, CACHED, True))
    assert len(samples) == 7 and len(case['edits']) == 5
    samples.append(dict(cycle=1, state=0, phase='restored', label='restored-original', source=original.encode()))
    for index, sample in enumerate(samples):
        custom = [CUSTOM[int(i)] for i in orders[index % 4]]
        sample['modes'] = ['native', *custom] if index % 2 == 0 else [*custom, 'native']
        yield sample


def assessment(rows, case='token'):
    assert case == 'token' and len(rows) == 40
    expected = [(0, s) for s in [0, -1, 1, 2, 3, 4, 5]] + [(1, 0)]
    groups = []
    for cycle, state in expected:
        selected = [r for r in rows if r['cycle'] == cycle and r['state'] == state]
        assert len(selected) == len(MODES)
        modes = {r['mode']: r for r in selected}
        assert set(modes) == set(MODES)
        assert len({r['source_sha256'] for r in selected}) == 1
        for r in selected:
            assert all(math.isfinite(v) and v > 0 for v in [r['seconds'], r['cpu']['total_seconds']])
        if state > 0: groups.append((cycle, state, modes))
    pairs = []
    for cycle, state, modes in groups:
        a, b, c, anchor = (modes[m] for m in CUSTOM)
        pairs.append(dict(cycle=cycle, state=state, source_sha256=a['source_sha256'],
            wall_ratio=c['seconds'] / a['seconds'], cpu_ratio=c['cpu']['total_seconds'] / a['cpu']['total_seconds'],
            anchor_wall_ratio=c['seconds'] / anchor['seconds'], anchor_cpu_ratio=c['cpu']['total_seconds'] / anchor['cpu']['total_seconds'],
            aa_wall_ratio=b['seconds'] / a['seconds'], aa_cpu_ratio=b['cpu']['total_seconds'] / a['cpu']['total_seconds'],
            native_wall_ratio=c['seconds'] / modes['native']['seconds']))
    med = lambda key: statistics.median(p[key] for p in pairs)
    envelope = {kind: max(abs(p['aa_' + kind + '_ratio'] - 1) for p in pairs) for kind in ['wall', 'cpu']}
    wall_ok = med('wall_ratio') < 1 - envelope['wall']
    cpu_margin = med('cpu_ratio') + envelope['cpu']
    cpu_ok = med('cpu_ratio') <= 1.0 and cpu_margin <= 1.05
    return dict(pairs=pairs, edited_pairs=5, aa_pairs=5, aa_envelope=envelope,
        wall_with_noise_margin=med('wall_ratio') + envelope['wall'], cpu_with_noise_margin=cpu_margin,
        gate_passed=wall_ok and cpu_ok, adoption_verdict='not evaluated by this screen',
        next_action='prospective full comparison' if wall_ok and cpu_ok else 'park candidate; cancel unstarted guards',
        paired_wall_ratio=med('wall_ratio'), paired_cpu_ratio=med('cpu_ratio'),
        paired_anchor_wall_ratio=med('anchor_wall_ratio'), paired_anchor_cpu_ratio=med('anchor_cpu_ratio'),
        paired_native_wall_ratio=med('native_wall_ratio'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=CASES, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--cache-qualification', type=Path, required=True)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--harness', type=Path, required=True)
    parser.add_argument('--emission', type=Path, required=True)
    args = parser.parse_args()
    assert re.fullmatch('branch-spaces-flush-screen-' + args.case + r'-(?:continuation-)?\d{2}', args.run_id)
    assert '-continuation-' not in args.run_id, 'fresh screen required'
    project, variant, pattern, reference = CASES[args.case]
    case = WORKFLOWS[project] if variant is None else WORKFLOW_VARIANTS[project, variant]
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        admission = 14  # 6 GiB new data allowance plus an 8 GiB reserve
        require_space(ROOT, admission)
        harness_path = args.harness.resolve(strict=True)
        harness = json.loads(harness_path.read_text())
        assert harness['status'] == 'passed' and harness['tests'] == 12
        integration_path = ROOT / 'results/guarded-local-facts-main-final-audit-01/summary.json'
        integration = json.loads(integration_path.read_text())
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
                       'guarded-local-facts-main-build-01') / 'summary.json' for m in CUSTOM}
        builds = {m: json.loads(p.read_text()) for m, p in build_paths.items()}
        tools = {m: installed_tools(b['tool_key'])[0] for m, b in builds.items()}
        for m, build in builds.items():
            assert build['status'] == 'passed'
            assert all(sha(tools[m] / name) == digest for name, digest in build['binaries'].items())
            expected = dict(passed=365,ignored=1) if m=='anchor' else (532 if m=='candidate' else dict(passed=513, ignored=5))
            assert build['tests']['test-debug']==build['tests']['test-release']==expected
            require_export_option(tools[m], build['tool_key'], 'filtered-tests')
            if m in CACHED:
                require_export_option(tools[m], build['tool_key'], 'function-cache-auto')
        assert builds['baseline']['tool_key'] == BASELINE_KEY
        assert builds['anchor']['tool_key'] == 'fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e'
        assert builds['candidate']['binaries']['rust-interp-vm'] != builds['baseline']['binaries']['rust-interp-vm']
        for binary in ['rust-interp-mir-export', 'rust-interp-rustc-wrapper']:
            assert builds['candidate']['binaries'][binary] == builds['baseline']['binaries'][binary]
        proofs = [args.cache_qualification.resolve(strict=True)]
        strict = json.loads(proofs[0].read_text())
        assert strict['status']=='passed' and strict['commands']==119
        assert strict['tool_key']==builds['candidate']['tool_key']
        assert strict['source_restored'] and strict['automatic_cache_qualified']
        control_proofs = [ROOT/'results'/name/'summary.json' for name in
            ['guarded-local-facts-main-qualification-01','guarded-local-facts-main-projects-01','guarded-local-facts-main-parser-01']]
        assert validate_baseline(builds['baseline'],integration,*[json.loads(p.read_text()) for p in control_proofs])
        assert builds['candidate']['composition']['compiler_source_key']==EXPORTER_KEY
        coverage_path=args.profile.resolve(strict=True);coverage=json.loads(coverage_path.read_text())
        assert coverage['status']=='passed' and coverage['tool_key']==builds['candidate']['tool_key']
        assert coverage['vm_sha256']==builds['candidate']['binaries']['rust-interp-vm']
        assert coverage['commands']==3 and coverage['exact_logical_counts_memory_and_entropy'] and coverage['exact_per_pc_counts']
        assert coverage['exact_operation_map_reconstruction']
        assert all(c['statistics']['jit_declined_functions']==0 for c in coverage['comparisons'])
        emission_path=args.emission.resolve(strict=True);emission=json.loads(emission_path.read_text())
        assert emission['status']=='passed' and emission['tool_key']==builds['candidate']['tool_key']
        assert emission['commands']==2 and emission['exact_adopted_reconstruction']
        assert emission['only_dead_after_flush_words_removed'] and emission['guest_commands']==0
        assert emission['selector_growth_accounted']
        changed = source / case['file']
        original = changed.read_bytes()
        states = list(protocol_states(original.decode(), case))
        assert len(states) == 8 and len(case['edits']) == 5
        paths = [Path(__file__), Path(__file__).with_name('QUALIFICATION.md'), Path(__file__).with_name('PLAN.md'),
                 reference_path, marker, listing_path, coverage_path, emission_path, harness_path, harness_inputs, integration_path,
                 *build_paths.values(), *proofs, *control_proofs]
        paths += [ROOT / 'scripts' / name for name in ['interpreter.py', 'workspace_cache.py', 'std_mir.py',
            'toolchain_lookup.py', 'test_discovery.py', 'workflow_cases.py', 'workflow_controls.py', 'workflow_measurements.py',
            'workflow_io.py', 'suite_reports.py', 'native_suite.py', 'compare_saved_runtime.py']]
        paths += [tool / name for tool in tools.values() for name in builds['candidate']['binaries']]
        paths += [source / p for p in subprocess.check_output(['git', 'ls-files', '-z'], cwd=source).decode().split('\0')
                  if p and source / p != changed]
        native_target = ROOT / '.work' / args.run_id / 'native'
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
            composition='branch-selected fixed addresses and successor-live spills; adopted baseline/duplicate/candidate share cached lookup and automatic function cache',
            cycles=1, edited_pairs=5, aa_pairs=5, expected_commands=40,
            schedule=[dict(cycle=s['cycle'], state=s['state'], phase=s['phase'],
                source_sha256=hashlib.sha256(s['source']).hexdigest(), modes=s['modes']) for s in states],
            estimated_new_gib=6, reserve_gib=8,
            storage_basis='previous full token: custom caches 391164/391164/391164/260300 KiB; native 393252 KiB; allow 6 GiB including artifacts and margin',
            guest_rustflags=ref['guest_rustflags'], build_tool_opt_level=ref.get('build_tool_opt_level'),
            instruction_limit=ref['instruction_limit'], allocation_limit=ref['allocation_limit'],
            native_profiles=['repository'],
            timings='complete commands; native suite time from rounded libtest output, residual is not pure compilation',
            gate='candidate/baseline wall<1-AA wall; CPU<=1 and CPU+AA CPU<=1.05; screen admission only, not adoption; A/A is maximum absolute individual pair deviation, not a confidence interval',
            stop='retain any failure; no partial-pair splicing, automatic retry, or repeat to cross a gate')
        plan.update(retained_commands=0, new_commands=40,
                    native_target=str(native_target.relative_to(ROOT)))
        write(work / 'plan.json', plan)
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                             'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET','CARGO_BUILD_BUILD_DIR']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.pop('RUST_TEST_THREADS', None)
        env.update(CARGO_TERM_COLOR='never', RUST_INTERP_LAUNCH_STATS='1')
        if ref.get('build_tool_opt_level') is not None:
            for profile in ['DEV', 'TEST']:
                env['CARGO_PROFILE_' + profile + '_BUILD_OVERRIDE_OPT_LEVEL'] = str(ref['build_tool_opt_level'])
        guest = env.copy()
        if ref['guest_rustflags']: guest['RUSTFLAGS'] = ' '.join(ref['guest_rustflags'])
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
                command = native_command(TOOLCHAIN, source / 'Cargo.toml', case['package'], native_target,
                                         2, 'default', names)
                command.insert(command.index('--'), '--message-format=json')
                selected_env = env
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
            assert sha(changed) == digest and (child.returncode == 0) == success, stderr[-3000:]
            assert ('Checking ' if mode in CUSTOM else 'Compiling ') + case['package'] in stderr
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
            else:
                row['outcomes'] = native_outcomes(stdout, names, success)
                executable = native_executable(stdout, source, native_target)
                row['native_executable']=snapshot(executable)
                (ROOT/row['native_executable']['path']).chmod(executable.stat().st_mode & 0o777)
                row['native_build_executable']=str(executable.relative_to(ROOT))
                duration = re.findall(r'test result: (?:ok|FAILED)\..*?finished in ([0-9.]+)s', stdout)
                assert len(duration) == 1
                row['native_reported_suite_seconds'] = float(duration[0])
                row['native_build_and_residual_seconds'] = row['seconds'] - float(duration[0])
            previous[mode] = digest
            write(work / 'records.json', rows)
            print(cycle, state, mode, round(row['seconds'], 3), flush=True)
            return row

        with SourceEdit(changed, original) as edit:
            for sample in states:
                before = sha(changed)
                edit.replace(sample['source'])
                transitions.append(dict(cycle=sample['cycle'], state=sample['state'], before=before, after=sha(changed)))
                write(work / 'transitions.json', transitions)
                order = sample['modes']
                selected = {m: invoke(m, sample) for m in order}
                assert len({tuple(map(tuple, row['outcomes'])) for row in selected.values()}) == 1
                for mode in ['duplicate', 'candidate']:
                    assert selected['baseline']['artifact'] == selected[mode]['artifact']
                    assert selected['baseline']['catalog'] == selected[mode]['catalog']
        assert changed.read_bytes() == original and all(sha(ROOT / p) == h for p, h in frozen.items())
        assert len(rows) == 40
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
        result = assessment(rows, args.case)
        result.update(status='passed', case=args.case, commands=len(rows), test_count=len(names), tests=names,
            retained_commands=0, new_commands=40,
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
