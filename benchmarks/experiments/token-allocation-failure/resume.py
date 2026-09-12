#!/usr/bin/env python3
"""Correct the recorded token budget and finish actual-export catalog qualification."""
import hashlib,json,os,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write,SourceEdit
from workflow_cases import WORKFLOW_VARIANTS
from workflow_measurements import source_states
from interpreter import installed_tools
from native_suite import test_status
from suite_reports import read_report,validate_report


def main():
    run='prepared-catalog-token-corrected-02'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        prior=ROOT/'.work/prepared-catalog-token-01';old=json.loads((prior/'plan.json').read_text())
        old_rows=json.loads((prior/'records.json').read_text());assert len(old_rows)==4
        terminal=json.loads((ROOT/'.work/experiments/prepared-catalog-token-01/status.json').read_text())
        assert terminal['owner']==str(ROOT) and terminal['status']=='finished' and terminal['returncode']==1
        ref_path=ROOT/'results/export-reuse-screen-token-01/summary.json';reference=json.loads(ref_path.read_text())
        assert reference['allocation_limit']==150000 and old.get('allocation_limit') is None
        names=old['tests'];case=WORKFLOW_VARIANTS['fre',reference['workflow']];assert names==case['tests']
        source=ROOT/'.work/sources/fre';path=source/case['file'];original=path.read_bytes()
        assert sha(path)==old['original_sha256']
        marker=source/'.rust-interp-owned.json';owner=json.loads(marker.read_text())
        assert owner['owner']==str(ROOT) and owner['revision']==reference['revision']==old['revision']
        edited=list(source_states(original.decode(),case,1,['native','baseline','candidate'],True))[-1]['source']
        assert hashlib.sha256(edited).hexdigest()==old['executed_source_sha256']
        tool,key=installed_tools(old['tool_key'])
        artifact=ROOT/'.work/prepared-catalog-token-diagnose-01/program.rbc'
        catalog=Path(str(artifact)+'.entries.json')
        original_launch=[json.loads(line.removeprefix('rust-interp-launch: ')) for line in old_rows[-1]['stderr'].splitlines() if line.startswith('rust-interp-launch: ')][0]
        assert sha(artifact)==original_launch['artifact_sha256'] and sha(catalog)==original_launch['entry_catalog_sha256']
        work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
        entropy_path=ROOT/'results/fixed-frame-clear-entropy-check-01/summary.json';entropy=json.loads(entropy_path.read_text())
        library=ROOT/entropy['library'];assert entropy['status']=='passed' and sha(library)==entropy['library_sha256']
        frozen_paths=[Path(__file__),Path(__file__).with_name('PLAN.md'),ref_path,prior/'plan.json',prior/'records.json',marker,artifact,catalog,entropy_path,library]
        frozen_paths += [ROOT/'scripts'/name for name in ['interpreter.py','workflow_io.py','workflow_cases.py','workflow_measurements.py','native_suite.py','suite_reports.py','compare_saved_runtime.py']]
        frozen_paths += [tool/name for name in ['rust-interp-vm','rust-interp-mir-export','rust-interp-rustc-wrapper']]
        for row in old_rows[:3]:
            native=Path(row['command'][0]);assert sha(native)==old['frozen'][str(native.relative_to(ROOT))]
            frozen_paths.append(native)
        frozen={str(p.relative_to(ROOT)):sha(p) for p in frozen_paths}
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,tool_key=key,allocation_limit=150000,
            previous_allocation_limit=100000,source_sha256=old['executed_source_sha256'],
            cache_namespace='prepared-catalog-token-01',minimum_child_gib=8,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_PROFILE_')) and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_TERM_COLOR='never',RUST_INTERP_LAUNCH_STATS='1',RUSTFLAGS=' '.join(old['guest_rustflags']))
        rows=[]
        def invoke(label,command,child_env=env):
            require_space(ROOT,8)
            child,stdout,stderr=capture(command,cwd=source,env=child_env,receipt_path=work/'active.json',receipt=dict(label=label))
            row=dict(label=label,command=command,returncode=child.returncode,stdout=stdout,stderr=stderr);rows.append(row);write(work/'records.json',rows)
            assert child.returncode==0,stderr
            return row
        with SourceEdit(path,original) as edit:
            edit.replace(edited)
            for row in old_rows[:3]:
                control=invoke(row['label'],row['command'])
                assert test_status(row['command'][2],control['returncode'],control['stdout'])=='passed'
            command=list(old_rows[-1]['command']);report_path=work/'exported-suite.json'
            assert '--allocation-limit' not in command
            command+=['--allocation-limit',str(reference['allocation_limit'])]
            command[command.index('--suite-report')+1]=str(report_path)
            row=invoke('corrected-export-and-execute',command)
            assert 'Checking fre-kernels' in row['stderr'] and path.read_bytes()==edited
            report,digest=read_report(report_path);validate_report(report,names,'fresh',True)
            launch=[json.loads(line.removeprefix('rust-interp-launch: ')) for line in row['stderr'].splitlines() if line.startswith('rust-interp-launch: ')][0]
            assert launch['allocation_limit']==reference['allocation_limit'] and launch['suite_report_sha256']==digest
            assert launch['artifact_sha256']==sha(artifact) and launch['entry_catalog_sha256']==sha(catalog)
            base=[str(tool/'rust-interp-vm'),'--engine','jit','--jit-resumable-calls','--jit-persistent-registers',
                  '--instruction-limit',str(reference['instruction_limit']),'--allocation-limit',str(reference['allocation_limit'])]
            ordinary=invoke('ordinary-batch',base+[str(artifact)]);assert ordinary['stdout']=='0\n'
            exact=[];consumption=[]
            for label,mode,action in [('fresh-record','fresh','record'),('fresh-replay','fresh','replay'),('prepared-replay','prepared','replay')]:
                output=work/(label+'.json')
                replay=dict(env,DYLD_INSERT_LIBRARIES=str(library),RUST_INTERP_ENTROPY_MODE=action,RUST_INTERP_ENTROPY_TAPE=str(work/'entropy.tape'))
                row=invoke(label,base+['--isolated-batch',mode,'--suite-report',str(output),'--suite-catalog',str(catalog),str(artifact)],replay)
                assert row['stdout']=='0\n'
                result,_=read_report(output);validate_report(result,names,mode,True)
                assert result['entry_source']=='artifact-bound catalog'
                exact.append([{k:t[k] for k in ['name','function','status','instructions','peak_guest_memory']} for t in result['tests']])
                consumption.append(re.findall(r'entropy_calls=(\d+) entropy_bytes=(\d+)',row['stderr']))
            assert exact[0]==exact[1]==exact[2] and consumption[0]==consumption[1]==consumption[2] and len(consumption[0])==1
        assert path.read_bytes()==original and all(sha(ROOT/p)==h for p,h in frozen.items())
        assert len(rows)==8
        out=ROOT/'results'/run;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',commands=8,native_tests=names,tool_key=key,
            actual_exported_catalog=True,isolated_tests=exact[0],entropy=consumption[0],source_restored=True,
            selected_source_sha256=old['executed_source_sha256'],artifact_sha256=sha(artifact),catalog_sha256=sha(catalog),
            allocation_limit=150000,prior_limit=100000,prior_failure='benchmark controller omitted the reference allocation limit',
            corrected_command_recompiled_source=True,bytecode_unchanged_by_runtime_limit=True,
            performance_measurement=False,raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json')))
        print('PASS: native, corrected actual export and exact fresh/prepared replay at the recorded allocation limit',flush=True)


if __name__=='__main__':main()
