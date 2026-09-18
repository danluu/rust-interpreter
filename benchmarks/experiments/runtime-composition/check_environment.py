"""Compare one fresh adopted baseline with the failed candidate profile."""
import json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/runtime-composition-workflows'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from native_observation import exact_logical_counts,validate
NAME='runtime-composition-environment-01'
BASE='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
def read(p):return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        failed=ROOT/'.work/runtime-composition-profile-01';records=read(failed/'records.json')
        assert len(records)==1 and records[0]['returncode']==0
        outer=read(ROOT/'.work/experiments/runtime-composition-profile-01/status.json')
        assert outer['status']=='finished' and outer['returncode']==1
        reference=read(ROOT/'results/current-runtime-boundaries-02/summary.json')
        tape=ROOT/reference['raw']/'0.tape'
        entropy=read(ROOT/'results/fixed-frame-clear-entropy-check-01/summary.json')
        library=ROOT/entropy['library'];assert sha(library)==entropy['library_sha256']
        prior=read(ROOT/'results/scratch-memory-values-profile-01/summary.json')
        old,=[r for r in prior['comparisons'] if r['index']==0 and r['mode']=='candidate']
        paths=[Path(__file__),failed/'plan.json',failed/'records.json',failed/'candidate-0-profile.json',
            ROOT/old['profile_path'],ROOT/'.work/interpreter-tools'/BASE/'rust-interp-vm',tape,library]
        assert sha(paths[4])==old['profile_sha256']
        paths += [ROOT/p for p in read(failed/'plan.json')['frozen']]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            frozen=frozen,expected_guest_commands=1,performance_measurement=False))
        command=records[0]['command'][:];command[0]=str(ROOT/'.work/interpreter-tools'/BASE/'rust-interp-vm')
        command.remove('--jit-indirect-calls')
        command[command.index('--profile')+1]=str(work/'profile.json')
        command[command.index('--jit-code-dump')+1]=str(work/'code')
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(DYLD_INSERT_LIBRARIES=str(library),RUST_INTERP_ENTROPY_MODE='replay',
            RUST_INTERP_ENTROPY_TAPE=str(tape),RUST_INTERP_VM_STATS='1')
        child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=work/'active.json',receipt=dict(label='fresh-adopted-baseline'))
        write(work/'records.json',[dict(label='fresh-adopted-baseline',command=command,pid=child.pid,returncode=child.returncode,stdout=out,stderr=err)])
        assert child.returncode==0 and out=='0\n',err
        profile=read(work/'profile.json');candidate=read(failed/'candidate-0-profile.json')
        stats={k:int(v) for k,v in re.findall(r'\b([a-z_]+)=(\d+)\b',err)}
        candidate_stats={k:int(v) for k,v in re.findall(r'\b([a-z_]+)=(\d+)\b',records[0]['stderr'])}
        comparisons={k:dict(fresh=stats[k],candidate=candidate_stats[k],retained=old['statistics'][k])
            for k in ['instructions','peak_guest_memory','entropy_calls','entropy_bytes']}
        totals=exact_logical_counts(profile,candidate)
        assert all(v['fresh']==v['candidate'] for v in comparisons.values())
        observation=validate(read(work/'code/operations.json'),read(work/'code/map.json'),(work/'code/code.bin').read_bytes(),profile,child.pid)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/NAME;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',commands=1,tool_key=BASE,exact_current_candidate_counts=True,
            comparisons=comparisons,logical_counts=totals,original_code_reconstructed=True,mapped_spans=observation['spans'],
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),performance_measurement=False))
        print(json.dumps(comparisons),flush=True)
if __name__=='__main__':main()
