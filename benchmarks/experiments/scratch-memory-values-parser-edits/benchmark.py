"""Matched changed-source parser guards on the qualified scalar/scratch runtime."""
import argparse,hashlib,json,math,os,re,shutil,statistics,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/pgrust-parser-probe'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/pgrust-parser-edits'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/scratch-memory-values-full'))
from probe import PIN,fingerprint,native_inventory,native_target
from states import source_states,native_outcomes,custom_export_ran
from prerequisites import load as prerequisites
from compare_saved_runtime import acquire_lock,sha
from interpreter import installed_tools
from suite_reports import read_report,validate_report,validate_runtime_limits
from workflow_io import SourceEdit,capture,require_space,write_json as write
from workflow_measurements import child_usage,child_cpu_since
from workflow_controls import exporter_seconds
from bench_e2e_workflow import build_metrics
MODES=['native','baseline','duplicate','candidate']

def schedule(states):
    assert len(states)==22
    result=[]
    for i,state in enumerate(states):
        for n in ['0132','1203','2310','3021'][i%4]:
            result.append(dict(cycle=state['cycle'],state=state['state'],mode=MODES[int(n)],label=state['label'],source_sha256=hashlib.sha256(state['source']).hexdigest()))
    assert len(result)==88
    return result

def custom_command(template,key,mode,raw,index):
    assert mode in MODES[1:] and '--jit-scalar-calls' not in template
    command=template.copy();command[0]=sys.executable
    for option,value in [('--tool-key',key),('--suite-report',str(raw/f'{index}-suite.json')),('--cache-namespace',raw.name+':'+mode)]:
        assert command.count(option)==1;command[command.index(option)+1]=value
    if mode=='candidate':command+=['--jit-scalar-calls']
    return command

def ratios(records):
    expected=[(c,s) for c in range(3) for s in [0,-1,1,2,3,4,5]]+[(3,0)]
    assert len(records)==88
    pairs=[]
    for cycle,state in expected:
        selected=[r for r in records if (r['cycle'],r['state'])==(cycle,state)]
        modes={r['mode']:r for r in selected};assert len(selected)==4 and set(modes)==set(MODES)
        assert len({r['source_sha256'] for r in selected})==1
        for r in selected:assert all(math.isfinite(r[k]) and r[k]>0 for k in ['wall_seconds','cpu_seconds'])
        if state<=0:continue
        row=dict(cycle=cycle,state=state)
        for key in ['wall_seconds','cpu_seconds']:
            row[key]=dict(candidate_baseline=modes['candidate'][key]/modes['baseline'][key],
                candidate_native=modes['candidate'][key]/modes['native'][key],aa=modes['duplicate'][key]/modes['baseline'][key])
        pairs.append(row)
    medians={}
    for key in ['wall_seconds','cpu_seconds']:
        ratio=statistics.median(r[key]['candidate_baseline'] for r in pairs)
        aa=max(abs(statistics.median(r[key]['aa'] for r in pairs if r['state']==s)-1) for s in range(1,6))
        medians[key]=dict(candidate_baseline=ratio,candidate_native=statistics.median(r[key]['candidate_native'] for r in pairs),
            aa_envelope=aa,with_noise_margin=ratio+aa)
    return dict(pairs=pairs,medians=medians,edited_pairs=15,aa_pairs=15,
        gate_passed=all(v['with_noise_margin']<=1.05 for v in medians.values()))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    parser.add_argument('--profile',choices=['incremental','repository'],required=True);args=parser.parse_args()
    assert args.run_id=='scratch-memory-values-parser-edits-'+args.profile+'-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,24)
        base,build,paths=prerequisites();keys=dict(baseline=base['tool_key'],duplicate=base['tool_key'],candidate=build['tool_key'])
        compatibility_path=ROOT/'results/scratch-memory-values-parser-01/summary.json';compatibility=json.loads(compatibility_path.read_text())
        assert compatibility['status']=='passed' and compatibility['custom_tests_passed']==114 and compatibility['tool_key']==keys['candidate']
        closed=json.loads(compatibility_path.with_name('closure.json').read_text());assert closed['status']=='closed' and closed['all_hashes_verified']
        assert sha(compatibility_path)==closed['summary_sha256']
        checkpoint_path=ROOT/'results/scratch-memory-values-edit-rg-aot-01/closure.json';checkpoint=json.loads(checkpoint_path.read_text())
        assert checkpoint['status']=='closed' and checkpoint['completed_cases']==['token','folded','pgrust','rg-aot']
        assert checkpoint['all_retained_artifacts_and_sources_verified']
        if args.profile=='repository':
            first=ROOT/'results/scratch-memory-values-parser-edits-incremental-01/summary.json';proof=json.loads(first.read_text())
            assert proof['status']=='passed' and proof['commands']==88 and proof['measurement']['gate_passed'];paths.append(first)
        harness_path=ROOT/'results/scratch-memory-values-parser-edits-protocol-01/summary.json';harness=json.loads(harness_path.read_text())
        assert harness['status']=='passed' and harness['tests']==16
        inputs=ROOT/harness['raw']/'inputs.json';assert sha(inputs)==harness['inputs_sha256']
        assert all(sha(ROOT/p)==h for p,h in json.loads(inputs.read_text()).items())
        # Retained template and native inventory define the same original target;
        # every current compiler key and candidate runtime is supplied explicitly.
        prior_path=ROOT/'.work/pgrust-parser-support-04/plan.json';prior=json.loads(prior_path.read_text())
        support_path=ROOT/'results/pgrust-parser-support-04/summary.json';support=json.loads(support_path.read_text())
        assert support['status']=='passed' and sha(prior_path)==support['plan_sha256']
        native_raw=ROOT/'.work/pgrust-parser-support-01';assert fingerprint(native_raw/'records.json')==prior['frozen'][str((native_raw/'records.json').relative_to(ROOT))]
        native_rows=json.loads((native_raw/'records.json').read_text());assert sha(native_raw/'native.stdout')==native_rows[0]['stdout_sha256']
        names=native_inventory((native_raw/'native.stdout').read_text());assert len(names)==114
        custom=prior['command'];assert [custom[i+1] for i,v in enumerate(custom) if v=='--entry']==names
        source=ROOT/'.work/sources/pgrust';owner=json.loads((source/'.rust-interp-owned.json').read_text())
        assert owner['owner']==str(ROOT) and owner['revision']==PIN
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==PIN
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
        changed=source/'crates/backend/parser/gram_core/src/parse.rs';original=changed.read_bytes();states=source_states(original);order=schedule(states)
        paths += [compatibility_path,compatibility_path.with_name('closure.json'),checkpoint_path,harness_path,inputs,prior_path,support_path,native_raw/'records.json',native_raw/'native.stdout']
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]
        paths += [ROOT/'benchmarks/experiments/pgrust-parser-edits'/n for n in ['states.py','test_protocol.py']]+[ROOT/'benchmarks/experiments/pgrust-parser-probe/probe.py']
        paths += list((ROOT/'scripts').glob('*.py'))+[source/'.rust-interp-owned.json']
        paths += [source/p for p in subprocess.check_output(['git','ls-files','-z'],cwd=source).decode().split('\0') if p and source/p!=changed]
        frozen={str(p.relative_to(ROOT)):fingerprint(p) for p in paths}
        raw=ROOT/'.work'/args.run_id;raw.mkdir(exist_ok=False);artifacts=raw/'artifacts';artifacts.mkdir()
        native=native_rows[0]['command'].copy();native[native.index('--target-dir')+1]=str(raw/'native')
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_PROFILE_')) and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET','CARGO_BUILD_BUILD_DIR','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        if args.profile=='incremental':env['CARGO_INCREMENTAL']='1'
        write(raw/'plan.json',dict(owner=str(ROOT),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            revision=PIN,tool_keys=keys,frozen=frozen,profile=args.profile,cargo_incremental=env.get('CARGO_INCREMENTAL','project defaults'),
            schedule=order,original_source_sha256=sha(changed),native_template=native,custom_template=custom,commands=88,original_tests=114,
            initial_minimum_gib=24,minimum_child_gib=8,cargo_jobs=2,prepared_workers=2,native_threads='libtest default',artifact_history='paired-cycle'))
        records=[];identities={};previous=dict.fromkeys(MODES)
        def snapshot(path,suffix):
            digest=sha(path);saved=artifacts/(digest+suffix)
            if not saved.exists():shutil.copy2(path,saved)
            assert sha(saved)==digest;return dict(path=str(saved.relative_to(ROOT)),sha256=digest)
        with SourceEdit(changed,original) as edit:
            for state in states:
                edit.replace(state['source']);group=[]
                for scheduled in [r for r in order if (r['cycle'],r['state'])==(state['cycle'],state['state'])]:
                    index=len(records);mode=scheduled['mode'];success=state['state']!=-1;require_space(ROOT,8)
                    assert sha(changed)==scheduled['source_sha256'] and previous[mode]!=sha(changed)
                    command=native.copy() if mode=='native' else custom_command(custom,keys[mode],mode,raw,index)
                    selected_env=env.copy()
                    if mode!='native':selected_env['RUST_INTERP_LAUNCH_STATS']='1'
                    usage=child_usage();start=time.perf_counter()
                    child,out,err=capture(command,cwd=source,env=selected_env,receipt_path=raw/'active.json',receipt=dict(index=index,**scheduled))
                    wall=time.perf_counter()-start;cpu=child_cpu_since(usage)
                    (raw/f'{index}.stdout').write_text(out);(raw/f'{index}.stderr').write_text(err)
                    row=dict(scheduled,index=index,pid=child.pid,command=command,returncode=child.returncode,wall_seconds=wall,cpu_seconds=cpu['total_seconds'],cpu=cpu,
                        previous_source_sha256=previous[mode],stdout_sha256=sha(raw/f'{index}.stdout'),stderr_sha256=sha(raw/f'{index}.stderr'))
                    records.append(row);write(raw/'records.json',records)
                    assert child.returncode==(0 if success else (101 if mode=='native' else 1))
                    if mode=='native':
                        row['outcomes']=native_outcomes(out,names,success)
                        exe=native_target(out,source/'crates/backend/parser/gram_core/src/lib.rs').resolve(strict=True);assert exe.is_relative_to(raw/'native')
                        row['executable']=snapshot(exe,'.native');assert 'Compiling gram_core ' in err
                    else:
                        launch,=[json.loads(line.split(': ',1)[1]) for line in err.splitlines() if line.startswith('rust-interp-launch: ')]
                        assert launch['tool_key']==keys[mode] and launch['borrowck_cache']=='off' and launch['function_cache']=='auto'
                        assert launch.get('jit_scalar_calls',False)==(mode=='candidate') and launch['toolchain_lookup']['mode']=='cached'
                        report,digest=read_report(raw/f'{index}-suite.json',launch['suite_report_sha256'])
                        row['outcomes']=validate_report(report,names,'prepared',success);validate_runtime_limits(report,100000000000,150000,required=True)
                        assert report['workers']==report['requested_workers']==2 and custom_export_ran(err)
                        row.update(suite_sha256=digest,launch=launch,stages=exporter_seconds(err),build=build_metrics(launch))
                        for kind,suffix in [('artifact','.rbc'),('entry_catalog','.json')]:
                            item=snapshot(Path(launch[kind+'_path']),suffix);assert item['sha256']==launch[kind+'_sha256'];row[kind]=item
                            identity=state['cycle'],state['state'],kind
                            assert identities.setdefault(identity,item['sha256'])==item['sha256']
                    previous[mode]=sha(changed);group.append(row);write(raw/'records.json',records)
                    print(index+1,args.profile,mode,state['cycle'],state['state'],'validated',flush=True)
                assert all(r['outcomes']==group[0]['outcomes'] for r in group)
        assert changed.read_bytes()==original and all(v==sha(changed) for v in previous.values())
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
        assert all(fingerprint(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/args.run_id;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',commands=88,original_tests=114,profile=args.profile,tool_keys=keys,source_restored=True,
            original_assertions_unchanged=True,exact_native_test_outcomes=True,candidate_control_artifacts_match=True,artifact_history='paired-cycle',
            raw=str(raw.relative_to(ROOT)),plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),measurement=ratios(records),performance_measurement=True))
        print('Completed 88 parser commands; gate',ratios(records)['gate_passed'],flush=True)
if __name__=='__main__':main()
