#!/usr/bin/env python3
"""Compare full checked project listings with preserved original-source libtest binaries."""
import json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from interpreter import installed_tools,require_export_option
from test_discovery import read_listing
from workflow_io import capture,require_space,write_json as write


def main():
    run='test-discovery-real-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        build_path=ROOT/'results/test-discovery-build-01/summary.json';build=json.loads(build_path.read_text())
        assert build['status']=='passed' and all(v==dict(passed=325,ignored=1) for v in build['tests'].values())
        tool,key=installed_tools(build['tool_key']);require_export_option(tool,key,'list-tests')
        work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_PROFILE_')) and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_DEV_DEBUG='0',CARGO_PROFILE_TEST_DEBUG='0',CARGO_TERM_COLOR='never',RUST_INTERP_LAUNCH_STATS='1')
        frozen_paths=[Path(__file__),Path(__file__).with_name('PLAN.md'),build_path]
        frozen_paths += [ROOT/'scripts'/n for n in ['interpreter.py','test_discovery.py','workflow_io.py','std_mir.py']]
        frozen_paths += [tool/n for n in ['rust-interp-vm','rust-interp-mir-export','rust-interp-rustc-wrapper']]
        cases=[]
        for project,package,reference,count in [('pgrust','hashfn','prepared-catalog-pgrust-03',4),('fre','fre-kernels','prepared-suite-token-01',389)]:
            source=ROOT/'.work/sources'/project;marker=source/'.rust-interp-owned.json';owned=json.loads(marker.read_text())
            rp=ROOT/'results'/reference/'summary.json';report=json.loads(rp.read_text());ap=rp.with_name('isolated-assessment.json');assessment=json.loads(ap.read_text())
            assert owned['owner']==str(ROOT) and owned['revision']==report['revision']
            assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==report['revision']
            assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source,text=True).strip()
            assert assessment['status']=='passed' and assessment['source_restored'] and assessment['test_source_unchanged']
            restored=ROOT/assessment['raw']/'restoration.json';assert sha(restored)==assessment['restoration_sha256']
            native_row=[r for r in json.loads(restored.read_text()) if r['mode']=='native'];assert len(native_row)==1 and native_row[0]['returncode']==0
            np=ROOT/assessment['raw']/'native-restored.json';assert sha(np)==native_row[0]['suite_sha256']
            native=json.loads(np.read_text());assert native['status']=='passed' and native['build']['returncode']==0
            executable=Path(native['executable']);assert executable.is_file() and not executable.is_symlink() and executable.is_relative_to(ROOT/'.work/runs'/reference/'native')
            frozen_paths += [rp,ap,restored,np,executable,marker]
            for rel in subprocess.check_output(['git','ls-files','-z'],cwd=source).decode().split('\0'):
                if rel:frozen_paths.append(source/rel)
            cases.append(dict(project=project,package=package,revision=report['revision'],source=source,executable=executable,reference=reference,expected_count=count))
        frozen={str(p.relative_to(ROOT)):sha(p) for p in frozen_paths}
        write(work/'plan.json',dict(owner=str(ROOT),tool_key=key,frozen=frozen,minimum_child_gib=8,performance_measurement=False,native_control='Retained Cargo-reported executables from verified original-source restoration; list anew, without rebuilding.'))
        rows=[];results=[]
        def invoke(label,command,source):
            require_space(ROOT,8)
            child,stdout,stderr=capture(command,cwd=source,env=env,receipt_path=work/'active.json',receipt=dict(label=label))
            row=dict(label=label,command=command,returncode=child.returncode,stdout=stdout,stderr=stderr);rows.append(row);write(work/'records.json',rows)
            assert child.returncode==0,stderr;return row
        for case in cases:
            project=case['project'];source=case['source'];executable=case['executable']
            native=invoke(project+'-native-list',[str(executable),'--list','--format=terse'],source)
            names=sorted(line.removesuffix(': test') for line in native['stdout'].splitlines() if line.endswith(': test'))
            assert len(names)==len(set(names))==case['expected_count']
            native_ignored=invoke(project+'-native-ignored',[str(executable),'--list','--format=terse','--ignored'],source)
            ignored=sorted(line.removesuffix(': test') for line in native_ignored['stdout'].splitlines() if line.endswith(': test'))
            command=[sys.executable,str(ROOT/'scripts/interpreter.py'),'--manifest-path',str(source/'Cargo.toml'),'--package',case['package'],'--jobs','2','--tool-key',key,'--cache-namespace',run,'--std-mir','--test-body','--list-tests']
            row=invoke(project+'-custom-list',command,source);report=json.loads(row['stdout']);provenance=report['discovery_provenance']
            listing,digest=read_listing(Path(provenance['path']));assert digest==provenance['sha256'] and provenance['exporter_sha256']==sha(tool/'rust-interp-mir-export')
            assert [t['name'] for t in listing['tests']]==names
            assert [t['name'] for t in listing['tests'] if t['ignored']]==ignored
            snapshot=work/(project+'-tests.json');snapshot.write_bytes(Path(provenance['path']).read_bytes())
            results.append(dict(project=project,package=case['package'],revision=case['revision'],count=len(names),ignored=len(ignored),should_panic=sum(t['should_panic'] for t in listing['tests']),names_match_native=True,ignored_match_native=True,executed=False,listing_path=str(snapshot.relative_to(ROOT)),listing_sha256=digest,native_executable_sha256=sha(executable),native_reference=case['reference']))
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/run;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',commands=len(rows),cases=results,tool_key=key,performance_measurement=False,source_unchanged=True,raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json')))
        print('PASS: full pgrust/fre names and ignore selection match native libtest',flush=True)


if __name__=='__main__':main()
