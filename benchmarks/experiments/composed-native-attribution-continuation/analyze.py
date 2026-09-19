"""Finish only missing analysis; no guest or timing execution."""
import os
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'benchmarks/experiments/composed-fre-runtime-sampling'))
from common import KEY,VM,read,verify,terminal,acquire_lock,sha,require_space,write
sys.path.insert(0,str(ROOT/'benchmarks/experiments/composed-native-attribution'))
from attribute import attribute
from workflow_io import capture
RUN='composed-fre-runtime-sampling-01-analysis-02'
PARENT='composed-fre-runtime-sampling-01'
QUAL='composed-native-attribution-protocol-01'

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        parent=ROOT/'.work'/PARENT;original=read(parent/'plan.json');verify(original)
        qualified=ROOT/'results'/QUAL;closure=read(qualified/'closure.json')
        assert closure['status']=='closed' and closure['all_hashes_verified']
        assert sha(qualified/'summary.json')==closure['summary_sha256']
        assert sha(qualified/'terminal.json')==closure['terminal_sha256']
        assert sha(ROOT/closure['bindings'])==closure['bindings_sha256']
        assert sha(ROOT/closure['evidence'])==closure['evidence_sha256']
        frozen={p:r['sha256'] for p,r in read(ROOT/closure['bindings']).items()}
        frozen.update(read(ROOT/closure['evidence']))
        for p in [*qualified.glob('*.json'),*(ROOT/'results'/(PARENT+'-analysis-01')).glob('*.json'),
                  *Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md')]:
            frozen[str(p.relative_to(ROOT))]=sha(p)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        assert original['tool_key']==KEY and original['vm_sha256']==VM
        block,exhaustive=original['cases'];assert [block['label'],exhaustive['label']]==['block','exhaustive']
        prior,=read(parent/'analysis-records.json')
        assert prior['label']=='block' and prior['returncode']==0 and prior['command']==block['summary_command']
        assert (ROOT/'results'/block['run_id']/'summary.json').is_file()
        assert not (ROOT/'results'/exhaustive['run_id']).exists()
        assert not (ROOT/'results'/block['run_id']/'operation-attribution.json').exists()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],parent=PARENT,qualification=QUAL,
            original_plan_sha256=sha(parent/'plan.json'),summary_command=exhaustive['summary_command'],
            reused_summary=block['run_id'],new_guest_commands=0))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        env['PYTHONDONTWRITEBYTECODE']='1';require_space(ROOT,8)
        child,out,err=capture(exhaustive['summary_command'],cwd=ROOT,env=env,
            receipt_path=raw/'active.json',receipt=dict(stage='exhaustive summary'))
        for stream,value in [('stdout',out),('stderr',err)]:(raw/('exhaustive.'+stream)).write_text(value)
        write(raw/'records.json',[dict(label='exhaustive',command=exhaustive['summary_command'],pid=child.pid,
            returncode=child.returncode,stdout_sha256=sha(raw/'exhaustive.stdout'),stderr_sha256=sha(raw/'exhaustive.stderr'))])
        assert child.returncode==0,err
        reports=[];write(raw/'attributions.json',reports)
        for case in original['cases']:
            require_space(ROOT,8)
            assert read(ROOT/'results'/case['run_id']/'summary.json')['options']['jit_indirect_calls'] is True
            report=attribute(case['run_id'],ROOT/case['profile'],VM)
            reports.append(dict(case=case['label'],run_id=case['run_id'],**report))
            write(raw/'attributions.json',reports)
            print(case['label'],report['by_label'],flush=True)
        verify(original);assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/PARENT;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',tool_key=KEY,vm_sha256=VM,guest_commands=2,
            new_guests_during_analysis=0,summary_commands=2,reused_successful_summary_commands=1,
            new_summary_commands=1,reused_controls=11,region_reader_controls=5,cases=reports,
            raw=str(raw.relative_to(ROOT)),original_raw=str(parent.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),original_plan_sha256=sha(parent/'plan.json'),
            records_sha256=sha(raw/'records.json'),attributions_sha256=sha(raw/'attributions.json'),
            archived_vm_sources_sha256=original['archived_vm_sources_sha256'],
            all_frozen_inputs_verified=True,ordinary_entropy=True,performance_measurement=False,
            profile_used_for_static_identity_only=True,standalone_fresh_owner_not_persistent_session=True))

if __name__=='__main__':main()
