"""Bind the composed runtime, unchanged adopted baseline and closed admission."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/runtime-composition-screen'))
from compare_saved_runtime import sha
from interpreter import installed_tools
from screen import EXPORTER_KEY,validate_baseline,validate_matched_profile
BASELINE_KEY='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
CANDIDATE_KEY='45a1529e5e3069e23d2222cfe63758208e6259522dd9c5e520c332600121441b'


def validate_candidate(build,strict,real,profile,screen,closure):
    assert all(p['status']=='passed' for p in [build,strict,real,profile,screen,closure])
    assert build['tool_key']==strict['tool_key']==real['tool_key']==profile['tool_key']==CANDIDATE_KEY
    assert build['tests']=={'test-debug':666,'test-release':666} and build['ignored_per_profile']==25
    assert build['matched_control']['tool_key']==BASELINE_KEY
    assert validate_matched_profile(build,profile)
    assert strict['commands']==122 and strict['source_restored'] and strict['automatic_cache_qualified']
    assert set(strict['strict_rejections'])=={'type','borrow'} and strict['actual_demand_artifact']
    assert strict['scalar_enabled_strict_cargo'] and strict['scalar_partial_artifact_rejections']==1
    assert strict['indirect_enabled_strict_cargo'] and strict['indirect_partial_artifact_rejections']==1
    assert real['commands']==26 and real['fresh_baseline_commands']==13 and real['selected_tests']==7 and real['prepared_suites']==6
    assert real['matched_control_key']==BASELINE_KEY and real['jit_scalar_calls'] and real['jit_indirect_calls']
    assert real['native_assertion_outcomes_match'] and real['deterministic_controls_exact']
    assert real['vm_sha256']==build['binaries']['rust-interp-vm']
    assert profile['python_controls_reused']==5 and profile['launcher_controls_reused']==9
    for row in profile['comparisons']:
        assert row['statistics']['jit_declined_functions']==0
        assert 0<row['logical_counts']['scalar']<=row['logical_counts']['native']
        assert row['current_native_bytes']==row['statistics']['jit_bytes']
    assert screen['commands']==40 and screen['gate_passed'] and screen['source_restored']
    assert screen['test_source_unchanged'] and screen['native_assertion_outcomes_match'] and screen['candidate_control_bytecode_matches']
    assert screen['tool_keys']['candidate']==CANDIDATE_KEY
    assert screen['tool_keys']['baseline']==screen['tool_keys']['duplicate']==BASELINE_KEY
    assert closure['performance_gate_passed'] and not closure['parked']
    assert closure['full_comparison_commands']==closure['held_out_commands']==closure['repeated_screen_commands']==0
    return True


def load():
    def read(p):return json.loads(p.read_text())
    names=['build-01','qualification-02','real-controls-01','profile-02','screen-token-01']
    paths=[ROOT/'results'/('runtime-composition-'+n)/'summary.json' for n in names]
    paths.append(paths[-1].with_name('closure.json'))
    proofs=[read(p) for p in paths]
    assert validate_candidate(*proofs)
    candidate=proofs[0];baseline=dict(status='passed',**candidate['matched_control'])
    adopted_names=['scratch-memory-values-build-02','scratch-scalar-main-qualification-01',
        'scratch-memory-values-qualification-01','scratch-memory-values-full-01','scratch-memory-values-parser-01']
    adopted_paths=[ROOT/'results'/n/'summary.json' for n in adopted_names]
    assert validate_baseline(*map(read,adopted_paths));paths+=adopted_paths

    def retain(path,expected):
        assert sha(path)==expected,path
        paths.append(path)
    def bind(p,item):
        if item['kind']=='git':
            data=subprocess.check_output(['git','show',item['revision']+':'+p],cwd=ROOT)
            assert hashlib.sha256(data).hexdigest()==item['sha256'],p
        else:
            assert item['kind']=='retained';retain(ROOT/p,item['sha256'])
    def closed(summary):
        closure_path=summary.with_name('closure.json');proof=read(closure_path);paths.append(closure_path)
        assert proof['status']=='closed'
        retain(summary,proof['summary_sha256']);retain(summary.with_name('terminal.json'),proof['terminal_sha256'])
        bp=ROOT/proof.get('bindings',proof.get('source_bindings',''))
        retain(bp,proof.get('bindings_sha256',proof.get('source_bindings_sha256')))
        b=read(bp)
        if 'artifacts' in b:
            for p,h in b['artifacts'].items():retain(ROOT/p,h)
        sources=b.get('frozen_inputs',b.get('source',b))
        for p,item in sources.items():bind(p,item)
    for path in paths[:4]:closed(path)
    launcher_path=ROOT/'results/runtime-composition-launcher-02/summary.json';launcher=read(launcher_path)
    assert launcher['status']=='passed' and launcher['python']==dict(discovered=443,passed=421,skipped=22)
    assert launcher['vm_tool_key']==CANDIDATE_KEY
    closed(launcher_path)
    closure=proofs[-1]
    source_path=ROOT/closure['source_bindings_path'];retain(source_path,closure['source_bindings_sha256'])
    sources=read(source_path)['files']
    for p,item in sources.items():
        data=subprocess.check_output(['git','show',item['git_source']],cwd=ROOT)
        assert hashlib.sha256(data).hexdigest()==item['sha256']
    evidence_path=ROOT/closure['evidence_path'];retain(evidence_path,closure['evidence_sha256'])
    evidence=read(evidence_path);assert len(evidence)==closure['evidence_files']
    for p,h in evidence.items():
        if p not in sources:retain(ROOT/p,h)
        else:assert sources[p]['sha256']==h
    for build in [baseline,candidate]:
        tool,key=installed_tools(build['tool_key'])
        for n,h in build['binaries'].items():retain(tool/n,h)
        for n in ['ready.json','source.json','capabilities.json']:paths.append(tool/n)
    profile=proofs[3];raw=ROOT/profile['raw'];records=read(raw/'records.json')
    assert len(records)==6
    for r in records:
        assert r['returncode']==0 and '--jit-scalar-calls' in r['command']
        assert ('--jit-indirect-calls' in r['command'])==(r['mode']=='candidate')
        expected=CANDIDATE_KEY if r['mode']=='candidate' else BASELINE_KEY
        assert r['command'][0]==str(ROOT/'.work/interpreter-tools'/expected/'rust-interp-vm')
    return baseline,candidate,list(dict.fromkeys(paths))
