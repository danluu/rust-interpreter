#!/usr/bin/env python3
"""Exercise real rustc entry catalogs, Result adapters, edits and strict borrow checking."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools, require_export_option
from suite_reports import read_report
from workflow_io import SourceEdit, capture, require_space, write_json as write

NAMES=['tests::first','tests::result_body','tests::constant_size','tests::constant_alignment']
SOURCE='''#[inline(never)]
fn successor(value: u64) -> u64 { value.wrapping_add(1) }
#[cfg(test)]
mod tests {
    #[test] fn first() { assert_eq!(super::successor(6), 7); }
    #[test] fn result_body() -> Result<(), &'static str> {
        if super::successor(12) != 13 { return Err("wrong successor"); }
        Ok(())
    }
    #[test] fn constant_size() { assert_eq!(core::mem::size_of::<u64>(), 8); }
    #[test] fn constant_alignment() { assert_eq!(core::mem::align_of::<u64>(), 8); }
}
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--build',type=Path,required=True)
    args=parser.parse_args();assert re.fullmatch(r'prepared-catalog-fixture-\d{2}',args.run_id)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        build_path=args.build.resolve();build=json.loads(build_path.read_text())
        assert build['status']=='passed' and all(c==dict(passed=322,ignored=1) for c in build['tests'].values())
        tool,key=installed_tools(build['tool_key']);require_export_option(tool,key,'entry-catalog')
        old,_=installed_tools('9ae791980111702fbe88b04e5fff74d6816218fba433701ab54b370447f9337b')
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
        source=work/'source';source.mkdir();path=source/'lib.rs';path.write_text(SOURCE)
        manifest=source/'Cargo.toml';manifest.write_text('[package]\nname="catalog-fixture"\nversion="0.0.0"\nedition="2024"\n[lib]\npath="lib.rs"\n[workspace]\n')
        (source/'Cargo.lock').write_text('version = 4\n\n[[package]]\nname = "catalog-fixture"\nversion = "0.0.0"\n')
        paths=[Path(__file__),Path(__file__).with_name('CATALOG.md'),build_path,manifest,source/'Cargo.lock']
        paths += [ROOT/'scripts'/name for name in ['interpreter.py','native_suite.py','suite_reports.py','workflow_io.py','std_mir.py']]
        paths += [tool/name for name in ['rust-interp-vm','rust-interp-mir-export','rust-interp-rustc-wrapper']]+[old/'rust-interp-vm']
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,tests=NAMES,tool_key=key,
            source_sha256=sha(path),scope='real compiler/catalog correctness; no performance measurement'))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_PROFILE_')) and
            k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER',
                      'CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never',RUST_INTERP_LAUNCH_STATS='1')
        records=[]
        def invoke(label,command):
            require_space(ROOT,8)
            child,stdout,stderr=capture(command,cwd=source,env=env,receipt_path=work/'active.json',receipt=dict(label=label))
            row=dict(label=label,command=command,returncode=child.returncode,stdout=stdout,stderr=stderr)
            records.append(row);write(work/'records.json',records)
            return row
        original=path.read_bytes()
        wrong=SOURCE.replace('wrapping_add(1)','wrapping_add(2)').encode()
        invalid=(SOURCE+"fn invalid_borrow() -> &'static str { let value = String::from(\"local\"); &value }\n").encode()
        marker=b'#[cfg(test)]\nmod tests {'
        assert original.split(marker)[1]==wrong.split(marker)[1]
        catalogs=[];legacy_rejected=False
        with SourceEdit(path,original) as edit:
            for state,payload in [('original',original),('wrong',wrong),('borrow-error',invalid),('restored',original)]:
                edit.replace(payload);outcomes=[];artifacts=[]
                for mode in ['native','fresh','prepared']:
                    report=work/(state+'-'+mode+'.json')
                    common=['--manifest-path',str(manifest),'--package','catalog-fixture','--jobs','2',
                            '--suite-report',str(report),*[a for name in NAMES for a in ['--entry',name]]]
                    if mode=='native':
                        command=[sys.executable,str(ROOT/'scripts/native_suite.py'),*common,'--target-dir',str(work/'native')]
                    else:
                        command=[sys.executable,str(ROOT/'scripts/interpreter.py'),*common,'--tool-key',key,'--test-body',
                            '--engine','jit','--jit-resumable-calls','--jit-persistent-registers','--inline-leaves','--std-mir',
                            '--cache-namespace',args.run_id+':'+mode,'--isolated-batch',mode]
                    row=invoke(state+'-'+mode,command)
                    if state=='borrow-error':
                        assert row['returncode']!=0 and 'E0515' in row['stderr'],row
                        if mode!='native':assert not report.exists()
                        continue
                    assert (row['returncode']==0)==(state!='wrong'),row
                    result,digest=read_report(report)
                    assert [t['name'] for t in result['tests']]==NAMES
                    outcomes.append([t['status'] for t in result['tests']])
                    assert result['passed']==(2 if state=='wrong' else 4) and result['failed']==(2 if state=='wrong' else 0)
                    if mode!='native':
                        assert result['entry_source']=='artifact-bound catalog'
                        launch=[json.loads(line.removeprefix('rust-interp-launch: ')) for line in row['stderr'].splitlines() if line.startswith('rust-interp-launch: ')][0]
                        assert launch['suite_report_sha256']==digest
                        catalog_path=Path(launch['entry_catalog_path']);catalog=json.loads(catalog_path.read_text())
                        assert catalog['entries'][1]['body_name'].startswith('Result test adapter: ')
                        artifact=Path(launch['artifact_path']);data=artifact.read_bytes()
                        assert hashlib.sha256(data).hexdigest()==catalog['artifact_sha256']==launch['artifact_sha256']
                        snapshot=work/(state+'-'+mode+'.rbc');snapshot.write_bytes(data)
                        write(work/(state+'-'+mode+'.entries.json'),catalog)
                        artifacts.append(catalog['artifact_sha256']);catalogs.append(dict(state=state,mode=mode,sha256=sha(catalog_path)))
                if state=='borrow-error':continue
                assert outcomes[0]==outcomes[1]==outcomes[2] and artifacts[0]==artifacts[1]
                retained=invoke(state+'-retained-vm',[str(old/'rust-interp-vm'),'--engine','jit','--jit-resumable-calls',
                    '--jit-persistent-registers',str(snapshot)])
                assert (retained['returncode']==0)==(state!='wrong'),retained
                if state=='original':
                    missing=work/'without-catalog.json'
                    rejected=invoke('optimized-root-without-catalog',[str(tool/'rust-interp-vm'),'--engine','jit',
                        '--jit-resumable-calls','--isolated-batch','prepared','--suite-report',str(missing),str(snapshot)])
                    assert rejected['returncode']!=0 and 'selected batch' in rejected['stderr'] and not missing.exists()
                    legacy_rejected=True
        assert path.read_bytes()==original and all(sha(ROOT/p)==h for p,h in frozen.items())
        assert len(records)==16 and legacy_rejected and len(catalogs)==6
        out=ROOT/'results'/args.run_id;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',commands=len(records),tests=NAMES,tool_key=key,
            catalogs=catalogs,result_adapter_verified=True,optimized_root_needs_catalog=True,
            wrong_edit_rejected=True,nonselected_borrow_error_rejected=True,source_restored=True,
            performance_measurement=False,raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json')))
        print('PASS: 16 commands; optimized entries, Result adapter, strict borrow checking and restoration',flush=True)


if __name__=='__main__':main()
