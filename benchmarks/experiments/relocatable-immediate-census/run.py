"""Qualify and run a test-only coverage census on exact actual parser misses."""
import json,os,shutil,subprocess,sys,time
from pathlib import Path
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='relocatable-immediate-census-01'
def read(p):return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated);assert shutil.disk_usage(ROOT).free>=needed
        frozen={}
        def bind(p,h=None):
            actual=sha(p)
            if h is not None:assert actual==h,p
            frozen[str(p.relative_to(ROOT))]=actual
            return read(p) if p.suffix=='.json' else actual
        def closed(name):
            p=ROOT/'results'/name;c=bind(p/'closure.json');assert c['status']=='closed' and c['all_hashes_verified']
            s=bind(p/'summary.json',c['summary_sha256']);t=bind(p/'terminal.json',c['terminal_sha256'])
            assert s['status']=='passed' and t['status']=='finished' and t['returncode']==0 and t['owner']==str(ROOT)
            return s
        trace=closed('template-miss-parser-01');assert trace['history_reconstructed'] and trace['test_invocations']==1824
        cause=closed('template-miss-causes-01');assert cause['valid_edit_counts']['immediate_values_only']==2563
        saved=closed('cross-program-template-suites-01');cases=bind(ROOT/saved['raw']/'input.json',saved['outputs'][saved['raw']+'/input.json'])['cases']
        assert [c['state'] for c in cases]==[0,-1,1,2,3,4,5,0]
        artifacts=[];attempts=[];previous=[{},{}]
        for ordinal,case in enumerate(cases):
            bind(Path(case['artifact_path']),case['artifact_sha256'])
            artifacts.append(dict(path=case['artifact_path'],sha256=case['artifact_sha256'],state=case['state']))
            path=ROOT/trace['raw']/'cached'/f'{ordinal}.report.json';report=bind(path,trace['outputs'][str(path.relative_to(ROOT))])
            assert report['request_id']==ordinal+1
            for w in report['worker_records']:
                assert w['templates']['trace_dropped']==0
                for e in w['templates']['trace']:
                    fid=e['function'];old=previous[w['worker']].get(fid);previous[w['worker']][fid]=ordinal
                    if case['state']>0 and e['lookup']!='hit':
                        attempts.append(dict(previous=old,ordinal=ordinal,function=fid,worker=w['worker'],emission_ns=e['emission_ns']))
        assert len(attempts)==sum(cause['valid_edit_counts'].values())
        assert sum(a['emission_ns'] for a in attempts)==sum(cause['valid_edit_emission_ns'].values())
        paths=[ROOT/p for p in subprocess.check_output(['git','ls-files','crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],cwd=ROOT,text=True).splitlines()]
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]
        paths += [Path(focus.__file__),ROOT/'scripts/compare_saved_runtime.py',ROOT/'scripts/workflow_io.py']
        for p in paths:bind(p)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);write(raw/'input.json',dict(artifacts=artifacts,attempts=attempts));write(raw/'records.json',[])
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=3,input_sha256=sha(raw/'input.json'),
            target=str(target),allocated_target_bytes=allocated,required_free_bytes=needed,
            original_project_guest_commands=0,executable_code_publications=0,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1',
            RUST_INTERP_IMMEDIATE_CENSUS_INPUT=str(raw/'input.json'),RUST_INTERP_IMMEDIATE_CENSUS_OUTPUT=str(raw/'report.json'))
        records=[]
        for label,extra,select,expected in [
            ('debug',[],['jit::relocatable_immediate_census::','--','--skip','census_saved_parser_immediate_shapes'],5),
            ('release',['--release'],['jit::relocatable_immediate_census::','--','--skip','census_saved_parser_immediate_shapes'],5),
            ('census',['--release'],['jit::relocatable_immediate_census::census_saved_parser_immediate_shapes','--','--ignored','--exact'],1)]:
            require_space(ROOT,8);assert shutil.disk_usage(ROOT).free>=needed
            command=['cargo','+nightly-2026-09-08','test',*extra,'--locked','--offline','--jobs','2','--manifest-path',str(ROOT/'Cargo.toml'),
                '--target-dir',str(target),'-p','rust-interp-bytecode','--lib',*select]
            start=time.time();child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(label=label))
            for stream,value in [('stdout',out),('stderr',err)]:(raw/(label+'.'+stream)).write_text(value)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-start,
                stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr'))));write(raw/'records.json',records)
            assert child.returncode==0 and f'test result: ok. {expected} passed; 0 failed; 0 ignored;' in out,(out+err)[-6000:]
            assert all(sha(ROOT/p)==h for p,h in frozen.items());print(label,'passed',flush=True)
        report=read(raw/'report.json');assert report['input_sha256']==sha(raw/'input.json')
        assert report['guest_commands']==report['executable_code_publications']==0 and report['cache_admission'] is False
        assert [r['attempt'] for r in report['rows']]==attempts
        counts=Counter();nanos=Counter();matches=[]
        for row in report['rows']:
            k=row['category'];assert k in ['first_worker_function','unchanged_body','eligible_immediate_shape_match','not_matched']
            counts[k]+=1;nanos[k]+=row['attempt']['emission_ns']
            if k=='eligible_immediate_shape_match':
                assert row['current']['shape']==row['previous']['shape'] and row['current']['exact']!=row['previous']['exact']
                matches.append(row)
        output=ROOT/'results'/RUN;output.mkdir(exist_ok=False)
        write(output/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),commands=3,controls_per_profile=5,
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),
            outputs={str((raw/n).relative_to(ROOT)):sha(raw/n) for n in ['input.json','report.json']},
            counts=dict(counts),emission_ns=dict(nanos),most_expensive_shape_matches=sorted(matches,key=lambda r:r['attempt']['emission_ns'],reverse=True)[:30],
            original_project_guest_commands=0,executable_code_publications=0,cache_admission=False,performance_measurement=False,scope=report['scope']))
        print(json.dumps(dict(counts=counts,emission_ms={k:v/1e6 for k,v in nanos.items()})),flush=True)
if __name__=='__main__':
    if sys.argv[1:]==['--close']:focus.RUN=RUN;focus.close()
    else:assert len(sys.argv)==1;main()
