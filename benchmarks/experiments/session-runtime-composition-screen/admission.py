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
    candidate=closed('session-runtime-composition-install-01')
    assert candidate['rust']==dict(passed=720,ignored=19) and candidate['python']==dict(discovered=468,passed=446,skipped=22)
    composition=candidate['composition']
    assert composition['duration_order'] is True and composition['shared_literal_keys'] is False
    assert composition['parameterized_literals'] is True and composition['buffered_template_keys'] is False
    assert composition['diagnostic_feature'] is False and composition['template_key_domain']=='cross-program-staging-literals-v3'
    replay=closed('session-runtime-composition-fre-replay-01')
    assert replay['test_invocations']==192 and replay['verified_cache_hits']>0 and replay['kernel_cpu_reconciled']
    parser=closed('session-runtime-composition-parser-replay-01')
    assert parser['test_invocations']==1824 and parser['verified_cache_hits']>0 and parser['kernel_cpu_reconciled']
    assert replay['indirect_calls'] is parser['indirect_calls'] is True
    for proof in [candidate,replay,parser]:
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
    bind(Path(composition['server_path']),composition['server_executable_sha256'])
    return dict(baseline=baseline,duplicate=baseline,candidate=candidate,anchor=anchor),paths
