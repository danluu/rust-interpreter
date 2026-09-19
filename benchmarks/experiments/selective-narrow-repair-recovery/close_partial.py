"""Retain the successful first capture and the failed observer, without a rerun."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write


def read(p):return json.loads(p.read_text())


def main():
    run='selective-narrow-repair-profile-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        raw=ROOT/'.work'/run;outer=ROOT/'.work/experiments'/run
        plan=read(raw/'plan.json');terminal=read(outer/'status.json')
        assert terminal['status']=='finished' and terminal['returncode']==1
        assert terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT)
        assert terminal['plan_sha256']==sha(outer/'plan.json')
        assert terminal['log_sha256']==sha(outer/'command.log')
        assert terminal['command'][1:]==plan['controller_command'][1:]
        assert 'native bytes changed outside scalar target immediates' in (outer/'command.log').read_text()
        bindings={};evidence={}
        for path,digest in plan['frozen'].items():
            assert sha(ROOT/path)==digest
            if not path.startswith(('.work/','results/')):
                data=subprocess.check_output(['git','show',plan['source_revision']+':'+path],cwd=ROOT)
                assert hashlib.sha256(data).hexdigest()==digest
                bindings[path]=dict(revision=plan['source_revision'],sha256=digest)
            else:evidence[path]=digest
        controls=read(raw/'controls.json');records=read(raw/'records.json')
        assert controls['returncode']==0 and 'Ran 6 tests' in (raw/'controls.stderr').read_text()
        for stream in ['stdout','stderr']:assert sha(raw/('controls.'+stream))==controls[stream+'_sha256']
        assert len(records)==1 and records[0]['index']==0 and records[0]['returncode']==0 and records[0]['stdout']=='0\n'
        artifacts={}
        for path in [raw/'candidate-0-profile.json',*[raw/'candidate-0-code'/n for n in ['code.bin','map.json','operations.json']]]:
            artifacts[str(path.relative_to(ROOT))]=sha(path)
        for path in [raw/'plan.json',raw/'records.json',raw/'controls.json',raw/'controls.stdout',raw/'controls.stderr',
                     outer/'status.json',outer/'plan.json',outer/'command.log',ROOT/'.work/selective-native-identity-diff.json']:
            evidence[str(path.relative_to(ROOT))]=sha(path)
        out=ROOT/'results'/run;out.mkdir(exist_ok=False)
        write(raw/'partial-bindings.json',dict(frozen_inputs=plan['frozen'],git_sources=bindings,evidence=evidence,artifacts=artifacts))
        (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
        write(out/'summary.json',dict(status='observer-failed',source_revision=plan['source_revision'],tool_key=plan['tool_key'],
            commands=1,successful_guest_commands=1,python_controls=6,unstarted_indices=[1,2],
            reason='Call profiles render operands; observer recognized only the bare Call label and normalized zero sites.',
            raw=str(raw.relative_to(ROOT)),plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),
            no_runtime_failure_observed=True,performance_measurement=False))
        write(out/'closure.json',dict(status='closed',all_hashes_verified=True,summary_sha256=sha(out/'summary.json'),
            terminal_sha256=sha(out/'terminal.json'),bindings=str((raw/'partial-bindings.json').relative_to(ROOT)),
            bindings_sha256=sha(raw/'partial-bindings.json'),source_files=len(bindings),evidence_files=len(evidence),
            preserved_capture_files=len(artifacts),guest_commands=0,auditor_sha256=sha(Path(__file__))))
        print('Closed partial profile: successful capture retained; remaining two never started',flush=True)


if __name__=='__main__':main()
