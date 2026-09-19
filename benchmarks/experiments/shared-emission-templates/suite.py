"""Check the explicit suite option and original-workload sharing coverage."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from interpreter import installed_tools
from suite_reports import read_report,validate_report,validate_runtime_limits,validate_shared_templates
from workflow_io import capture,require_space,write_json as write

RUN='shared-emission-templates-suite-01'
BASELINE='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'

def read(p):return json.loads(p.read_text())

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        frozen={}
        def bind(path,digest=None):
            path=Path(path);value=sha(path)
            if digest is not None:assert value==digest,path
            frozen[str(path.relative_to(ROOT))]=value
            return read(path) if path.suffix=='.json' else path
        build_folder=ROOT/'results/shared-emission-templates-build-01'
        closed=bind(build_folder/'closure.json');assert closed['status']=='closed' and closed['all_hashes_verified']
        build=bind(build_folder/'summary.json',closed['summary_sha256'])
        assert build['status']=='passed' and build['composition']['kind']=='shared-suite-emission-templates'
        assert build['composition']['compiler_source_key']==BASELINE
        source=bind(ROOT/build['source_manifest'],build['source_manifest_sha256'])
        for p,h in source['frozen'].items():
            if p.startswith(('crates/','scripts/','tests/')) or p in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:bind(ROOT/p,h)
        strict_folder=ROOT/'results/shared-emission-templates-qualification-01'
        closed=bind(strict_folder/'closure.json');assert closed['status']=='closed' and closed['logs_verified']
        strict=bind(strict_folder/'summary.json',closed['summary_sha256'])
        assert strict['status']=='passed' and strict['commands']==121 and strict['tool_key']==build['tool_key']
        strict_raw=ROOT/strict['raw'];bind(strict_raw/'plan.json',strict['plan_sha256']);bind(strict_raw/'records.json',strict['records_sha256'])
        partial=bind(strict_raw/'demand.rbc');assert int.from_bytes(partial.read_bytes()[:4],'little')==(5|(1<<16))
        tool,key=installed_tools(build['tool_key']);assert key==build['tool_key']
        for n,h in build['binaries'].items():bind(tool/n,h)
        vm=tool/'rust-interp-vm'

        def history(run,states,count):
            folder=ROOT/'results'/run;closed=bind(folder/'closure.json')
            assert closed['status']=='closed' and (closed.get('all_hashes_verified') or closed.get('all_retained_artifacts_and_sources_verified'))
            summary=bind(folder/'summary.json',closed['summary_sha256']);assert summary['status']=='passed'
            assert summary['tool_keys']['baseline']==BASELINE
            raw=ROOT/summary['raw']
            plan=bind(raw/'plan.json',summary.get('plan_sha256') or summary['evidence']['plan'])
            records=bind(raw/'records.json',summary.get('records_sha256') or summary['evidence']['records'])
            cases=[]
            for state in states:
                old=next(r for r in records if r['cycle']==0 and r['state']==state and r['mode']=='baseline')
                artifact=ROOT/old['artifact']['path'];bind(artifact,old['artifact']['sha256'])
                catalog=ROOT/old['entry_catalog']['path'];entries=bind(catalog,old['entry_catalog']['sha256'])
                names=[e['name'] for e in entries['entries']];assert len(names)==len(set(names))==count
                prior_path=Path(old['launch']['suite_report_path']);prior=bind(prior_path,old['suite_sha256'])
                outcomes=validate_report(prior,names,'prepared',state!=-1)
                assert [list(row) for row in outcomes]==old['outcomes']
                validate_runtime_limits(prior,100000000000,150000,required=True)
                assert old['launch']['tool_key']==BASELINE
                cases.append(dict(name=('pgrust-parser' if count==114 else 'rg-aot')+('-wrong' if state==-1 else '-original'),
                    artifact=artifact,catalog=catalog,names=names,outcomes=outcomes,success=state!=-1))
            return cases
        cases=history('runtime-composition-parser-edits-incremental-01',[0,-1],114)
        private,=history('runtime-composition-edit-rg-aot-02',[0],1);cases.append(private)
        for path in Path(__file__).parent.iterdir():
            if path.suffix in ['.py','.md']:bind(path)
        for n in ['workflow_io.py','compare_saved_runtime.py','suite_reports.py','native_suite.py','interpreter.py']:bind(ROOT/'scripts'/n)
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        variants=[('ordinary-two',False,2),('shared-one',True,1),('shared-two',True,2)]
        schedule=[dict(case=c['name'],variant=v,sharing=sharing,requested_workers=workers)
                  for c in cases for v,sharing,workers in (variants if len(c['names'])>1 else [variants[2]])]
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],tool_key=key,
            schedule=schedule,expected_commands=13,original_project_guest_commands=7,
            initial_minimum_gib=12,minimum_child_gib=8,source_edits=0,performance_measurement=False,
            native_outcomes_reused=True,entropy='ordinary OS',scope='original assertions and sharing coverage; no latency comparison'))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        records=[];outputs={};coverage=[];write(raw/'records.json',records)
        def invoke(label,command,expected):
            require_space(ROOT,8);command=list(map(str,command));start=time.time()
            child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(label=label))
            for stream,value in [('stdout',out),('stderr',err)]:(raw/(label+'.'+stream)).write_text(value)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,
                expected_returncode=expected,seconds=time.time()-start,
                stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr'))))
            write(raw/'records.json',records)
            assert child.returncode==expected,(label,err[-3000:])
            assert all(sha(ROOT/p)==h for p,h in frozen.items())
            return out,err
        for scheduled in schedule:
            c=next(c for c in cases if c['name']==scheduled['case']);label=c['name']+'-'+scheduled['variant']
            report_path=raw/(label+'.json');sharing=scheduled['sharing'];workers=scheduled['requested_workers']
            command=[vm,'--engine','jit','--jit-resumable-calls','--jit-persistent-registers','--jit-scalar-calls',
                '--isolated-batch','prepared','--suite-workers',str(workers),'--suite-report',report_path,
                '--suite-catalog',c['catalog'],'--instruction-limit','100000000000','--allocation-limit','150000']
            if sharing:command+=['--jit-shared-templates']
            out,err=invoke(label,[*command,c['artifact']],0 if c['success'] else 1)
            report,digest=read_report(report_path);outputs[str(report_path.relative_to(ROOT))]=digest
            assert validate_report(report,c['names'],'prepared',c['success'])==c['outcomes']
            validate_runtime_limits(report,100000000000,150000,required=True);validate_shared_templates(report,sharing)
            assert report['requested_workers']==workers and report['workers']==min(workers,len(c['names']))
            assert out==('0\n' if c['success'] else '')
            totals={k:sum(t.get('shared_templates',{}).get(k,0) for t in report['tests']) for k in ['hits','misses','restored_code_bytes']}
            coverage.append(dict(scheduled,**totals,tests=len(c['names']),storage=report.get('shared_templates',{}).get('storage')))
            print(label,'qualified',totals,flush=True)

        original=cases[0];report_path=raw/'rejected-suite.json'
        batch=['--isolated-batch','prepared','--suite-report',report_path]
        common=['--engine','jit','--jit-resumable-calls','--jit-shared-templates']
        rejects=[('no-batch',common,original['artifact'],'shared templates require a prepared isolated batch'),
            ('fresh',common+['--isolated-batch','fresh','--suite-report',report_path],original['artifact'],'shared templates require a prepared isolated batch'),
            ('interpreter',['--engine','interpreter','--jit-resumable-calls','--jit-shared-templates',*batch],original['artifact'],'isolated batches require resumable JIT execution'),
            ('no-resumable',['--engine','jit','--jit-shared-templates',*batch],original['artifact'],'isolated batches require resumable JIT execution'),
            ('duplicate',['--jit-shared-templates','--jit-shared-templates'],original['artifact'],'duplicate shared template option'),
            ('partial',common+batch,partial,'isolated test batches require fully checked bytecode')]
        for label,flags,artifact,message in rejects:
            out,err=invoke('reject-'+label,[vm,*flags,artifact],1)
            assert not out and message in err and not report_path.exists()
            print('reject-'+label,'qualified',flush=True)
        assert len(records)==13
        active=[r for r in coverage if r['requested_workers']==2 and r['sharing'] and r['tests']>1]
        assert len(active)==2
        # Preserve a zero-hit observation as a mechanism failure; never silently retry.
        observed=all(r['hits']>0 for r in active)
        destination=ROOT/'results'/RUN;destination.mkdir(exist_ok=False)
        write(destination/'summary.json',dict(status='passed',source_revision=revision,tool_key=key,
            commands=len(records),coverage=coverage,sharing_observed_in_both_parser_states=observed,
            mechanism_gate_passed=observed,original_project_guest_commands=7,cli_rejections=6,
            original_assertions_unchanged=True,native_outcomes_reused=True,source_edits=0,performance_measurement=False,
            raw=str(raw.relative_to(ROOT)),plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),outputs=outputs))

if __name__=='__main__':main()
