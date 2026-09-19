"""Qualify relocation equality and reuse the saved block execution without replay."""
import importlib.util,os,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from compare import compare
RUN='heap-layout-native-comparison-01'
FAILED='heap-layout-profile-02'
read=focus.read
VALIDATOR=ROOT/'benchmarks/experiments/compact-switch-adopted-profile/qualify.py'
spec=importlib.util.spec_from_file_location('retained_guest_validator',VALIDATOR)
validator=importlib.util.module_from_spec(spec);spec.loader.exec_module(validator)

def saved_block():
    out=ROOT/'results'/FAILED;closure=read(out/'closure.json');summary=read(out/'summary.json')
    assert closure['status']=='closed' and closure['all_hashes_verified'] and closure['all_generated_artifacts_retained']
    assert sha(out/'summary.json')==closure['summary_sha256'] and sha(out/'terminal.json')==closure['terminal_sha256']
    assert summary['status']=='profile-failed' and summary['commands']==1 and summary['original_project_guest_commands']==1
    raw=ROOT/summary['raw'];plan=read(raw/'plan.json');rows=read(raw/'records.json')
    assert sha(raw/'plan.json')==summary['plan_sha256'] and sha(raw/'records.json')==summary['records_sha256']
    assert len(rows)==1 and rows[0]['returncode']==0 and rows[0]['index']==0
    paths=[out/'closure.json',out/'summary.json',out/'terminal.json',raw/'plan.json',raw/'records.json',VALIDATOR,
           Path(validator.native_observation.__file__)]
    for key in ['bindings','evidence']:
        path=ROOT/closure[key];assert sha(path)==closure[key+'_sha256'];paths.append(path)
    for p,h in read(ROOT/closure['evidence']).items():assert sha(ROOT/p)==h;paths.append(ROOT/p)
    for p,h in plan['frozen'].items():assert sha(ROOT/p)==h,p;paths.append(ROOT/p)
    case=plan['cases'][0];assert case['item']['index']==0
    previous=read(ROOT/case['previous'])
    semantic=validator.validate_case(raw,rows[0],case['item'],case['prior'],previous)
    original=ROOT/'.work/compact-switch-current-host-01/adopted'
    def dump(base,profile):
        code=base/'0-code'
        return (code/'code.bin').read_bytes(),read(code/'operations.json'),read(code/'map.json'),profile
    old=dump(original,previous);new=dump(raw,read(raw/'0-profile.json'))
    old_rows=read(original.parent/'records.json');old_row,=[r for r in old_rows if r['mode']=='adopted' and r['index']==0]
    validator.validate(old[1],old[2],old[0],old[3],old_row['pid'])
    paths.append(original.parent/'records.json')
    proof=compare(old,new)
    return dict(index=0,semantic=semantic,relocation_equality=proof,original_guest_reused=True),paths

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        # Verify closed input ownership/hashes before creating any qualification state.
        proof,paths=saved_block()
        paths += [*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md'),Path(focus.__file__)]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);write(raw/'records.json',[])
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=1,tests=9,
            original_project_guest_commands=0,reused_guest_commands=1,performance_measurement=False))
        require_space(ROOT,8)
        command=[sys.executable,'-B','-m','unittest','discover','-s',str(Path(__file__).parent),'-p','test_compare.py','-v']
        start=time.time();child,out,err=capture(command,cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),
            receipt_path=raw/'active.json',receipt=dict(label='controls'))
        for stream,value in [('stdout',out),('stderr',err)]:(raw/('controls.'+stream)).write_text(value)
        records=[dict(label='controls',command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-start,
            stdout_sha256=sha(raw/'controls.stdout'),stderr_sha256=sha(raw/'controls.stderr'))]
        write(raw/'records.json',records)
        assert child.returncode==0 and 'Ran 9 tests in ' in err and '\nOK\n' in err,(out+err)[-6000:]
        write(raw/'saved-block.json',proof);assert saved_block()[0]==proof
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        outputs={str((raw/'saved-block.json').relative_to(ROOT)):sha(raw/'saved-block.json')}
        result=ROOT/'results'/RUN;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),commands=1,tests=9,
            outputs=outputs,proof=proof,plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),
            original_project_guest_commands=0,reused_guest_commands=1,performance_measurement=False,default_runtime_adoption=False))
        print('Nine relocation controls and retained original block checks passed; no guest replay',flush=True)

def close():
    terminal=read(ROOT/'.work/experiments'/RUN/'status.json')
    if terminal['returncode']==0:
        expected=read(ROOT/'results'/RUN/'summary.json')['proof']
        assert saved_block()[0]==expected
    focus.RUN=RUN;focus.close()

if __name__=='__main__':
    if sys.argv[1:]==['--close']:close()
    else:assert len(sys.argv)==1;main()
