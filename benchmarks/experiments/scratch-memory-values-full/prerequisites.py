"""Bind the qualified scalar/scratch runtime and closed primary before full edits."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/scratch-memory-values'))
from compare_saved_runtime import sha
from interpreter import installed_tools
from screen import BASELINE_KEY as ADOPTED_KEY, EXPORTER_KEY, validate_baseline, validate_matched_profile

BASELINE_KEY = '4a1381c40d6b412aa613aa1ae4ba4eea0fc6a290fae143d96af48101eb1fc177'
CANDIDATE_KEY = 'df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
CONTROL_SOURCE = 'ab6adbe8b9d9ae81f5e500859b803f4f27005ca1'


def validate_candidate(build, strict, real, profile, screen, closure):
    assert all(p['status'] == 'passed' for p in [build, strict, real, profile, screen, closure])
    assert build['tool_key'] == strict['tool_key'] == real['tool_key'] == profile['tool_key'] == CANDIDATE_KEY
    assert build['tests'] == {'test-debug': 608, 'test-release': 608} and build['ignored_per_profile'] == 13
    assert build['matched_control']['tool_key'] == BASELINE_KEY
    assert build['matched_control']['composition']['source_commit'] == CONTROL_SOURCE
    assert validate_matched_profile(build, profile)
    assert strict['commands'] == 121 and strict['source_restored'] and strict['automatic_cache_qualified']
    assert set(strict['strict_rejections']) == {'type', 'borrow'}
    assert strict['scalar_enabled_strict_cargo'] and strict['actual_demand_artifact']
    assert strict['scalar_partial_artifact_rejections'] == 1
    assert real['commands'] == 13 and real['selected_tests'] == 7 and real['prepared_suites'] == 6
    assert real['native_assertion_outcomes_match'] and real['deterministic_controls_exact'] and real['jit_scalar_calls']
    assert real['vm_sha256'] == build['binaries']['rust-interp-vm']
    assert profile['python_controls'] == 3 and profile['launcher_controls'] == 7
    for row in profile['comparisons']:
        assert row['statistics']['jit_declined_functions'] == 0
        assert 0 <= row['logical_counts']['scalar'] <= row['logical_counts']['native']
        assert row['current_native_bytes'] == row['statistics']['jit_bytes']
    assert screen['commands'] == 40 and screen['gate_passed'] and screen['source_restored']
    assert screen['test_source_unchanged'] and screen['native_assertion_outcomes_match']
    assert screen['candidate_control_bytecode_matches']
    assert screen['tool_keys']['candidate'] == CANDIDATE_KEY
    assert screen['tool_keys']['baseline'] == screen['tool_keys']['duplicate'] == BASELINE_KEY
    assert closure['performance_gate_passed'] and not closure['parked']
    assert closure['full_comparison_commands'] == closure['held_out_commands'] == closure['repeated_screen_commands'] == 0
    return True


def load():
    names = ['guarded-local-facts-main-build-01', 'guarded-local-facts-main-final-audit-01',
             'guarded-local-facts-main-qualification-01', 'guarded-local-facts-main-projects-01',
             'guarded-local-facts-main-parser-01', 'scratch-memory-values-build-02',
             'scratch-memory-values-qualification-01', 'scratch-memory-values-real-controls-01',
             'scratch-memory-values-profile-01', 'scratch-memory-values-screen-token-01']
    paths = [ROOT / 'results' / name / 'summary.json' for name in names]
    paths.append(ROOT / 'results/scratch-memory-values-screen-token-01/closure.json')
    proofs = [json.loads(p.read_text()) for p in paths]
    assert validate_baseline(*proofs[:5]) and validate_candidate(*proofs[5:])
    candidate, closure = proofs[5], proofs[-1]
    baseline = dict(status='passed', **candidate['matched_control'])

    def retain(path, digest):
        assert sha(path) == digest, path
        paths.append(path)

    def binding(path, item):
        if item['kind'] == 'git':
            data = subprocess.check_output(['git', 'show', item['revision'] + ':' + path], cwd=ROOT)
            assert hashlib.sha256(data).hexdigest() == item['sha256'], path
        else:
            assert item['kind'] == 'retained'
            retain(ROOT / path, item['sha256'])

    # Verify historical source against its recorded commit, and retained data
    # against its closed hashes. No historical controller is rebound to HEAD.
    for path, proof in zip(paths[:10][5:], proofs[5:10]):
        if path.parent.name.endswith('screen-token-01'):
            continue
        closed_path = path.with_name('closure.json')
        closed = json.loads(closed_path.read_text()); paths.append(closed_path)
        assert closed['status'] == 'closed'
        retain(path, closed['summary_sha256'])
        retain(path.with_name('terminal.json'), closed['terminal_sha256'])
        bindings_path = ROOT / closed.get('bindings', closed.get('source_bindings', ''))
        retain(bindings_path, closed.get('bindings_sha256', closed.get('source_bindings_sha256')))
        bindings = json.loads(bindings_path.read_text())
        if 'frozen_inputs' in bindings:
            for key, digest in bindings['artifacts'].items(): retain(ROOT / key, digest)
            bindings = bindings['frozen_inputs']
        for key, item in bindings.items(): binding(key, item)
    source_path = ROOT / closure['source_bindings_path']
    retain(source_path, closure['source_bindings_sha256'])
    source_bindings = json.loads(source_path.read_text())['files']
    for path, item in source_bindings.items():
        data = subprocess.check_output(['git', 'show', item['git_source']], cwd=ROOT)
        assert hashlib.sha256(data).hexdigest() == item['sha256'], path
    evidence_path = ROOT / closure['evidence_path']; retain(evidence_path, closure['evidence_sha256'])
    evidence = json.loads(evidence_path.read_text()); assert len(evidence) == closure['evidence_files']
    for path, digest in evidence.items():
        if path not in source_bindings: retain(ROOT / path, digest)
        else: assert source_bindings[path]['sha256'] == digest
    for item in [candidate, baseline]:
        retain(ROOT / item['source_manifest'], item['source_manifest_sha256'])
        tool, _ = installed_tools(item['tool_key'])
        for name, digest in item['binaries'].items(): retain(tool / name, digest)
    retain(ROOT / baseline['command_record'], baseline['command_record_sha256'])
    for proof in proofs[5:10]:
        raw = ROOT / proof['raw']
        for name in ['plan', 'records']: retain(raw / (name + '.json'), proof[name + '_sha256'])
    profile = proofs[8]
    records = json.loads((ROOT / profile['raw'] / 'records.json').read_text())
    assert len(records) == 6
    vm = installed_tools(CANDIDATE_KEY)[0] / 'rust-interp-vm'
    for record in records:
        assert record['returncode'] == 0
        assert ('--jit-scalar-calls' in record['command']) == (record['mode'] == 'candidate')
        if record['mode'] == 'candidate': assert record['command'][0] == str(vm)
    for row in profile['comparisons']:
        for key in ['profile', 'operations', 'code']: retain(ROOT / row[key + '_path'], row[key + '_sha256'])
        retain((ROOT / row['code_path']).with_name('map.json'), row['map_sha256'])
    return baseline, candidate, list(dict.fromkeys(paths))
