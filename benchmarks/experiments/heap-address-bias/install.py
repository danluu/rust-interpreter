"""Build the candidate production VM in a fresh target; reuse verified tests."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from interpreter import installed_tools

NAME='heap-address-build-03'

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,14)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        prior_path=ROOT/'results/heap-address-build-02/summary.json'
        prior=json.loads(prior_path.read_text());assert prior['tests']=={'test-debug':553,'test-release':553}
        old=ROOT/prior['raw'];source_manifest=ROOT/prior['source_manifest']
        assert sha(source_manifest)==prior['source_manifest_sha256']
        frozen=json.loads(source_manifest.read_text())['frozen']
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        assert prior['binaries']['rust-interp-vm']==prior['matched_control']['binaries']['rust-interp-vm']
        assert json.loads((old/'commands.json').read_text())==prior['commands']
        for row in prior['commands']:
            assert row['returncode']==0
            for stream in ['stdout','stderr']:assert sha(old/(row['label']+'.'+stream))==row[stream+'_sha256']
        control=prior['matched_control'];control_tools,key=installed_tools(control['tool_key'])
        assert all(sha(control_tools/n)==h for n,h in control['binaries'].items())
        for p in [prior_path,ROOT/'results/heap-address-build-02/assessment.json',
            ROOT/'results/heap-address-build-02/terminal.json',source_manifest,old/'commands.json',old/'reuse.json',
            Path(__file__),ROOT/control['source_manifest'],ROOT/control['command_record']]:
            frozen[str(p.relative_to(ROOT))]=sha(p)
        work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False);target=work/'target'
        source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        write(work/'plan.json',dict(owner=str(ROOT),source_commit=source,frozen=frozen,
            target=str(target),test_source_manifest=prior['source_manifest'],reused_tests=prior['tests'],
            rejected_tool_key=prior['tool_key'],matched_control=control))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never',CARGO_INCREMENTAL='0',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',CARGO_PROFILE_RELEASE_DEBUG='1')
        command=['cargo','+nightly-2026-09-08','build','--release','--locked','--offline','--jobs','2',
            '--target-dir',str(target),'-p','rust-interp-bytecode','--bin','rust-interp-vm']
        started=time.time();free=shutil.disk_usage(ROOT).free;require_space(ROOT,8)
        child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=work/'active.json',receipt=dict(label='candidate-vm'))
        (work/'stdout').write_text(out);(work/'stderr').write_text(err)
        record=dict(command=command,pid=child.pid,returncode=child.returncode,started_at=started,finished_at=time.time(),
            stdout_sha256=sha(work/'stdout'),stderr_sha256=sha(work/'stderr'))
        write(work/'commands.json',[record]);assert child.returncode==0,err[-4000:]
        assert 'Compiling rust-interp-bytecode' in err
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        binaries=dict(control['binaries']);binaries['rust-interp-vm']=sha(target/'release/rust-interp-vm')
        assert binaries['rust-interp-vm']!=control['binaries']['rust-interp-vm'], 'candidate reused control executable'
        composition=dict(kind='heap-address-bias-composition',schema_version=1,source_commit=source,
            compiler_source_key=control['composition']['compiler_source_key'],binaries=binaries)
        key=hashlib.sha256(json.dumps(composition,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        with (ROOT/'.work/interpreter-tools.lock').open('a') as publication:
            acquire_lock(publication,45);installed=ROOT/'.work/interpreter-tools'/key;installed.mkdir(exist_ok=False)
            for name in binaries:shutil.copy2(target/'release'/name if name=='rust-interp-vm' else control_tools/name,installed/name)
            caps=json.loads(subprocess.check_output([str(installed/'rust-interp-mir-export'),'--rust-interp-capabilities'],env=env,text=True))
            caps.update(tool_key=key,exporter_sha256=binaries['rust-interp-mir-export']);write(installed/'capabilities.json',caps)
            write(installed/'source.json',dict(tool_key=key,composition=composition,files=frozen,source_commit=source,
                source=str(ROOT),key_algorithm='SHA256 of canonical composition JSON'))
            assert all(sha(installed/n)==h for n,h in binaries.items());write(installed/'ready.json',binaries)
        result=ROOT/'results'/NAME;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',source_commit=source,tool_key=key,binaries=binaries,
            composition=composition,matched_control=control,tests=prior['tests'],tests_reused_from=str(prior_path.relative_to(ROOT)),
            commands=[record],source_manifest=str((work/'plan.json').relative_to(ROOT)),source_manifest_sha256=sha(work/'plan.json'),
            raw=str(work.relative_to(ROOT)),performance_measurement=False,distinct_control_and_candidate_executables=True))
        write(result/'setup-accounting.json',dict(status='passed',tool_key=key,new_setup_seconds=time.time()-started,
            free_before=free,free_after=shutil.disk_usage(ROOT).free,qualified_test_setup=str(prior_path.relative_to(ROOT)),
            prior_setup_and_rejection_receipts=['results/heap-address-build-01/terminal.json','results/heap-address-build-02/setup-accounting.json'],
            definition='Fresh candidate VM build and installation; prior builds, passing tests and rejected publication are retained separately and are not zero-cost.',
            performance_measurement=False))
        print('PASS: source-bound 553 tests/profile reused; distinct candidate VM',key,binaries['rust-interp-vm'],flush=True)

if __name__=='__main__':main()
