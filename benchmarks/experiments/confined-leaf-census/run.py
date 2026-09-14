"""Qualify and run a bounded join of completed typed and sampled call evidence."""
import json
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from analyze import analyze


def main():
    name='confined-leaf-census-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,10)
        directory=Path(__file__).parent
        build_path=ROOT/'results/frame-initialization-constants-build-01/summary.json'
        coverage_path=ROOT/'results/frame-initialization-constants-coverage-01/summary.json'
        previous_path=ROOT/'results/native-call-cost-census-01/summary.json'
        build,coverage,previous=[json.loads(p.read_text()) for p in [build_path,coverage_path,previous_path]]
        assert all(p['status']=='passed' for p in [build,coverage,previous])
        assert build['tests']=={'debug':10,'release':10} and build['oracle_cases_per_profile']==6400
        assert coverage['all_frozen_inputs_verified'] and previous['all_frozen_inputs_verified']
        assert coverage['guest_commands']==coverage['runtime_changes']==previous['guest_commands']==previous['rust_builds']==0
        typed_path=ROOT/build['raw']/'typed.json';assert sha(typed_path)==build['typed_sha256']
        typed=json.loads(typed_path.read_text());assert len(typed['functions'])==build['functions']
        paths=[build_path,coverage_path,previous_path,typed_path]
        for result,path in [(coverage,coverage_path),(previous,previous_path)]:
            plan=ROOT/result['raw']/'plan.json';assert sha(plan)==result['plan_sha256']
            inputs=json.loads(plan.read_text());assert inputs['owner']==str(ROOT)
            bindings=path.with_name('source-bindings.json');assert sha(bindings)==result['source_bindings_sha256']
            paths += [plan,bindings]
        # The coverage audit already closes the compiler failures and typed proof.
        coverage_inputs=json.loads((ROOT/coverage['raw']/'plan.json').read_text())['frozen']
        for path in [build_path,typed_path,previous_path]:assert sha(path)==coverage_inputs[str(path.relative_to(ROOT))]
        inputs=[]
        for label in ['block','exhaustive']:
            item,=[c for c in previous['cases'] if c['case']==label]
            path=ROOT/previous['raw']/(label+'.json');assert sha(path)==item['report_sha256']
            inputs.append((item,path));paths.append(path)
        paths += [p for p in directory.iterdir() if p.suffix in ['.py','.md']]
        paths += [ROOT/'scripts'/n for n in ['compare_saved_runtime.py','workflow_io.py']]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        work=ROOT/'.work'/name;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            frozen=frozen,guest_commands=0,rust_builds=0,executable_publications=0,performance_measurement=False))
        child,out,err=capture([sys.executable,'-m','unittest','test_analyze','-v'],cwd=directory,
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),receipt_path=work/'active.json',receipt=dict(stage='join identity controls'))
        (work/'stdout').write_text(out);(work/'stderr').write_text(err)
        write(work/'record.json',dict(pid=child.pid,returncode=child.returncode,stdout_sha256=sha(work/'stdout'),stderr_sha256=sha(work/'stderr')))
        assert child.returncode==0 and 'Ran 3 tests' in err and err.rstrip().endswith('OK'),err
        cases=[]
        for item,path in inputs:
            result=analyze(typed,json.loads(path.read_text()))
            assert result['incoming_calls']==item['native_calls']
            assert result['protocol_samples']==item['call_samples']+item['return_samples']
            assert result['generated_samples']==item['generated_samples']
            write(work/(item['case']+'.json'),result)
            cases.append(dict(case=item['case'],groups=result['groups'],incoming_calls=result['incoming_calls'],
                generated_samples=result['generated_samples'],protocol_samples=result['protocol_samples'],
                report_sha256=sha(work/(item['case']+'.json')),top_selected=result['selected'][:12]))
            print(item['case'],json.dumps(result['groups']),flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/name;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',controls=3,cases=cases,guest_commands=0,rust_builds=0,
            executable_publications=0,performance_measurement=False,raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),record_sha256=sha(work/'record.json'),all_frozen_inputs_verified=True,
            limitation='Upper bound before scalar slot widths, address escape, lowering and fault materialization. Sampled protocol includes required checks; whole-function counts are not per-native-call costs. No speedup prediction.'))

if __name__=='__main__':main()
