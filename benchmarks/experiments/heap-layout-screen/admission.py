"""Bind qualified runtime components and require prior project gates to be closed."""
import json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
from compare_saved_runtime import sha
from interpreter import installed_tools
BASELINE='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
ANCHOR='fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e'
CASES=['token']
def read(p):return json.loads(p.read_text())

def load(case):
    assert case in CASES;paths=[]
    def bind(p,h=None):
        digest=sha(p)
        if h is not None:assert digest==h,p
        paths.append(p);return read(p) if p.suffix=='.json' else digest
    def closed(name):
        folder=ROOT/'results'/name;c=bind(folder/'closure.json')
        assert c['status']=='closed' and c['all_hashes_verified']
        s=bind(folder/'summary.json',c['summary_sha256']);t=bind(folder/'terminal.json',c['terminal_sha256'])
        assert s['status']=='passed' and t['status']=='finished' and t['returncode']==0 and t['owner']==str(ROOT)
        return s
    candidate=closed('heap-layout-install-01')
    assert candidate['rust']==dict(passed=618,ignored=13) and candidate['python']==dict(discovered=468,passed=446,skipped=22)
    composition=candidate['composition']
    assert composition['kind']=='heap-layout' and composition['heap_layout_hash'] is True
    assert composition['experimental_template_session'] is False and composition['diagnostic_feature'] is False
    assert composition['compiler_source_key']==BASELINE
    assert composition['cargo_features']==['rust-interp-bytecode/heap-layout-hash']
    replay=closed('heap-layout-profile-01')
    assert replay['commands']==3 and replay['adopted_tool_key']==BASELINE
    for field in ['exact_per_pc_counts','exact_memory_and_entropy','exact_operation_maps','exact_native_code_and_maps']:assert replay[field] is True
    assert candidate['binaries']['rust-interp-vm']==replay['vm_sha256']
    for proof in [candidate,replay]:
        plan=bind(ROOT/proof['raw']/'plan.json',proof['plan_sha256'])
        for name,h in plan['frozen'].items():
            if name.startswith(('crates/','scripts/','tests/')) or name in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:bind(ROOT/name,h)
    baseline=bind(ROOT/'results/scratch-scalar-main-qualification-01/summary.json')
    anchor=bind(ROOT/'results/parallel-suites-build-01/summary.json')
    assert baseline['status']==anchor['status']=='passed' and baseline['tool_key']==BASELINE and anchor['tool_key']==ANCHOR
    assert anchor['tests']['test-debug']==anchor['tests']['test-release']==dict(passed=365,ignored=1)
    for build in [baseline,candidate,anchor]:
        folder,key=installed_tools(build['tool_key']);assert key==build['tool_key']
        for name,h in build['binaries'].items():bind(folder/name,h)
        for name in ['ready.json','source.json','capabilities.json']:bind(folder/name)
    for name in ['rust-interp-mir-export','rust-interp-rustc-wrapper']:assert candidate['binaries'][name]==baseline['binaries'][name]
    from screen import validate_baseline
    prior=[bind(ROOT/'results'/name/'summary.json') for name in
        ['scratch-memory-values-build-02','scratch-memory-values-qualification-01','scratch-memory-values-full-01','scratch-memory-values-parser-01']]
    assert validate_baseline(prior[0],baseline,*prior[1:])
    assert candidate['matched_control']['binaries']==baseline['binaries']
    return dict(baseline=baseline,duplicate=baseline,candidate=candidate,anchor=anchor),paths
