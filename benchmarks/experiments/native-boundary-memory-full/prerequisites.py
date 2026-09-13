"""Join the exact runtime/strict-checking controls before full edit histories."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/native-boundary-memory'))
from compare_saved_runtime import sha
from screen import BASELINE_KEY, EXPORTER_KEY, validate_baseline

CANDIDATE_KEY = 'b012f42afdf6da7f898c389d95a1deec51196db0981fee77f115c7edb362329a'


def validate_candidate(build, strict, real, profile, screen):
    assert all(p['status'] == 'passed' for p in [build, strict, real, profile, screen])
    assert build['tool_key'] == strict['tool_key'] == real['tool_key'] == profile['tool_key'] == CANDIDATE_KEY
    assert build['tests'] == {'test-debug': 519, 'test-release': 519}
    assert build['composition']['kind'] == 'native-boundary-memory-composition'
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
    names = ['guarded-local-facts-main-build-01', 'guarded-local-facts-main-final-audit-01',
             'guarded-local-facts-main-qualification-01', 'guarded-local-facts-main-projects-01', 'guarded-local-facts-main-parser-01',
             'native-boundary-memory-build-01', 'native-boundary-memory-qualification-01',
             'native-boundary-memory-real-controls-01', 'native-boundary-memory-profile-01',
             'native-boundary-memory-screen-token-01']
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
