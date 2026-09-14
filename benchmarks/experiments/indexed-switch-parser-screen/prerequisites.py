"""Bind the qualified runtime and the previously measured full-parser controls."""
import json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
from compare_saved_runtime import sha
from interpreter import installed_tools
BASELINE='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
ANCHOR='4a1381c40d6b412aa613aa1ae4ba4eea0fc6a290fae143d96af48101eb1fc177'

def read(p):return json.loads(p.read_text())

def load():
    paths=[]
    def closed(name):
        folder=ROOT/'results'/name
        summary=read(folder/'summary.json');closure=read(folder/'closure.json')
        assert summary['status']=='passed' and closure['status']=='closed'
        assert sha(folder/'summary.json')==closure['summary_sha256']
        assert sha(folder/'terminal.json')==closure['terminal_sha256']
        terminal=read(folder/'terminal.json')
        assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==str(ROOT)
        paths.extend(folder/n for n in ['summary.json','closure.json','terminal.json'])
        for field in ['bindings','source_bindings']:
            if field in closure:
                binding=ROOT/closure[field];assert sha(binding)==closure[field+'_sha256'];paths.append(binding)
                for path,digest in read(binding).get('artifacts',{}).items():
                    assert sha(ROOT/path)==digest;paths.append(ROOT/path)
        return summary
    candidate=closed('indexed-switches-build-02')
    strict=closed('indexed-switches-qualification-01')
    small=closed('indexed-switches-profile-02')
    parser=closed('indexed-switches-parser-profile-01')
    assert candidate['tests']['test-debug']==candidate['tests']['test-release']>=612
    assert candidate['python']['passed']>=408 and candidate['python']['skipped']==22
    assert candidate['composition']['kind']=='indexed-switches'
    assert strict['commands']==122 and strict['source_restored'] and strict['automatic_cache_qualified']
    assert strict['strict_rejections']==['type','borrow'] and strict['actual_demand_artifact']
    assert strict['indexed_partial_artifact_rejections']==strict['scalar_partial_artifact_rejections']==1
    assert small['commands']==3 and small['exact_per_pc_counts'] and small['exact_operation_map_reconstruction']
    assert small['operation_map_schema']==2
    assert parser['commands']==1 and parser['exact_per_pc_counts_memory_entropy'] and parser['exact_operation_map_reconstruction']
    assert parser['indexed_switches'] is True and parser['exact_native_bytes_after_bound_relocation']
    assert all(s['tool_key']==candidate['tool_key'] for s in [strict,small,parser])
    manifest=ROOT/candidate['source_manifest'];assert sha(manifest)==candidate['source_manifest_sha256'];paths.append(manifest)
    for name,digest in read(manifest)['frozen'].items():
        if name.startswith(('crates/','scripts/','tests/')) or name in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:
            assert sha(ROOT/name)==digest,('qualified source changed',name);paths.append(ROOT/name)
    adopted_path=ROOT/'results/scratch-scalar-main-qualification-01/summary.json'
    adopted=read(adopted_path);assert adopted['status']=='passed' and adopted['tool_key']==BASELINE
    assert candidate['matched_control']['tool_key']==BASELINE and candidate['matched_control']['binaries']==adopted['binaries']
    prior_path=ROOT/'results/scratch-memory-values-build-02/summary.json';prior=read(prior_path)
    assert prior['status']=='passed' and prior['tool_key']==BASELINE and prior['binaries']==adopted['binaries']
    anchor=prior['matched_control'];assert anchor['tool_key']==ANCHOR
    history=closed('scratch-memory-values-parser-edits-incremental-01')
    assert history['commands']==88 and history['original_tests']==114 and history['exact_native_test_outcomes']
    assert history['tool_keys']==dict(baseline=ANCHOR,duplicate=ANCHOR,candidate=BASELINE)
    paths += [adopted_path,prior_path]
    for build in [candidate,adopted,anchor]:
        tools,key=installed_tools(build['tool_key']);assert key==build['tool_key']
        for name,digest in build['binaries'].items():
            assert sha(tools/name)==digest;paths.append(tools/name)
        for name in ['rust-interp-mir-export','rust-interp-rustc-wrapper']:
            assert build['binaries'][name]==adopted['binaries'][name]
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
    return adopted,candidate,paths
