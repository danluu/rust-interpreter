"""Replay real checked parser edits through separate VM commands and owned sessions."""
import json,os,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from workflow_measurements import child_usage,child_cpu_since
from template_session_receipt import read_receipt
from interpreter import installed_tools
sys.path.insert(0,str(ROOT/'benchmarks/experiments/cross-program-template-session'))
from parser import receive
RUN='session-runtime-composition-parser-replay-01'
def read(p):return json.loads(p.read_text())

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12);frozen={}
        def bind(path,digest=None):
            h=sha(path)
            if digest is not None:assert h==digest,path
            frozen[str(path.relative_to(ROOT))]=h
            return read(path) if path.suffix=='.json' else h
        def closed(run):
            folder=ROOT/'results'/run;c=bind(folder/'closure.json');assert c['status']=='closed' and c['all_hashes_verified']
            bind(folder/'terminal.json',c['terminal_sha256']);return bind(folder/'summary.json',c['summary_sha256'])
        qualification=closed('session-runtime-composition-qualification-02');assert qualification['duration_order'] is True and qualification['shared_literal_keys'] is False
        assert qualification['parameterized_literals'] is True and qualification['buffered_template_keys'] is False
        assert qualification['template_key_domain']=='cross-program-staging-literals-v3' and qualification['artifact_digest_reuse'] is True
        assert qualification['status']=='passed' and qualification['large_function_interpreter_threshold']==65536
        assert qualification['tests']['debug']==qualification['tests']['release'] and qualification['tests']['release']['passed']>=679
        assert qualification['indirect_calls_supported'] is True and qualification['readonly_scalar_leaves'] is True and qualification['successor_only_spills'] is True
        assert qualification['tests']['python']==dict(discovered=468,passed=446,skipped=22)
        plan=bind(ROOT/qualification['raw']/'plan.json',qualification['plan_sha256'])
        for p,h in plan['frozen'].items():
            if p.startswith(('crates/','scripts/','tests/')) or p in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:bind(ROOT/p,h)
        for p,h in qualification['outputs'].items():bind(ROOT/p,h)
        vm=ROOT/qualification['raw']/'release-rust-interp-vm'
        server=ROOT/qualification['raw']/'release-rust-interp-template-session'
        bind(ROOT/'benchmarks/experiments/cross-program-template-session/parser.py')
        suites=closed('cross-program-template-suites-01');assert suites['status']=='passed' and suites['test_invocations']==1824
        input_path=ROOT/suites['raw']/'input.json';saved=bind(input_path,suites['outputs'][str(input_path.relative_to(ROOT))]);cases=saved['cases']
        assert [c['state'] for c in cases]==[0,-1,1,2,3,4,5,0]
        for case in cases:
            assert len(case['expected'])==114
            bind(Path(case['artifact_path']),case['artifact_sha256']);bind(Path(case['catalog_path']),case['catalog_sha256'])
        for p in [*(p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']),Path(focus.__file__)]:bind(p)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],required_free_bytes=12*1024**3,minimum_child_gib=8,
            expected_commands=2,original_project_guest_commands=16,suite_executions=16,test_invocations=1824,
            verify_every_hit=True,large_function_interpreter_threshold=65536,diagnostic_feature=False,performance_measurement=False,default_runtime_adoption=False))
        records=[];comparisons=[];outputs={};reference={};hits=0;write(raw/'records.json',records)
        for mode,capacity in [('fresh',0),('cached',64*1024**2)]:
            require_space(ROOT,8);folder=raw/mode;folder.mkdir();endpoint=ROOT/'.work/ts'/('composition-parser-01-'+mode)
            command=[str(server),'--serve-socket',str(endpoint),'--history-bytes',str(capacity),'--verify-hits']
            child=None;error=None;ready=None;closed_response=None;started=time.time();record_outputs={};clients=[]
            def retain(p):record_outputs[str(p.relative_to(ROOT))]=sha(p)
            with (raw/(mode+'.stderr')).open('xb') as stderr,(raw/(mode+'.stdout')).open('xb') as wire:
                try:
                    child=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=stderr)
                    identity=subprocess.check_output(['ps','-p',str(child.pid),'-o','pid,ppid,lstart,tty,command'],text=True)
                    write(folder/'server.json',dict(pid=child.pid,parent_pid=os.getpid(),identity=identity,command=command,cwd=str(ROOT),started_at=started));retain(folder/'server.json')
                    ready=receive(child,wire);assert ready['kind']=='ready' and ready['pid']==child.pid and ready['executable_sha256']==sha(server)
                    assert ready['indirect_calls'] is True and ready['duration_order'] is True and ready['shared_literal_keys'] is False
                    assert ready['parameterized_literals'] is True and ready['buffered_template_keys'] is False
                    assert ready['large_function_interpreter_threshold']==65536 and ready['artifact_digest_reuse'] is True
                    assert ready['workers']==2 and ready['history_bytes_per_worker']==capacity and ready['verify_hits'] is True
                    write(folder/'ready.json',ready);retain(folder/'ready.json');retain(endpoint/'ready.json');previous=ready['cpu_at_ready']
                    for ordinal,case in enumerate(cases):
                        require_space(ROOT,8);report_path=folder/(str(ordinal)+'.report.json');success=case['state']!=-1
                        invocation=[str(vm),'--jit-template-session',str(endpoint/'ready.json'),'--engine','jit',
                            '--jit-resumable-calls','--jit-persistent-registers','--jit-scalar-calls','--jit-indirect-calls','--isolated-batch','prepared',
                            '--suite-workers','2','--suite-catalog',case['catalog_path'],'--suite-report',str(report_path),
                            '--instruction-limit','100000000000','--allocation-limit','150000',case['artifact_path']]
                        usage_before=child_usage();start=time.perf_counter()
                        client,out,err=capture(invocation,cwd=ROOT,env=os.environ.copy(),receipt_path=folder/'active-client.json',receipt=dict(ordinal=ordinal))
                        elapsed=time.perf_counter()-start;usage_client=child_cpu_since(usage_before)
                        for stream,value in [('stdout',out),('stderr',err)]:
                            p=folder/(str(ordinal)+'.'+stream);p.write_text(value);retain(p)
                        for p in [report_path,Path(str(report_path)+'.session.json')]:
                            if p.is_file():retain(p)
                        clients.append(dict(ordinal=ordinal,state=case['state'],command=invocation,pid=client.pid,returncode=client.returncode,
                            wall_seconds=elapsed,waited_client_cpu=usage_client))
                        write(folder/'clients.json',clients);retain(folder/'clients.json')
                        assert client.returncode==(0 if success else 1),(out+err)[-4096:]
                        receipt=read_receipt(endpoint/'ready.json',report_path,Path(case['artifact_path']),Path(case['catalog_path']),client.returncode,
                            expected_jit_options=dict(persistent_registers=True,scalar_calls=True,indirect_calls=True))
                        assert receipt['status']=='completed' and receipt['server_pid']==child.pid and receipt['request_id']==ordinal+1
                        assert receipt['server_executable_sha256']==sha(server)
                        response=receipt['response'];report=read(report_path)
                        for field in ['user_us','system_us']:
                            assert previous[field]<=response['cpu_before'][field]<=response['cpu_after'][field]
                        previous=response['cpu_after']
                        assert report['selected']==report['completed']==114 and report['request_id']==ordinal+1
                        assert report['runtime_limits']==dict(instructions=100_000_000_000,allocations=150000,memory_bytes=64*1024**2,frames=4096)
                        assert report['jit_code_limit_bytes']==16*1024**2 and report['workers']==2 and report['poisoned'] is False
                        tests=report['tests'];assert [t['index'] for t in tests]==list(range(114))
                        assert sorted((t['name'],t['status']) for t in tests)==sorted(map(tuple,case['expected']))
                        failures={t['name']:t['error'] for t in tests if t['status']=='failed'}
                        if mode=='fresh':reference[ordinal]=failures
                        else:assert failures==reference[ordinal]
                        workers=report['worker_records'];assert len(workers)==2 and {w['worker'] for w in workers}=={0,1}
                        for w in workers:
                            assert 'preparation_observer' not in w
                            assert w['status']=='completed' and w['poisoned'] is False
                            if mode=='fresh':assert w['templates'] is w['storage'] is None
                            else:
                                assert w['templates']['hits']==w['templates']['verified_hits'];hits+=w['templates']['hits']
                                assert w['storage']['charged_bytes']<=capacity and w['storage']['entries']<=16384
                            assert all(t.get('jit_bytes',0)<=16*1024**2 for t in w['tests'])
                        comparisons.append(dict(mode=mode,ordinal=ordinal,state=case['state'],passed=report['passed'],failed=report['failed'],
                            workers=[{k:v for k,v in w.items() if k!='tests'} for w in workers]))
                        print(mode,ordinal,case['state'],'matched',flush=True)
                    child.stdin.close();closed_response=receive(child,wire)
                    assert closed_response['kind']=='closed' and closed_response['reason']=='owner_eof' and closed_response['requests_consumed']==8
                    write(folder/'closed.json',closed_response);retain(folder/'closed.json')
                except BaseException as exc:error=repr(exc)[:6000]
                finally:
                    if child is not None:
                        if child.stdin is not None:child.stdin.close()
                        tail=child.stdout.read();wire.write(tail);wire.flush();stderr.flush()
                        pid,status,usage=os.wait4(child.pid,0);assert pid==child.pid;child.returncode=os.waitstatus_to_exitcode(status)
                        records.append(dict(label=mode,command=command,pid=pid,returncode=child.returncode,seconds=time.time()-started,
                            kernel_cpu=dict(user_seconds=usage.ru_utime,system_seconds=usage.ru_stime),
                            stdout_sha256=sha(raw/(mode+'.stdout')),stderr_sha256=sha(raw/(mode+'.stderr')),
                            completed_clients=len(clients),outputs=record_outputs,error=error));write(raw/'records.json',records)
            assert error is None,error
            assert child.returncode==0 and tail==b''
            for field,kernel in [('user_us',usage.ru_utime),('system_us',usage.ru_stime)]:
                assert previous[field]<=closed_response['cpu_at_close'][field]<=kernel*1_000_000+1000
            outputs.update(record_outputs)
        assert len(comparisons)==16 and hits>0 and all(sha(ROOT/p)==h for p,h in frozen.items())
        output=ROOT/'results'/RUN;output.mkdir(exist_ok=False)
        write(output/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),commands=2,
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),outputs=outputs,comparisons=comparisons,
            suite_executions=16,test_invocations=1824,verified_cache_hits=hits,original_project_guest_commands=16,
            kernel_cpu_reconciled=True,indirect_calls=True,readonly_scalar_leaves=True,successor_only_spills=True,duration_order=True,shared_literal_keys=False,parameterized_literals=True,buffered_template_keys=False,artifact_digest_reuse=True,large_function_interpreter_threshold=65536,diagnostic_feature=False,performance_measurement=False,default_runtime_adoption=False,
            scope='Saved checked parser suites through separate VM clients and owned sessions; verifier re-emits every hit. No source-build or speedup measurement.'))

if __name__=='__main__':
    if sys.argv[1:]==['--close']:
        focus.RUN=RUN;focus.close()
    else:
        assert len(sys.argv)==1
        main()
