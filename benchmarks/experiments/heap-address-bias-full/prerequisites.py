"""Bind the exact matched runtime, strict controls and closed primary before full edits."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/heap-address-bias'))
from compare_saved_runtime import sha
from screen import BASELINE_KEY as ADOPTED_KEY, EXPORTER_KEY, validate_baseline, validate_matched_profile

BASELINE_KEY = '4a1381c40d6b412aa613aa1ae4ba4eea0fc6a290fae143d96af48101eb1fc177'
CANDIDATE_KEY = '5929f04f51274ed010b38a48aed95ba817e63adcb593b98dc73c702046c5d259'
REJECTED_KEY = 'd7bb1e823fc0e77f57000e294243fd78338ad91190cee23605de575dd693c5a5'
CONTROL_SOURCE = 'ab6adbe8b9d9ae81f5e500859b803f4f27005ca1'


def validate_candidate(build, strict, real, profile, screen, closure):
    assert all(p['status'] == 'passed' for p in [build, strict, real, profile, screen, closure])
    assert build['tool_key'] == strict['tool_key'] == real['tool_key'] == profile['tool_key'] == CANDIDATE_KEY
    assert build['tests'] == {'test-debug': 553, 'test-release': 553}
    assert build['distinct_control_and_candidate_executables']
    assert build['matched_control']['tool_key'] == BASELINE_KEY
    assert build['matched_control']['composition']['source_commit'] == CONTROL_SOURCE
    assert validate_matched_profile(build, profile)
    assert strict['commands'] == 119 and strict['source_restored'] and strict['automatic_cache_qualified']
    assert set(strict['strict_rejections']) == {'type', 'borrow'}
    assert real['commands'] == 13 and real['selected_tests'] == 7 and real['prepared_suites'] == 6
    assert real['native_assertion_outcomes_match'] and real['deterministic_controls_exact']
    assert real['vm_sha256'] == profile['vm_sha256'] == build['binaries']['rust-interp-vm']
    assert profile['new_executions'] == 4 and profile['reused_executions'] == 2
    assert profile['code_partition_verified']
    for row in profile['comparisons']:
        assert all(row[k] for k in ['exact_per_pc_counts', 'exact_logical_counts_memory_and_entropy',
                                    'exact_operation_map_reconstruction'])
    assert screen['commands'] == 40 and screen['gate_passed'] and screen['source_restored']
    assert screen['test_source_unchanged'] and screen['native_assertion_outcomes_match']
    assert screen['candidate_control_bytecode_matches']
    assert screen['tool_keys']['candidate'] == CANDIDATE_KEY
    assert screen['tool_keys']['baseline'] == screen['tool_keys']['duplicate'] == BASELINE_KEY
    assert closure['performance_gate_passed'] and not closure['parked']
    assert closure['actual_profile_guest_executions'] == 6 and closure['profile_prefix_executions_reused']
    assert closure['rejected_tool_key'] == REJECTED_KEY and closure['rejected_tool_benchmark_executions'] == 0
    assert closure['full_comparison_commands'] == closure['held_out_commands'] == closure['repeated_screen_commands'] == 0
    return True


def load():
    names = ['guarded-local-facts-main-build-01', 'guarded-local-facts-main-final-audit-01',
             'guarded-local-facts-main-qualification-01', 'guarded-local-facts-main-projects-01',
             'guarded-local-facts-main-parser-01', 'heap-address-build-03',
             'heap-address-qualification-01', 'heap-address-real-controls-01',
             'heap-address-profile-03', 'heap-address-screen-token-01']
    paths = [ROOT / 'results' / name / 'summary.json' for name in names]
    paths.append(ROOT / 'results/heap-address-screen-token-01/closure.json')
    proofs = [json.loads(p.read_text()) for p in paths]
    assert validate_baseline(*proofs[:5])
    assert validate_candidate(*proofs[5:])
    candidate, closure = proofs[5], proofs[-1]
    baseline = dict(status='passed', **candidate['matched_control'])
    # Closure is historical. Its source bindings distinguish Git-bound prior
    # controllers from current files; do not silently rebind those to HEAD.
    for index in [5, 6, 8, 9]:
        path = paths[index]
        assert closure['evidence'][str(path.relative_to(ROOT))] == sha(path)
    bindings = paths[-1].with_name('source-bindings.json')
    assert sha(bindings) == closure['source_bindings_sha256']; paths.append(bindings)
    for item in [candidate, baseline]:
        path = ROOT / item['source_manifest']
        assert sha(path) == item['source_manifest_sha256']; paths.append(path)
    path = ROOT / baseline['command_record']
    assert sha(path) == baseline['command_record_sha256']; paths.append(path)
    for proof in proofs[6:10]:
        raw = ROOT / proof['raw']
        for name in ['plan', 'records']:
            path = raw / (name + '.json')
            assert sha(path) == proof[name + '_sha256']; paths.append(path)
    for row in proofs[8]['comparisons']:
        for field, digest in [('profile_path', 'profile_sha256'), ('operations_path', 'operation_map_sha256'),
                              ('map_path', 'code_map_sha256'), ('code_path', 'code_sha256')]:
            path = ROOT / row[field]; assert sha(path) == row[digest]; paths.append(path)
    return baseline, candidate, paths
