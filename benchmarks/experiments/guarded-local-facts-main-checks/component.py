"""Require the recorded, fully tested compiler/measured-VM composition."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).parent.parent / 'guarded-local-facts-main'))
from inputs import VM_KEY, VM_SHA, COMPILER_CONTROLS
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import sha


def require_build(build):
    assert build['status'] == 'passed'
    assert build['composition']['kind'] == 'guarded-local-facts-main-compiler'
    assert build['composition']['vm_source_key'] == VM_KEY
    assert build['binaries']['rust-interp-vm'] == VM_SHA
    assert build['composition']['binaries'] == build['binaries']
    assert build['tests']['test-debug'] == build['tests']['test-release']
    assert build['tests']['test-debug']['passed'] >= 504
    assert build['tests']['test-debug']['ignored'] == 5
    assert build['tests']['controller-tests'] == dict(tests=6, skipped=0)
    assert build['prior_vm_and_shared_inputs_match']
    assert build['separately_qualified_compiler_control_additions'] == COMPILER_CONTROLS
    raw = ROOT / build['raw']
    assert raw.parent == ROOT / '.work'
    for name, field in [('plan', 'plan_sha256'), ('records', 'records_sha256'),
                        ('compiler-control-target', 'compiler_control_target_sha256')]:
        assert sha(raw / (name + '.json')) == build[field]
    assert all(sha(ROOT / '.work/interpreter-tools' / build['tool_key'] / name) == digest
               for name, digest in build['binaries'].items())
    plan = json.loads((raw / 'plan.json').read_text())
    assert plan['source_commit'] == build['source_commit']
    assert plan['source'] == str(ROOT / '.work/publication-main')
    for path, digest in plan['frozen'].items():
        assert sha(ROOT / path) == digest, path
        # Commands execute the current owned-root launcher and fixtures.
        # Verify those bytes against the actually tested publication source.
        prefix = '.work/publication-main/'
        if path.startswith(prefix):
            assert sha(ROOT / path[len(prefix):]) == digest, path
