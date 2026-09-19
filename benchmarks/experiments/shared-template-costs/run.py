"""Audit all edited preparation receipts from the closed shared-template primary."""
import json,os,statistics,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from measure import BASELINE,measure
RUN='shared-template-costs-01'
def read(p):return json.loads(p.read_text())

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        frozen={}
        def bind(path,digest=None):
            value=sha(path)
            if digest is not None:assert value==digest,path
            frozen[str(path.relative_to(ROOT))]=value
            return read(path) if path.suffix=='.json' else value
        folder=ROOT/'results/shared-emission-templates-parser-screen-incremental-01'
        closed=bind(folder/'closure.json');assert closed['status']=='closed' and closed['all_hashes_verified']
        history=bind(folder/'summary.json',closed['summary_sha256'])
        assert history['status']=='passed' and history['commands']==32 and not history['measurement']['gate_passed']
        assert history['source_restored'] and history['candidate_control_artifacts_match']
        original=ROOT/history['raw'];bind(original/'plan.json',history['plan_sha256'])
        records=bind(original/'records.json',history['records_sha256'])
        bind(folder/'terminal.json',closed['terminal_sha256'])
        build_folder=ROOT/'results/shared-emission-templates-build-01'
        build_closed=bind(build_folder/'closure.json');assert build_closed['status']=='closed' and build_closed['all_hashes_verified']
        build=bind(build_folder/'summary.json',build_closed['summary_sha256'])
        source=bind(ROOT/build['source_manifest'],build['source_manifest_sha256'])
        for p,h in source['frozen'].items():
            if p.startswith('crates/bytecode/'):bind(ROOT/p,h)
        keys=history['tool_keys'];assert keys==dict(baseline=BASELINE,duplicate=BASELINE,candidate=build['tool_key'])
        selected=[]
        for row in records:
            if row['mode']=='native' or row['state'] not in range(1,6):continue
            path=Path(row['launch']['suite_report_path'])
            assert path.is_relative_to(original) and row['command'][row['command'].index('--suite-report')+1]==str(path)
            assert row['suite_sha256']==row['launch']['suite_report_sha256']
            selected.append((row,bind(path,row['suite_sha256'])))
        assert len(selected)==15
        assert {(r['cycle'],r['state'],r['mode']) for r,_ in selected}=={(0,s,m) for s in range(1,6) for m in keys}
        for p in Path(__file__).parent.iterdir():
            if p.suffix in ['.py','.md']:bind(p)
        for name in ['compare_saved_runtime.py','workflow_io.py','suite_reports.py','native_suite.py']:bind(ROOT/'scripts'/name)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=1,expected_controls=10,
            retained_edited_receipts=15,initial_minimum_gib=12,minimum_child_gib=8,
            original_project_guest_commands=0,compiler_build_commands=0,performance_measurement=False))
        require_space(ROOT,8)
        env={k:v for k,v in os.environ.items() if k!='PYTHONPATH'};env['PYTHONDONTWRITEBYTECODE']='1'
        child,out,err=capture([sys.executable,'-m','unittest','test_measure','-v'],cwd=Path(__file__).parent,env=env,
            receipt_path=raw/'active.json',receipt=dict(label='controls'))
        (raw/'controls.stdout').write_text(out);(raw/'controls.stderr').write_text(err)
        write(raw/'records.json',[dict(label='controls',pid=child.pid,returncode=child.returncode,
            stdout_sha256=sha(raw/'controls.stdout'),stderr_sha256=sha(raw/'controls.stderr'))])
        assert child.returncode==0 and 'Ran 10 tests in ' in err and err.rstrip().endswith('OK'),err
        rows=[dict(measure(row,suite,row['mode'],keys[row['mode']]),source_record_index=row['index']) for row,suite in selected]
        fields=['command_seconds','execution_seconds','suite_seconds','compile_interval_sum_seconds',
            'largest_worker_compile_seconds','constructor_interval_sum_seconds','store_preparation_seconds',
            'retained_code_bytes','retained_function_owners','declined_function_owners','template_storage_bytes','template_storage_functions']
        medians={mode:{field:statistics.median(r[field] for r in rows if r['mode']==mode) for field in fields} for mode in keys}
        sharing={field:statistics.median(r['shared_templates'][field] for r in rows if r['mode']=='candidate') for field in ['hits','misses','restored_code_bytes']}
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/RUN;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',source_revision=revision,commands=1,controls=10,
            retained_edited_receipts=15,rows=rows,medians=medians,candidate_sharing_medians=sharing,
            original_project_guest_commands=0,compiler_build_commands=0,production_runtime_changes=0,performance_measurement=False,
            interval_scope='Elapsed worker intervals overlap; separate stage medians are not additive, CPU time or demonstrated command savings.',
            raw=str(raw.relative_to(ROOT)),plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json')))
        print('Passed10controls; audited15existing receipts; no new guest/build',flush=True)
        for mode,row in medians.items():print(mode,json.dumps(row,sort_keys=True),flush=True)
        print('candidate sharing',json.dumps(sharing,sort_keys=True),flush=True)

if __name__=='__main__':main()
