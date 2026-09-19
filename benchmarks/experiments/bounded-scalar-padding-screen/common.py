"""Closed tool/original integration provenance shared by this new workflow."""
from pathlib import Path
import subprocess
import sys
from model import ROOT, KEY, CANDIDATE, TARGET, NAMES, schedule

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/cross-program-template-model'))
import focus
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write
from interpreter import installed_tools, require_export_option

PROTOCOL='bounded-scalar-padding-screen-protocol-01'
RUN='bounded-scalar-padding-screen-es8-01'
SOURCE=ROOT/'.work/sources/fre'
CHANGED=SOURCE/'crates/fre-kernels/src/forward_anchored.rs'
read=focus.read


def inputs():
    frozen={}
    def bind(path,expected=None,load=True):
        digest=sha(path)
        if expected is not None:assert digest==expected,path
        frozen[str(path.relative_to(ROOT))]=digest
        return read(path) if load and path.suffix=='.json' else digest
    qualified=ROOT/'results/scratch-scalar-main-qualification-01'
    closure=bind(qualified/'closure.json')
    assert closure['status']=='closed' and closure['all_frozen_inputs_verified']
    tool=bind(qualified/'summary.json',closure['summary_sha256'])
    terminal=bind(qualified/'terminal.json',closure['terminal_sha256'])
    assert tool['status']=='passed' and tool['tool_key']==KEY and terminal['returncode']==0
    tools,key=installed_tools(KEY)
    for name,digest in tool['binaries'].items():bind(tools/name,digest)
    for option in ['filtered-tests','function-cache-auto']:require_export_option(tools,key,option)
    for name in ['ready.json','source.json','capabilities.json']:bind(tools/name)
    strict=ROOT/'results/scratch-memory-values-qualification-01'
    closure=bind(strict/'closure.json')
    assert closure['status']=='closed' and closure['logs_verified']
    checks=bind(strict/'summary.json',closure['summary_sha256'])
    bind(strict/'terminal.json',closure['terminal_sha256'])
    assert checks['status']=='passed' and checks['commands']==121 and checks['tool_key']==KEY
    assert checks['scalar_enabled_strict_cargo'] and checks['automatic_cache_qualified'] and checks['source_restored']
    previous=bind(ROOT/'results/fre-integration-targets-02/summary.json')
    assert previous['status']=='passed' and previous['original_tests_passed']==52
    prior_plan=bind(ROOT/previous['raw']/'plan.json')
    assert prior_plan['owner']==str(ROOT) and prior_plan['source_commit']==previous['source_commit']
    records=bind(ROOT/previous['raw']/'records.json',previous['records_sha256'])
    case,=[r for r in records if r['target']==TARGET]
    assert case['status']=='passed' and case['tests']==2
    assert sorted(case['custom']['command'][i+1] for i,v in enumerate(case['custom']['command']) if v=='--entry')==NAMES
    owner=bind(SOURCE/'.rust-interp-owned.json')
    assert owner['owner']==str(ROOT) and owner['revision']==prior_plan['source_pin']
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip()==owner['revision']
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=SOURCE).strip()
    candidate_result=ROOT/'results/bounded-scalar-padding-install-01'
    closure=bind(candidate_result/'closure.json')
    assert closure['status']=='closed' and closure['all_hashes_verified']
    candidate=bind(candidate_result/'summary.json',closure['summary_sha256'])
    terminal=bind(candidate_result/'terminal.json',closure['terminal_sha256'])
    assert terminal['returncode']==0 and terminal['owner']==str(ROOT)
    assert candidate['status']=='passed' and candidate['tool_key']==CANDIDATE
    assert candidate['composition']['layout_bounded_scalar_padding'] and candidate['reused_frontend_commands']==121
    assert candidate['rust']==dict(passed=613,ignored=14)
    for path,h in candidate['outputs'].items(): bind(ROOT/path,h)
    candidate_plan=bind(ROOT/candidate['raw']/'plan.json',candidate['plan_sha256'])
    for path,h in candidate_plan['frozen'].items():
        if path.startswith(('crates/','scripts/','tests/')) or path in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']: bind(ROOT/path,h)
    candidate_tools,candidate_key=installed_tools(CANDIDATE);assert candidate_key==CANDIDATE
    for option in ['filtered-tests','function-cache-auto']:require_export_option(candidate_tools,candidate_key,option)
    assert subprocess.check_output(['git','diff','--name-only',candidate['composition']['adopted_runtime_source'],'--','crates'],cwd=ROOT,text=True).splitlines()==candidate['composition']['runtime_diff_files']
    paths=[*HERE.glob('*.py'),*HERE.glob('*.md'),*list((ROOT/'scripts').glob('*.py')),Path(focus.__file__),
        ROOT/'benchmarks/experiments/test-targets/edit.py',ROOT/'benchmarks/experiments/test-targets/ES8.md',
        ROOT/'benchmarks/experiments/tuned-native/timing.py',ROOT/'benchmarks/experiments/tuned-native/native_results.py']
    paths += [SOURCE/p for p in subprocess.check_output(['git','ls-files','-z'],cwd=SOURCE).decode().split('\0') if p]
    for path in paths:bind(path,load=False)
    original=CHANGED.read_bytes()
    return frozen,original,owner


def require_protocol(frozen):
    folder=ROOT/'results'/PROTOCOL;closure=read(folder/'closure.json')
    assert closure['status']=='closed' and closure['all_hashes_verified']
    summary=read(folder/'summary.json')
    assert sha(folder/'summary.json')==closure['summary_sha256']
    assert summary['status']=='passed' and summary['controls']==14 and summary['commands']==1
    raw=ROOT/summary['raw'];plan=read(raw/'plan.json')
    assert sha(raw/'plan.json')==summary['plan_sha256']
    for p,h in plan['frozen'].items():
        assert sha(ROOT/p)==h,p
        assert frozen.setdefault(p,h)==h,p
    for path in [folder/'closure.json',folder/'summary.json',folder/'terminal.json',raw/'plan.json',raw/'records.json']:
        frozen[str(path.relative_to(ROOT))]=sha(path)


def revision():
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
