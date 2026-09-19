"""Actual saved parser suites, two prepared workers, exact verification on every cache hit."""
import json,os,shutil,subprocess,sys,time
from pathlib import Path
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='cross-program-template-suites-01'
def read(p):return json.loads(p.read_text())

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated);assert shutil.disk_usage(ROOT).free>=needed
        frozen={}
        def bind(p,digest=None):
            h=sha(p)
            if digest is not None:assert h==digest,p
            frozen[str(p.relative_to(ROOT))]=h
            return read(p) if p.suffix=='.json' else h
        def closed(run):
            folder=ROOT/'results'/run;c=bind(folder/'closure.json')
            assert c['status']=='closed' and c['all_hashes_verified']
            bind(folder/'terminal.json',c['terminal_sha256'])
            return bind(folder/'summary.json',c['summary_sha256'])
        workspace=closed('cross-program-template-workspace-01')
        assert workspace['status']=='passed' and all(x==dict(passed=628,ignored=15) for x in workspace['tests'].values())
        model=closed('cross-program-template-model-09');assert model['status']=='passed' and model['tests_per_profile']==20
        model_plan=bind(ROOT/model['raw']/'plan.json',model['plan_sha256'])
        for p,h in model_plan['frozen'].items():
            if p.startswith('crates/') or p in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:bind(ROOT/p,h)
        old=closed('emitter-register-workspace-parser-screen-incremental-01')
        assert old['commands']==32 and old['source_restored'] and old['candidate_control_artifacts_match']
        old_raw=ROOT/old['raw'];bind(old_raw/'plan.json',old['plan_sha256']);records=bind(old_raw/'records.json',old['records_sha256'])
        baseline=[r for r in records if r['mode']=='baseline'];assert [(r['cycle'],r['state']) for r in baseline]==[(0,s) for s in [0,-1,1,2,3,4,5]]+[(1,0)]
        cases=[]
        for row in baseline:
            native,=[r for r in records if r['cycle']==row['cycle'] and r['state']==row['state'] and r['mode']=='native']
            assert row['outcomes']==native['outcomes'] and len(row['outcomes'])==114
            assert row['returncode']==(1 if row['state']==-1 else 0) and row['launch']['borrowck_cache']=='off'
            a=row['artifact'];c=row['entry_catalog'];bind(ROOT/a['path'],a['sha256']);catalog=bind(ROOT/c['path'],c['sha256'])
            assert {e['name'] for e in catalog['entries']}=={n for n,_ in row['outcomes']}
            assert row['launch']['runtime_limits']==dict(allocations=150000,frames=4096,instructions=100000000000,memory_bytes=67108864)
            cases.append(dict(state=row['state'],artifact_path=str(ROOT/a['path']),artifact_sha256=a['sha256'],
                catalog_path=str(ROOT/c['path']),catalog_sha256=c['sha256'],expected=row['outcomes']))
        for p in Path(__file__).parent.iterdir():
            if p.suffix in ['.py','.md']:bind(p)
        for name in ['compare_saved_runtime.py','workflow_io.py']:bind(ROOT/'scripts'/name)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);write(raw/'input.json',dict(cases=cases,disk_path=str(ROOT)))
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],target=str(target.relative_to(ROOT)),
            required_free_bytes=needed,allocated_target_bytes=allocated,minimum_child_gib=8,expected_commands=1,
            input_sha256=sha(raw/'input.json'),original_project_guest_commands=1,planned_suite_executions=16,
            planned_test_invocations=1824,executable_code_publication=True,verify_every_hit=True,
            performance_measurement=False,production_runtime_changes=0))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1',
            RUST_INTERP_TEMPLATE_SUITES_INPUT=str(raw/'input.json'),RUST_INTERP_TEMPLATE_SUITES_OUTPUT=str(raw/'report.json'))
        command=['cargo','+nightly-2026-09-08','test','--release','--locked','--offline','--jobs','2',
            '--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target),'-p','rust-interp-bytecode',
            '--lib','jit::cross_program_templates::suites::cross_program_template_execute_saved_parser_suites','--','--ignored','--exact']
        require_space(ROOT,8);assert shutil.disk_usage(ROOT).free>=needed;write(raw/'records.json',[])
        start=time.time();child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(label='suites'))
        (raw/'suites.stdout').write_text(out);(raw/'suites.stderr').write_text(err)
        write(raw/'records.json',[dict(label='suites',command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-start,
            stdout_sha256=sha(raw/'suites.stdout'),stderr_sha256=sha(raw/'suites.stderr'))])
        assert child.returncode==0 and 'test result: ok. 1 passed; 0 failed; 0 ignored;' in out,(out+err)[-6000:]
        report=read(raw/'report.json');assert report['schema_version']==1 and report['input_sha256']==sha(raw/'input.json')
        assert report['status']=='passed' and report['workers']==2 and report['recorded_test_invocations']==1824
        assert report['verify_every_cache_hit'] is True and report['production_cache_admission'] is False
        rows=report['records'];journal=[json.loads(line) for line in (raw/'report.jsonl').read_text().splitlines()]
        key=lambda r:(r['mode'],r['ordinal'],r['worker'])
        assert len(rows)==len(journal)==32 and sorted(rows,key=key)==sorted(journal,key=key)
        assert {key(r) for r in rows}=={(mode,i,w) for mode in ['fresh','cached'] for i in range(8) for w in range(2)}
        summaries=[];hits=0;errors={}
        for mode in ['fresh','cached']:
            for ordinal,case in enumerate(cases):
                workers=[r for r in rows if r['mode']==mode and r['ordinal']==ordinal]
                outcomes=[]
                for row in workers:
                    assert row['status']=='passed' and row['state']==case['state'] and row['artifact_sha256']==case['artifact_sha256']
                    assert row['code_bytes']<=16*1024**2 and row['history_charge']<=64*1024**2 and row['history_entries']<=16384
                    if mode=='cached':
                        assert row['cache']['hits']==row['cache']['verified_hits'];hits+=row['cache']['hits']
                    else:assert row['cache'] is None and row['history_entries']==0
                    outcomes.extend(row['outcomes'])
                assert len(outcomes)==114 and {r['index'] for r in outcomes}==set(range(114))
                assert sorted((r['name'],r['status']) for r in outcomes)==sorted(map(tuple,case['expected']))
                failures={r['name']:r['error'] for r in outcomes if r['status']=='failed'}
                if mode=='fresh':errors[ordinal]=failures
                else:assert failures==errors[ordinal]
                summaries.append(dict(mode=mode,ordinal=ordinal,state=case['state'],tests=114,
                    passed=sum(r['status']=='passed' for r in outcomes),failed=sum(r['status']=='failed' for r in outcomes),
                    workers=[{k:v for k,v in r.items() if k!='outcomes'} for r in sorted(workers,key=lambda r:r['worker'])]))
        assert hits>0 and all(sha(ROOT/p)==h for p,h in frozen.items())
        output=ROOT/'results'/RUN;output.mkdir(exist_ok=False)
        write(output/'summary.json',dict(status='passed',source_revision=revision,commands=1,comparisons=summaries,
            raw=str(raw.relative_to(ROOT)),plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),
            outputs={str(p.relative_to(ROOT)):sha(p) for p in [raw/'input.json',raw/'report.json',raw/'report.jsonl']},
            original_project_guest_commands=1,suite_executions=16,test_invocations=1824,verified_cache_hits=hits,
            executable_code_publications=True,performance_measurement=False,production_cache_admission=False,scope=report['scope']))
        print('passed16 suites/1824 test invocations; verified cache hits',hits,flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['--close']:
        focus.RUN=RUN;focus.close()
    else:
        assert len(sys.argv)==1
        main()
