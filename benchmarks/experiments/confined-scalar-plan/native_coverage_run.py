"""Close scalar IR proof and join retained per-PC profiles without guest execution."""
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
from native_coverage import analyze

def read(path):return json.loads(path.read_text())

def main():
    name='confined-scalar-native-coverage-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        build_path=ROOT/'results/confined-scalar-native-build-01/summary.json';build=read(build_path);raw=ROOT/build['raw']
        assert build['status']=='passed' and build['tests']=={'debug':24,'release':24} and build['commands']==8
        assert build['oracle_cases_per_profile']==6400 and build['scalar_copy_cases_per_profile']==2187
        plan_path=raw/'plan.json';assert sha(plan_path)==build['plan_sha256'];plan=read(plan_path)
        assert plan['owner']==str(ROOT) and plan['guest_commands']==plan['runtime_changes']==0
        paths=[build_path,plan_path];bindings={}
        for path,digest in plan['frozen'].items():
            if sha(ROOT/path)==digest:bindings[path]=dict(kind='current',sha256=digest)
            else:
                data=subprocess.check_output(['git','show',plan['source_revision']+':'+path]);assert hashlib.sha256(data).hexdigest()==digest
                bindings[path]=dict(kind='git',revision=plan['source_revision'],sha256=digest)
        terminal=build_path.with_name('terminal.json');status=read(terminal)
        assert status['status']=='finished' and status['returncode']==0 and status['owner']==str(ROOT)
        assert terminal.read_bytes()==(ROOT/'.work/experiments/confined-scalar-native-build-01/status.json').read_bytes()
        log=ROOT/'.work/experiments/confined-scalar-native-build-01/command.log';assert sha(log)==status['log_sha256'];paths += [terminal,log]
        records=raw/'records.json';assert sha(records)==build['records_sha256'];paths.append(records)
        for record in read(records):
            assert record['returncode']==0
            for stream in ['stdout','stderr']:
                p=raw/(record['label']+'.'+stream);assert sha(p)==record[stream+'_sha256'];paths.append(p)
        typed_path=raw/'typed.json';assert sha(typed_path)==build['typed_sha256'];paths.append(typed_path);typed=read(typed_path)
        assert len(typed['functions'])==build['functions']
        prior_path=ROOT/'results/confined-scalar-ir-coverage-01/summary.json';prior=read(prior_path);paths.append(prior_path)
        assert prior['status']=='passed' and prior['all_frozen_inputs_verified'] and prior['controls']==2
        inputs=[]
        for label in ['block','exhaustive']:
            item,=[c for c in prior['cases'] if c['case']==label]
            p=ROOT/prior['raw']/(label+'.json');assert sha(p)==item['report_sha256'];paths.append(p)
            inputs.append((label,p))
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.rs','.md','.toml','.lock']]
        paths += [ROOT/'scripts'/n for n in ['workflow_io.py','compare_saved_runtime.py']]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        work=ROOT/'.work'/name;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),guest_commands=0,runtime_changes=0))
        write(work/'source-bindings.json',bindings)
        child,out,err=capture([sys.executable,'-m','unittest','test_native_coverage','-v'],cwd=Path(__file__).parent,
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),receipt_path=work/'active.json',receipt=dict(stage='native-emission join controls'))
        (work/'stdout').write_text(out);(work/'stderr').write_text(err)
        write(work/'record.json',dict(pid=child.pid,returncode=child.returncode,stdout_sha256=sha(work/'stdout'),stderr_sha256=sha(work/'stderr')))
        assert child.returncode==0 and 'Ran 2 tests' in err and err.rstrip().endswith('OK'),err
        cases=[]
        for label,p in inputs:
            require_space(ROOT,8);report=analyze(typed,read(p));write(work/(label+'.json'),report)
            cases.append(dict(case=label,groups=report['groups'],report_sha256=sha(work/(label+'.json')),top_selected=report['selected'][:12]))
            print(label,json.dumps(report['groups']),flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/name;result.mkdir(exist_ok=False);write(result/'source-bindings.json',bindings)
        write(result/'summary.json',dict(status='passed',controls=2,cases=cases,raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),record_sha256=sha(work/'record.json'),source_bindings_sha256=sha(work/'source-bindings.json'),
            all_frozen_inputs_verified=True,guest_commands=0,rust_builds=0,runtime_changes=0,performance_measurement=False,
            limitation='Native emission coverage and synthetic native tests do not qualify the original guest Call transaction or predict complete-command speed.'))

if __name__=='__main__':main()
