"""Bind qualified runtime components and require prior project gates to be closed."""
import json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
from compare_saved_runtime import sha
from interpreter import installed_tools
BASELINE='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
CANDIDATE='60bc004658a1db09e1c905eed50e25062f1ff8ae27811331aed9ad51b206a5a5'
ANCHOR='fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e'
CASES=['token','folded','pgrust']
def read(p):return json.loads(p.read_text())

def validate_previous(case,previous):
    assert case in CASES
    expected=CASES[:CASES.index(case)]
    assert len(previous)==len(expected)
    for name,proof in zip(expected,previous):
        assert proof['case']==name and proof['status']=='passed' and proof['commands']==176
        assert proof['source_restored'] and proof['original_assertions_unchanged']
        assert proof['measurement']['gate_passed'] and proof['measurement']['verdict']=='passed'
        assert proof['tool_keys']['candidate']==CANDIDATE
    return True

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
    full=closed('cross-program-template-parser-full-incremental-03')
    assert full['commands']==110 and full['measurement']['verdict']=='passed' and full['measurement']['gate_passed']
    assert full['tool_keys']['candidate']==CANDIDATE
    candidate=closed('session-duration-order-install-01');assert candidate['tool_key']==CANDIDATE
    assert candidate['rust']==dict(passed=679,ignored=17) and candidate['python']==dict(discovered=464,passed=442,skipped=22)
    composition=candidate['composition']
    assert composition['duration_order'] is True and composition['shared_literal_keys'] is False
    assert composition['parameterized_literals'] is True and composition['buffered_template_keys'] is False
    assert composition['diagnostic_feature'] is False and composition['template_key_domain']=='cross-program-staging-literals-v1'
    replay=closed('session-duration-order-fre-token-replay-01')
    assert replay['test_invocations']==192 and replay['verified_cache_hits']>0 and replay['kernel_cpu_reconciled']
    assert validate_previous(case,[closed('session-project-edit-'+name+'-01') for name in CASES[:CASES.index(case)]])
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
    bind(Path(composition['server_path']),composition['server_executable_sha256'])
    return dict(baseline=baseline,duplicate=baseline,candidate=candidate,anchor=anchor,**{'session-fresh':candidate}),paths
