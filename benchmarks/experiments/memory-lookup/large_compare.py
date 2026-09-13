#!/usr/bin/env python3
"""Frozen real-edit comparison of memory-runtime and compiler-identity cache composition."""
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
from std_mir import checked_std_mir

BASELINE = 'f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8'
CANDIDATE = 'f0af2e3e4c1093fd0e7bb5a5a53dd8e72b305d7e1536ea9c4b999ba2acaa965a'
CUSTOM = ['baseline', 'duplicate', 'candidate']
MODES = [*CUSTOM, 'native', 'native_lines', 'check']
ORDERS = ['012', '120', '201', '210', '102', '021']
PINS = dict(nushell='9d3157963241cf89447119d34d6e887859f5e7e8',
    pgrust='38d2517d3e09168a8fe222837730d435238ff358', **{'rg-aot':'474782386e976f80f7bcbc2643eaaeac1d787ad3'})
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


def timing_path(stderr):
    reports=re.findall(r'Timing report saved to [`"]?([^`\n"]+\.html)',stderr)
    assert len(reports)==1,'missing or ambiguous Cargo unit timing report'
    return reports[0]


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
    assert case in ['nushell', 'rg-aot']
    wall_margin = median('wall_ratio') + envelope['wall']
    cpu_margin = median('cpu_ratio') + envelope['cpu']
    return dict(pairs=pairs, edited_pairs=15, aa_pairs=15, aa_envelope=envelope,
        wall_with_noise_margin=wall_margin, cpu_with_noise_margin=cpu_margin,
        gate_passed=wall_margin <= 1.05 and cpu_margin <= 1.05,
        paired_wall_ratio=median('wall_ratio'), paired_cpu_ratio=median('cpu_ratio'),
        paired_native_wall_ratio=median('native_wall_ratio'),
        paired_native_lines_wall_ratio=median('native_lines_wall_ratio'))



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=['nushell', 'rg-aot'], required=True)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    root = SOURCE.resolve(strict=True)
    interpreter.ROOT = root
    assert re.fullmatch('memory-lookup-edit-'+args.case+r'-\d{2}', args.run_id)
    proof_names = ['memory-lookup-python-tests-01', 'memory-lookup-cargo-01',
        'wide-bitwise-build-01', 'memory-operands-build-02', 'memory-operands-cache-01',
        'memory-operands-qualification-01', 'memory-operands-serial-01', 'memory-operands-profile-01']
    proofs = [root/'results'/name/'summary.json' for name in proof_names]
    harness, cargo, wide, memory, cache, exact, serial, profile = [json.loads(p.read_text()) for p in proofs]
    assert all(p['status'] == 'passed' for p in [harness, cargo, wide, memory, cache, exact, serial, profile])
    assert harness['tests'] == 138 and cargo['commands'] == 20 and cargo['cache_hits_verified']
    harness_inputs = root / harness['raw'] / 'inputs.json'
    assert sha(harness_inputs) == harness['inputs_sha256']
    assert all(sha(root/p) == h for p,h in json.loads(harness_inputs.read_text()).items())
    proofs.append(harness_inputs)
    assert wide['tool_key'] == BASELINE and memory['tool_key'] == CANDIDATE
    for build, count in [(wide, 419), (memory, 428)]:
        assert build['tests']['test-debug'] == build['tests']['test-release'] == dict(passed=count, ignored=1)
    assert cache['tool_key'] == exact['tool_key'] == profile['tool_key'] == CANDIDATE
    assert cache['automatic_cache_qualified'] and profile['exact_per_pc_counts']
    assert profile['exact_logical_counts_memory_and_entropy'] and profile['commands'] == 3
    assert serial['binaries']['candidate'] == memory['binaries']['rust-interp-vm']
    keys = dict(baseline=BASELINE, duplicate=BASELINE, candidate=CANDIDATE)
    tool_paths = {m: interpreter.installed_tools(key)[0] for m,key in keys.items()}
    manifests = {m: json.loads((p/'ready.json').read_text()) for m,p in tool_paths.items()}
    assert manifests['baseline'] == manifests['duplicate'] == wide['binaries']
    assert manifests['candidate'] == memory['binaries'] == cargo['tools']['candidate']
    assert manifests['candidate']['rust-interp-vm'] != manifests['baseline']['rust-interp-vm']
    for binary in ['rust-interp-mir-export', 'rust-interp-rustc-wrapper']:
        assert manifests['candidate'][binary] == manifests['baseline'][binary]
    with (root / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        std = checked_std_mir(TOOLCHAIN)
        assert std[2] == cargo['identity']['std_mir_key']
        estimate_paths = []
        if args.case == 'rg-aot':
            needed = 8*1024**3
        else:
            estimate_name = {'nushell':'nu', 'pgrust':'pgrust-basic'}[args.case]
            estimate_path = root/'results'/('aggregate-relocation-space-'+estimate_name+'-native-01')/'summary.json'
            estimate = json.loads(estimate_path.read_text())
            assert estimate['status'] == 'completed' and estimate['unique_original_bytes'] > 0
            needed = 8*1024**3 + (estimate['unique_original_bytes']*6*120+99)//100
            estimate_paths.append(estimate_path)
        assert shutil.disk_usage(root).free >= needed, 'insufficient pre-edit cache admission'
        source = root / '.work/sources' / args.case
        marker = source / '.rust-interp-owned.json'
        owner = json.loads(marker.read_text())
        assert owner['owner'] == str(root) and owner['revision'] == PINS[args.case]
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip() == owner['revision']
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
        if args.case == 'rg-aot':
            adapter_path = root/'.work/private/workflow-rg-aot.json'
            adapter = json.loads(adapter_path.read_text())
            assert adapter['owner'] == str(root) and adapter['revision'] == PINS[args.case]
            case = adapter['case']
            assert case['private'] and len(case['tests']) == 1
            estimate_paths.append(adapter_path)
        else:
            case = WORKFLOW_VARIANTS['nushell','type-relations'] if args.case == 'nushell' else WORKFLOWS[args.case]
        workers = min(2, len(case['tests']))
        changed = source / case['file']
        original = changed.read_bytes()
        states = list(source_states(original.decode(), case, 3, CUSTOM, True))
        assert len(states) == 21
        paths = [Path(__file__), Path(__file__).with_name('WORKFLOW.md'), Path(__file__).with_name('PLAN.md'), marker,
                 root/'.work/std-mir'/std[2]/'ready.json', *estimate_paths, *proofs]
        helpers = ['interpreter.py','workspace_cache.py','std_mir.py','test_discovery.py','workflow_cases.py',
            'workflow_controls.py','workflow_measurements.py','workflow_io.py','suite_reports.py','native_suite.py','compare_saved_runtime.py','toolchain_lookup.py']
        paths += [base/'scripts'/name for base in [root,SOURCE] for name in helpers]
        paths += [p/name for p in tool_paths.values() for name in ['ready.json','capabilities.json',*manifests['candidate']]]
        paths += [source/p for p in subprocess.check_output(['git','ls-files','-z'],cwd=source).decode().split('\0') if p and source/p != changed]
        frozen = {str(p.relative_to(root)):fingerprint(p) for p in paths}
        work = root / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(root),frozen=frozen,case=args.case,revision=owner['revision'],
            source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip(),
            tool_keys=keys,binaries=manifests,std_mir_key=std[2],source_sha256=sha(changed),tests=case['tests'],commands=132,
            required_free_bytes=needed,admitted_free_bytes=shutil.disk_usage(root).free,cargo_workers=2,
            suite_workers=workers,native_test_threads='default',cargo_timings=True,
            identity_lookup={m:'cached' if m=='candidate' else 'fresh' for m in CUSTOM},
            gate='candidate/wide ratio plus corresponding A/A envelope <=1.05 for wall and CPU independently; engineering margin, not a confidence interval',
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
                            '--isolated-batch','prepared','--suite-workers',str(workers),'--suite-report',suite,'--function-cache','auto',
                            '--inline-leaves','--trap-unsupported-calls','--run-try-callbacks','--timings']
                        if workers == 1:
                            command += ['--test-filter', case['tests'][0], '--test-exact']
                        else:
                            for name in case['tests']: command += ['--entry',name]
                        command += ['--toolchain-lookup', 'cached' if mode == 'candidate' else 'fresh']
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
                    timing=work/f'{cycle}-{state}-{mode}-timing.html';shutil.copy2(timing_path(stderr),timing)
                    row['cargo_timing']=dict(path=str(timing.relative_to(root)),sha256=sha(timing))
                    if mode in CUSTOM:
                        launch,=[json.loads(s.split(': ',1)[1]) for s in stderr.splitlines() if s.startswith('rust-interp-launch: ')]
                        assert launch['tool_key']==keys[mode] and launch['function_cache']=='auto'
                        observed = launch['toolchain_lookup']
                        assert observed['mode'] == ('cached' if mode == 'candidate' else 'fresh')
                        if mode == 'candidate':
                            assert observed['outcome'] in (['miss','hit'] if cycle == 0 and state == 0 else ['hit'])
                        else: assert observed['outcome'] == 'fresh' 
                        report,suite_sha=read_report(suite,launch['suite_report_sha256'])
                        names=[t['name'] for t in report['tests']];assert sorted(names)==sorted(case['tests'])
                        row['outcomes']=sorted(validate_report(report,names,'prepared',success))
                        validate_runtime_limits(report,INSTRUCTIONS,ALLOCATIONS,required=True)
                        assert report['workers']==report['requested_workers']==workers
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
                    print(cycle,state,mode,'expected outcome',flush=True)
                assert len({json.dumps(selected[m]['outcomes']) for m in MODES if m!='check'})==1
                for kind in ['artifact','entry_catalog']:
                    assert len({selected[m][kind]['sha256'] for m in CUSTOM})==1
        assert len(rows)==132 and changed.read_bytes()==original
        assert all(fingerprint(root/p)==h for p,h in frozen.items())
        result=assessment(rows,args.case)
        result.update(status='passed',case=args.case,commands=132,test_count=len(case['tests']),source_restored=True,
            test_source_unchanged=True,candidate_control_bytecode_matches=True,tool_keys=keys,
            private=args.case=='rg-aot',raw=str(work.relative_to(root)),
            evidence={name:sha(work/(name+'.json')) for name in ['plan','records','transitions','space']},
            median_edited_seconds={m:statistics.median(r['seconds'] for r in rows if r['mode']==m and r['state']>0) for m in MODES})
        out=root/'results'/args.run_id;out.mkdir(exist_ok=False);write(out/'summary.json',result)
        print(json.dumps({k:result[k] for k in ['status','gate_passed','paired_wall_ratio','paired_cpu_ratio','aa_envelope']}),flush=True)


if __name__=='__main__':main()
