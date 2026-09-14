"""Close the two-command startup failure before any candidate or edited pair."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
RUN='scalar-aggregate-screen-exhaustive-01'
def read(p):return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,10)
        raw=ROOT/'.work'/RUN;outer=ROOT/'.work/experiments'/RUN
        terminal=read(outer/'status.json');assert terminal['owner']==str(ROOT) and terminal['status']=='finished' and terminal['returncode']==1
        assert sha(outer/'command.log')==terminal['log_sha256']
        plan=read(raw/'plan.json');assert plan['owner']==str(ROOT)
        rows=read(raw/'records.json');assert [(r['state'],r['mode'],r['returncode']) for r in rows]==[(0,'native',0),(0,'baseline',0)]
        evidence={};bindings={}
        def retain(p,expected=None):
            h=sha(p)
            if expected is not None:assert h==expected,p
            evidence[str(p.relative_to(ROOT))]=h;return h
        for p,h in plan['frozen'].items():
            retain(ROOT/p,h)
            if not p.startswith(('.work/','results/')):
                data=subprocess.check_output(['git','show',plan['source_revision']+':'+p])
                assert hashlib.sha256(data).hexdigest()==h
                bindings[p]=dict(revision=plan['source_revision'],sha256=h)
        for name in ['plan.json','records.json','transitions.json','space.json','active.json']:retain(raw/name)
        source=ROOT/'.work/sources/fre';changed=source/plan['case']['file'];retain(changed,plan['original_source_sha256'])
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==plan['revision']
        retained=[]
        for row in rows:
            for name in ['native_executable','cargo_timing']:
                if name in row:retain(ROOT/row[name]['path'],row[name]['sha256'])
            if row['mode']=='baseline':
                launch,=[json.loads(line.split(': ',1)[1]) for line in row['stderr'].splitlines() if line.startswith('rust-interp-launch: ')]
                assert launch['tool_key']==plan['tools']['baseline']
                suite=read(Path(launch['suite_report_path']))
                assert suite['workers']==1 and suite['requested_workers']==2 and len(suite['tests'])==1
                assert suite['tests'][0]['name']==plan['names'][0] and suite['passed']==1 and suite['failed']==0
                for key in ['artifact','entry_catalog','test_selection','suite_report']:
                    p=Path(launch[key+'_path']).resolve(strict=True);assert p.is_relative_to(ROOT)
                    h=retain(p,launch[key+'_sha256']);copy=raw/'artifacts'/h
                    if copy.exists():assert sha(copy)==h
                    else:copy.write_bytes(p.read_bytes())
                    retain(copy,h);retained.append(dict(kind=key,path=str(copy.relative_to(ROOT)),sha256=h))
        for name in ['plan.json','status.json','command.log']:retain(outer/name)
        result=ROOT/'results'/RUN;result.mkdir(exist_ok=False)
        summary=dict(status='setup-failed',commands=2,valid_edited_pairs=0,candidate_commands=0,performance_gate_evaluated=False,
            source_revision=plan['source_revision'],source_restored=True,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),retained=retained,
            reason='Prepared runner clamps requested2 workers to1 for one selected test; harness incorrectly required2 active workers.',
            performance_measurement=False)
        write(result/'summary.json',summary);retain(result/'summary.json')
        (result/'terminal.json').write_bytes((outer/'status.json').read_bytes());retain(result/'terminal.json')
        write(raw/'setup-failure-evidence.json',dict(files=evidence,git_bindings=bindings))
        write(result/'closure.json',dict(status='closed',all_hashes_verified=True,source_restored=True,valid_edited_pairs=0,candidate_commands=0,
            evidence_files=len(evidence),source_revision=plan['source_revision'],summary_sha256=sha(result/'summary.json'),
            terminal_sha256=sha(result/'terminal.json'),bindings=str((raw/'setup-failure-evidence.json').relative_to(ROOT)),
            bindings_sha256=sha(raw/'setup-failure-evidence.json'),auditor_sha256=sha(Path(__file__)),
            auditor_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()))
        print('closed setup failure:',len(evidence),'files; no candidate command or edited pair')
if __name__=='__main__':main()
