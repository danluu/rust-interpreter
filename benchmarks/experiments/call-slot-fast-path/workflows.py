#!/usr/bin/env python3
"""Fixed A/A and primary edit workflows for guarded native Call argument slots."""
import argparse
import ast
import fcntl
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'benchmarks/experiments/aggregate-byte-writes'))
from build import read, write, sha, require, installed_tools
CONTROL = '9637b0acb1d208524c3c8b446af64cfd5e2d0d3be75e1412a8df76750ce36223'
from heldout_controls import compare_controls, paired
from verify_repeated_workflow import verify
from workflow_space import required_bytes, admit

CANDIDATE = 'ac38fa59bbf22bc80a1db9729e02e0fb5372c47ee675492e53ab3658ef53db92'
ORDER = [('aa', 'folded-literal-trie'), ('aa', 'token-phrase'),
         ('e2e', 'folded-literal-trie'), ('e2e', 'token-phrase')]


def run_id(phase, label):
    return 'call-slot-'+phase+'-01-'+label


def stage_aa(text):
    """Change only the distinct-tools guard; require the exact control key."""
    old = '''        if (baseline_key==key and baseline_guest_flags==guest_flags and
            args.baseline_inline_leaves==args.inline_leaves and
            resolved_jobs['baseline']==resolved_jobs['candidate'] and
            not args.candidate_jit_native_calls and
            args.candidate_jit_persistent_registers==args.baseline_jit_persistent_registers and
            args.candidate_jit_resumable_calls==args.baseline_jit_resumable_calls):
            parser.error('baseline and candidate must differ in tool build, guest settings, or Cargo worker count')'''
    require(text.count(old) == 1, 'A/A staging guard changed')
    new = (f'        if baseline_key != {CONTROL!r} or key != {CONTROL!r}:\n'
           "            parser.error('A/A requires the exact qualified control on both sides')")
    staged = text.replace(old, new)
    assertions = lambda code: [ast.dump(n, include_attributes=False) for n in ast.walk(ast.parse(code))
                               if isinstance(n, ast.Assert)]
    require(assertions(text) == assertions(staged), 'A/A changed benchmark assertions')
    compile(staged, 'call-slot-aa-harness', 'exec')
    return staged


def tools_for(phase):
    result = {}
    for mode, key in [('baseline', CONTROL), ('candidate', CONTROL if phase == 'aa' else CANDIDATE)]:
        directory, actual = installed_tools(key)
        report = read(ROOT/'results'/('aggregate-relocation-build-01' if key == CONTROL else 'call-slot-build-01')/'summary.json')
        require(actual == report['tool_key'] == key, 'tool identity changed')
        require(all(sha(directory/n) == h for n,h in report['binaries'].items()), 'binary changed')
        result[mode] = dict(tool_key=key, vm_sha256=report['binaries']['rust-interp-vm'],
            exporter_sha256=report['binaries']['rust-interp-mir-export'], wrapper_sha256=report['binaries']['rust-interp-rustc-wrapper'])
    require(all(result['baseline'][k] == result['candidate'][k] for k in ['exporter_sha256','wrapper_sha256']), 'frontend differs')
    return result


def assess(report, case, phase):
    tools = tools_for(phase)
    compare_controls(report, case, tools)
    require(report['comparison']['identical_bytecode_required'], 'artifact identity was not required')
    reference = read(ROOT/'results'/('aggregate-relocation-e2e-01-'+case['label'])/'summary.json')
    for field in ['case_sha256','revision','tests','edits','batch','instruction_limit','allocation_limit',
                  'build_tool_opt_level','initial_mode_order','std_mir']:
        if field == 'std_mir':
            require(report[field]['key'] == reference[field]['key'], 'std MIR identity differs')
        else:
            require(report[field] == reference[field], 'original case setting differs: '+field)
    checked = verify(report)
    require((checked['commands'], checked['check_commands'], checked['edited_pairs'], checked['exact_artifact_hashes_verified'])
            == (63,21,15,42), 'incomplete primary coverage')
    rows = read(ROOT/report['raw']/'records.json')
    for row in rows:
        if row['mode'] == 'native':
            continue
        t = tools[row['mode']]
        for call in row['calls']:
            command = call['command']
            require(command[command.index('--tool-key')+1] == call['launch']['tool_key'] == t['tool_key'], 'executed tool differs')
            require(call['rustflags'] == ' '.join(report['tool_builds'][row['mode']]['guest_rustflags']), 'executed flags differ')
    result = paired(rows)
    for field, key in [('median_seconds','seconds'), ('median_cpu_seconds','cpu_seconds')]:
        actual = {mode:statistics.median(r[key] for r in rows if r['mode'] == mode and r['state'] > 0)
                  for mode in ['native','baseline','candidate']}
        require(actual == report[field], 'reported median differs')
        result[field] = actual
    result.update(verification=checked, expected_tools=tools, phase=phase, label=case['label'])
    if phase == 'aa':
        deviations = sorted(abs(p['wall_ratio']-1) for p in result['pairs'])
        result['wall_envelope'] = max(abs(result['wall_ratio']-1), deviations[13])
        result.update(passed=None, wall_limit=None, cpu_limit=None,
            note='Fixed identical-tool control. All fifteen pairs retained; the envelope is descriptive, not a confidence interval.')
    elif case['label'] == 'token-phrase':
        aa_path = ROOT/'results'/run_id('aa', case['label'])/'slot-assessment.json'
        aa = read(aa_path)
        require(aa['phase'] == 'aa' and aa['label'] == case['label'], 'A/A control missing')
        # Recompute the control from its original receipts; never trust a stale envelope.
        control = assess(read(aa_path.with_name('summary.json')), case, 'aa')
        require(control['wall_envelope'] == aa['wall_envelope'], 'A/A envelope changed')
        result.update(wall_limit=.9, cpu_limit=1.0, wall_envelope=aa['wall_envelope'],
            passed=result['wall_ratio'] <= .9 and result['cpu_ratio'] < 1 and 1-result['wall_ratio'] > aa['wall_envelope'],
            aa_report_sha256=sha(aa_path))
    return result


def qualifications():
    # The fixed plan runs primary performance after focused workspace/smoke
    # qualification. Broader native/TLS/fre and held-outs gate adoption later.
    build = ROOT/'results/call-slot-build-01/summary.json'
    smoke = ROOT/'results/call-slot-smoke-01/summary.json'
    b, s = read(build), read(smoke)
    require(b['status'] == s['status'] == 'passed' and b['tool_key'] == s['tool_key'] == CANDIDATE,
            'guarded Call candidate qualification incomplete')
    require(b['tests']['debug'] == b['tests']['release'] and b['tests']['debug']['passed'] == 297 and
            b['tests']['debug']['ignored'] == 1 and len(b['tests']['debug']['call_slot_tests']) == 8,
            'focused workspace qualification differs')
    require(len(s['commands']) == 20 and len(s['cases']) == 2 and
            all(c['original_assertions_pass'] for c in s['cases']), 'original-artifact smoke incomplete')
    return [build, smoke]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=['aa','e2e'], required=True)
    parser.add_argument('--case', choices=['folded-literal-trie','token-phrase'], required=True)
    args = parser.parse_args()
    run = run_id(args.phase, args.case)
    work = ROOT/'.work'/run
    work.mkdir(exist_ok=False)
    status = dict(status='preflight', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time())
    write(work/'status.json', status)
    try:
        with (ROOT/'.work/benchmark.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            paths = qualifications()
            control_path = ROOT/'results/call-slot-workflow-controls-01/summary.json'
            controls = read(control_path)
            require(controls['status'] == 'passed' and all(sha(ROOT/p) == h for p,h in controls['frozen'].items()),
                    'workflow control qualification changed')
            paths.append(control_path)
            index = ORDER.index((args.phase, args.case))
            if index:
                previous = run_id(*ORDER[index-1])
                require(read(ROOT/'.work'/previous/'status.json')['status'] == 'finished' and
                        read(ROOT/'.work/experiments'/previous/'status.json').get('returncode') == 0,
                        'fixed predecessor or supervisor incomplete')
            tools = tools_for(args.phase)
            case = next(c for c in read(ROOT/'benchmarks/workflow-corpus.json')['cases'] if c['label'] == args.case)
            original = ROOT/'scripts/bench_e2e_workflow.py'
            harness = original
            if args.phase == 'aa':
                harness = work/'bench_identical.py'
                harness.write_text(stage_aa(original.read_text()))
            estimate = required_bytes(cache_bytes=4*1024**3, growth_percent=20,
                command_floor_bytes=8*1024**3, archive_reserve_bytes=2*1024**3, evidence_reserve_bytes=256*1024**2)
            fs = os.statvfs(ROOT)
            admission = dict(checked_at=time.time(), observed_free_bytes=fs.f_bavail*fs.f_frsize, estimate=estimate)
            admission['passed'] = admit(admission['observed_free_bytes'], estimate)
            write(work/'admission.json', admission)
            require(admission['passed'], 'insufficient space; no benchmark child started')
            command = [sys.executable, str(harness), '--run-id', run, '--project', case['project'], '--workflow', case['workflow'],
                '--cycles','3','--jobs','4','--native-jobs','18','--native-profile','o0-incremental',
                '--native-test-threads','default','--check-floor','--minimum-free-gib','8',
                '--baseline-tool-key',CONTROL,'--candidate-tool-key',tools['candidate']['tool_key'],
                '--comparison-engine','jit','--expect-identical-bytecode',
                '--baseline-jit-resumable-calls','--baseline-jit-persistent-registers',
                '--candidate-jit-resumable-calls','--candidate-jit-persistent-registers',*case['flags']]
            paths += [Path(__file__), original, harness, ROOT/'benchmarks/experiments/call-slot-census/FAST-PATH-NEXT.md', ROOT/'benchmarks/workflow-corpus.json']
            paths += [ROOT/'scripts'/n for n in ['interpreter.py','verify_repeated_workflow.py','workflow_space.py',
                'workflow_cases.py','workflow_case_file.py','workflow_controls.py','workflow_measurements.py','workflow_io.py','workflow_jobs.py','std_mir.py']]
            frozen = {str(p.relative_to(ROOT)):sha(p) for p in paths}
            write(work/'plan.json', dict(command=command, frozen=frozen, expected_tools=tools, phase=args.phase,
                source_commit=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()))
        require(time.time()-admission['checked_at'] < 60, 'space admission expired')
        env = os.environ.copy()
        env['PYTHONPATH'] = str(ROOT/'scripts')
        with (work/'command.log').open('x') as log:
            child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
            try:
                status.update(status='running', child_pid=child.pid, child_started_at=time.time(), command=command)
                write(work/'status.json', status)
            finally:
                code = child.wait()
        status.update(child_returncode=code, child_finished_at=time.time())
        write(work/'status.json', status)
        require(code == 0, 'workflow failed; preserve original history')
        with (ROOT/'.work/benchmark.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            require(all(sha(ROOT/p) == h for p,h in frozen.items()), 'frozen workflow input changed')
            path = ROOT/'results'/run/'summary.json'
            report = read(path)
            result = assess(report, case, args.phase)
            result.update(run_id=run, evidence={str(path.relative_to(ROOT)):sha(path), **frozen})
            write(path.with_name('slot-assessment.json'), result)
            path.with_name('slot-assessment.md').write_text(
                f"# {args.case}: call-slot {args.phase}\n\n"
                f"Paired wall ratio {result['wall_ratio']:.6f}; child CPU ratio {result['cpu_ratio']:.6f}. "
                f"Gate: {result['passed'] if args.phase != 'aa' else 'control only'}.\n\n"
                f"Native/control/candidate medians: {report['median_seconds']['native']:.3f}s / "
                f"{report['median_seconds']['baseline']:.3f}s / {report['median_seconds']['candidate']:.3f}s.\n\n"
                '63 primary commands, 21 independent Cargo checks, 15 edited pairs and 42 identical paired artifacts verify. '
                'Three cycles are descriptive and correlated; no unchanged-build or fastest-native claim.\n')
        status.update(status='finished', returncode=0, finished_at=time.time(), passed=result['passed'])
        write(work/'status.json', status)
        print({k:result[k] for k in ['run_id','wall_ratio','cpu_ratio','passed']}, flush=True)
    except BaseException as error:
        status.update(status='failed', error=repr(error), finished_at=time.time())
        write(work/'status.json', status)
        raise


if __name__ == '__main__':
    main()
