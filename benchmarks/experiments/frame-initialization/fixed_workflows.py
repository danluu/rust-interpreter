#!/usr/bin/env python3
"""Run one admitted original library workflow with the qualified clearing VM."""
import argparse
import fcntl
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/aggregate-byte-writes'))
from qualify_test_bodies import read, require, sha, write
from interpreter import installed_tools
from heldout_controls import compare_controls, paired
from heldout_space import estimate as large_estimate
from verify_repeated_workflow import verify
from workflow_space import admit, required_bytes

CASES = ['folded-literal-trie', 'token-phrase', 'nushell-type-relations', 'ruff', 'nushell',
         'forward-anchored-tls', 'pgrust-sha1-inline8', 'pgrust', 'rg-aot']


def acquire(lock):
    deadline = time.monotonic() + 45
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(min(1, max(0, deadline - time.monotonic())))


def tools_for(build_path=None):
    receipt_path = ROOT / '.work/fixed-frame-clear-01/installed-tools.json'
    receipt = read(receipt_path)
    if build_path is not None:
        build = read(build_path)
        combined = ROOT / build['raw'] / 'installed-tools.json'
        require(build['status'] == 'passed' and sha(combined) == build['installed_tools_sha256'] and
            read(combined) == build['installed_tools'], 'combined build/tool receipt differs')
        receipt = dict(baseline=receipt['candidate'], candidate=build['installed_tools']['candidate'])
    result = {}
    for mode in ['baseline', 'candidate']:
        key = receipt[mode]['tool_key']
        directory, _ = installed_tools(key)
        binaries = read(directory / 'ready.json')
        result[mode] = dict(tool_key=key, vm_sha256=binaries['rust-interp-vm'],
            exporter_sha256=binaries['rust-interp-mir-export'], wrapper_sha256=binaries['rust-interp-rustc-wrapper'])
    a, b = result['baseline'], result['candidate']
    require(a['vm_sha256'] != b['vm_sha256'] and a['exporter_sha256'] == b['exporter_sha256'] and
        a['wrapper_sha256'] == b['wrapper_sha256'], 'comparison must isolate the VM')
    return result


def space_estimate(label):
    if label in ['nushell-type-relations', 'ruff', 'nushell']:
        return large_estimate(label)
    if label == 'pgrust':
        # Complete native objects, both custom caches and check metadata are
        # present in these inventories. Keep the same 20% growth and 8GiB floor.
        bound, total, reserve = {}, 0, 0
        for mode in ['native', 'baseline', 'candidate', 'check']:
            path = ROOT / 'results' / ('whole-call-space-pgrust-' + mode + '-archive-01') / 'summary.json'
            report = read(path)
            plan = ROOT / report['plan']
            require(report['status'] == 'completed' and sha(plan) == report['plan_sha256'], 'pgrust inventory changed')
            inventory = read(plan)
            require(inventory['owner'] == str(ROOT) and inventory['mode'] == mode and
                inventory['workflow'] == report['workflow'] == 'aggregate-relocation-heldout-01-pgrust', 'pgrust cache identity differs')
            groups = inventory['manifest']['groups']
            size = sum(g['bytes'] for g in groups)
            require(size == report['unique_original_bytes'] > 0, 'pgrust inventory size differs')
            require(any(p.endswith('.o') for g in groups for p in g['paths']) if mode == 'native' else True,
                'native cache was reclaimed before inventory')
            require(report['verification']['commands'] == 63 and report['verification']['check_commands'] == 21 and
                report['verification']['edited_pairs'] == 15, 'pgrust reference is incomplete')
            bound.update({str(path.relative_to(ROOT)): sha(path), str(plan.relative_to(ROOT)): sha(plan)})
            total += size
            if mode == 'check':
                reserve = report['preflight_required_bytes']
        return required_bytes(cache_bytes=total, growth_percent=20, command_floor_bytes=8 * 1024**3,
            archive_reserve_bytes=reserve, evidence_reserve_bytes=256 * 1024**2), bound
    return required_bytes(cache_bytes=4 * 1024**3, growth_percent=20, command_floor_bytes=8 * 1024**3,
        archive_reserve_bytes=2 * 1024**3, evidence_reserve_bytes=256 * 1024**2), {}


def reference_path(label):
    name = ('aggregate-relocation-e2e-01-' + label if label in CASES[:2] else
            'aggregate-relocation-heldout-01-' + ('ruff-retry-01' if label == 'ruff' else label))
    return ROOT / 'results' / name / 'summary.json'


def assess(report, case, tools, limit=1.05):
    compare_controls(report, case, tools)
    require(report['comparison']['identical_bytecode_required'], 'runtime comparison must require identical bytecode')
    checked = verify(report)
    require(tuple(checked[k] for k in ['commands', 'check_commands', 'edited_pairs', 'exact_artifact_hashes_verified']) ==
        (63, 21, 15, 42), 'workflow coverage differs')
    label = case['label']
    reference_file = reference_path(label)
    reference = read(reference_file)
    for field in ['case_sha256', 'revision', 'tests', 'edits', 'batch', 'instruction_limit', 'allocation_limit',
                  'build_tool_opt_level', 'initial_mode_order', 'std_mir']:
        actual, expected = report[field], reference[field]
        if field == 'std_mir' and actual is not None and expected is not None:
            actual, expected = actual['key'], expected['key']
        require(actual == expected, 'original case setting differs: ' + field)
    rows = read(ROOT / report['raw'] / 'records.json')
    for row in rows:
        if row['mode'] == 'native':
            continue
        for call in row['calls']:
            command = call['command']
            require(command.count('--tool-key') == 1 and command[command.index('--tool-key') + 1] ==
                call['launch']['tool_key'] == tools[row['mode']]['tool_key'], 'executed VM differs')
            flags = report['tool_builds'][row['mode']]['guest_rustflags']
            require(call['rustflags'] == (' '.join(flags) if flags else None), 'executed guest flags differ')
    result = paired(rows)
    result.update(wall_limit=limit, cpu_limit=limit,
        passed=result['wall_ratio'] <= limit and result['cpu_ratio'] <= limit)
    for field, key in [('median_seconds', 'seconds'), ('median_cpu_seconds', 'cpu_seconds')]:
        actual = {mode: statistics.median(r[key] for r in rows if r['mode'] == mode and r['state'] > 0)
                  for mode in ['native', 'baseline', 'candidate']}
        require(actual == report[field], 'reported median differs')
        result[field] = actual
    result.update(verification=checked, expected_tools=tools, label=label,
        reference=str(reference_file.relative_to(ROOT)), reference_sha256=sha(reference_file))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=CASES, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--comparison-build', type=Path,
        help='compare a qualified combined candidate with the previous fixed-clear candidate on a primary')
    args = parser.parse_args()
    if args.comparison_build is not None:
        args.comparison_build = args.comparison_build.resolve()
        require(args.case in CASES[:2] and args.run_id.startswith('fixed-frame-clear-combined-library-'),
            'combined workflow comparisons are the two predeclared primaries')
    else:
        require(not args.run_id.startswith('fixed-frame-clear-combined-'), 'combined run requires its build receipt')
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['.', '..'], 'invalid run ID')
    work = ROOT / '.work' / args.run_id
    work.mkdir(exist_ok=False)
    status = dict(status='preflight', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time())
    write(work / 'status.json', status)
    try:
        with (ROOT / '.work/benchmark.lock').open('a') as lock:
            acquire(lock)
            combined = args.comparison_build is not None
            prefix = 'fixed-frame-clear-combined-' if combined else 'fixed-frame-clear-'
            suffixes = ['confirm-01', 'native-01', 'tls-01', 'fre-01', 'integration-01'] if combined else [
                'confirm-02', 'native-01', 'tls-01', 'fre-01', 'integration-02']
            paths = [ROOT / 'results' / (prefix + suffix) / 'summary.json' for suffix in suffixes]
            confirm, native, tls, fre, integration = [read(p) for p in paths]
            require(all(r['status'] == 'passed' for r in [confirm, native, tls, fre, integration]), 'qualification incomplete')
            require(confirm['gate_passed'] and confirm['edited_pairs'] == 15 and native['commands'] == 47004 and
                tls['commands'] == 245 and fre['counts'] == dict(passed=382, ignored=7) and
                integration['original_tests_passed'] == 52 and integration['source_unchanged'], 'qualification counts differ')
            tools = tools_for(args.comparison_build)
            confirmation_baseline = (read(args.comparison_build)['installed_tools']['baseline']['tool_key']
                if combined else tools['baseline']['tool_key'])
            require(all(r['tool_key'] == tools['candidate']['tool_key'] for r in [confirm, native, tls, fre, integration]) and
                confirm['baseline_tool_key'] == confirmation_baseline, 'qualified VM differs')
            case = next(c for c in read(ROOT / 'benchmarks/workflow-corpus.json')['cases'] if c['label'] == args.case)
            estimate, bound = space_estimate(args.case)
            fs = os.statvfs(ROOT)
            admission = dict(checked_at=time.time(), observed_free_bytes=fs.f_bavail * fs.f_frsize, estimate=estimate, references=bound)
            admission['passed'] = admit(admission['observed_free_bytes'], estimate)
            write(work / 'admission.json', admission)
            require(admission['passed'], 'space admission refused before benchmark or source edits')
            command = [sys.executable, str(ROOT / 'scripts/bench_e2e_workflow.py'), '--run-id', args.run_id,
                '--project', case['project'], '--workflow', case['workflow'], '--cycles', '3', '--jobs', '4',
                '--native-jobs', '18', '--native-profile', 'o0-incremental', '--native-test-threads', 'default',
                '--check-floor', '--minimum-free-gib', '8', '--candidate-tool-key', tools['candidate']['tool_key'],
                '--baseline-tool-key', tools['baseline']['tool_key'], '--comparison-engine', 'jit', '--expect-identical-bytecode',
                '--baseline-jit-resumable-calls', '--baseline-jit-persistent-registers',
                '--candidate-jit-resumable-calls', '--candidate-jit-persistent-registers', *case['flags']]
            paths += [Path(__file__), HERE / 'FIXED-QUALIFICATION.md', HERE / 'FIXED-WORKFLOWS.md',
                ROOT / '.work/fixed-frame-clear-01/installed-tools.json', ROOT / 'benchmarks/workflow-corpus.json',
                reference_path(args.case)]
            paths += [ROOT / 'scripts' / n for n in ['bench_e2e_workflow.py', 'interpreter.py', 'verify_repeated_workflow.py',
                'workflow_cases.py', 'workflow_case_file.py', 'workflow_controls.py', 'workflow_measurements.py',
                'workflow_io.py', 'workflow_jobs.py', 'workflow_space.py', 'std_mir.py']]
            paths += [ROOT / 'benchmarks/experiments/aggregate-byte-writes' / n for n in ['heldout_controls.py', 'heldout_space.py']]
            if combined:
                build = read(args.comparison_build)
                paths += [args.comparison_build, ROOT / build['raw'] / 'installed-tools.json', HERE / 'FIXED-INTEGRATION.md']
            frozen = {**bound, **{str(p.relative_to(ROOT)): sha(p) for p in paths}}
            write(work / 'plan.json', dict(command=command, frozen=frozen, expected_tools=tools, case=case,
                admission=admission, wall_cpu_limit=1.04 if combined else 1.05,
                comparison_scope='combined candidate versus previous fixed-clear candidate' if combined else 'original fixed-clear candidate versus baseline',
                source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()))
        require(time.time() - admission['checked_at'] < 60, 'space admission expired')
        with (work / 'command.log').open('x') as log:
            child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
            status.update(status='running', child_pid=child.pid, command=command, child_started_at=time.time(),
                child_identity=subprocess.run(['ps', '-p', str(child.pid), '-o', 'pid,ppid,lstart,tty,command'], capture_output=True, text=True).stdout)
            write(work / 'status.json', status)
            code = child.wait()
        status.update(child_returncode=code, child_finished_at=time.time())
        write(work / 'status.json', status)
        require(code == 0, 'workflow failed; preserve original evidence')
        with (ROOT / '.work/benchmark.lock').open('a') as lock:
            acquire(lock)
            require(all(sha(ROOT / p) == h for p, h in frozen.items()), 'frozen workflow inputs changed')
            require(tools_for(args.comparison_build) == tools, 'installed VM changed')
            path = ROOT / 'results' / args.run_id / 'summary.json'
            result = assess(read(path), case, tools, 1.04 if combined else 1.05)
            result.update(evidence={str(path.relative_to(ROOT)): sha(path), **frozen})
            write(path.with_name('fixed-clear-assessment.json'), result)
            path.with_name('fixed-clear-assessment.md').write_text(
                f"The {args.case} retention gate **{'passes' if result['passed'] else 'fails'}**: paired complete-command wall "
                f"{(result['wall_ratio'] - 1) * 100:+.2f}%, CPU {(result['cpu_ratio'] - 1) * 100:+.2f}%. "
                'All 63 primary commands, 21 checks, 15 edited pairs and 42 artifact hashes verify. '
                'Native, baseline and candidate absolute medians are recorded in JSON; original assertions and source controls are retained.\n')
        status.update(status='finished', passed=result['passed'], finished_at=time.time())
        write(work / 'status.json', status)
        print({k: result[k] for k in ['label', 'passed', 'wall_ratio', 'cpu_ratio', 'median_seconds']}, flush=True)
    except BaseException as error:
        status.update(status='failed', error=repr(error), finished_at=time.time())
        write(work / 'status.json', status)
        raise


if __name__ == '__main__':
    main()
