"""Complete original public project histories with complete ordinary-process accounting."""
import argparse,json,os,re,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import SourceEdit,capture,require_space,write_json as write
from workflow_measurements import source_states,child_usage,child_cpu_since
from workflow_cases import WORKFLOWS,WORKFLOW_VARIANTS
from workflow_controls import exporter_seconds
from test_discovery import read_listing,read_selection
from suite_reports import read_report,validate_report,validate_runtime_limits
from interpreter import installed_tools,require_export_option
from accounting import MODES,CUSTOM,SESSION_MODES,STATES,schedule,ratios
from admission import load,CASES,CANDIDATE
from commands import command,validate_options
sys.path.insert(0,str(ROOT/'benchmarks/experiments/runtime-composition-screen'))
from screen import native_executable
CASE_INPUTS={'token':('fre','token-phrase-allocation','token_phrase::tests::','prepared-suite-token-01'),
    'folded':('fre','folded-literal-trie','folded_literal_trie::tests::','prepared-suite-folded-01'),
    'pgrust':('pgrust',None,'','prepared-catalog-pgrust-03')}
PROTOCOL='compact-switch-adopted-guard-protocol-01'
def validate_protocol(summary):
    assert summary['status']=='passed' and summary['tests']==27
    assert summary['new_tests']==27 and summary['reused_tests']==0
    assert summary['commands']==summary['validated_commands']==7 and summary['reused_commands']==0
    assert summary['candidate_key']==CANDIDATE
    assert summary['original_project_guest_commands']==0 and summary['performance_measurement'] is False
    return True

def strict_probes():
    return [('type',b'\nfn rust_interp_strict_type_probe() { let _: u32 = "invalid"; }\n','E0308'),
                        ('borrow',b'\nfn rust_interp_strict_borrow_probe() { let mut x=0; let a=&mut x; let b=&mut x; core::hint::black_box((a,b)); }\n','E0499')]

def read(p):return json.loads(p.read_text())
def case_states(original,case):
    states=list(source_states(original.decode(),case,3,['baseline','duplicate','candidate'],True))
    states.append(dict(cycle=3,state=0,phase='restored',label='restored-original',source=original))
    assert [(s['cycle'],s['state']) for s in states]==STATES
    return states

def native_outcomes(stdout,names,success):
    found=re.findall(r'^test (.+) \.\.\. (ok|FAILED|ignored)$',stdout,re.M)
    assert len(found)==len(names) and set(dict(found))==set(names) and all(s!='ignored' for _,s in found)
    statuses=dict(found);failed=sum(s=='FAILED' for s in statuses.values())
    summary=re.findall(r'test result: (ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored;',stdout)
    assert summary==[('ok' if success else 'FAILED',str(len(names)-failed),str(failed),'0')]
    assert (failed==0)==success
    return [(name,'passed' if statuses[name]=='ok' else 'failed') for name in names]

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--case',choices=CASES,required=True)
    parser.add_argument('--run-id',required=True);args=parser.parse_args()
    assert args.run_id=='compact-switch-adopted-edit-'+args.case+'-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        project,variant,pattern,reference_name=CASE_INPUTS[args.case]
        admission=16 if project=='fre' else 12;require_space(ROOT,admission)
        builds,paths=load(args.case);candidate=builds['candidate']
        protocol_folder=ROOT/'results'/PROTOCOL;closure=read(protocol_folder/'closure.json')
        assert closure['status']=='closed' and closure['all_hashes_verified']
        protocol=read(protocol_folder/'summary.json');assert sha(protocol_folder/'summary.json')==closure['summary_sha256']
        assert closure['four_expected_compiler_rejections'] and closure['no_code_or_metadata_emitted']
        assert validate_protocol(protocol)
        protocol_plan=ROOT/protocol['raw']/'plan.json';assert sha(protocol_plan)==protocol['plan_sha256']
        for name,h in read(protocol_plan)['frozen'].items():assert sha(ROOT/name)==h,name;paths.append(ROOT/name)
        paths += [protocol_folder/name for name in ['closure.json','summary.json','terminal.json']]+[protocol_plan]
        case=WORKFLOWS[project] if variant is None else WORKFLOW_VARIANTS[project,variant]
        source=ROOT/'.work/sources'/project;reference_path=ROOT/'results'/reference_name/'summary.json';reference=read(reference_path)
        owner_path=source/'.rust-interp-owned.json';owner=read(owner_path)
        assert owner['owner']==str(ROOT) and owner['revision']==reference['revision']
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==reference['revision']
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
        listing_path=ROOT/'.work/test-discovery-real-01'/(project+'-tests.json');listing,_=read_listing(listing_path)
        names=[t['name'] for t in listing['tests'] if pattern in t['name'] and not t['ignored']]
        assert len(names)>=2 and set(case['tests'])<=set(names)
        assert all(t['ordinary_test'] for t in listing['tests'] if t['name'] in names)
        for mode,build in builds.items():
            tools,key=installed_tools(build['tool_key']);require_export_option(tools,key,'filtered-tests')
            if mode!='anchor':require_export_option(tools,key,'function-cache-auto')
        changed=source/case['file'];original=changed.read_bytes();states=case_states(original,case);order=schedule(states)
        assert len(case['edits'])==5 and len(order)==154
        paths += [reference_path,owner_path,listing_path]
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]
        paths += list((ROOT/'scripts').glob('*.py'))
        paths += [ROOT/'benchmarks/experiments/runtime-composition-screen/screen.py']
        # Including the edited file binds its restored value in the final audit.
        paths += [source/name for name in subprocess.check_output(['git','ls-files','-z'],cwd=source).decode().split('\0') if name]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        raw=ROOT/'.work'/args.run_id;raw.mkdir(exist_ok=False);artifacts=raw/'artifacts';artifacts.mkdir()
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_PROFILE_')) and k not in
            ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET','CARGO_BUILD_BUILD_DIR','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1',RUST_TEST_THREADS='2')
        if reference.get('build_tool_opt_level') is not None:
            for profile in ['DEV','TEST']:env['CARGO_PROFILE_'+profile+'_BUILD_OVERRIDE_OPT_LEVEL']=str(reference['build_tool_opt_level'])
        guest=dict(env,RUST_INTERP_LAUNCH_STATS='1')
        if reference['guest_rustflags']:guest['RUSTFLAGS']=' '.join(reference['guest_rustflags'])
        lines=dict(env,CARGO_PROFILE_DEV_DEBUG='line-tables-only',CARGO_PROFILE_TEST_DEBUG='line-tables-only')
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            controller_command=[sys.executable,*sys.orig_argv[1:]],case_name=args.case,case=case,project=project,revision=reference['revision'],
            source=str(source.relative_to(ROOT)),original_source_sha256=sha(changed),names=names,pattern=pattern,
            reference=reference,tool_keys={m:b['tool_key'] for m,b in builds.items()},frozen=frozen,schedule=order,
            initial_minimum_gib=admission,additional_namespace_allowance_gib=2,minimum_child_gib=8,
            cargo_jobs=2,native_threads=2,prepared_workers=2,expected_commands=154,strict_controls=2,
            original_project_guest_commands=132,performance_measurement=True,default_runtime_adoption=False))
        records=[];strict=[];space=[];owners_by_mode={};previous=dict.fromkeys(MODES)
        write(raw/'records.json',records);write(raw/'strict.json',strict)
        def snapshot(path):
            digest=sha(path);target=artifacts/(digest+path.suffix)
            if not target.exists():shutil.copy2(path,target)
            assert sha(target)==digest;return dict(path=str(target.relative_to(ROOT)),sha256=digest)
        try:
            with SourceEdit(changed,original) as edit:
                endpoints={}
                for label,code,diagnostic in strict_probes():
                    require_space(ROOT,8);assert b'rust_interp_strict_' not in original;edit.replace(original+code)
                    cmd=command(ROOT,source,case,reference,names,pattern,raw,'strict-'+label,'candidate',builds,endpoints,raw.name+':strict')
                    child,out,err=capture(cmd,cwd=source,env=guest,receipt_path=raw/'active-strict.json',receipt=dict(label=label))
                    for stream,value in [('stdout',out),('stderr',err)]:(raw/('strict-'+label+'.'+stream)).write_text(value)
                    strict.append(dict(label=label,command=cmd,pid=child.pid,returncode=child.returncode,source_sha256=sha(changed),
                        stdout_sha256=sha(raw/('strict-'+label+'.stdout')),stderr_sha256=sha(raw/('strict-'+label+'.stderr'))));write(raw/'strict.json',strict)
                    assert child.returncode==101 and diagnostic in err and 'rust-interp-launch: ' not in err
                    assert not (raw/('strict-'+label+'-suite.json')).exists()
                    assert 'rust-interp-export: ' not in err;edit.replace(original)
                for state in states:
                    edit.replace(state['source']);group=[]
                    for scheduled in [r for r in order if (r['cycle'],r['state'])==(state['cycle'],state['state'])]:
                        require_space(ROOT,8);index=len(records);mode=scheduled['mode'];success=state['state']!=-1
                        assert previous[mode]!=sha(changed)==scheduled['source_sha256']
                        cmd=command(ROOT,source,case,reference,names,pattern,raw,index,mode,builds,endpoints)
                        selected_env=guest if mode in CUSTOM else lines if mode=='native_lines' else env
                        space.append(dict(index=index,phase='before',free_bytes=shutil.disk_usage(ROOT).free));write(raw/'space.json',space)
                        usage=child_usage();started=time.perf_counter()
                        child,out,err=capture(cmd,cwd=source,env=selected_env,receipt_path=raw/'active.json',receipt=dict(index=index,**scheduled))
                        wall=time.perf_counter()-started;cpu=child_cpu_since(usage)
                        for stream,value in [('stdout',out),('stderr',err)]:(raw/(str(index)+'.'+stream)).write_text(value)
                        row=dict(scheduled,index=index,command=cmd,pid=child.pid,returncode=child.returncode,wall_seconds=wall,
                            cpu_seconds=cpu['total_seconds'],cpu=cpu,previous_source_sha256=previous[mode],
                            stdout_sha256=sha(raw/(str(index)+'.stdout')),stderr_sha256=sha(raw/(str(index)+'.stderr')))
                        records.append(row);write(raw/'records.json',records)
                        assert child.returncode==(0 if success or mode=='check' else 1 if mode in CUSTOM else 101),err[-3000:]
                        assert ('Checking ' if mode in CUSTOM or mode=='check' else 'Compiling ')+case['package'] in err
                        if mode in CUSTOM:
                            launch,=[json.loads(line.split(': ',1)[1]) for line in err.splitlines() if line.startswith('rust-interp-launch: ')]
                            assert launch['tool_key']==builds[mode]['tool_key'] and validate_options(launch,cmd,mode)
                            report,digest=read_report(raw/(str(index)+'-suite.json'),launch['suite_report_sha256'])
                            row['outcomes']=validate_report(report,names,'prepared',success)
                            validate_runtime_limits(report,reference['instruction_limit'],reference['allocation_limit'],required=True)
                            assert report['workers']==2
                            assert report['requested_workers']==2
                            artifact=Path(launch['artifact_path']);catalog=Path(launch['entry_catalog_path'])
                            row.update(launch=launch,suite_sha256=digest,artifact=snapshot(artifact),catalog=snapshot(catalog),stages=exporter_seconds(err))
                            assert row['artifact']['sha256']==launch['artifact_sha256'] and row['catalog']['sha256']==launch['entry_catalog_sha256']
                            entries=read(catalog)['entries'];assert [e['name'] for e in entries]==names
                            assert [e['function'] for e in entries]==[t['function'] for t in report['tests']]
                            selection_path=Path(launch['test_selection_path']);selection,selection_sha=read_selection(selection_path,artifact,pattern,False)
                            assert selection['selected']==names and selection_sha==launch['test_selection_sha256'];row['selection']=snapshot(selection_path)
                            assert sum(line.startswith('rust-interp-export: ') for line in err.splitlines())==1
                        elif mode!='check':
                            row['outcomes']=native_outcomes(out,names,success)
                            executable=native_executable(out,source,raw/mode);row['executable']=snapshot(executable)
                        previous[mode]=sha(changed);group.append(row);write(raw/'records.json',records)
                        space.append(dict(index=index,phase='after',free_bytes=shutil.disk_usage(ROOT).free));write(raw/'space.json',space)
                        print(index+1,args.case,mode,state['cycle'],state['state'],'validated',flush=True)
                    assert len({tuple(map(tuple,r['outcomes'])) for r in group if r['mode']!='check'})==1
                    for field in ['artifact','catalog']:
                        assert len({r[field]['sha256'] for r in group if r['mode'] in CUSTOM and r['mode']!='anchor'})==1
        finally:
            sessions={};write(raw/'sessions.json',sessions)
        assert changed.read_bytes()==original and all(v==sha(changed) for v in previous.values())
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/args.run_id;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',case=args.case,commands=154,strict_controls=2,original_tests=len(names),
            source_restored=True,original_assertions_unchanged=True,exact_native_test_outcomes=True,candidate_control_artifacts_match=True,
            raw=str(raw.relative_to(ROOT)),tool_keys={m:b['tool_key'] for m,b in builds.items()},
            **{name+'_sha256':sha(raw/(name+'.json')) for name in ['plan','records','strict','sessions','space']},
            measurement=ratios(records,sessions,args.case),performance_measurement=True,default_runtime_adoption=False))
        print('Completed154 commands; gate',ratios(records,sessions,args.case)['gate_passed'],flush=True)
if __name__=='__main__':main()
