"""Audit adopted-VM preparation intervals in retained edited-source receipts."""
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from interpreter import installed_tools
from measure import BASELINE,measure
RUN='jit-preparation-costs-02'
SOURCE='fca687ebac0ea9374a1426addd01169fe707f608'


def read(path):return json.loads(path.read_text())


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        frozen={}
        def bind(path,expected=None):
            digest=sha(path)
            if expected is not None:assert digest==expected,path
            name=str(path.relative_to(ROOT));assert name not in frozen or frozen[name]==digest
            frozen[name]=digest
            return read(path) if path.suffix=='.json' else digest
        failed_path=ROOT/'results/jit-preparation-costs-01/summary.json'
        failed_closed=bind(failed_path.with_name('closure.json'))
        failed=bind(failed_path,failed_closed['summary_sha256'])
        assert failed_closed['status']=='closed' and failed_closed['all_hashes_verified']
        assert failed['status']=='observer-failed' and failed['new_guest_commands']==0
        adopted=bind(ROOT/'results/scratch-scalar-main-qualification-01/summary.json')
        assert adopted['status']=='passed' and adopted['tool_key']==BASELINE
        tools,key=installed_tools(BASELINE);assert key==BASELINE
        for name,digest in adopted['binaries'].items():bind(tools/name,digest)
        assert not subprocess.check_output(['git','diff','--name-only',SOURCE,'--','crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],cwd=ROOT).strip()
        for name in ['jit.rs','prepared.rs','suite.rs','lib.rs']:bind(ROOT/'crates/bytecode/src'/name)
        full_path=ROOT/'results/runtime-composition-full-02/summary.json'
        full_closed=bind(full_path.with_name('closure.json'));full=bind(full_path,full_closed['summary_sha256'])
        assert full_closed['status']=='closed' and full_closed['all_retained_artifacts_and_sources_verified']
        assert full_closed['runtime_adopted'] is False and full['commands']==726
        final_evidence=bind(ROOT/full_closed['snapshot']/'evidence.json',full_closed['evidence_sha256'])
        histories=[]
        for case in ['token','folded','pgrust','rg-aot','nushell']:
            name='results/runtime-composition-edit-'+case+'-02/summary.json'
            histories.append((case,ROOT/name,final_evidence[name],3))
        parser_path=ROOT/'results/runtime-composition-parser-edits-incremental-01/summary.json'
        parser_closed=bind(parser_path.with_name('closure.json'))
        assert parser_closed['status']=='closed' and parser_closed['all_hashes_verified']
        bind(ROOT/parser_closed['evidence'],parser_closed['evidence_sha256'])
        histories.append(('nushell-parser-incremental',parser_path,parser_closed['summary_sha256'],3))
        primary_path=ROOT/'results/selective-narrow-repair-screen-token-01/summary.json'
        primary_closed=bind(primary_path.with_name('closure.json'))
        assert primary_closed['status']=='passed' and primary_closed['parked']
        primary_evidence=bind(ROOT/primary_closed['evidence_path'],primary_closed['evidence_sha256'])
        histories.append(('token-recent',primary_path,primary_evidence[str(primary_path.relative_to(ROOT))],1))
        inputs=[]
        for case,path,digest,cycles in histories:
            summary=bind(path,digest);assert summary['status']=='passed' and summary['source_restored']
            assert summary['tool_keys']['baseline']==BASELINE
            raw=ROOT/summary['raw'];hashes=summary.get('evidence') or {k:summary[k+'_sha256'] for k in ['plan','records']}
            bind(raw/'plan.json',hashes['plan']);records=bind(raw/'records.json',hashes['records'])
            assert len(records)==summary['commands']
            rows=[r for r in records if r['mode']=='baseline' and r['state'] in range(1,6)]
            assert [(r['cycle'],r['state']) for r in rows]==[(c,s) for c in range(cycles) for s in range(1,6)]
            selected=[]
            for row in rows:
                suite_path=Path(row['launch']['suite_report_path'])
                assert suite_path.is_relative_to(raw) and row['command'].count('--suite-report')==1
                assert row['command'][row['command'].index('--suite-report')+1]==str(suite_path)
                assert row['suite_sha256']==row['launch']['suite_report_sha256']
                suite=bind(suite_path,row['suite_sha256'])
                selected.append((row,suite))
            inputs.append((case,path,selected))
        for path in Path(__file__).parent.iterdir():
            if path.suffix in ['.py','.md']:bind(path)
        for name in ['compare_saved_runtime.py','workflow_io.py','interpreter.py']:bind(ROOT/'scripts'/name)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.argv],required_free_gib=12,minimum_child_gib=8,
            adopted_tool_key=BASELINE,restored_rust_source=SOURCE,expected_controls=7,
            retained_edited_receipts=95,new_guest_commands=0,compiler_build_commands=0,
            performance_measurement=False))
        require_space(ROOT,8)
        child,out,err=capture([sys.executable,'-m','unittest','test_measure','-v'],cwd=Path(__file__).parent,
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),receipt_path=raw/'active.json',receipt=dict(stage='audit controls'))
        (raw/'controls.stdout').write_text(out);(raw/'controls.stderr').write_text(err)
        write(raw/'controls.json',dict(pid=child.pid,returncode=child.returncode,
            stdout_sha256=sha(raw/'controls.stdout'),stderr_sha256=sha(raw/'controls.stderr')))
        assert child.returncode==0 and 'Ran 7 tests' in err and err.rstrip().endswith('OK'),err
        cases=[]
        fields=['command_seconds','execution_seconds','suite_seconds','compile_interval_sum_seconds',
            'largest_worker_compile_seconds','compile_interval_sum_over_command','compile_interval_sum_over_execution',
            'constructor_interval_sum_seconds','retained_code_bytes','retained_function_owners','declined_function_owners']
        for case,path,selected in inputs:
            rows=[measure(row,suite) for row,suite in selected]
            cases.append(dict(case=case,history=str(path.relative_to(ROOT)),history_sha256=sha(path),
                receipts=len(rows),tests_per_receipt=sorted({r['tests'] for r in rows}),rows=rows,
                medians={field:statistics.median(r[field] for r in rows) for field in fields}))
        assert sum(c['receipts'] for c in cases)==95
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/RUN;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',source_revision=revision,cases=cases,controls=7,
            retained_edited_receipts=95,adopted_tool_key=BASELINE,new_guest_commands=0,compiler_build_commands=0,
            production_runtime_changes=0,private_details_redacted=True,performance_measurement=False,
            interval_scope='Nested elapsed compilation and constructor intervals; worker sums overlap, are not CPU time and are not measured command savings.',
            raw=str(raw.relative_to(ROOT)),plan_sha256=sha(raw/'plan.json'),controls_sha256=sha(raw/'controls.json')))
        print('PASS seven controls and95 retained edited receipts; zero new guests/builds',flush=True)
        for case in cases:print(case['case'],json.dumps(case['medians'],sort_keys=True),flush=True)


def close():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        raw=ROOT/'.work'/RUN;result=ROOT/'results'/RUN;outer=ROOT/'.work/experiments'/RUN
        summary=read(result/'summary.json');plan=read(raw/'plan.json');terminal=read(outer/'status.json')
        assert summary['status']=='passed' and sha(raw/'plan.json')==summary['plan_sha256']
        assert sha(raw/'controls.json')==summary['controls_sha256']
        bindings={};evidence={}
        for path,digest in plan['frozen'].items():
            assert sha(ROOT/path)==digest
            if not path.startswith(('.work/','results/')):
                data=subprocess.check_output(['git','show',plan['source_revision']+':'+path],cwd=ROOT)
                assert hashlib.sha256(data).hexdigest()==digest
                bindings[path]=dict(revision=plan['source_revision'],sha256=digest)
            else:evidence[path]=digest
        control=read(raw/'controls.json');assert control['returncode']==0
        for stream in ['stdout','stderr']:assert sha(raw/('controls.'+stream))==control[stream+'_sha256']
        assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==terminal['cwd']==str(ROOT)
        assert terminal['command'][1:]==plan['controller_command'][1:]
        assert sha(outer/'plan.json')==terminal['plan_sha256'] and sha(outer/'command.log')==terminal['log_sha256']
        for path in [raw/'plan.json',raw/'controls.json',raw/'controls.stdout',raw/'controls.stderr',
                     outer/'status.json',outer/'plan.json',outer/'command.log']:
            evidence[str(path.relative_to(ROOT))]=sha(path)
        assert not (result/'closure.json').exists()
        write(raw/'source-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
        (result/'terminal.json').write_bytes((outer/'status.json').read_bytes())
        write(result/'closure.json',dict(status='closed',all_hashes_verified=True,source_files=len(bindings),
            frozen_inputs=len(plan['frozen']),evidence_files=len(evidence),summary_sha256=sha(result/'summary.json'),
            source_bindings=str((raw/'source-bindings.json').relative_to(ROOT)),source_bindings_sha256=sha(raw/'source-bindings.json'),
            evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json'),
            terminal_sha256=sha(result/'terminal.json'),new_guest_commands=0,performance_measurement=False))
        print('Closed',RUN,len(plan['frozen']),'frozen inputs',flush=True)


if __name__=='__main__':
    if sys.argv[1:]==['--close']:close()
    else:
        assert len(sys.argv)==1
        main()
