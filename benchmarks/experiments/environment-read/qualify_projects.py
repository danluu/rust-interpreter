#!/usr/bin/env python3
"""Qualify environment-capable exports against original project edit outcomes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools
from suite_reports import read_report, validate_report, validate_runtime_limits
from workflow_cases import WORKFLOW_VARIANTS
from workflow_io import SourceEdit, capture, require_space, write_json as write
from workflow_measurements import source_states

CASES = ['nushell', 'rg-aot', 'token', 'folded', 'pgrust']
STATES = [0, -1, 1, 2, 3, 4, 5, 0]


def references(rows):
    selected = []
    for index, state in enumerate(STATES):
        cycle = int(index == len(STATES) - 1)
        matches = [r for r in rows if r['mode'] == 'candidate'
                   and r['cycle'] == cycle and r['state'] == state]
        assert len(matches) == 1, ('ambiguous reference', cycle, state)
        selected.append(matches[0])
    return selected


def reference_artifact(row, kind):
    keys = [kind] if kind == 'artifact' else ['catalog', 'entry_catalog']
    present = [key for key in keys if key in row]
    assert len(present) == 1, ('ambiguous reference artifact', kind, present)
    return row[present[0]]


def selected_cases(names):
    assert names and len(set(names)) == len(names), 'empty or duplicate cases'
    assert names == [name for name in CASES if name in names], 'unknown or reordered cases'
    return list(names)


def rewrite_command(command, key, namespace, report):
    result = list(command)
    for option, value in [('--tool-key', key), ('--cache-namespace', namespace),
                          ('--suite-report', str(report))]:
        assert result.count(option) == 1, ('ambiguous command option', option)
        index = result.index(option) + 1
        assert index < len(result) and not result[index].startswith('--')
        assert result[index] != value, ('reference output would be reused', option)
        result[index] = value
    return result


def fingerprint(path):
    if path.is_symlink():
        return dict(kind='symlink', sha256=hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest())
    return dict(kind='file', sha256=sha(path))


def project_states(original, case):
    states = list(source_states(original.decode(), case, 1,
                                ['baseline', 'duplicate', 'candidate'], True))
    assert len(states) == 7
    states.append(dict(cycle=1, state=0, source=original, label='restored-original'))
    return states


def launch_borrow_cache(row):
    return row['launch']['borrowck_cache']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--harness', type=Path, required=True)
    parser.add_argument('--cases', nargs='+', choices=CASES, default=CASES)
    args = parser.parse_args()
    cases = selected_cases(args.cases)
    expected_commands = len(cases) * len(STATES)
    assert args.run_id.startswith('environment-read-projects-') and Path(args.run_id).name == args.run_id
    build_path, harness_path = args.build.resolve(strict=True), args.harness.resolve(strict=True)
    build, harness = [json.loads(p.read_text()) for p in [build_path, harness_path]]
    assert build['status'] == harness['status'] == 'passed'
    assert build['tests'] == {'test-debug': 89, 'test-release': 89}
    assert harness['tests'] == 6
    runtime_path = ROOT / 'results/environment-read-build-02/summary.json'
    runtime = json.loads(runtime_path.read_text())
    assert runtime['status'] == 'passed' and runtime['tests'] == {'test-debug': 484, 'test-release': 484}
    assert runtime['binaries']['rust-interp-vm'] == build['binaries']['rust-interp-vm']
    focused_path = ROOT / 'results/environment-read-qualification-01/summary.json'
    focused = json.loads(focused_path.read_text())
    assert focused['status'] == 'passed' and focused['commands'] == 119 and focused['tool_key'] == build['tool_key']
    tools, key = installed_tools(build['tool_key'])
    assert json.loads((tools / 'ready.json').read_text()) == build['binaries']
    proof_path = ROOT / 'results/guarded-ranges-admission-resume-01/summary.json'
    proof = json.loads(proof_path.read_text())
    assert proof['status'] == 'passed' and proof['all_five_gates_passed'] and proof['commands'] == 726
    assert proof['final_source_and_input_audit_passed'] and proof['no_completed_case_repeated']
    prior_records_path = ROOT / proof['raw'] / 'records.json'
    assert sha(prior_records_path) == proof['records_sha256']
    prior_records = json.loads(prior_records_path.read_text())
    inputs_path = ROOT / harness['raw'] / 'inputs.json'
    assert sha(inputs_path) == harness['inputs_sha256']
    assert all(sha(ROOT / p) == h for p, h in json.loads(inputs_path.read_text()).items())
    work = ROOT / '.work' / args.run_id
    work.mkdir(exist_ok=False)
    records, completed = [], []
    frozen = {str(p.relative_to(ROOT)): fingerprint(p) for p in
              [Path(__file__), Path(__file__).with_name('PLAN.md'),
               build_path, harness_path, runtime_path, focused_path, proof_path, inputs_path, prior_records_path]}
    frozen.update({str((tools / name).relative_to(ROOT)): fingerprint(tools / name)
                   for name in build['binaries']})
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
           and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                         'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR',
                         'CARGO_BUILD_TARGET', 'CARGO_BUILD_BUILD_DIR', 'RUST_TEST_THREADS']}
    assert not any(k.startswith('DYLD_') for k in env)
    env.update(CARGO_TERM_COLOR='never', RUST_INTERP_LAUNCH_STATS='1')
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 16)
        for case_name in cases:
            reference = ROOT / 'results' / ('guarded-ranges-edit-' + case_name + '-01') / 'summary.json'
            row, = [c for c in prior_records if c['case'] == case_name]
            assert sha(reference) == row['summary_sha256']
            prior = json.loads(reference.read_text())
            raw = ROOT / prior['raw']
            plan_path, rows_path = raw / 'plan.json', raw / 'records.json'
            evidence = prior.get('evidence') or {n: prior[n + '_sha256'] for n in ['plan', 'records']}
            assert sha(plan_path) == evidence['plan'] and sha(rows_path) == evidence['records']
            plan = json.loads(plan_path.read_text())
            expected = references(json.loads(rows_path.read_text()))
            project = case_name if case_name in ['nushell', 'rg-aot', 'pgrust'] else 'fre'
            source = ROOT / '.work/sources' / project
            marker = source / '.rust-interp-owned.json'
            owner = json.loads(marker.read_text())
            assert owner['owner'] == str(ROOT) and owner['revision'] == plan['revision']
            assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == plan['revision']
            assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source).strip()
            if case_name == 'nushell':
                case = WORKFLOW_VARIANTS['nushell', 'type-relations']
                estimate = json.loads((ROOT / 'results/aggregate-relocation-space-nu-native-01/summary.json').read_text())
                needed = 8 + estimate['unique_original_bytes'] * 1.2 / 1024**3
            elif case_name == 'rg-aot':
                adapter_path = ROOT / '.work/private/workflow-rg-aot.json'
                adapter = json.loads(adapter_path.read_text())
                assert adapter['owner'] == str(ROOT) and adapter['revision'] == plan['revision']
                case, needed = adapter['case'], 8
                frozen[str(adapter_path.relative_to(ROOT))] = fingerprint(adapter_path)
            else:
                case, needed = plan['case'], 12 if project == 'fre' else 8
            require_space(ROOT, needed)
            changed = source / case['file']
            original = changed.read_bytes()
            assert sha(changed) == expected[0]['source_sha256']
            states = project_states(original, case)
            paths = [reference, plan_path, rows_path, marker]
            paths += [source / p for p in subprocess.check_output(['git', 'ls-files', '-z'], cwd=source).decode().split('\0')
                      if p and source / p != changed]
            frozen.update({str(p.relative_to(ROOT)): fingerprint(p) for p in paths})
            write(work / 'plan.json', dict(owner=str(ROOT), frozen=frozen, tool_key=key,
                cases=cases, expected_commands=expected_commands, performance_measurement=False,
                reference_history='first complete cycle, then cycle1 original as restoration',
                minimum_child_gib=8, current_case=case_name, admitted_free_bytes=shutil.disk_usage(ROOT).free))
            selected_env = dict(env)
            limits = plan['runtime_limits'] if case_name in ['nushell', 'rg-aot'] else dict(
                instructions=plan['instruction_limit'], allocations=plan['allocation_limit'])
            workers = plan.get('suite_workers', plan.get('custom_suite_workers'))
            if case_name not in ['nushell', 'rg-aot']:
                if plan['guest_rustflags']:
                    selected_env['RUSTFLAGS'] = ' '.join(plan['guest_rustflags'])
                if plan['build_tool_opt_level'] is not None:
                    for profile in ['DEV', 'TEST']:
                        selected_env['CARGO_PROFILE_' + profile + '_BUILD_OVERRIDE_OPT_LEVEL'] = str(plan['build_tool_opt_level'])
            with SourceEdit(changed, original) as edit:
                for index, (state, prior_row) in enumerate(zip(states, expected)):
                    edit.replace(state['source'])
                    assert sha(changed) == prior_row['source_sha256'], (case_name, index, 'source history differs')
                    require_space(ROOT, 8)
                    suite = work / f'{case_name}-{index}-suite.json'
                    command = rewrite_command(prior_row['command'], key, args.run_id + ':' + case_name, suite)
                    child, stdout, stderr = capture(command, cwd=source, env=selected_env,
                        receipt_path=work / 'active.json', receipt=dict(case=case_name, state=index))
                    observation = dict(case=case_name, state=index, pid=child.pid, command=command,
                        returncode=child.returncode, stdout=stdout, stderr=stderr, source_sha256=sha(changed))
                    records.append(observation); write(work / 'records.json', records)
                    assert child.returncode == prior_row['returncode'], (case_name, index, 'unexpected exit')
                    assert 'Checking ' + case['package'] in stderr
                    assert launch_borrow_cache(prior_row) == 'off'
                    launch, = [json.loads(s.split(': ', 1)[1]) for s in stderr.splitlines()
                               if s.startswith('rust-interp-launch: ')]
                    assert launch['tool_key'] == key and launch['toolchain_lookup']['mode'] == 'cached'
                    assert launch['function_cache'] == prior_row['launch']['function_cache']
                    assert launch['borrowck_cache'] == 'off'
                    assert launch['toolchain_lookup']['outcome'] in (['hit', 'miss'] if index == 0 else ['hit'])
                    report, digest = read_report(suite, launch['suite_report_sha256'])
                    names = [t['name'] for t in report['tests']]
                    assert sorted(names) == sorted(name for name, _ in prior_row['outcomes'])
                    assert sorted(validate_report(report, names, 'prepared', state['state'] != -1)) == sorted(
                        tuple(outcome) for outcome in prior_row['outcomes'])
                    validate_runtime_limits(report, limits['instructions'], limits['allocations'], required=True)
                    assert report['workers'] == report['requested_workers'] == workers
                    for kind, suffix in [('artifact', 'rbc'), ('entry_catalog', 'json')]:
                        reference_bytes = reference_artifact(prior_row, kind)
                        assert sha(Path(launch[kind + '_path'])) == launch[kind + '_sha256']
                        saved = work / f'{case_name}-{index}-{kind}.{suffix}'
                        shutil.copy2(launch[kind + '_path'], saved)
                        assert sha(saved) == launch[kind + '_sha256']
                        observation[kind] = dict(path=str(saved.relative_to(ROOT)), sha256=sha(saved),
                            reference_sha256=reference_bytes['sha256'], identical_to_reference=sha(saved) == reference_bytes['sha256'])
                    observation['suite_sha256'] = digest
                    write(work / 'records.json', records)
                    print(case_name, index, 'verified artifacts and expected outcomes', flush=True)
            assert changed.read_bytes() == original
            assert all(fingerprint(ROOT / p) == h for p, h in frozen.items())
            completed.append(dict(case=case_name, commands=8, source_restored=True,
                exact_reference_artifacts=all(r[k]['identical_to_reference'] for r in records if r['case'] == case_name for k in ['artifact', 'entry_catalog']), original_assertion_outcomes=True, private=case_name == 'rg-aot'))
        assert len(records) == expected_commands and len(completed) == len(cases)
        assert all(sha(ROOT / p) == h for p, h in json.loads(inputs_path.read_text()).items())
        result = ROOT / 'results' / args.run_id
        result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', commands=expected_commands, cases=completed,
            tool_key=key, performance_measurement=False, private_details_redacted=True,
            raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'), records_sha256=sha(work / 'records.json')))


if __name__ == '__main__':
    main()
