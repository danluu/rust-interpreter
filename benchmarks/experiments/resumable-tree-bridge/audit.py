"""Close the completed bridge screen with its source, artifact and setup proofs."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import screen

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        names=['tree-bridge-build-01','tree-bridge-qualification-01','tree-bridge-controls-01',
            'tree-bridge-profile-01','tree-bridge-screen-protocol-01','tree-bridge-screen-token-01']
        frozen={};evidence={};proofs=[]
        def retain(path,expected=None):
            path=Path(path);digest=sha(path)
            if expected is not None:assert digest==expected,path
            key=str(path.relative_to(ROOT));assert key not in evidence or evidence[key]==digest
            evidence[key]=digest
        for name in names:
            directory=ROOT/'results'/name;path=directory/'summary.json';proof=json.loads(path.read_text())
            assert proof['status']=='passed';proofs.append(proof);retain(path)
            raw=ROOT/proof['raw'];outer=ROOT/'.work/experiments'/name
            terminal=directory/'terminal.json';final=json.loads(terminal.read_text())
            assert final['status']=='finished' and final['returncode']==0 and final['owner']==final['cwd']==str(ROOT)
            assert final==json.loads((outer/'status.json').read_text())
            retain(terminal);retain(outer/'plan.json',final['plan_sha256']);retain(outer/'command.log',final['log_sha256'])
            if 'source_manifest' in proof:
                plan=ROOT/proof['source_manifest'];retain(plan,proof['source_manifest_sha256'])
                inputs=json.loads(plan.read_text())['frozen'];records=proof['commands']
                assert records==json.loads((raw/'commands.json').read_text());retain(raw/'commands.json')
                for record in records:
                    assert record['returncode']==0
                    for suffix in ['stdout','stderr']:retain(raw/(record['label']+'.'+suffix),record[suffix+'_sha256'])
            elif 'inputs_sha256' in proof:
                plan=raw/'inputs.json';retain(plan,proof['inputs_sha256']);inputs=json.loads(plan.read_text())
                for item in ['stdout','stderr','active.json']:retain(raw/item)
            else:
                plan=raw/'plan.json';retain(plan,proof['plan_sha256']);inputs=json.loads(plan.read_text())['frozen']
                retain(raw/'records.json',proof['records_sha256'])
                records=json.loads((raw/'records.json').read_text())
                for record in records:
                    for suffix in ['stdout','stderr']:
                        if suffix+'_sha256' in record:retain(ROOT/record[suffix],record[suffix+'_sha256'])
            for path,digest in inputs.items():
                assert path not in frozen or frozen[path]==digest,path
                frozen[path]=digest
        build,strict,controls,profile,harness,result=proofs
        assert build['tests']=={'test-debug':556,'test-release':556}
        setup_path=ROOT/'results/tree-bridge-build-01/setup-accounting.json';setup=json.loads(setup_path.read_text())
        assert setup['status']=='passed' and setup['tool_key']==build['tool_key']
        assert setup['qualification_summary_sha256']==sha(ROOT/'results/tree-bridge-build-01/summary.json');retain(setup_path)
        assert strict['commands']==119 and strict['jit_tree_bridge'] and strict['source_restored'] and strict['automatic_cache_qualified']
        assert controls['launcher_tests']==harness['launcher_tests']==386 and controls['profile_controls']==6
        assert controls['launcher_skipped']==harness['launcher_skipped']==16 and harness['tests']==13
        assert harness['launcher_source_hashes_match'] and harness['launcher_commands_reused']==1
        assert strict['tool_key']==profile['tool_key']==build['tool_key']
        assert profile['commands']==3 and profile['exact_logical_counts_memory_and_entropy'] and profile['exact_backend_accounting']
        for case in profile['comparisons']:
            base=ROOT/profile['raw'];index=case['index']
            for suffix,key in [('profile.json','profile_sha256'),('accounting.json','accounting_sha256'),
                ('code/map.json','code_map_sha256'),('code/code.bin','code_sha256')]:
                retain(base/(str(index)+'-'+suffix),case[key])
            assert case['statistics']['jit_declined_functions']==0 and case['statistics']['jit_tree_entries']>0
        assert result['commands']==40 and result['source_restored'] and result['test_source_unchanged']
        assert result['native_assertion_outcomes_match'] and result['candidate_control_bytecode_matches']
        raw=ROOT/result['raw'];plan=json.loads((raw/'plan.json').read_text());rows=json.loads((raw/'records.json').read_text())
        recalculated=screen.assessment(rows);assert all(result[key]==value for key,value in recalculated.items())
        for name in ['transitions','space']:retain(raw/(name+'.json'),result[name+'_sha256'])
        source=ROOT/'.work/sources/fre'
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==plan['revision']
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
        assert sha(source/plan['case']['file'])==plan['original_source_sha256']
        retained={}
        for row in rows:
            if row['mode'] in screen.CUSTOM:assert row['launch']['jit_tree_bridge'] is (row['mode']=='candidate')
            for kind in ['artifact','catalog','entry_catalog','selection','native_executable','cargo_timing']:
                if kind in row:
                    item=row[kind];assert item['path'] not in retained or retained[item['path']]==item['sha256']
                    retained[item['path']]=item['sha256'];retain(ROOT/item['path'],item['sha256'])
        assert retained and all(sha(ROOT/path)==digest for path,digest in frozen.items())
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();bindings=[]
        for path,digest in sorted(frozen.items()):
            if path.startswith(('crates/','scripts/','benchmarks/','tests/')) or path in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:
                spec=revision+':'+path;body=subprocess.check_output(['git','show',spec],cwd=ROOT)
                assert hashlib.sha256(body).hexdigest()==digest;bindings.append(dict(path=path,sha256=digest,git_source=spec))
        focused=ROOT/'results/tree-bridge-focused-closure-01';closure=json.loads((focused/'summary.json').read_text())
        assert closure['status']=='passed' and closure['runs']==6 and closure['source_bindings']==1202
        retain(focused/'summary.json');retain(focused/'manifest.json',closure['manifest_sha256']);retain(focused/'evidence.tar.gz',closure['archive_sha256'])
        for name in ['tree-bridge-real-controls-01','tree-bridge-full-01']:assert not (ROOT/'.work'/name).exists()
        out=ROOT/'results/tree-bridge-screen-token-01';assert not (out/'closure.json').exists()
        write(out/'source-bindings.json',dict(source_revision=revision,files=bindings))
        write(out/'closure.json',dict(status='passed',performance_gate_passed=result['gate_passed'],parked=not result['gate_passed'],
            full_comparison_commands=0,held_out_commands=0,repeated_screen_commands=0,
            unique_frozen_inputs=len(frozen),retained_artifacts_verified=len(retained),source_bindings=len(bindings),
            source_bindings_sha256=sha(out/'source-bindings.json'),evidence=evidence,auditor_sha256=sha(Path(__file__))))
        print('closed bridge screen:',len(frozen),'inputs,',len(retained),'artifacts,',len(bindings),'Git bindings',flush=True)

if __name__=='__main__':main()
