"""Bind the new composition and require each preceding independently closed gate."""
import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
from compare_saved_runtime import sha
PUBLIC=ROOT/'benchmarks/experiments/compact-native-switch-guards/admission.py'
PROTOCOL='compact-native-switch-parser-protocol-01'
PROFILES=['incremental','repository']
def read(p):return json.loads(p.read_text())
def components():
    spec=importlib.util.spec_from_file_location('composition_public_admission',PUBLIC)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    builds,paths=module.load('token');paths.append(PUBLIC)
    return builds['baseline'],builds['candidate'],paths

def closed(name,paths):
    folder=ROOT/'results'/name;closure=read(folder/'closure.json')
    assert closure['status']=='closed' and closure['all_hashes_verified']
    summary=read(folder/'summary.json');terminal=read(folder/'terminal.json')
    assert sha(folder/'summary.json')==closure['summary_sha256'] and sha(folder/'terminal.json')==closure['terminal_sha256']
    assert summary['status']=='passed' and terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==str(ROOT)
    paths.extend(folder/n for n in ['closure.json','summary.json','terminal.json'])
    return summary

def validate_prior(proofs,candidate,profile):
    assert profile in PROFILES
    expected=['token','folded','pgrust','rg-aot']
    if profile=='repository':expected.append('parser-incremental')
    assert len(proofs)==len(expected)
    for case,proof in zip(expected,proofs):
        assert proof['tool_keys']['candidate']==candidate
        assert proof['source_restored'] and proof['original_assertions_unchanged']
        assert proof['measurement']['gate_passed'] and proof['measurement']['verdict']=='passed'
        assert proof['commands']==(110 if case=='parser-incremental' else 176)
        if case=='parser-incremental':assert proof['profile']=='incremental' and proof['original_tests']==114
        else:assert proof['case']==case
    return True

def load(profile):
    base,candidate,paths=components()
    proofs=[closed('compact-native-switch-edit-'+case+'-01',paths) for case in ['token','folded','pgrust','rg-aot']]
    if profile=='repository':proofs.append(closed('compact-native-switch-parser-incremental-01',paths))
    assert validate_prior(proofs,candidate['tool_key'],profile)
    protocol=closed(PROTOCOL,paths);assert protocol['tests']==14 and protocol['new_tests']==6 and protocol['reused_tests']==8
    plan=ROOT/protocol['raw']/'plan.json';assert sha(plan)==protocol['plan_sha256'];paths.append(plan)
    for name,h in read(plan)['frozen'].items():assert sha(ROOT/name)==h,name;paths.append(ROOT/name)
    return base,candidate,paths
