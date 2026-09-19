"""Require closed actual-client correctness, launcher and accounting evidence."""
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
        folder=ROOT/'results'/name;c=read(folder/'closure.json');s=read(folder/'summary.json')
        assert c['status']=='closed' and s['status']=='passed' and sha(folder/'summary.json')==c['summary_sha256']
        assert sha(folder/'terminal.json')==c['terminal_sha256'];t=read(folder/'terminal.json')
        assert t['owner']==str(ROOT) and t['status']=='finished' and t['returncode']==0
        paths.extend(folder/n for n in ['closure.json','summary.json','terminal.json'])
        return s
    candidate=closed('session-duration-order-install-01')
    replay=closed('session-duration-order-parser-client-01')
    protocol=closed('cross-program-template-parser-full-protocol-01')
    primary=closed('cross-program-template-parser-screen-incremental-06')
    assert primary['measurement']['gate_passed'] and primary['measurement']['verdict']=='passed'
    assert primary['tool_keys']['candidate']==candidate['tool_key']
    assert primary['commands']==40 and primary['strict_controls']==2
    assert candidate['python']['passed']==442 and candidate['python']['skipped']==22
    assert candidate['rust']==dict(passed=679,ignored=17)
    assert replay['test_invocations']==1824 and replay['verified_cache_hits']>0 and replay['kernel_cpu_reconciled']
    assert protocol['tests']==8
    assert candidate['composition']['artifact_digest_reuse'] is replay['artifact_digest_reuse'] is True
    assert candidate['composition']['template_key_domain']=='cross-program-staging-literals-v1'
    assert candidate['composition']['duration_order'] is replay['duration_order'] is True
    assert candidate['composition']['shared_literal_keys'] is replay['shared_literal_keys'] is False
    assert candidate['composition']['parameterized_literals'] is replay['parameterized_literals'] is True
    assert candidate['composition']['buffered_template_keys'] is replay['buffered_template_keys'] is False
    ordering=closed('session-duration-order-evidence-01')
    assert ordering['priority_conformity_reports']==16 and ordering['priority_conformity_invocations']==1824
    assert candidate['composition']['large_function_interpreter_threshold']==replay['large_function_interpreter_threshold']==65536
    assert candidate['composition']['diagnostic_feature'] is replay['diagnostic_feature'] is False
    for s in [candidate,replay,protocol]:
        plan_path=ROOT/s['raw']/'plan.json';assert sha(plan_path)==s['plan_sha256'];paths.append(plan_path)
        for path,h in read(plan_path)['frozen'].items():
            if path.startswith(('crates/','scripts/','tests/','benchmarks/experiments/cross-program-template-screen/','benchmarks/experiments/cross-program-template-full-parser/',
                    'benchmarks/experiments/session-duration-order-install/','benchmarks/experiments/session-duration-order-workspace/',
                    'benchmarks/experiments/session-duration-order-replay/','benchmarks/experiments/session-duration-order-phases/')) or path in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:
                assert sha(ROOT/path)==h,('qualified source changed',path);paths.append(ROOT/path)
    base_path=ROOT/'results/scratch-scalar-main-qualification-01/summary.json';base=read(base_path);paths.append(base_path)
    assert base['status']=='passed' and base['tool_key']==BASELINE
    for build in [base,candidate]:
        tools,key=installed_tools(build['tool_key']);assert key==build['tool_key']
        for name,h in build['binaries'].items():assert sha(tools/name)==h;paths.append(tools/name)
        for name in ['rust-interp-mir-export','rust-interp-rustc-wrapper']:assert build['binaries'][name]==base['binaries'][name]
    server=Path(candidate['composition']['server_path']);assert sha(server)==candidate['composition']['server_executable_sha256'];paths.append(server)
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
    return base,candidate,paths
