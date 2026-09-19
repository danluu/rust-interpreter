"""Actual saved parser edits through two owned production session processes."""
import json,os,shutil,struct,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
RUN='cross-program-template-session-parser-01'
def read(p):return json.loads(p.read_text())

def frame(child,value):
    data=json.dumps(value,separators=(',',':')).encode();assert len(data)<=4*1024**2
    child.stdin.write(struct.pack('<I',len(data))+data);child.stdin.flush()
def receive(child,wire):
    def exact(n):
        data=bytearray()
        while len(data)<n:
            part=child.stdout.read(n-len(data))
            if not part:raise RuntimeError('session closed before its complete response')
            data.extend(part);wire.write(part)
        return bytes(data)
    n,=struct.unpack('<I',exact(4));assert 0<n<=4*1024**2
    return json.loads(exact(n))

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        frozen={}
        def bind(path,digest=None):
            h=sha(path)
            if digest is not None:assert h==digest,path
            frozen[str(path.relative_to(ROOT))]=h
            return read(path) if path.suffix=='.json' else h
        def closed(run):
            folder=ROOT/'results'/run;c=bind(folder/'closure.json');assert c['status']=='closed' and c['all_hashes_verified']
            bind(folder/'terminal.json',c['terminal_sha256']);return bind(folder/'summary.json',c['summary_sha256'])
        transport=closed('cross-program-template-session-transport-02')
        assert transport['status']=='passed' and transport['owned_session_processes']==8
        plan=bind(ROOT/transport['raw']/'plan.json',transport['plan_sha256'])
        for p,h in plan['frozen'].items():
            if p.startswith('crates/') or p in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:bind(ROOT/p,h)
        binary=ROOT/transport['raw']/'release-rust-interp-template-session'
        bind(binary,transport['outputs'][str(binary.relative_to(ROOT))])
        suites=closed('cross-program-template-suites-01');assert suites['status']=='passed' and suites['test_invocations']==1824
        input_path=ROOT/suites['raw']/'input.json';saved=bind(input_path,suites['outputs'][str(input_path.relative_to(ROOT))])
        cases=saved['cases'];assert [c['state'] for c in cases]==[0,-1,1,2,3,4,5,0]
        for case in cases:
            assert len(case['expected'])==114
            bind(Path(case['artifact_path']),case['artifact_sha256']);bind(Path(case['catalog_path']),case['catalog_sha256'])
        for p in [*(p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']),Path(focus.__file__),
            ROOT/'scripts/compare_saved_runtime.py',ROOT/'scripts/workflow_io.py']:bind(p)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        # Only an environment digest is retained. Values travel in the owned
        # inherited pipe and must never be written to captures or receipts.
        pairs=[[list(k),list(v)] for k,v in os.environb.items()]
        import hashlib
        environment_sha=hashlib.sha256(json.dumps(pairs,separators=(',',':')).encode()).hexdigest()
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],required_free_bytes=12*1024**3,minimum_child_gib=8,
            expected_commands=2,original_project_guest_commands=2,suite_executions=16,test_invocations=1824,
            environment_sha256=environment_sha,verify_every_hit=True,performance_measurement=False,default_runtime_adoption=False))
        records=[];comparisons=[];outputs={};reference={};hits=0;write(raw/'records.json',records)
        for mode,capacity in [('fresh',0),('cached',64*1024**2)]:
            require_space(ROOT,8);folder=raw/mode;folder.mkdir();command=[str(binary),'--serve-stdio','--history-bytes',str(capacity),'--verify-hits']
            child=None;error=None;ready=None;responses=[];closed_response=None;started=time.time();record_outputs={}
            with (raw/(mode+'.stderr')).open('xb') as stderr,(raw/(mode+'.stdout')).open('xb') as wire:
                try:
                    child=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=stderr)
                    identity=subprocess.check_output(['ps','-p',str(child.pid),'-o','pid,ppid,lstart,tty,command'],text=True)
                    write(raw/'active.json',dict(label=mode,pid=child.pid,parent_pid=os.getpid(),identity=identity,
                        command=command,cwd=str(ROOT),started_at=started,status='running'))
                    ready=receive(child,wire);assert ready['kind']=='ready' and ready['schema']==1 and ready['pid']==child.pid
                    assert ready['executable_sha256']==sha(binary) and ready['workers']==2
                    assert ready['history_bytes_per_worker']==capacity and ready['verify_hits'] is True
                    write(folder/'ready.json',ready);record_outputs[str((folder/'ready.json').relative_to(ROOT))]=sha(folder/'ready.json')
                    previous=ready['cpu_at_ready']
                    for ordinal,case in enumerate(cases):
                        require_space(ROOT,8);report_path=folder/(str(ordinal)+'.report.json')
                        body=dict(command='run',artifact=dict(path=case['artifact_path'],sha256=case['artifact_sha256']),
                            catalog=dict(path=case['catalog_path'],sha256=case['catalog_sha256']),report=str(report_path),cwd=str(ROOT),
                            environment=pairs,budget=dict(instructions=100_000_000_000,allocations=150000,memory_bytes=64*1024**2,
                                frames=4096,code_bytes=16*1024**2,persistent_registers=True,scalar_calls=True))
                        frame(child,dict(schema=1,id=ordinal+1,body=body));response=receive(child,wire);responses.append(response)
                        response_path=folder/(str(ordinal)+'.response.json');write(response_path,response)
                        record_outputs[str(response_path.relative_to(ROOT))]=sha(response_path)
                        assert response['kind']=='result' and response['id']==ordinal+1 and response['poisoned'] is False,response
                        assert response['report']==str(report_path) and response['report_sha256']==sha(report_path)
                        record_outputs[str(report_path.relative_to(ROOT))]=sha(report_path)
                        for field in ['user_us','system_us']:
                            assert previous[field]<=response['cpu_before'][field]<=response['cpu_after'][field]
                        previous=response['cpu_after'];report=read(report_path)
                        assert report['selected']==report['completed']==114 and report['request_id']==ordinal+1
                        assert report['artifact_sha256']==case['artifact_sha256'] and report['catalog_sha256']==case['catalog_sha256']
                        assert report['runtime_limits']==dict(instructions=100_000_000_000,allocations=150000,memory_bytes=64*1024**2,frames=4096)
                        assert report['jit_code_limit_bytes']==16*1024**2 and report['workers']==2 and report['poisoned'] is False
                        tests=report['tests'];assert len(tests)==114 and [t['index'] for t in tests]==list(range(114))
                        assert sorted((t['name'],t['status']) for t in tests)==sorted(map(tuple,case['expected']))
                        failures={t['name']:t['error'] for t in tests if t['status']=='failed'}
                        assert response['status']==report['status']==('failed' if failures else 'passed')
                        if mode=='fresh':reference[ordinal]=failures
                        else:assert failures==reference[ordinal]
                        workers=report['worker_records'];assert len(workers)==2 and {w['worker'] for w in workers}=={0,1}
                        for w in workers:
                            assert w['status']=='completed' and w['poisoned'] is False
                            if mode=='fresh':assert w['templates'] is w['storage'] is None
                            else:
                                assert w['templates']['hits']==w['templates']['verified_hits'];hits+=w['templates']['hits']
                                assert w['storage']['charged_bytes']<=capacity and w['storage']['entries']<=16384
                            assert all(t.get('jit_bytes',0)<=16*1024**2 for t in w['tests'])
                        comparisons.append(dict(mode=mode,ordinal=ordinal,state=case['state'],passed=report['passed'],failed=report['failed'],
                            workers=[{k:v for k,v in w.items() if k!='tests'} for w in workers]))
                        print(mode,ordinal,case['state'],'matched',flush=True)
                    frame(child,dict(schema=1,id=9,body=dict(command='shutdown')));closed_response=receive(child,wire)
                    assert closed_response['kind']=='closed' and closed_response['requests_consumed']==9
                    write(folder/'closed.json',closed_response);record_outputs[str((folder/'closed.json').relative_to(ROOT))]=sha(folder/'closed.json')
                except BaseException as exc:
                    error=repr(exc)[:6000]
                finally:
                    if child is not None:
                        if child.stdin is not None:child.stdin.close()
                        # EOF is the normal stop contract. Drain and reap this
                        # exact owned process even if later bookkeeping fails.
                        tail=child.stdout.read();wire.write(tail);wire.flush();stderr.flush()
                        pid,status,usage=os.wait4(child.pid,0);assert pid==child.pid
                        child.returncode=os.waitstatus_to_exitcode(status)
                        record=dict(label=mode,command=command,pid=pid,returncode=child.returncode,seconds=time.time()-started,
                            kernel_cpu=dict(user_seconds=usage.ru_utime,system_seconds=usage.ru_stime),
                            stdout_sha256=sha(raw/(mode+'.stdout')),stderr_sha256=sha(raw/(mode+'.stderr')),
                            completed_responses=len(responses),outputs=record_outputs,error=error)
                        records.append(record);write(raw/'records.json',records)
            assert error is None,error
            assert child.returncode==0 and tail==b''
            for field,kernel in [('user_us',usage.ru_utime),('system_us',usage.ru_stime)]:
                assert previous[field]<=closed_response['cpu_at_close'][field]<=kernel*1_000_000+1000
            assert sum(closed_response['cpu_at_close'].values())>sum(ready['cpu_at_ready'].values())
            outputs.update(record_outputs)
        assert len(comparisons)==16 and hits>0 and all(sha(ROOT/p)==h for p,h in frozen.items())
        output=ROOT/'results'/RUN;output.mkdir(exist_ok=False)
        write(output/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),commands=2,
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),outputs=outputs,comparisons=comparisons,
            suite_executions=16,test_invocations=1824,verified_cache_hits=hits,original_project_guest_commands=2,
            kernel_cpu_reconciled=True,performance_measurement=False,default_runtime_adoption=False,
            scope='Saved checked artifact suites through the production session binary; verifier re-emits every hit. No source-build or speedup measurement.'))

if __name__=='__main__':
    if sys.argv[1:]==['--close']:
        focus.RUN=RUN;focus.close()
    else:
        assert len(sys.argv)==1
        main()
