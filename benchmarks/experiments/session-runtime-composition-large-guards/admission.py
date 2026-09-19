"""Qualify components once; refuse skipping any full project/parser guard."""
import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
from compare_saved_runtime import sha
CANDIDATE='3ebea1cdc1a521169df8bba1ca139df97759aaf200798c2bcb91bef4cba3c5ad'
CASES=['rg-aot','nushell']
PUBLIC=ROOT/'benchmarks/experiments/session-runtime-composition-guards/admission.py'
def read(p):return json.loads(p.read_text())
def components():
    spec=importlib.util.spec_from_file_location('composition_public_admission',PUBLIC)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    builds,paths=module.load('token');paths.append(PUBLIC)
    return builds,paths

def validate_previous(case,proofs):
    assert case in CASES
    expected=['token','folded','pgrust']
    if case=='nushell':expected+=['rg-aot','parser-incremental','parser-repository']
    assert len(proofs)==len(expected)
    for name,proof in zip(expected,proofs):
        assert proof['status']=='passed' and proof['source_restored'] and proof['original_assertions_unchanged']
        assert proof['tool_keys']['candidate']==CANDIDATE
        assert proof['measurement']['gate_passed'] and proof['measurement']['verdict']=='passed'
        if name.startswith('parser-'):
            assert proof['profile']==name.removeprefix('parser-') and proof['commands']==110 and proof['original_tests']==114
        else:assert proof['case']==name and proof['commands']==176
    return True

def load(case):
    builds,paths=components()
    def closed(name):
        folder=ROOT/'results'/name;c=read(folder/'closure.json');s=read(folder/'summary.json');t=read(folder/'terminal.json')
        assert c['status']=='closed' and c['all_hashes_verified']
        assert sha(folder/'summary.json')==c['summary_sha256'] and sha(folder/'terminal.json')==c['terminal_sha256']
        assert t['owner']==str(ROOT) and t['status']=='finished' and t['returncode']==0
        paths.extend(folder/n for n in ['closure.json','summary.json','terminal.json'])
        return s
    names=['session-runtime-composition-edit-'+c+'-01' for c in ['token','folded','pgrust']]
    if case=='nushell':names+=['session-runtime-composition-edit-rg-aot-01']+['session-runtime-composition-parser-'+p+'-01' for p in ['incremental','repository']]
    assert validate_previous(case,[closed(name) for name in names])
    return builds,paths
