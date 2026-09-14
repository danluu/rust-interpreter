"""Close an exact saved-sample boundary census without repeating its analysis."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write
def read(p):return json.loads(p.read_text())
def main():
    name=sys.argv[1];assert re.fullmatch(r'scalar-next-boundaries-\d{2}',name)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        out=ROOT/'results'/name;summary=read(out/'summary.json');assert summary['status']=='passed'
        raw=ROOT/summary['raw'];plan=read(raw/'plan.json');assert plan['owner']==str(ROOT)
        assert sha(raw/'plan.json')==summary['plan_sha256'];bindings={}
        for path,digest in plan['frozen'].items():
            assert sha(ROOT/path)==digest
            if path.startswith(('.work/','results/')):bindings[path]=dict(kind='retained',sha256=digest)
            else:
                data=subprocess.check_output(['git','show',plan['source_revision']+':'+path],cwd=ROOT)
                assert hashlib.sha256(data).hexdigest()==digest
                bindings[path]=dict(kind='git',revision=plan['source_revision'],sha256=digest)
        assert [c['generated_samples'] for c in summary['cases']]==[1561,1231]
        for c in summary['cases']:
            for key,p in c['policies'].items():
                assert p['candidate_functions']==len(plan['candidates'][key])
                assert p['transition_samples']==sum(p['by_part'].values())==sum(f['transition_samples'] for f in p['sampled_targets'])
                assert p['body_samples']==sum(f['body_samples'] for f in p['sampled_targets'])
        outer=ROOT/'.work/experiments'/name;terminal=read(outer/'status.json')
        assert terminal['owner']==terminal['cwd']==str(ROOT) and terminal['status']=='finished' and terminal['returncode']==0
        assert sha(outer/'plan.json')==terminal['plan_sha256'] and sha(outer/'command.log')==terminal['log_sha256']
        assert not (out/'closure.json').exists()
        write(raw/'bindings.json',bindings);(out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
        write(out/'closure.json',dict(status='closed',source_revision=plan['source_revision'],frozen_inputs=len(bindings),
            all_hashes_verified=True,bindings=str((raw/'bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'bindings.json'),
            summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),guest_commands=0,performance_measurement=False))
        print(name,len(bindings),'bindings verified')
if __name__=='__main__':main()
