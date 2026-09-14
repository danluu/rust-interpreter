"""Inspect qualified bridge native costs without another timing comparison."""
from pathlib import Path
import json,os,sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import sha,acquire_lock
from workflow_io import capture,require_space,write_json as write

def main():
    run='tree-bridge-native-sampling-01';directory=Path(__file__).parent
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        build_path=ROOT/'results/tree-shared-cursor-build-01/summary.json'
        profile_path=ROOT/'results/tree-shared-cursor-profile-01/summary.json'
        closure_path=ROOT/'results/tree-shared-cursor-screen-token-01/closure.json'
        controls_path=ROOT/'results/tree-bridge-native-sampling-controls-01/summary.json'
        build,profile,closure,controls=[json.loads(p.read_text()) for p in [build_path,profile_path,closure_path,controls_path]]
        assert all(p['status']=='passed' for p in [build,profile,closure,controls])
        assert closure['parked'] and controls['tests']==7 and controls['guest_commands']==0
        assert profile['exact_logical_per_pc_counts'] and profile['exact_backend_accounting']
        assert build['binaries']['rust-interp-vm']==profile['vm_sha256']=='2c20261d1eedbaae115ab102a0ef076e0bc43560e773d78e2a9d1b7a07216697'
        key=build['tool_key'];tool=ROOT/'.work/interpreter-tools'/key
        assert all(sha(tool/name)==h for name,h in build['binaries'].items())
        source=ROOT/build['source_manifest'];assert sha(source)==build['source_manifest_sha256']
        assert all(sha(ROOT/p)==h for p,h in json.loads(source.read_text())['frozen'].items())
        cwork=ROOT/controls['raw'];assert sha(cwork/'plan.json')==controls['plan_sha256'] and sha(cwork/'record.json')==controls['record_sha256']
        assert all(sha(ROOT/p)==h for p,h in json.loads((cwork/'plan.json').read_text())['frozen'].items())
        artifact=ROOT/'.work/call-capacity-credit-edit-token-02/artifacts/caa66fcf85d85196264fd2fc5b024918f36a9fccc8237d79af7987182796b1d9.rbc'
        catalog=artifact.with_name('490789b82f653196fba00fdb290821edaae0ddc6b152aaf84f93bc815077a794.json')
        assert sha(artifact)==artifact.stem and sha(catalog)==catalog.stem
        paths=list(directory.glob('*.py'))+[directory/'PLAN.md',build_path,profile_path,closure_path,controls_path,source,cwork/'plan.json',cwork/'record.json',artifact,catalog]
        paths += [tool/name for name in build['binaries']]
        paths += [ROOT/'scripts'/n for n in ['compare_saved_runtime.py','workflow_io.py','interpreter.py']]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,guest_executions=2,commands=6,
            performance_measurement=False,tool_key=key,minimum_free_gib=8,ordinary_entropy=True))
    env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_'))}
    assert not any(k.startswith('DYLD_') for k in env)
    env['PYTHONDONTWRITEBYTECODE']='1';records=[]
    for index,label in enumerate(['block','exhaustive']):
        name='tree-bridge-native-sample-'+label+'-01'
        commands=[[str(directory/'sample_owned_vm.py'),'--tool-key',key,'--artifact',str(artifact),
            '--artifact-sha256',sha(artifact),'--run-id',name,'--repetitions','1','--duration','3',
            '--instruction-limit','100000000000','--allocation-limit','150000','--jit-persistent-registers',
            '--jit-resumable-calls','--jit-tree-bridge','--dump-code',
            '--select-test',profile['comparisons'][index]['name'],'--suite-catalog',str(catalog),
            '--lock-wait-seconds','45','--minimum-free-bytes',str(8*1024**3)],
            [str(directory/'summarize_owned_sample.py'),'--run-id',name],
            [str(directory/'attribute_generated_sample.py'),'--run-id',name]]
        for stage,command in enumerate(commands):
            require_space(ROOT,8)
            lock=None
            if stage:
                lock=(ROOT/'.work/benchmark.lock').open('a');acquire_lock(lock,45)
            try:
                assert all(sha(ROOT/p)==h for p,h in frozen.items())
                child,out,err=capture([sys.executable,*command],cwd=ROOT,env=env,
                    receipt_path=work/'active.json',receipt=dict(case=label,stage=stage))
                records.append(dict(case=label,stage=stage,pid=child.pid,command=command,
                    returncode=child.returncode,stdout=out,stderr=err));write(work/'records.json',records)
                assert child.returncode==0,(out+err)[-4000:]
            finally:
                if lock:lock.close()
            print(label,stage,'PASS',flush=True)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/run;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',guest_executions=2,commands=6,tool_key=key,
            vm_sha256=profile['vm_sha256'],performance_measurement=False,raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json')))

if __name__=='__main__':main()
