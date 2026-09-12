#!/usr/bin/env python3
"""Qualify real selected-entry catalogs against retained native assertions."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools, require_export_option
from native_suite import test_status
from suite_reports import read_report, validate_report
from workflow_cases import WORKFLOWS, WORKFLOW_VARIANTS
from workflow_io import SourceEdit, capture, require_space, write_json as write
from workflow_measurements import source_states


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    parser.add_argument('--case',choices=['ruff','token'],default='ruff')
    args=parser.parse_args();assert re.fullmatch('prepared-catalog-'+args.case+r'-\d{2}',args.run_id)
    project='ruff' if args.case=='ruff' else 'fre'
    workflow='ruff' if args.case=='ruff' else 'token-phrase-allocation'
    package='ruff_linter' if args.case=='ruff' else 'fre-kernels'
    case=WORKFLOWS[project] if args.case=='ruff' else WORKFLOW_VARIANTS[project,workflow]
    start_floor=8.75 if args.case=='ruff' else 8.375
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,start_floor)
        build_path=ROOT/'results/prepared-catalog-build-02/summary.json';build=json.loads(build_path.read_text())
        assert build['status']=='passed' and build['tests']['test-release']==dict(passed=322,ignored=1)
        tool,key=installed_tools(build['tool_key']);require_export_option(tool,key,'entry-catalog')
        fixture=ROOT/'results/prepared-catalog-fixture-01/summary.json';assert json.loads(fixture.read_text())['status']=='passed'
        history_id='aggregate-relocation-heldout-01-ruff-retry-01' if args.case=='ruff' else 'export-reuse-screen-token-01'
        raw=ROOT/'.work/runs'/history_id
        reference_path=ROOT/'results'/history_id/'summary.json';reference=json.loads(reference_path.read_text())
        rows=json.loads((raw/'records.json').read_text());native_row=[row for row in rows if row['mode']=='native'][-1]
        assert native_row['state']==5 and native_row['calls'][0]['returncode']==0
        names=native_row['tests'];assert len(names)==(6 if args.case=='ruff' else 3) and names==case['tests']
        matches=re.findall(r'Running unittests src/lib.rs \(([^)]+)\)',native_row['calls'][0]['stderr']);assert len(matches)==1
        native=Path(matches[0]);assert native.is_relative_to(raw/'native') and not native.is_symlink()
        supervisor_path=ROOT/'.work/experiments'/history_id/'status.json';supervisor=json.loads(supervisor_path.read_text())
        assert supervisor['status']=='finished' and supervisor['returncode']==0 and supervisor['owner']==str(ROOT)
        assert native.stat().st_mtime<=supervisor['finished_at']
        source=ROOT/'.work/sources'/project;marker_path=source/'.rust-interp-owned.json';marker=json.loads(marker_path.read_text())
        assert marker['owner']==str(ROOT) and marker['revision']==reference['revision']
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==reference['revision']
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source,text=True).strip()
        path=source/case['file'];original=path.read_bytes()
        states=list(source_states(original.decode(),case,1,['native','baseline','candidate'],True))
        edited=states[-1]['source'];assert hashlib.sha256(edited).hexdigest()==native_row['source_sha256']
        entropy_path=ROOT/'results/fixed-frame-clear-entropy-check-01/summary.json';entropy=json.loads(entropy_path.read_text())
        library=ROOT/entropy['library'];assert entropy['status']=='passed' and sha(library)==entropy['library_sha256']
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
        paths=[Path(__file__),Path(__file__).with_name('CATALOG.md'),build_path,fixture,reference_path,raw/'records.json',
            supervisor_path,marker_path,native,entropy_path,library,source/'Cargo.toml',source/'Cargo.lock']
        paths += [ROOT/'scripts'/name for name in ['interpreter.py','native_suite.py','suite_reports.py','workflow_io.py',
            'workflow_cases.py','workflow_measurements.py','std_mir.py']]
        paths += [tool/name for name in ['rust-interp-vm','rust-interp-mir-export','rust-interp-rustc-wrapper']]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,tool_key=key,revision=reference['revision'],
            original_sha256=sha(path),executed_source_sha256=hashlib.sha256(edited).hexdigest(),tests=names,
            cargo_incremental=False,guest_rustflags=reference['guest_rustflags'],allocation_limit=reference.get('allocation_limit'),minimum_start_gib=start_floor,minimum_child_gib=8,
            scope='Actual custom export; matching retained native executable, no native rebuild or performance comparison'))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_PROFILE_')) and
            k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER',
                      'CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_TERM_COLOR='never',RUST_INTERP_LAUNCH_STATS='1')
        if reference['guest_rustflags']:env['RUSTFLAGS']=' '.join(reference['guest_rustflags'])
        records=[]
        def invoke(label,command,child_env=env):
            require_space(ROOT,8)
            child,stdout,stderr=capture(command,cwd=source,env=child_env,receipt_path=work/'active.json',receipt=dict(label=label))
            records.append(dict(label=label,command=command,returncode=child.returncode,stdout=stdout,stderr=stderr))
            write(work/'records.json',records);return records[-1]
        with SourceEdit(path,original) as edit:
            edit.replace(edited)
            for index,name in enumerate(names):
                row=invoke('native-'+str(index),[str(native),'--exact',name,'--test-threads=1'])
                assert test_status(name,row['returncode'],row['stdout'])=='passed'
            report_path=work/'exported-suite.json'
            command=[sys.executable,str(ROOT/'scripts/interpreter.py'),'--manifest-path',str(source/'Cargo.toml'),
                '--package',package,'--jobs','2','--tool-key',key,'--test-body','--std-mir','--inline-leaves',
                '--engine','jit','--jit-resumable-calls','--jit-persistent-registers',
                '--instruction-limit',str(reference['instruction_limit']),'--isolated-batch','fresh','--suite-report',str(report_path),
                '--cache-namespace',args.run_id,*[a for name in names for a in ['--entry',name]]]
            if reference.get('allocation_limit') is not None:
                command+=['--allocation-limit',str(reference['allocation_limit'])]
            for flag in ['trap-unsupported-calls','run-try-callbacks']:
                if reference.get(flag.replace('-','_')):command.append('--'+flag)
            row=invoke('export-and-execute',command);assert row['returncode']==0,row['stderr']
            assert 'Checking '+package in row['stderr'] and path.read_bytes()==edited
            report,digest=read_report(report_path);validate_report(report,names,'fresh',True)
            assert report['entry_source']=='artifact-bound catalog'
            launch=[json.loads(line.removeprefix('rust-interp-launch: ')) for line in row['stderr'].splitlines() if line.startswith('rust-interp-launch: ')][0]
            assert launch['suite_report_sha256']==digest
            artifact=work/'program.rbc';artifact.write_bytes(Path(launch['artifact_path']).read_bytes())
            catalog=work/'program.rbc.entries.json';catalog.write_bytes(Path(launch['entry_catalog_path']).read_bytes())
            assert sha(artifact)==launch['artifact_sha256']==json.loads(catalog.read_text())['artifact_sha256']
            base=[str(tool/'rust-interp-vm'),'--engine','jit','--jit-resumable-calls','--jit-persistent-registers',
                  '--instruction-limit',str(reference['instruction_limit'])]
            if reference.get('allocation_limit') is not None:base+=['--allocation-limit',str(reference['allocation_limit'])]
            normal=invoke('ordinary-batch',base+[str(artifact)]);assert normal['returncode']==0 and normal['stdout']=='0\n'
            exact=[];consumption=[]
            for label,mode,action in [('fresh-record','fresh','record'),('fresh-replay','fresh','replay'),('prepared-replay','prepared','replay')]:
                output=work/(label+'.json')
                replay=dict(env,DYLD_INSERT_LIBRARIES=str(library),RUST_INTERP_ENTROPY_MODE=action,RUST_INTERP_ENTROPY_TAPE=str(work/'entropy.tape'))
                row=invoke(label,base+['--isolated-batch',mode,'--suite-report',str(output),'--suite-catalog',str(catalog),str(artifact)],replay)
                assert row['returncode']==0 and row['stdout']=='0\n',row
                result,_=read_report(output);validate_report(result,names,mode,True)
                exact.append([{k:t[k] for k in ['name','function','status','instructions','peak_guest_memory']} for t in result['tests']])
                consumption.append(re.findall(r'entropy_calls=(\d+) entropy_bytes=(\d+)',row['stderr']))
            assert exact[0]==exact[1]==exact[2] and consumption[0]==consumption[1]==consumption[2] and len(consumption[0])==1
            if args.case=='ruff':
                absent=work/'without-catalog.json'
                rejected=invoke('missing-catalog',base+['--isolated-batch','prepared','--suite-report',str(absent),str(artifact)])
                assert rejected['returncode']!=0 and 'selected batch' in rejected['stderr'] and not absent.exists()
        assert path.read_bytes()==original and all(sha(ROOT/p)==h for p,h in frozen.items())
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source,text=True).strip()
        expected_rejections=int(args.case=='ruff')
        assert len(records)==len(names)+5+expected_rejections
        out=ROOT/'results'/args.run_id;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',case=args.case,commands=len(records),expected_rejections=expected_rejections,native_tests=names,tool_key=key,
            actual_exported_catalog=True,isolated_tests=exact[0],entropy=consumption[0],source_restored=True,
            selected_source_sha256=hashlib.sha256(edited).hexdigest(),artifact_sha256=sha(artifact),catalog_sha256=sha(catalog),
            performance_measurement=False,raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json')))
        print(f'PASS: actual {project} catalog, {len(names)} native assertions and exact isolated execution; source restored',flush=True)


if __name__=='__main__':main()
