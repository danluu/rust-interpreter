"""Observe real token edit history only after disabled/enabled artifact parity."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(HERE.parent / 'memory-lookup-main'))
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools
from suite_reports import read_report, validate_report, validate_runtime_limits
from workflow_io import SourceEdit, capture, require_space, write_json as write
from qualify_projects import references, project_states, reference_artifact, rewrite_command, fingerprint
from observe import messages, observation, require_cargo_export


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--qualification', type=Path, required=True)
    args = parser.parse_args()
    assert args.run_id.startswith('replay-costs-token-') and Path(args.run_id).name == args.run_id
    build_path, qualification_path = [p.resolve(strict=True) for p in [args.build, args.qualification]]
    build, qualified = [json.loads(p.read_text()) for p in [build_path, qualification_path]]
    assert build['status'] == qualified['status'] == 'passed' and qualified['commands'] == 26
    assert qualified['tool_key'] == build['tool_key']
    tools, key = installed_tools(build['tool_key'])
    assert all(sha(tools / name) == h for name, h in build['binaries'].items())
    reference_path = ROOT / 'results/memory-lookup-edit-token-01/summary.json'
    retained = json.loads(reference_path.read_text())
    raw = ROOT / retained['raw']
    plan_path, records_path = raw / 'plan.json', raw / 'records.json'
    assert sha(plan_path) == retained['plan_sha256'] and sha(records_path) == retained['records_sha256']
    plan = json.loads(plan_path.read_text())
    expected = references(json.loads(records_path.read_text()))
    source = ROOT / '.work/sources/fre'
    marker = source / '.rust-interp-owned.json'
    owner = json.loads(marker.read_text())
    assert owner['owner'] == str(ROOT) and owner['revision'] == plan['revision']
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == plan['revision']
    assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source).strip()
    changed = source / plan['case']['file']
    original = changed.read_bytes()
    states = project_states(original, plan['case'])
    env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
        and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
                      'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET', 'CARGO_BUILD_BUILD_DIR', 'RUST_TEST_THREADS']}
    assert not any(k.startswith('DYLD_') for k in env)
    env.update(CARGO_TERM_COLOR='never', RUST_INTERP_LAUNCH_STATS='1', PYTHONDONTWRITEBYTECODE='1')
    if plan['guest_rustflags']:
        env['RUSTFLAGS'] = ' '.join(plan['guest_rustflags'])
    if plan['build_tool_opt_level'] is not None:
        for profile in ['DEV', 'TEST']:
            env['CARGO_PROFILE_' + profile + '_BUILD_OVERRIDE_OPT_LEVEL'] = str(plan['build_tool_opt_level'])
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        # Two fresh metadata/cache histories, including bytecode and templates.
        require_space(ROOT, 16)
        work = ROOT / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        paths = [build_path, qualification_path, reference_path, plan_path, records_path, marker]
        paths += [p for p in HERE.glob('*') if p.is_file()]
        paths += [HERE.parent / 'memory-lookup-main/qualify_projects.py']
        paths += list((ROOT / 'scripts').glob('*.py'))
        paths += [tools / name for name in build['binaries']]
        paths += [source / p for p in subprocess.check_output(['git', 'ls-files', '-z'], cwd=source).decode().split('\0')
                  if p and source / p != changed]
        frozen = {str(p.relative_to(ROOT)): fingerprint(p) for p in paths}
        write(work / 'plan.json', dict(owner=str(ROOT), frozen=frozen, tool_key=key,
            cases=['token'], expected_commands=16, modes=['off', 'on'], states=[s['state'] for s in states],
            initial_reserve_gib=16, minimum_child_gib=8, performance_measurement=False,
            reference_history='cycle0 original/wrong/five valid edits, then cycle1 original'))
        rows = []
        with SourceEdit(changed, original) as edit:
            for index, (state, prior) in enumerate(zip(states, expected)):
                edit.replace(state['source'])
                assert sha(changed) == prior['source_sha256']
                for mode, value in [('off', '0'), ('on', '1')]:
                    require_space(ROOT, 8)
                    suite = work / f'{index}-{mode}-suite.json'
                    command = rewrite_command(prior['command'], key, args.run_id + ':' + mode, suite)
                    assert command[1] == str(ROOT / 'scripts/interpreter.py')
                    command[1] = str(HERE / 'launcher.py')
                    command[2:2] = ['--replay-costs', value]
                    child, stdout, stderr = capture(command, cwd=source, env=env,
                        receipt_path=work / 'active.json', receipt=dict(index=index, mode=mode))
                    row = dict(index=index, state=state['state'], mode=mode, pid=child.pid,
                        command=command, returncode=child.returncode, stdout=stdout, stderr=stderr,
                        source_sha256=sha(changed))
                    rows.append(row)
                    write(work / 'records.json', rows)
                    assert child.returncode == prior['returncode']
                    require_cargo_export(stderr, plan['case']['package'])
                    launch, = messages(stderr, 'rust-interp-launch')
                    assert launch['tool_key'] == key and launch['function_cache'] == 'auto'
                    assert launch['toolchain_lookup']['mode'] == 'cached'
                    report, digest = read_report(suite, launch['suite_report_sha256'])
                    names = [n for n, _ in prior['outcomes']]
                    assert sorted(validate_report(report, names, 'prepared', state['state'] != -1)) == sorted(tuple(x) for x in prior['outcomes'])
                    validate_runtime_limits(report, plan['instruction_limit'], plan['allocation_limit'], required=True)
                    assert report['workers'] == report['requested_workers'] == plan['custom_suite_workers']
                    for kind in ['artifact', 'entry_catalog']:
                        old = reference_artifact(prior, kind)
                        path = Path(launch[kind + '_path'])
                        assert sha(path) == launch[kind + '_sha256']
                        if sha(path) != old['sha256']:
                            shutil.copy2(path, work / f'{index}-{mode}-{kind}-mismatch')
                        assert sha(path) == old['sha256'] == sha(ROOT / old['path']), (index, mode, kind)
                    row['observer'] = observation(stderr, mode == 'on')
                    row['cache'], = messages(stderr, 'rust-interp-function-cache')
                    if mode == 'on':
                        assert (row['observer']['totals']['functions'] == 0) == (index == 0)
                    row.update(launch=launch, suite_sha256=digest, exact_retained_artifacts=True)
                    write(work / 'records.json', rows)
                    print(index, mode, 'exact artifacts and original outcomes', flush=True)
        assert changed.read_bytes() == original and len(rows) == 16
        assert all(fingerprint(ROOT / p) == h for p, h in frozen.items())
        destination = ROOT / 'results' / args.run_id
        destination.mkdir(exist_ok=False)
        write(destination / 'summary.json', dict(status='passed', commands=16, tool_key=key,
            exact_retained_artifacts=True, source_restored=True, tests=12,
            observations=[dict(state=r['state'], observer=r['observer'], cache=r['cache']) for r in rows if r['mode'] == 'on'],
            performance_measurement=False, raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work / 'plan.json'), records_sha256=sha(work / 'records.json')))


if __name__ == '__main__':
    main()
