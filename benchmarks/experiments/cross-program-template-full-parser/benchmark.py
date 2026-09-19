"""Full-parser changed-source primary including the complete owned-session cost."""
import argparse,hashlib,io,json,os,re,shutil,socket,subprocess,sys,time
from contextlib import ExitStack
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/pgrust-parser-probe'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/pgrust-parser-edits'))
sys.path.insert(0,str(Path(__file__).parent))
from probe import PIN,fingerprint,native_inventory,native_target
from states import source_states,native_outcomes,custom_export_ran
from prerequisites import load as prerequisites
from compare_saved_runtime import acquire_lock,sha
from interpreter import installed_tools
from suite_reports import read_report,validate_report,validate_runtime_limits,validate_shared_templates
from workflow_io import SourceEdit,capture,require_space,write_json as write
from workflow_measurements import child_usage,child_cpu_since
from workflow_controls import exporter_seconds
from accounting import MODES,SESSION_MODES,schedule,ratios
sys.path.append(str(ROOT/'benchmarks/experiments/cross-program-template-screen'))
from session_owner import Session,read_frame
from bench_e2e_workflow import build_metrics

def full_states(original):
    return source_states(original)

def custom_command(template,key,mode,raw,index,session_paths=None,namespace=None):
    assert mode in MODES[1:]
    assert not any(flag in template for flag in ['--jit-scalar-calls','--jit-demand-regions','--jit-demand-regions-if-large','--jit-shared-templates'])
    command=template.copy();command[0]=sys.executable
    for option,value in [('--tool-key',key),('--suite-report',str(raw/f'{index}-suite.json')),('--cache-namespace',namespace or raw.name+':'+mode)]:
        assert command.count(option)==1;command[command.index(option)+1]=value
    command+=['--jit-scalar-calls']
    if mode in SESSION_MODES:
        assert session_paths is not None
        command+=['--jit-template-session',str(session_paths[mode])]
    return command

def validate_outcome(test,mode):
    assert mode in MODES[1:] and test['status'] in ['passed','failed']
    assert 'jit_demand' not in test

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    parser.add_argument('--profile',choices=['incremental'],required=True);args=parser.parse_args()
    assert re.fullmatch('cross-program-template-parser-full-'+args.profile+r'-\d{2}',args.run_id)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,24)
        base,build,paths=prerequisites()
        keys=dict(baseline=base['tool_key'],duplicate=base['tool_key'],candidate=build['tool_key']);keys['session-fresh']=build['tool_key']
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
        changed=source/'crates/backend/parser/gram_core/src/parse.rs';original=changed.read_bytes();states=full_states(original);order=schedule(states)
        paths += [prior_path,support_path,native_raw/'records.json',native_raw/'native.stdout']
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]
        paths += [ROOT/'benchmarks/experiments/cross-program-template-screen/session_owner.py']
        paths += [ROOT/'benchmarks/experiments/pgrust-parser-edits'/n for n in ['states.py','test_protocol.py']]+[ROOT/'benchmarks/experiments/pgrust-parser-probe/probe.py']
        paths += list((ROOT/'scripts').glob('*.py'))+[source/'.rust-interp-owned.json']
        paths += [source/p for p in subprocess.check_output(['git','ls-files','-z'],cwd=source).decode().split('\0') if p and source/p!=changed]
        frozen={str(p.relative_to(ROOT)):fingerprint(p) for p in paths}
        raw=ROOT/'.work'/args.run_id;raw.mkdir(exist_ok=False);artifacts=raw/'artifacts';artifacts.mkdir()
        native=native_rows[0]['command'].copy();native[native.index('--target-dir')+1]=str(raw/'native')
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_PROFILE_')) and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET','CARGO_BUILD_BUILD_DIR','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1',RUST_TEST_THREADS='2')
        if args.profile=='incremental':env['CARGO_INCREMENTAL']='1'
        write(raw/'plan.json',dict(owner=str(ROOT),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),controller_command=[sys.executable,*sys.orig_argv[1:]],
            revision=PIN,tool_keys=keys,frozen=frozen,profile=args.profile,cargo_incremental=env.get('CARGO_INCREMENTAL','project defaults'),
            schedule=order,original_source_sha256=sha(changed),native_template=native,custom_template=custom,commands=110,strict_controls=2,original_tests=114,
            initial_minimum_gib=24,new_cache_allowance_gib=16,minimum_child_gib=8,cargo_jobs=2,prepared_workers=2,native_threads=2,artifact_history='paired-cycle'))
        records=[];space=[];identities={};previous=dict.fromkeys(MODES);session_objects={};strict=[]
        write(raw/'records.json',records);write(raw/'strict.json',strict)
        def snapshot(path,suffix):
            digest=sha(path);saved=artifacts/(digest+suffix)
            if not saved.exists():shutil.copy2(path,saved)
            assert sha(saved)==digest;return dict(path=str(saved.relative_to(ROOT)),sha256=digest)
        try:
            with ExitStack() as owners, SourceEdit(changed,original) as edit:
                for mode,capacity in [('session-fresh',0),('candidate',64*1024**2)]:
                    require_space(ROOT,8)
                    endpoint=ROOT/'.work/ts'/('full-parser-'+args.run_id.rsplit('-',1)[-1]+'-'+mode)
                    owner=Session(Path(build['composition']['server_path']),source,endpoint,raw/mode,capacity,write,sha)
                    session_objects[mode]=owner;owners.callback(owner.close)
                session_paths={mode:owner.endpoint/'ready.json' for mode,owner in session_objects.items()}
                for label,code,diagnostic in [('type',b'\nfn rust_interp_strict_type_probe() { let _: u32 = "invalid"; }\n','E0308'),
                        ('borrow',b'\nfn rust_interp_strict_borrow_probe() { let mut value=0; let a=&mut value; let b=&mut value; std::hint::black_box((a,b)); }\n','E0499')]:
                    require_space(ROOT,8);assert b'rust_interp_strict_' not in original
                    edit.replace(original+code)
                    command=custom_command(custom,keys['candidate'],'candidate',raw,'strict-'+label,session_paths,raw.name+':strict')
                    child,out,err=capture(command,cwd=source,env=dict(env,RUST_INTERP_LAUNCH_STATS='1'),receipt_path=raw/'active-strict.json',receipt=dict(label=label))
                    for stream,value in [('stdout',out),('stderr',err)]:(raw/('strict-'+label+'.'+stream)).write_text(value)
                    strict.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,source_sha256=sha(changed),
                        stdout_sha256=sha(raw/('strict-'+label+'.stdout')),stderr_sha256=sha(raw/('strict-'+label+'.stderr'))));write(raw/'strict.json',strict)
                    assert child.returncode==101 and diagnostic in err and 'rust-interp-launch: ' not in err
                    assert not (raw/('strict-'+label+'-suite.json')).exists() and not (raw/('strict-'+label+'-suite.json.session.json')).exists()
                    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
                        connection.settimeout(30);connection.connect(str(session_objects['candidate'].endpoint/'socket'))
                        with connection.makefile('rb') as stream:greeting=read_frame(stream,io.BytesIO())
                    assert greeting['next_id']==1 and greeting['pid']==session_objects['candidate'].record['pid']
                    strict[-1]['next_session_request_id']=1;write(raw/'strict.json',strict)
                    edit.replace(original)
                for state in states:
                    edit.replace(state['source']);group=[]
                    for scheduled in [r for r in order if (r['cycle'],r['state'])==(state['cycle'],state['state'])]:
                        index=len(records);mode=scheduled['mode'];success=state['state']!=-1;require_space(ROOT,8)
                        assert sha(changed)==scheduled['source_sha256'] and previous[mode]!=sha(changed)
                        space.append(dict(index=index,phase='before',free_bytes=shutil.disk_usage(ROOT).free));write(raw/'space.json',space)
                        command=native.copy() if mode=='native' else custom_command(custom,keys[mode],mode,raw,index,session_paths)
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
                            assert launch.get('jit_scalar_calls',False) is True and launch['toolchain_lookup']['mode']=='cached'
                            report,digest=read_report(raw/f'{index}-suite.json',launch['suite_report_sha256'])
                            row['outcomes']=validate_report(report,names,'prepared',success);validate_runtime_limits(report,100000000000,150000,required=True)
                            assert report['workers']==2 and custom_export_ran(err)
                            if mode in SESSION_MODES:
                                receipt=launch['template_session'];assert receipt['server_pid']==session_objects[mode].record['pid']
                                assert receipt['server_executable_sha256']==build['composition']['server_executable_sha256'] and receipt['verify_hits'] is False
                                assert receipt['request_id']==len([r for r in records if r['mode']==mode])
                                assert receipt['history_bytes_per_worker']==(0 if mode=='session-fresh' else 64*1024**2)
                                assert receipt['receipt_sha256']==sha(raw/f'{index}-suite.json.session.json')
                                assert report['selected']==report['completed']==114 and report['poisoned'] is False
                                for worker in report['worker_records']:
                                    assert worker['status']=='completed' and worker['poisoned'] is False
                                    if mode=='session-fresh':assert worker['templates'] is worker['storage'] is None
                                    else:
                                        assert worker['templates']['verified_hits']==0
                                        assert worker['storage']['charged_bytes']<=64*1024**2 and worker['storage']['entries']<=16384
                            else:assert report['requested_workers']==2 and 'template_session' not in launch
                            assert launch.get('jit_shared_templates',False) is False
                            validate_shared_templates(report,False)
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
        finally:
            sessions={mode:owner.record for mode,owner in session_objects.items()};write(raw/'sessions.json',sessions)
        assert changed.read_bytes()==original and all(v==sha(changed) for v in previous.values())
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
        assert all(fingerprint(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/args.run_id;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',commands=110,strict_controls=2,original_tests=114,profile=args.profile,tool_keys=keys,source_restored=True,
            original_assertions_unchanged=True,exact_native_test_outcomes=True,candidate_control_artifacts_match=True,artifact_history='paired-cycle',
            raw=str(raw.relative_to(ROOT)),plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),space_sha256=sha(raw/'space.json'),sessions_sha256=sha(raw/'sessions.json'),strict_sha256=sha(raw/'strict.json'),measurement=ratios(records,sessions),performance_measurement=True))
        print('Completed 110 parser commands and2 strict rejections; gate',ratios(records,sessions)['gate_passed'],flush=True)
if __name__=='__main__':main()
