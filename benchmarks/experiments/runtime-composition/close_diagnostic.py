"""Close the stopped profile and fresh-baseline environment diagnostic."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
def read(p):return json.loads(p.read_text())
def main():
    name=sys.argv[1];assert re.fullmatch(r'runtime-composition-(?:profile|environment)-01',name)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,10)
        raw=ROOT/'.work'/name;outer=ROOT/'.work/experiments'/name;out=ROOT/'results'/name
        terminal=read(outer/'status.json');plan=read(raw/'plan.json');records=read(raw/'records.json')
        assert terminal['status']=='finished' and terminal['owner']==plan['owner']==str(ROOT)
        assert sha(outer/'command.log')==terminal['log_sha256']
        assert len(records)==1 and records[0]['returncode']==0
        bindings={}
        for p,h in plan['frozen'].items():
            assert sha(ROOT/p)==h,p
            if p.startswith(('.work/','results/')):bindings[p]=dict(kind='retained',sha256=h)
            else:
                data=subprocess.check_output(['git','show',plan['source_revision']+':'+p],cwd=ROOT)
                assert hashlib.sha256(data).hexdigest()==h,p
                bindings[p]=dict(kind='git',revision=plan['source_revision'],sha256=h)
        artifacts={str(p.relative_to(ROOT)):sha(p) for p in raw.rglob('*') if p.is_file()}
        out.mkdir(exist_ok=True);assert not (out/'closure.json').exists()
        if terminal['returncode']:
            assert name=='runtime-composition-profile-01' and not (out/'summary.json').exists()
            write(out/'summary.json',dict(status='failed',phase='retained-profile-identity',commands=1,expected_commands=3,
                raw=str(raw.relative_to(ROOT)),source_revision=plan['source_revision'],
                plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),
                original_assertions_passed=True,instruction_count_matched=False,performance_measurement=False))
        else:
            summary=read(out/'summary.json');assert summary['status']=='passed' and summary['commands']==1
            assert sha(raw/'plan.json')==summary['plan_sha256'] and sha(raw/'records.json')==summary['records_sha256']
        write(raw/'closure-bindings.json',dict(frozen_inputs=bindings,artifacts=artifacts))
        (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
        write(out/'closure.json',dict(status='closed',source_revision=plan['source_revision'],all_hashes_verified=True,
            frozen_input_count=len(bindings),artifact_count=len(artifacts),bindings=str((raw/'closure-bindings.json').relative_to(ROOT)),
            bindings_sha256=sha(raw/'closure-bindings.json'),summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),performance_measurement=False))
        print(name,terminal['returncode'],len(bindings),'source bindings;',len(artifacts),'artifacts verified')
if __name__=='__main__':main()
