"""Close the saved-receipt preparation audit without running any new guest."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write


def read(p):return json.loads(p.read_text())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run');parser.add_argument('supervisor');args=parser.parse_args()
    assert re.fullmatch(r'cross-edit-emission-weight-[0-9]{2}',args.run)
    assert re.fullmatch(r'[a-z0-9-]+',args.supervisor)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        raw,out=ROOT/'.work'/args.run,ROOT/'results'/args.run
        plan,summary=read(raw/'plan.json'),read(out/'summary.json')
        assert summary['status']=='passed' and sha(raw/'plan.json')==summary['plan_sha256']
        assert sha(raw/'records.json')==summary['records_sha256']
        bindings,evidence={},{}
        for path,digest in plan['frozen'].items():
            assert sha(ROOT/path)==digest
            if path.startswith(('.work/','results/')):evidence[path]=digest
            else:
                blob=subprocess.check_output(['git','show',plan['source_revision']+':'+path],cwd=ROOT)
                assert hashlib.sha256(blob).hexdigest()==digest
                bindings[path]=dict(revision=plan['source_revision'],sha256=digest)
        records=read(raw/'records.json');assert len(records)==summary['commands']
        for row in records:
            assert row['returncode']==0
            for stream in ['stdout','stderr']:
                path=raw/(row['label']+'.'+stream)
                assert sha(path)==row[stream+'_sha256']
                evidence[str(path.relative_to(ROOT))]=sha(path)
        for path,digest in summary.get('outputs',{}).items():
            assert sha(ROOT/path)==digest;evidence[path]=digest
        outer=ROOT/'.work/experiments'/args.supervisor
        terminal=read(outer/'status.json')
        assert terminal['status']=='finished' and terminal['returncode']==0
        assert terminal['owner']==terminal['cwd']==str(ROOT)
        assert terminal['plan_sha256']==sha(outer/'plan.json') and terminal['log_sha256']==sha(outer/'command.log')
        assert terminal['command'][1:]==plan['controller_command'][1:]
        assert Path(terminal['command'][0]).resolve()==Path(plan['controller_command'][0]).resolve()
        for path in [raw/'plan.json',raw/'records.json',outer/'plan.json',outer/'status.json',outer/'command.log']:
            evidence[str(path.relative_to(ROOT))]=sha(path)
        assert not (out/'closure.json').exists()
        write(raw/'source-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
        (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
        write(out/'closure.json',dict(status='closed',source_revision=plan['source_revision'],all_hashes_verified=True,
            source_files=len(bindings),frozen_inputs=len(plan['frozen']),evidence_files=len(evidence),
            source_bindings=str((raw/'source-bindings.json').relative_to(ROOT)),source_bindings_sha256=sha(raw/'source-bindings.json'),
            evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json'),
            summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
            original_project_guest_commands=0,native_fixture_execution=False,performance_measurement=False))
        print('Closed',args.run,flush=True)


if __name__=='__main__':main()
