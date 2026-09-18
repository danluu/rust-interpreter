"""Qualify launcher readmission while binding the unchanged, qualified Rust VM."""
import json, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
NAME='runtime-composition-launcher-01'
STD='bd27cc0f910e0c93a9a6cf088789ef526d36a8697a7717e08d7585f5d19467ef'
def read(p):return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        build_path=ROOT/'results/runtime-composition-build-01/summary.json';build=read(build_path)
        closure_path=build_path.with_name('closure.json');closed=read(closure_path)
        assert build['status']=='passed' and closed['all_hashes_verified'] and sha(build_path)==closed['summary_sha256']
        bp=ROOT/build['source_manifest'];assert sha(bp)==build['source_manifest_sha256']
        old=read(bp)['frozen']
        rust_paths=[p for p in old if p.startswith('crates/') or p in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']]
        assert all(sha(ROOT/p)==old[p] for p in rust_paths)
        paths=[ROOT/p for p in rust_paths]+[build_path,closure_path,bp]
        paths+=list((ROOT/'scripts').glob('*.py'))+list((ROOT/'tests').glob('*.py'))
        paths+=list(Path(__file__).parent.glob('*.py'))+list(Path(__file__).parent.glob('*.md'))
        std=ROOT/'.work/std-mir'/STD;ready=std/'ready.json';prior=read(ready)
        paths += [ready]+[std/n for n in prior['artifacts']]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            frozen=frozen,expected_commands=2,guest_commands=0,unchanged_rust_inputs=len(rust_paths),performance_measurement=False))
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',RUST_TEST_THREADS='2')
        records=[]
        for label,command in [('python',[sys.executable,'-m','unittest','discover','-s','tests','-v']),
                ('readmit',[sys.executable,'scripts/std_mir.py'])]:
            require_space(ROOT,8)
            child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=work/'active.json',receipt=dict(label=label))
            for stream,payload in [('stdout',out),('stderr',err)]:(work/(label+'.'+stream)).write_text(payload)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,
                stdout_sha256=sha(work/(label+'.stdout')),stderr_sha256=sha(work/(label+'.stderr'))))
            write(work/'records.json',records);assert child.returncode==0,(out+err)[-6000:]
            if label=='python':
                assert 'Ran 443 tests' in err and err.rstrip().endswith('OK (skipped=22)')
                assert 'test_std_mir_readmission' in err and 'test_std_runtime_selection' in err
            else:
                assert json.loads(out)['key']==STD
            assert all(sha(ROOT/p)==h for p,h in frozen.items())
            print(label,'passed',flush=True)
        device=(std/next(iter(prior['artifacts']))).stat().st_dev
        receipt=std/f'readmission-{sha(ready)}-{device}.json';proof=read(receipt)
        assert proof['ready_sha256']==sha(ready) and proof['old_devices']==[16777231] and proof['new_devices']==[16777229]
        assert len(proof['artifacts'])==len(prior['artifacts'])==26
        for name,item in proof['artifacts'].items():
            info=(std/name).stat()
            assert item['stamp']==[info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns]
            assert item['sha256']==sha(std/name)==prior['artifacts'][name]['sha256']
        out=ROOT/'results'/NAME;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',commands=2,python=dict(discovered=443,passed=421,skipped=22),
            unchanged_rust_inputs=len(rust_paths),vm_tool_key=build['tool_key'],rust_tests_reused=build['tests'],
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),
            readmission=str(receipt.relative_to(ROOT)),readmission_sha256=sha(receipt),all_26_std_hashes_match=True,
            historical_manifest_unchanged=True,guest_commands=0,performance_measurement=False))
if __name__=='__main__':main()
