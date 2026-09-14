"""Close heap-bias setup, reused diagnostics and one changed-source primary."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import screen
from mechanism import verify

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
from suite_reports import validate_report

# Historical controllers remain bound even when a later controller fixed an
# assumption. No changed runtime source or benchmark history is spliced in.
STAGES=[('heap-address-focus-01','39278e11',0),
    ('heap-address-build-01','9498108a',1),('heap-address-build-02','fec35cac',0),
    ('heap-address-build-03','e8cb3c1f',0),('heap-address-qualification-01','b75b4214',0),
    ('heap-address-profile-01','0b4805ed',1),('heap-address-screen-protocol-01','baa6a467',0),
    ('heap-address-profile-02','bdfb6e25',1),('heap-address-screen-protocol-02','c48cf82f',0),
    ('heap-address-profile-03','c48cf82f',0),('heap-address-screen-token-01','d083a79f',0)]

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        # This is a read-only closure plus small JSON manifests, not a compiler
        # or guest replay. Reserve 2 GiB above the unchanged 8 GiB child floor.
        acquire_lock(lock,45);require_space(ROOT,10)
        evidence={};bindings={};bodies={};summaries={};inputs_count=0
        current=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        def retain(path,expected=None):
            path=Path(path);digest=sha(path)
            if expected is not None:assert digest==expected,path
            key=str(path.relative_to(ROOT));assert key not in evidence or evidence[key]==digest
            evidence[key]=digest
        def git_bind(path,digest,revision,archive=None):
            if archive is None and (ROOT/path).is_file() and sha(ROOT/path)==digest:revision=current
            spec=revision+':'+path
            if spec not in bodies:bodies[spec]=hashlib.sha256(subprocess.check_output(['git','show',spec])).hexdigest()
            assert bodies[spec]==digest,(spec,digest,bodies[spec])
            bindings[(path,digest,spec)]=dict(path=path,sha256=digest,git_source=spec)
            if archive is not None:retain(archive,digest)
        for name,revision,code in STAGES:
            raw=ROOT/'.work'/name;out=ROOT/'results'/name;outer=ROOT/'.work/experiments'/name
            final=json.loads((out/'terminal.json').read_text())
            assert final['owner']==final['cwd']==str(ROOT) and final['status']=='finished' and final['returncode']==code
            retain(out/'terminal.json');retain(outer/'status.json',sha(out/'terminal.json'))
            retain(outer/'plan.json',final['plan_sha256']);retain(outer/'command.log',final['log_sha256'])
            for p in out.iterdir():
                if p.is_file() and p.name not in ['closure.json','source-bindings.json','closure-terminal.json']:retain(p)
            if (out/'summary.json').exists():summaries[name]=json.loads((out/'summary.json').read_text())
            plan=raw/('inputs.json' if 'protocol' in name else 'plan.json')
            retain(plan);payload=json.loads(plan.read_text());frozen=payload if 'protocol' in name else payload['frozen']
            inputs_count+=len(frozen)
            for path,digest in frozen.items():
                if path.startswith(('crates/','scripts/','benchmarks/','tests/')) or path in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:
                    git_bind(path,digest,revision)
                else:retain(ROOT/path,digest)
            # Retain exact child streams and records, excluding compiler caches
            # and large program dumps, which are bound explicitly below.
            for p in raw.iterdir():
                if p.is_file():retain(p)
            if (raw/'commands.json').exists():
                for row in json.loads((raw/'commands.json').read_text()):
                    assert row['returncode']==0
                    for stream in ['stdout','stderr']:
                        p=raw/(row['label']+'.'+stream) if 'label' in row else raw/stream
                        retain(p,row[stream+'_sha256'])
            if name=='heap-address-qualification-01':
                for row in json.loads((raw/'records.json').read_text()):
                    for stream in ['stdout','stderr']:retain(ROOT/row[stream],row[stream+'_sha256'])
        build=summaries['heap-address-build-03'];old=summaries['heap-address-build-02']
        assert build['status']=='passed' and build['tests']=={'test-debug':553,'test-release':553}
        assert build['distinct_control_and_candidate_executables'] and build['tests_reused_from']=='results/heap-address-build-02/summary.json'
        control=build['matched_control']
        assert old['binaries']['rust-interp-vm']==control['binaries']['rust-interp-vm']!=build['binaries']['rust-interp-vm']
        assert json.loads((ROOT/'results/heap-address-build-02/assessment.json').read_text())['benchmark_commands']==0
        manifest=ROOT/control['source_manifest'];retain(manifest,control['source_manifest_sha256'])
        source=json.loads(manifest.read_text())
        for path,digest in source['files'].items():git_bind(path,digest,source['source_revision'],manifest.parent/'control-source'/path)
        for tool in [build,control]:
            base=ROOT/'.work/interpreter-tools'/tool['tool_key']
            assert json.loads((base/'ready.json').read_text())==tool['binaries']
            for name in ['ready.json','source.json','capabilities.json']:retain(base/name)
            for name,digest in tool['binaries'].items():retain(base/name,digest)
        for name in ['heap-address-focus-01','heap-address-build-02','heap-address-build-03']:
            proof=summaries[name];assert proof['status']=='passed'
        assert summaries['heap-address-focus-01']['tests']=={'debug':2,'release':2}
        strict=summaries['heap-address-qualification-01'];assert strict['commands']==119 and strict['tool_key']==build['tool_key']
        assert strict['source_restored'] and strict['automatic_cache_qualified']
        harness=summaries['heap-address-screen-protocol-02']
        assert (harness['tests'],harness['mechanism_controls'],harness['launcher_tests'],harness['launcher_skipped'])==(13,5,414,22)
        assert harness['launcher_commands_reused']==1
        profile=summaries['heap-address-profile-03'];assert screen.validate_matched_profile(build,profile)
        assert (profile['new_executions'],profile['reused_executions'])==(4,2)
        rows=json.loads((ROOT/profile['raw']/'records.json').read_text())
        assert len({r['pid'] for r in rows})==6 and all(r['returncode']==0 for r in rows)
        assert sum('reused_from' in r for r in rows)==2
        for row in profile['comparisons']:
            for path,key in [('profile_path','profile_sha256'),('operations_path','operation_map_sha256'),
                             ('map_path','code_map_sha256'),('code_path','code_sha256')]:retain(ROOT/row[path],row[key])
            if row['mode']=='candidate':
                prior,=[r for r in profile['comparisons'] if r['index']==row['index'] and r['mode']=='control']
                args=[]
                for item in [prior,row]:args.extend([json.loads((ROOT/item['operations_path']).read_text()),(ROOT/item['code_path']).read_bytes()])
                assert verify(*args)==row['mechanism']
        result=summaries['heap-address-screen-token-01'];raw=ROOT/result['raw']
        assert result['commands']==40 and result['source_restored'] and result['test_source_unchanged']
        assert result['native_assertion_outcomes_match'] and result['candidate_control_bytecode_matches']
        for name in ['plan','records','transitions','space']:retain(raw/(name+'.json'),result[name+'_sha256'])
        plan=json.loads((raw/'plan.json').read_text());rows=json.loads((raw/'records.json').read_text())
        assert all(result[k]==v for k,v in screen.assessment(rows).items())
        assert result['tool_keys']['baseline']==result['tool_keys']['duplicate']==control['tool_key']
        assert result['tool_keys']['candidate']==build['tool_key']
        artifacts={}
        for row in rows:
            success=row['state']!=-1
            assert (row['returncode']==0)==success
            if row['mode']=='native':assert row['outcomes']==[list(x) for x in screen.native_outcomes(row['stdout'],plan['names'],success)]
            else:
                command=row['command'];suite=Path(command[command.index('--suite-report')+1]);retain(suite,row['suite_sha256'])
                expected=sorted(validate_report(json.loads(suite.read_text()),plan['names'],'prepared',success))
                assert row['outcomes']==[list(x) for x in expected]
                assert row['launch']['tool_key']==result['tool_keys'][row['mode']]
            for kind in ['artifact','catalog','entry_catalog','selection','native_executable','cargo_timing']:
                if kind in row:
                    item=row[kind];retain(ROOT/item['path'],item['sha256']);artifacts[item['path']]=item['sha256']
        checkout=ROOT/'.work/sources/fre'
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=checkout,text=True).strip()==plan['revision']
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=checkout).strip()
        retain(checkout/plan['case']['file'],plan['original_source_sha256'])
        for name in ['heap-address-full-01','heap-address-real-controls-01']:assert not (ROOT/'.work'/name).exists()
        git_bind(str(Path(__file__).relative_to(ROOT)),sha(Path(__file__)),current)
        out=ROOT/'results/heap-address-screen-token-01';assert not (out/'closure.json').exists()
        write(out/'source-bindings.json',dict(files=list(bindings.values()),historical_controllers_preserved=True))
        write(out/'closure.json',dict(status='passed',performance_gate_passed=result['gate_passed'],parked=not result['gate_passed'],
            full_comparison_commands=0,held_out_commands=0,repeated_screen_commands=0,
            actual_profile_guest_executions=6,profile_prefix_executions_reused=True,
            rejected_tool_key=old['tool_key'],rejected_tool_benchmark_executions=0,
            frozen_input_references=inputs_count,source_bindings=len(bindings),retained_artifacts_verified=len(artifacts),
            source_bindings_sha256=sha(out/'source-bindings.json'),evidence=evidence,auditor_sha256=sha(Path(__file__))))
        print('closed heap-bias primary:',len(evidence),'evidence files,',len(bindings),'Git source bindings',flush=True)

if __name__=='__main__':main()
