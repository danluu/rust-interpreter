"""Require closed runtime, strict-checking and original-suite coverage evidence."""
import json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
from compare_saved_runtime import sha
from interpreter import installed_tools
BASELINE='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
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
        for field in ['bindings','source_bindings','evidence']:
            if field in closure:
                binding=ROOT/closure[field];assert sha(binding)==closure[field+'_sha256'];paths.append(binding)
        return summary
    candidate=closed('emitter-register-workspace-build-01')
    strict=closed('emitter-register-workspace-qualification-01')
    reconstructed=closed('emitter-register-workspace-reconstruction-01')
    assert candidate['tests']['test-debug']==candidate['tests']['test-release']>=615
    assert candidate['python']['passed']>=434 and candidate['python']['skipped']==22
    assert candidate['composition']['kind']=='bounded-emitter-register-workspace'
    assert strict['commands']==121 and strict['source_restored'] and strict['automatic_cache_qualified']
    assert strict['strict_rejections']==['type','borrow'] and strict['actual_demand_artifact']
    assert reconstructed['commands']==2 and reconstructed['guest_commands']==reconstructed['executable_code_publications']==0
    assert [(c['ordinary_functions'],c['scalar_bodies_reconstructed']) for c in reconstructed['cases']]==[(1050,60),(1245,69)]
    assert all(c['exact_full_function_reconstruction'] and c['complete_small_memory_partition'] for c in reconstructed['cases'])
    assert strict['tool_key']==candidate['tool_key']
    for path,digest in reconstructed['outputs'].items():assert sha(ROOT/path)==digest;paths.append(ROOT/path)
    manifest=ROOT/candidate['source_manifest'];assert sha(manifest)==candidate['source_manifest_sha256'];paths.append(manifest)
    for name,digest in read(manifest)['frozen'].items():
        if name.startswith(('crates/','scripts/','tests/')) or name in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:
            assert sha(ROOT/name)==digest,('qualified source changed',name);paths.append(ROOT/name)
    adopted_path=ROOT/'results/scratch-scalar-main-qualification-01/summary.json'
    adopted=read(adopted_path);assert adopted['status']=='passed' and adopted['tool_key']==BASELINE
    assert candidate['matched_control']['tool_key']==BASELINE and candidate['matched_control']['binaries']==adopted['binaries']
    history=closed('runtime-composition-parser-edits-incremental-01')
    assert history['commands']==88 and history['original_tests']==114 and history['exact_native_test_outcomes']
    assert history['tool_keys']['baseline']==history['tool_keys']['duplicate']==BASELINE
    paths += [adopted_path,ROOT/'benchmarks/experiments/emitter-register-workspace/QUALIFICATION.md']
    for build in [candidate,adopted]:
        tools,key=installed_tools(build['tool_key']);assert key==build['tool_key']
        for name,digest in build['binaries'].items():assert sha(tools/name)==digest;paths.append(tools/name)
        for name in ['rust-interp-mir-export','rust-interp-rustc-wrapper']:
            assert build['binaries'][name]==adopted['binaries'][name]
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
    return adopted,candidate,paths
