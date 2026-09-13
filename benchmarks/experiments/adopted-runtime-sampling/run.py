"""Capture two current owned native-PC samples with exact operation attribution."""
from pathlib import Path
import json
import os
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import sha,acquire_lock
from workflow_io import capture,require_space,write_json as write


def main():
    run='adopted-runtime-sampling-01'
    proof_path=ROOT/'results/guarded-local-facts-main-final-audit-01/summary.json'
    profile_path=ROOT/'results/guarded-local-facts-profile-01/summary.json'
    proof,profile=[json.loads(p.read_text()) for p in [proof_path,profile_path]]
    assert proof['status']==profile['status']=='passed' and proof['all_frozen_inputs_verified']
    assert profile['exact_operation_map_reconstruction'] and profile['exact_per_pc_counts']
    assert proof['binaries']['rust-interp-vm']==profile['vm_sha256']
    key=proof['tool_key'];tool=ROOT/'.work/interpreter-tools'/key
    assert all(sha(tool/name)==h for name,h in proof['binaries'].items())
    artifact=ROOT/'.work/call-capacity-credit-edit-token-02/artifacts/caa66fcf85d85196264fd2fc5b024918f36a9fccc8237d79af7987182796b1d9.rbc'
    catalog=artifact.with_name('490789b82f653196fba00fdb290821edaae0ddc6b152aaf84f93bc815077a794.json')
    assert sha(artifact)==artifact.stem and sha(catalog)==catalog.stem
    paths=[Path(__file__),Path(__file__).with_name('PLAN.md'),Path(__file__).with_name('attribute_current.py'),
           proof_path,profile_path,artifact,catalog]
    paths += [tool/name for name in proof['binaries']]
    paths += [ROOT/'scripts'/n for n in ['sample_owned_vm.py','summarize_owned_sample.py',
        'attribute_generated_sample.py','compare_saved_runtime.py','workflow_io.py','interpreter.py']]
    paths += [ROOT/'benchmarks/experiments/operation-map'/n for n in ['attribute.py','maps.py']]
    frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
    require_space(ROOT,12)
    work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
    write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,guest_executions=2,commands=6,
        performance_measurement=False,tool_key=key,minimum_free_gib=8,ordinary_entropy=True))
    env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_'))}
    assert not any(k.startswith('DYLD_') for k in env)
    env['PYTHONDONTWRITEBYTECODE']='1'
    records=[]
    for index,label in enumerate(['block','exhaustive']):
        name='adopted-runtime-sample-'+label+'-01'
        commands=[['scripts/sample_owned_vm.py','--tool-key',key,'--artifact',str(artifact),
            '--artifact-sha256',sha(artifact),'--run-id',name,'--repetitions','1','--duration','3',
            '--instruction-limit','100000000000','--allocation-limit','150000','--jit-persistent-registers',
            '--jit-resumable-calls','--dump-code','--jit-operation-map',
            '--select-test',profile['comparisons'][index]['name'],'--suite-catalog',str(catalog),
            '--lock-wait-seconds','45','--minimum-free-bytes',str(8*1024**3)],
            ['scripts/summarize_owned_sample.py','--run-id',name],
            [str(Path(__file__).with_name('attribute_current.py')),'--case',label,'--run-id',name]]
        for stage,command in enumerate(commands):
            assert all(sha(ROOT/p)==h for p,h in frozen.items())
            require_space(ROOT,8)
            lock=None
            if stage:
                lock=(ROOT/'.work/benchmark.lock').open('a');acquire_lock(lock,45)
            try:
                child,out,err=capture([sys.executable,*command],cwd=ROOT,env=env,
                    receipt_path=work/'active.json',receipt=dict(case=label,stage=stage))
                row=dict(case=label,stage=stage,pid=child.pid,command=command,
                    returncode=child.returncode,stdout=out,stderr=err)
                records.append(row);write(work/'records.json',records)
                assert child.returncode==0,(out+err)[-3000:]
            finally:
                if lock:lock.close()
            print(label,stage,'passed',flush=True)
    assert all(sha(ROOT/p)==h for p,h in frozen.items())
    result=ROOT/'results'/run;result.mkdir(exist_ok=False)
    write(result/'summary.json',dict(status='passed',guest_executions=2,commands=6,
        tool_key=key,vm_sha256=profile['vm_sha256'],performance_measurement=False,
        raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json')))


if __name__=='__main__':main()
