"""Retain the two setup commands stopped by the obsolete scalar-mode assertion."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write

def read(p):return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,10)
        outer=ROOT/'.work/experiments/runtime-composition-full-token-01'
        terminal=read(outer/'status.json')
        assert terminal['status']=='finished' and terminal['returncode']==1 and terminal['owner']==str(ROOT)
        assert sha(outer/'command.log')==terminal['log_sha256']
        assert "launch.get('jit_scalar_calls', False)" in (outer/'command.log').read_text()
        campaign=ROOT/'.work/runtime-composition-full-01';raw=ROOT/'.work/runtime-composition-edit-token-01'
        rows=read(raw/'records.json');plan=read(raw/'plan.json');parents=read(campaign/'records.json')
        assert len(rows)==2 and [(r['state'],r['mode'],r['returncode']) for r in rows]==[(0,'native',0),(0,'baseline',0)]
        assert len(parents)==1 and parents[0]['case']=='token' and parents[0]['returncode']==1
        source=ROOT/'.work/sources/fre'
        assert sha(source/plan['case']['file'])==plan['original_source_sha256']
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
        for stream in ['stdout','stderr']:assert sha(campaign/('token.'+stream))==parents[0][stream+'_sha256']
        bindings={}
        for manifest in [plan['frozen'],read(campaign/'plan.json')['frozen']]:
            for p,h in manifest.items():
                if p.startswith(('.work/','results/')):
                    assert sha(ROOT/p)==h,p
                    bindings[p]=dict(kind='retained',sha256=h)
                else:
                    data=subprocess.check_output(['git','show','8e54d74d:'+p],cwd=ROOT)
                    assert hashlib.sha256(data).hexdigest()==h,p
                    bindings[p]=dict(kind='git',revision='8e54d74d',sha256=h)
        artifacts={str(p.relative_to(ROOT)):sha(p) for p in (raw/'artifacts').rglob('*') if p.is_file()}
        for p in [raw/'plan.json',raw/'records.json',raw/'transitions.json',raw/'space.json',campaign/'plan.json',campaign/'records.json',campaign/'token.stdout',campaign/'token.stderr']:
            if p.exists():artifacts[str(p.relative_to(ROOT))]=sha(p)
        write(raw/'failure-bindings.json',dict(source=bindings,artifacts=artifacts))
        for name,commands in [('runtime-composition-edit-token-01',2),('runtime-composition-full-01',1)]:
            out=ROOT/'results'/name;out.mkdir(exist_ok=False)
            write(out/'summary.json',dict(status='failed',phase='setup-launcher-option-validation',commands=commands,
                guest_setup_commands=2,valid_edited_pairs=0,source_restored=True,performance_gate_evaluated=False,
                failure='obsolete assertion expected scalar calls only for candidate; adopted baseline already enables scalar calls',
                raw=str((raw if commands==2 else campaign).relative_to(ROOT)),performance_measurement=False))
            (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
            write(out/'closure.json',dict(status='closed',all_hashes_verified=True,source_revision='8e54d74d',
                frozen_input_count=len(bindings),artifact_count=len(artifacts),source_restored=True,
                bindings=str((raw/'failure-bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'failure-bindings.json'),
                summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),performance_gate_evaluated=False))
        print('Closed two setup commands; zero edited pairs; source restored')
if __name__=='__main__':main()
