"""Join the exact runtime/strict-checking controls before full edit histories."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/guarded-local-facts'))
from compare_saved_runtime import sha
from screen import BASELINE_KEY, EXPORTER_KEY, validate_baseline

CANDIDATE_KEY = '317a0bf16da0f15f562ab457408ab321b12f25211f8169ec8bcd8205a3cb7dfb'


def validate_candidate(build, strict, real, profile, screen):
    assert all(p['status'] == 'passed' for p in [build, strict, real, profile, screen])
    assert build['tool_key'] == strict['tool_key'] == real['tool_key'] == profile['tool_key'] == CANDIDATE_KEY
    assert build['tests'] == {'test-debug': 504, 'test-release': 504}
    assert build['composition']['kind'] == 'guarded-local-facts-composition'
    assert build['composition']['compiler_source_key'] == EXPORTER_KEY
    assert strict['commands'] == 119 and strict['source_restored'] and strict['automatic_cache_qualified']
    assert set(strict['strict_rejections']) == {'type', 'borrow'}
    assert real['commands'] == 13 and real['selected_tests'] == 7 and real['prepared_suites'] == 6
    assert real['native_assertion_outcomes_match'] and real['deterministic_controls_exact']
    assert real['vm_sha256'] == profile['vm_sha256'] == build['binaries']['rust-interp-vm']
    assert profile['commands'] == 3 and profile['exact_per_pc_counts']
    assert profile['exact_logical_counts_memory_and_entropy'] and profile['exact_operation_map_reconstruction']
    assert len(profile['comparisons']) == 3 and all(c['statistics']['jit_declined_functions'] == 0 for c in profile['comparisons'])
    assert screen['commands'] == 40 and screen['gate_passed'] and screen['source_restored']
    assert screen['test_source_unchanged'] and screen['native_assertion_outcomes_match']
    assert screen['candidate_control_bytecode_matches']
    assert screen['tool_keys']['candidate'] == CANDIDATE_KEY
    assert screen['tool_keys']['baseline'] == screen['tool_keys']['duplicate'] == BASELINE_KEY
    return True


def load():
    names = ['environment-main-build-01', 'environment-read-build-02',
             'environment-main-qualification-01', 'environment-main-projects-01', 'environment-main-final-audit-01',
             'guarded-local-facts-build-03', 'guarded-local-facts-qualification-01',
             'guarded-local-facts-real-controls-01', 'guarded-local-facts-profile-01',
             'guarded-local-facts-screen-token-continuation-01']
    paths = [ROOT / 'results' / name / 'summary.json' for name in names]
    proofs = [json.loads(p.read_text()) for p in paths]
    assert validate_baseline(*proofs[:5])
    assert validate_candidate(*proofs[5:])
    baseline, candidate = proofs[0], proofs[5]
    assert baseline['binaries']['rust-interp-vm'] != candidate['binaries']['rust-interp-vm']
    for binary in ['rust-interp-mir-export', 'rust-interp-rustc-wrapper']:
        assert baseline['binaries'][binary] == candidate['binaries'][binary]
    # All new correctness and primary-screen receipts must still bind to the
    # proof we are using. Historical sources are not silently rebound to HEAD.
    for proof in proofs[6:]:
        raw = ROOT / proof['raw']
        for name in ['plan', 'records']:
            path = raw / (name + '.json')
            assert sha(path) == proof[name + '_sha256']
            paths.append(path)
    return baseline, candidate, paths
