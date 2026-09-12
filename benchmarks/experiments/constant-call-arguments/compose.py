#!/usr/bin/env python3
"""Retain the exact control VM while changing only the checked exporter."""
import hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from interpreter import installed_tools
from workflow_io import require_space,write_json as write

def main():
    run='constant-fold-compose-03'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,4)
        base_path=ROOT/'results/suite-profiling-build-02/summary.json'
        build_path=ROOT/'results/constant-fold-build-10/summary.json'
        base=json.loads(base_path.read_text());build=json.loads(build_path.read_text())
        assert base['status']==build['status']=='passed'
        assert build['tests']['test-debug']==build['tests']['test-release']==dict(passed=368,ignored=1)
        plan_path=ROOT/build['raw']/'plan.json';plan=json.loads(plan_path.read_text())
        assert sha(plan_path)==build['source_manifest_sha256'] and all(sha(ROOT/p)==h for p,h in plan['frozen'].items())
        status_path=ROOT/'.work/experiments/constant-fold-build-10/status.json';status=json.loads(status_path.read_text())
        assert status['status']=='finished' and status['returncode']==0 and status['owner']==str(ROOT)
        assert sha(status_path.with_name('plan.json'))==status['plan_sha256'] and sha(status_path.with_name('command.log'))==status['log_sha256']
        control,_=installed_tools(base['tool_key']);compiler,_=installed_tools(build['tool_key'])
        binaries=dict(build['binaries']);binaries['rust-interp-vm']=base['binaries']['rust-interp-vm']
        composition=dict(kind='retained-vm-exporter-candidate',schema_version=1,source_commit=build['source_commit'],
            vm_tool_key=base['tool_key'],exporter_tool_key=build['tool_key'],binaries=binaries)
        key=hashlib.sha256(json.dumps(composition,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
        verifier=work/'rust-interp-call-census';built_verifier=Path(plan['target'])/'release'/verifier.name
        shutil.copy2(built_verifier,verifier);assert sha(verifier)==sha(built_verifier)
        frozen_paths=[Path(__file__),Path(__file__).with_name('PROTOTYPE.md'),Path(__file__).with_name('NULL-QUALIFICATION.md'),base_path,build_path,plan_path,status_path,verifier]
        frozen_paths += [tool/n for tool in [control,compiler] for n in ['rust-interp-vm','rust-interp-mir-export','rust-interp-rustc-wrapper','source.json','capabilities.json','ready.json']]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in frozen_paths}
        write(work/'plan.json',dict(owner=str(ROOT),composition=composition,frozen=frozen,execution_qualified=False))
        with (ROOT/'.work/interpreter-tools.lock').open('a') as publication:
            acquire_lock(publication,45)
            destination=ROOT/'.work/interpreter-tools'/key;destination.mkdir(exist_ok=False)
            for name,digest in binaries.items():
                shutil.copy2((control if name=='rust-interp-vm' else compiler)/name,destination/name)
                assert sha(destination/name)==digest
            caps=json.loads((compiler/'capabilities.json').read_text());assert caps['bytecode_version']==5
            caps.update(tool_key=key,exporter_sha256=binaries['rust-interp-mir-export']);write(destination/'capabilities.json',caps)
            write(destination/'source.json',dict(tool_key=key,composition=composition,source_commit=build['source_commit'],files=frozen,
                source=str(ROOT),key_algorithm='SHA256 of canonical composition JSON'))
            write(destination/'ready.json',binaries)
        assert installed_tools(key)[0]==destination and all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/run;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='composed',execution_qualified=False,tool_key=key,composition=composition,binaries=binaries,
            baseline_tool_key=base['tool_key'],verifier=str(verifier.relative_to(ROOT)),verifier_sha256=sha(verifier),
            source_commit=build['source_commit'],build=str(build_path.relative_to(ROOT)),
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json')))
        print(key,flush=True)

if __name__=='__main__':main()
