"""Close diagnostic build failures and join plans; no guest executes."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from coverage import analyze


def main():
    name='confined-scalar-plan-coverage-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,10)
        paths=[];bindings={}
        for number,rc in [('01',1),('02',0)]:
            run='confined-scalar-plan-build-'+number
            summary_path=ROOT/'results'/run/'summary.json';summary=json.loads(summary_path.read_text())
            raw=ROOT/summary['raw'];plan_path=raw/'plan.json';plan=json.loads(plan_path.read_text())
            terminal=ROOT/'results'/run/'terminal.json';status=json.loads(terminal.read_text())
            assert status['status']=='finished' and status['returncode']==rc and status['owner']==str(ROOT)
            assert terminal.read_bytes()==(ROOT/'.work/experiments'/run/'status.json').read_bytes()
            assert sha(ROOT/'.work/experiments'/run/'command.log')==status['log_sha256']
            assert plan['owner']==str(ROOT) and plan['guest_commands']==plan['runtime_changes']==0
            for path,digest in plan['frozen'].items():
                if sha(ROOT/path)==digest:bindings[path+':'+digest]=dict(kind='current',path=path,sha256=digest)
                else:
                    data=subprocess.check_output(['git','show',plan['source_revision']+':'+path])
                    assert hashlib.sha256(data).hexdigest()==digest
                    bindings[path+':'+digest]=dict(kind='git',path=path,revision=plan['source_revision'],sha256=digest)
            paths.extend([summary_path,terminal,plan_path,ROOT/'.work/experiments'/run/'command.log'])
            for record in json.loads((raw/'records.json').read_text()):
                for stream in ['stdout','stderr']:
                    p=raw/(record['label']+'.'+stream);assert sha(p)==record[stream+'_sha256'];paths.append(p)
            paths.append(raw/'records.json')
        assert summary['status']=='passed' and summary['tests']=={'debug':13,'release':13} and summary['commands']==4
        assert summary['oracle_cases_per_profile']==6400
        assert sha(raw/'plan.json')==summary['plan_sha256'] and sha(raw/'records.json')==summary['records_sha256']
        typed_path=raw/'typed.json';assert sha(typed_path)==summary['typed_sha256'];paths.append(typed_path)
        typed=json.loads(typed_path.read_text());assert len(typed['functions'])==summary['functions']
        prior_path=ROOT/'results/confined-leaf-census-01/summary.json';prior=json.loads(prior_path.read_text());paths.append(prior_path)
        assert prior['status']=='passed' and prior['all_frozen_inputs_verified'] and prior['controls']==3
        cases=[]
        for item in prior['cases']:
            p=ROOT/prior['raw']/(item['case']+'.json');assert sha(p)==item['report_sha256'];paths.append(p)
            cases.append((item['case'],json.loads(p.read_text())))
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.rs','.md','.toml','.lock']]
        paths += [ROOT/'scripts'/n for n in ['workflow_io.py','compare_saved_runtime.py']]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        work=ROOT/'.work'/name;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),guest_commands=0,runtime_changes=0))
        write(work/'source-bindings.json',bindings)
        child,out,err=capture([sys.executable,'-m','unittest','test_coverage','-v'],cwd=Path(__file__).parent,
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),receipt_path=work/'active.json',receipt=dict(stage='typed-plan join controls'))
        (work/'stdout').write_text(out);(work/'stderr').write_text(err)
        write(work/'record.json',dict(pid=child.pid,returncode=child.returncode,stdout_sha256=sha(work/'stdout'),stderr_sha256=sha(work/'stderr')))
        assert child.returncode==0 and 'Ran 2 tests' in err and err.rstrip().endswith('OK'),err
        reports=[]
        for label,previous in cases:
            report=analyze(typed,previous);write(work/(label+'.json'),report)
            reports.append(dict(case=label,groups=report['groups'],generated_samples=report['generated_samples'],
                report_sha256=sha(work/(label+'.json')),top_selected=report['selected'][:12]))
            print(label,json.dumps(report['groups']),flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/name;result.mkdir(exist_ok=False)
        write(result/'source-bindings.json',bindings)
        write(result/'summary.json',dict(status='passed',controls=2,cases=reports,raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),record_sha256=sha(work/'record.json'),source_bindings_sha256=sha(work/'source-bindings.json'),
            all_frozen_inputs_verified=True,guest_commands=0,rust_builds=0,runtime_changes=0,performance_measurement=False,
            address_nonescape_proved=False,limitation='Resolved accesses and scalar boundaries do not establish safe executable lowering, acyclic control flow, nonescape or infallibility.'))

if __name__=='__main__':main()
