#!/usr/bin/env python3
"""Frozen real-edit comparison of wrapper-only host MIR encoding policy."""
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

SOURCE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SOURCE / 'scripts'))
import interpreter
from compare_saved_runtime import acquire_lock, sha
from workflow_cases import WORKFLOWS, WORKFLOW_VARIANTS
from workflow_controls import native_command, exporter_seconds
from workflow_measurements import source_states, child_usage, child_cpu_since
from workflow_io import SourceEdit, capture, require_space, write_json as write
from suite_reports import read_report, validate_report, validate_runtime_limits

BASELINE = '49746a2218dbfdccacac0031f47e7a13b0440489c226979ff3374f6f899e09f9'
CANDIDATE = '466c60a2b833269591d014590e13811ffcc5efb8b91a3e667a041c40eaca2df5'
CUSTOM = ['baseline', 'duplicate', 'candidate']
MODES = [*CUSTOM, 'native', 'native_lines', 'check']
ORDERS = ['012', '120', '201', '210', '102', '021']
PINS = dict(nushell='9d3157963241cf89447119d34d6e887859f5e7e8',
    pgrust='38d2517d3e09168a8fe222837730d435238ff358', ruff='d136bd8d002a648de5f344df602e492658306f1e')
TOOLCHAIN = 'nightly-2026-09-08'
INSTRUCTIONS = 100_000_000_000
ALLOCATIONS = 150_000


def fingerprint(path):
    if path.is_symlink():
        return dict(kind='symlink', sha256=hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest())
    return dict(kind='file', sha256=sha(path))


def native_outcomes(stdout, names, success):
    found = re.findall(r'^test (.+) \.\.\. (ok|FAILED|ignored)$', stdout, re.M)
    assert len(found) == len(names) and set(dict(found)) == set(names)
    statuses = dict(found)
    assert 'ignored' not in statuses.values()
    failed = sum(v == 'FAILED' for v in statuses.values())
    assert (failed == 0) == success
    assert re.findall(r'test result: (ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored;', stdout) == [
        ('ok' if success else 'FAILED', str(len(names)-failed), str(failed), '0')]
    return sorted((name, 'passed' if status == 'ok' else 'failed') for name, status in found)


def order(cycle, state):
    index = cycle*5+state-1 if state > 0 else cycle*2+(state == -1)
    return [CUSTOM[int(i)] for i in ORDERS[index % len(ORDERS)]]


def assessment(rows, case):
    pairs = []
    for cycle in range(3):
        for state in range(1, 6):
            selected = [r for r in rows if r['cycle'] == cycle and r['state'] == state]
            modes = {r['mode']: r for r in selected}
            assert len(selected) == len(MODES) and set(modes) == set(MODES)
            assert len({r['source_sha256'] for r in selected}) == 1
            a, b, c = (modes[m] for m in CUSTOM)
            pairs.append(dict(cycle=cycle, state=state, source_sha256=a['source_sha256'],
                wall_ratio=c['seconds']/a['seconds'], cpu_ratio=c['cpu']['total_seconds']/a['cpu']['total_seconds'],
                aa_wall_ratio=b['seconds']/a['seconds'], aa_cpu_ratio=b['cpu']['total_seconds']/a['cpu']['total_seconds'],
                native_wall_ratio=c['seconds']/modes['native']['seconds'],
                native_lines_wall_ratio=c['seconds']/modes['native_lines']['seconds']))
    median = lambda key: statistics.median(p[key] for p in pairs)
    envelope = {kind: max(abs(statistics.median(p['aa_'+kind+'_ratio'] for p in pairs if p['state'] == state)-1)
        for state in range(1, 6)) for kind in ['wall', 'cpu']}
    noise_ok = envelope['wall'] <= .04 and envelope['cpu'] <= .03
    performance_ok = ((median('wall_ratio') < 1-envelope['wall'] and median('cpu_ratio') <= 1)
        if case == 'nushell' else max(median('wall_ratio'), median('cpu_ratio')) <= 1.05)
    return dict(pairs=pairs, edited_pairs=15, aa_pairs=15, aa_envelope=envelope, noise_acceptable=noise_ok,
        gate_passed=noise_ok and performance_ok, paired_wall_ratio=median('wall_ratio'),
        paired_cpu_ratio=median('cpu_ratio'), paired_native_wall_ratio=median('native_wall_ratio'),
        paired_native_lines_wall_ratio=median('native_lines_wall_ratio'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace-root', type=Path, required=True)
    parser.add_argument('--case', choices=list(PINS), required=True)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    root = args.workspace_root.resolve(strict=True)
    interpreter.ROOT = root
    assert re.fullmatch('host-mir-edit-'+args.case+r'-\d{2}', args.run_id)
    proofs = [root / 'results' / name / 'summary.json' for name in
        ['host-mir-build-01', 'host-mir-process-01', 'host-mir-cargo-01']]
    build, process, cargo = [json.loads(p.read_text()) for p in proofs]
    assert all(p['status'] == 'passed' for p in [build, process, cargo])
    assert build['tool_key'] == process['tool_key'] == cargo['tool_keys']['candidate'] == CANDIDATE
    assert build['tests'] == {p: dict(passed=16, failed=0, ignored=0) for p in ['debug', 'release']}
    assert process['commands'] == 19 and cargo['commands'] == 20 and cargo['host_and_guest_units_verified']
    keys = dict(baseline=BASELINE, duplicate=BASELINE, candidate=CANDIDATE)
    tool_paths = {m: interpreter.installed_tools(key)[0] for m, key in keys.items()}
    manifests = {m: json.loads((p/'ready.json').read_text()) for m,p in tool_paths.items()}
    assert manifests['candidate'] == build['binaries'] == cargo['tools']['candidate']
    assert manifests['baseline'] == cargo['tools']['baseline']
    for name in ['rust-interp-vm', 'rust-interp-mir-export']:
        assert len({m[name] for m in manifests.values()}) == 1
    with (root / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        estimate_name = {'nushell':'nu', 'ruff':'ruff', 'pgrust':'pgrust-basic'}[args.case]
        estimate_path = root / 'results' / ('aggregate-relocation-space-'+estimate_name+'-native-01') / 'summary.json'
        estimate = json.loads(estimate_path.read_text())
        assert estimate['status']=='completed' and estimate['unique_original_bytes']>0
        needed = 8*1024**3 + (estimate['unique_original_bytes']*6*120+99)//100
        assert shutil.disk_usage(root).free >= needed, 'insufficient pre-edit cache admission'
        source = root / '.work/sources' / args.case
        marker = source / '.rust-interp-owned.json'
        owner = json.loads(marker.read_text())
        assert owner['owner'] == str(root) and owner['revision'] == PINS[args.case]
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip() == owner['revision']
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
        case = WORKFLOW_VARIANTS['nushell','type-relations'] if args.case == 'nushell' else WORKFLOWS[args.case]
        changed = source / case['file']
        original = changed.read_bytes()
        states = list(source_states(original.decode(), case, 3, CUSTOM, True))
        assert len(states) == 21
        paths = [Path(__file__), Path(__file__).with_name('EDIT-PLAN.md'), marker, estimate_path, *proofs]
        helpers = ['interpreter.py','workspace_cache.py','std_mir.py','test_discovery.py','workflow_cases.py',
            'workflow_controls.py','workflow_measurements.py','workflow_io.py','suite_reports.py','native_suite.py','compare_saved_runtime.py']
        paths += [base/'scripts'/name for base in [root,SOURCE] for name in helpers]
        paths += [p/name for p in tool_paths.values() for name in ['ready.json','capabilities.json',*manifests['candidate']]]
        paths += [source/p for p in subprocess.check_output(['git','ls-files','-z'],cwd=source).decode().split('\0') if p and source/p != changed]
        frozen = {str(p.relative_to(root)):fingerprint(p) for p in paths}
        work = root / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(root),frozen=frozen,case=args.case,revision=owner['revision'],
            source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip(),
            tool_keys=keys,binaries=manifests,source_sha256=sha(changed),tests=case['tests'],commands=132,
            required_free_bytes=needed,admitted_free_bytes=shutil.disk_usage(root).free,cargo_workers=2,
            suite_workers=2,native_test_threads='default',cargo_timings=True,
            runtime_limits=dict(instructions=INSTRUCTIONS,allocations=ALLOCATIONS,memory_bytes=64*1024*1024,frames=4096)))
        env = {k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_PROFILE_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER',
                'CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET','CARGO_BUILD_BUILD_DIR','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env['CARGO_TERM_COLOR']='never'
        custom_env=dict(env,RUST_INTERP_LAUNCH_STATS='1')
        line_env=dict(env,CARGO_PROFILE_DEV_DEBUG='line-tables-only',CARGO_PROFILE_TEST_DEBUG='line-tables-only',
            CARGO_PROFILE_DEV_SPLIT_DEBUGINFO='unpacked',CARGO_PROFILE_TEST_SPLIT_DEBUGINFO='unpacked')
        rows,transitions,space=[],[],[]
        previous=dict.fromkeys(MODES)
        restored=dict(cycle=3,state=0,phase='restored',label='restored-original',source=original,modes=CUSTOM)
        with SourceEdit(changed,original) as edit:
            for sample in [*states,restored]:
                before=sha(changed);edit.replace(sample['source']);digest=sha(changed)
                cycle,state=sample['cycle'],sample['state'];success=state != -1
                transitions.append(dict(cycle=cycle,state=state,before=before,after=digest));write(work/'transitions.json',transitions)
                natives=['native','native_lines'] if (cycle+state)%2 else ['native_lines','native']
                custom=order(cycle,state)
                modes=[*natives,*custom,'check'] if (cycle+state)%2 else [*custom,*natives,'check']
                selected={}
                for mode in modes:
                    assert previous[mode] != digest,'unchanged source entered the latency sample'
                    require_space(root,8)
                    space.append(dict(cycle=cycle,state=state,mode=mode,free_bytes=shutil.disk_usage(root).free));write(work/'space.json',space)
                    suite=work/f'{cycle}-{state}-{mode}-suite.json'
                    if mode in CUSTOM:
                        command=[sys.executable,root/'scripts/interpreter.py','--manifest-path',source/'Cargo.toml',
                            '--package',case['package'],'--jobs','2','--tool-key',keys[mode],'--cache-namespace',args.run_id+':'+mode,
                            '--test-body','--std-mir','--engine','jit','--jit-resumable-calls','--jit-persistent-registers',
                            '--instruction-limit',str(INSTRUCTIONS),'--allocation-limit',str(ALLOCATIONS),
                            '--isolated-batch','prepared','--suite-workers','2','--suite-report',suite,'--function-cache','auto',
                            '--inline-leaves','--trap-unsupported-calls','--run-try-callbacks','--timings']
                        for name in case['tests']: command += ['--entry',name]
                        run_env=custom_env
                    else:
                        command=native_command(TOOLCHAIN,source/'Cargo.toml',case['package'],work/mode,2,'default',case['tests'],
                            check=mode=='check',timings=True)
                        run_env=line_env if mode=='native_lines' else env
                    began,usage=time.perf_counter(),child_usage()
                    child,stdout,stderr=capture(list(map(str,command)),cwd=source,env=run_env,
                        receipt_path=work/'active.json',receipt=dict(cycle=cycle,state=state,mode=mode))
                    row=dict(cycle=cycle,state=state,phase=sample['phase'],label=sample['label'],mode=mode,
                        command=list(map(str,command)),pid=child.pid,seconds=time.perf_counter()-began,cpu=child_cpu_since(usage),
                        returncode=child.returncode,stdout=stdout,stderr=stderr,source_sha256=digest,previous_source_sha256=previous[mode])
                    rows.append(row);write(work/'records.json',rows)
                    assert (child.returncode==0)==(success or mode=='check'),stderr[-3500:]
                    assert ('Checking ' if mode in CUSTOM or mode=='check' else 'Compiling ')+case['package'] in stderr
                    assert sha(changed)==digest
                    reports=re.findall(r'Timing report saved to (.+?\.html)',stderr)
                    assert len(reports)==1,'missing Cargo unit timing report'
                    timing=work/f'{cycle}-{state}-{mode}-timing.html';shutil.copy2(reports[0],timing)
                    row['cargo_timing']=dict(path=str(timing.relative_to(root)),sha256=sha(timing))
                    if mode in CUSTOM:
                        launch,=[json.loads(s.split(': ',1)[1]) for s in stderr.splitlines() if s.startswith('rust-interp-launch: ')]
                        assert launch['tool_key']==keys[mode] and launch['function_cache']=='auto'
                        report,suite_sha=read_report(suite,launch['suite_report_sha256'])
                        names=[t['name'] for t in report['tests']];assert sorted(names)==sorted(case['tests'])
                        row['outcomes']=sorted(validate_report(report,names,'prepared',success))
                        validate_runtime_limits(report,INSTRUCTIONS,ALLOCATIONS,required=True)
                        assert report['workers']==report['requested_workers']==2
                        row.update(launch=launch,suite_sha256=suite_sha,exporter_stages=exporter_seconds(stderr))
                        for kind,extension in [('artifact','rbc'),('entry_catalog','json')]:
                            path=work/f'{cycle}-{state}-{mode}-{kind}.{extension}'
                            shutil.copy2(launch[kind+'_path'],path);assert sha(path)==launch[kind+'_sha256']
                            row[kind]=dict(path=str(path.relative_to(root)),sha256=sha(path))
                    elif mode != 'check':
                        row['outcomes']=native_outcomes(stdout,case['tests'],success)
                        seconds,=re.findall(r'test result: (?:ok|FAILED)\..*?finished in ([0-9.]+)s',stdout)
                        row['native_reported_suite_seconds']=float(seconds)
                        row['build_and_residual_seconds']=row['seconds']-float(seconds)
                    previous[mode]=digest;selected[mode]=row;write(work/'records.json',rows)
                    print(cycle,state,mode,round(row['seconds'],3),'expected outcome',flush=True)
                assert len({json.dumps(selected[m]['outcomes']) for m in MODES if m!='check'})==1
                for kind in ['artifact','entry_catalog']:
                    assert len({selected[m][kind]['sha256'] for m in CUSTOM})==1
        assert len(rows)==132 and changed.read_bytes()==original
        assert all(fingerprint(root/p)==h for p,h in frozen.items())
        result=assessment(rows,args.case)
        result.update(status='passed',case=args.case,commands=132,test_count=len(case['tests']),source_restored=True,
            test_source_unchanged=True,candidate_control_bytecode_matches=True,raw=str(work.relative_to(root)),
            evidence={name:sha(work/(name+'.json')) for name in ['plan','records','transitions','space']},
            median_edited_seconds={m:statistics.median(r['seconds'] for r in rows if r['mode']==m and r['state']>0) for m in MODES})
        out=root/'results'/args.run_id;out.mkdir(exist_ok=False);write(out/'summary.json',result)
        print(json.dumps({k:result[k] for k in ['status','gate_passed','paired_wall_ratio','paired_cpu_ratio','aa_envelope']}),flush=True)


if __name__=='__main__':main()
