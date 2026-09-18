"""Full-parser changed-source primary for the indexed-switch runtime."""
import argparse,hashlib,json,math,os,re,shutil,statistics,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/pgrust-parser-probe'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/pgrust-parser-edits'))
sys.path.insert(0,str(Path(__file__).parent))
from probe import PIN,fingerprint,native_inventory,native_target
from states import source_states,native_outcomes,custom_export_ran
from prerequisites import load as prerequisites, ANCHOR
from compare_saved_runtime import acquire_lock,sha
from interpreter import installed_tools
from suite_reports import read_report,validate_report,validate_runtime_limits
from workflow_io import SourceEdit,capture,require_space,write_json as write
from workflow_measurements import child_usage,child_cpu_since
from workflow_controls import exporter_seconds
from bench_e2e_workflow import build_metrics
MODES=['native','baseline','duplicate','candidate','anchor']

def screen_states(original):
    full=source_states(original)
    return full[:7]+[dict(full[-1],cycle=1)]

def schedule(states):
    assert [(s['cycle'],s['state']) for s in states]==[(0,s) for s in [0,-1,1,2,3,4,5]]+[(1,0)]
    result=[]
    for i,state in enumerate(states):
        for offset in range(5):
            mode=MODES[(i+offset)%5]
            result.append(dict(cycle=state['cycle'],state=state['state'],mode=mode,label=state['label'],source_sha256=hashlib.sha256(state['source']).hexdigest()))
    return result

def custom_command(template,key,mode,raw,index):
    assert mode in MODES[1:]
    assert not any(flag in template for flag in ['--jit-scalar-calls','--jit-demand-regions','--jit-demand-regions-if-large','--indexed-switches'])
    command=template.copy();command[0]=sys.executable
    for option,value in [('--tool-key',key),('--suite-report',str(raw/f'{index}-suite.json')),('--cache-namespace',raw.name+':'+mode)]:
        assert command.count(option)==1;command[command.index(option)+1]=value
    if mode!='anchor':command+=['--jit-scalar-calls']
    if mode=='candidate':command+=['--indexed-switches']
    return command

def ratios(records):
    expected=[(0,s) for s in [0,-1,1,2,3,4,5]]+[(1,0)]
    assert len(records)==40
    pairs=[]
    for cycle,state in expected:
        selected=[r for r in records if (r['cycle'],r['state'])==(cycle,state)]
        modes={r['mode']:r for r in selected};assert len(selected)==5 and set(modes)==set(MODES)
        assert len({r['source_sha256'] for r in selected})==1
        for r in selected:assert all(math.isfinite(r[k]) and r[k]>0 for k in ['wall_seconds','cpu_seconds'])
        if state<=0:continue
        row=dict(cycle=cycle,state=state)
        for key in ['wall_seconds','cpu_seconds']:
            row[key]=dict(candidate_baseline=modes['candidate'][key]/modes['baseline'][key],
                candidate_native=modes['candidate'][key]/modes['native'][key],
                candidate_anchor=modes['candidate'][key]/modes['anchor'][key],aa=modes['duplicate'][key]/modes['baseline'][key])
        pairs.append(row)
    medians={}
    for key in ['wall_seconds','cpu_seconds']:
        ratio=statistics.median(r[key]['candidate_baseline'] for r in pairs)
        aa=max(abs(r[key]['aa']-1) for r in pairs)
        medians[key]=dict(candidate_baseline=ratio,candidate_native=statistics.median(r[key]['candidate_native'] for r in pairs),
            candidate_anchor=statistics.median(r[key]['candidate_anchor'] for r in pairs),aa_envelope=aa,with_noise_margin=ratio+aa)
    wall,cpu=medians['wall_seconds'],medians['cpu_seconds']
    passed=wall['with_noise_margin']<1 and cpu['candidate_baseline']<=1 and cpu['with_noise_margin']<=1.05
    noisy=max(wall['aa_envelope'],cpu['aa_envelope'])>0.08
    return dict(pairs=pairs,medians=medians,edited_pairs=5,aa_pairs=5,gate_passed=passed,
        verdict='passed' if passed else ('unmeasurable' if noisy else 'failed'),adoption=False)

def validate_outcome(test,mode):
    assert mode in MODES[1:] and test['status'] in ['passed','failed']
    assert 'jit_demand' not in test

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    parser.add_argument('--profile',choices=['incremental'],required=True);args=parser.parse_args()
    assert re.fullmatch('indexed-switches-parser-screen-'+args.profile+r'-\d{2}',args.run_id)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,14)
        base,build,paths=prerequisites()
        keys=dict(baseline=base['tool_key'],duplicate=base['tool_key'],candidate=build['tool_key'],anchor=ANCHOR)
        harness_path=ROOT/'results/indexed-switches-parser-protocol-01/summary.json';harness=json.loads(harness_path.read_text())
        assert harness['status']=='passed' and harness['tests']==19
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
        changed=source/'crates/backend/parser/gram_core/src/parse.rs';original=changed.read_bytes();states=screen_states(original);order=schedule(states)
        paths += [harness_path,inputs,prior_path,support_path,native_raw/'records.json',native_raw/'native.stdout']
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
            schedule=order,original_source_sha256=sha(changed),native_template=native,custom_template=custom,commands=40,original_tests=114,
            initial_minimum_gib=14,new_cache_allowance_gib=6,minimum_child_gib=8,cargo_jobs=2,prepared_workers=2,native_threads='libtest default',artifact_history='paired-cycle'))
        records=[];space=[];identities={};previous=dict.fromkeys(MODES)
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
                    space.append(dict(index=index,phase='before',free_bytes=shutil.disk_usage(ROOT).free));write(raw/'space.json',space)
                    command=native.copy() if mode=='native' else custom_command(custom,keys[mode],mode,raw,index)
                    selected_env=env.copy()
                    if mode!='native':selected_env['RUST_INTERP_LAUNCH_STATS']='1'
                    usage=child_usage();start=time.perf_counter()
                    child,out,err=capture(command,cwd=source,env=selected_env,receipt_path=raw/'active.json',receipt=dict(index=index,**scheduled))
                    wall=time.perf_counter()-start;cpu=child_cpu_since(usage)
                    space.append(dict(index=index,phase='after',free_bytes=shutil.disk_usage(ROOT).free));write(raw/'space.json',space)
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
                        assert launch.get('jit_scalar_calls',False)==(mode!='anchor') and launch['toolchain_lookup']['mode']=='cached'
                        report,digest=read_report(raw/f'{index}-suite.json',launch['suite_report_sha256'])
                        row['outcomes']=validate_report(report,names,'prepared',success);validate_runtime_limits(report,100000000000,150000,required=True)
                        assert report['workers']==report['requested_workers']==2 and custom_export_ran(err)
                        assert launch['indexed_switches']==(mode=='candidate')
                        for test in report['tests']:
                            validate_outcome(test,mode)
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
        write(result/'summary.json',dict(status='passed',commands=40,original_tests=114,profile=args.profile,tool_keys=keys,source_restored=True,
            original_assertions_unchanged=True,exact_native_test_outcomes=True,candidate_control_artifacts_match=True,artifact_history='paired-cycle',
            raw=str(raw.relative_to(ROOT)),plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),space_sha256=sha(raw/'space.json'),measurement=ratios(records),performance_measurement=True))
        print('Completed 40 parser commands; gate',ratios(records)['gate_passed'],flush=True)
if __name__=='__main__':main()
