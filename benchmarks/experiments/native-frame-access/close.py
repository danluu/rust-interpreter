"""Close the offline census without executing another diagnostic or guest."""
import hashlib
import subprocess
from run import ROOT, RUN, read, sha, write, acquire_lock, require_space


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        require_space(ROOT,8)
        raw,out=ROOT/'.work'/RUN,ROOT/'results'/RUN
        summary,plan=read(out/'summary.json'),read(raw/'plan.json')
        assert summary['status']=='passed' and summary['controls']==6
        for name in ['plan','record','details']:
            assert sha(raw/(name+'.json'))==summary[name+'_sha256']
        bindings,evidence={},{}
        for path,digest in plan['frozen'].items():
            assert sha(ROOT/path)==digest
            if path.startswith(('.work/','results/')): evidence[path]=digest
            else:
                blob=subprocess.check_output(['git','show',plan['source_revision']+':'+path],cwd=ROOT)
                assert hashlib.sha256(blob).hexdigest()==digest
                bindings[path]=dict(revision=plan['source_revision'],sha256=digest)
        record=read(raw/'record.json')
        assert record['returncode']==0
        for stream in ['stdout','stderr']:
            path=raw/('controls.'+stream)
            assert sha(path)==record[stream+'_sha256']
            evidence[str(path.relative_to(ROOT))]=sha(path)
        outer=ROOT/'.work/experiments'/RUN
        terminal=read(outer/'status.json')
        assert terminal['status']=='finished' and terminal['returncode']==0
        assert terminal['plan_sha256']==sha(outer/'plan.json') and terminal['log_sha256']==sha(outer/'command.log')
        for path in [raw/(name+'.json') for name in ['plan','record','details']]+[
                outer/name for name in ['plan.json','status.json','command.log']]:
            evidence[str(path.relative_to(ROOT))]=sha(path)
        assert not (out/'closure.json').exists()
        write(raw/'source-bindings.json',bindings)
        write(raw/'closed-evidence.json',evidence)
        (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
        write(out/'closure.json',dict(status='closed',source_revision=plan['source_revision'],
            all_hashes_verified=True,frozen_inputs=len(plan['frozen']),source_files=len(bindings),
            source_bindings=str((raw/'source-bindings.json').relative_to(ROOT)),source_bindings_sha256=sha(raw/'source-bindings.json'),
            evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json'),
            summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
            new_guest_commands=0,performance_measurement=False))
        print('Closed private-frame census:',len(plan['frozen']),'frozen inputs',flush=True)


if __name__=='__main__': main()
