"""Read-only binding of the original failed five-row native qualification.

The old stock binary remains unqualified and is never executed or overwritten.
This reader cannot reinterpret the failed terminal as a successful prerequisite.
"""
import hashlib
import json
from pathlib import Path

A = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
SOURCE = A/'experiments/hir-options-hash-native-controls-01'
WORK = A/'.work/hir-options-hash-native-controls-01'
AUDIT = A/'.work/native-controls-failure-verification-01.json'
AUDIT_SHA256 = 'af25ceeda3cf32cf63d73b3fd2cee05726267166e0babd58587b884815256f3e'
INPUTS_SHA256 = 'edb807bfe3d24db7ea327750e57bf6034b1a2a42eb36acc6a59f5f4efbdf17fd'
DIAGNOSIS = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918/.work/native-stock-wrapper-lint-source-review-01.json')
DIAGNOSIS_SHA256 = 'db4f73adb8985b96a6219d375c5e3994af4973e2c54038965e0e65d42d8ebf08'


def require(ok, message):
    if not ok: raise ValueError(message)


def validate(check, files):
    """check freezes or verifies each exact path; files is the full new closure."""
    def data(path, expected=None):
        path = Path(check(Path(path)))
        require(path.stat().st_size <= 64*2**20, 'bounded prior proof required')
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        require(expected is None or digest == expected, 'prior proof digest differs')
        return json.loads(raw)
    audit = data(AUDIT, AUDIT_SHA256)
    old = data(SOURCE/'inputs.json', INPUTS_SHA256)
    require(all(files.get(name) == row for name,row in old['files'].items()), 'original native full closure omitted or changed')
    require(audit['status'] == 'verified-retained-failure' and audit['children'] == 5
            and audit['intended_children'] == 20 and audit['unexecuted_indices'] == list(range(5,20))
            and audit['all_child_returncodes_zero'] is True and audit['fixture_never_created'] is True
            and audit['native_roles_and_behavior_qualified'] is False
            and audit['inputs_sha256'] == INPUTS_SHA256,
            'honest failed-five audit required')
    for name, row in audit['evidence_files'].items():
        check(Path(name))
        require(files[name] == row, 'closed original evidence changed')
    stock = audit['unqualified_stock']; check(Path(stock['path']))
    require(stock['qualified'] is False and files[stock['path']] == {key:stock[key] for key in ['identity','sha256','size']},
            'original unqualified stock changed')
    terminal = data(WORK/'receipt.json', audit['receipt_sha256'])
    require(terminal['status'] == 'failed' and terminal['error'] == "ValueError('stock build emitted diagnostics')"
            and len(terminal['commands']) == 5 and terminal['source_restored'] is False
            and all(terminal[k] == [] for k in ['fixture_compilations','native_executions','hits']),
            'original failure was changed or relabeled')
    for index,ref in enumerate(terminal['commands']):
        child = data(ref['path'],ref['sha256'])
        require(Path(ref['path']) == WORK/'commands'/f'{index:03}'/'receipt.json'
                and child['status'] == 'finished' and child['returncode'] == 0, 'original five-row outcome differs')
    for name in ['plan.json','launch.json','snapshot-plan.json','metadata-preflight.json']:
        data(SOURCE/name)
    data(DIAGNOSIS,DIAGNOSIS_SHA256)
    for path in [A/'.work/verify_native_controls_failure_01.py',
                 *[A/'.work/native-controls-failure-verification-execution-01'/name for name in ['record.json','stdout','stderr']]]:
        check(path)
    execution=data(A/'.work/native-controls-failure-verification-execution-01/record.json')
    require(execution['returncode']==0 and execution['source_sha256']==files[str(A/'.work/verify_native_controls_failure_01.py')]['sha256'],
            'failed-attempt audit execution differs')
    root=Path(stock['path']).parent
    require(set(p.name for p in root.iterdir()) == {'smoke-rustc'}, 'old failed native root membership changed')
    require(set(p.name for p in (WORK/'commands').iterdir()) == {f'{i:03}' for i in range(5)}, 'old failed command membership changed')
    return dict(source=str(SOURCE),evidence=str(WORK),receipt_sha256=audit['receipt_sha256'],
        inputs_sha256=INPUTS_SHA256,audit=dict(path=str(AUDIT),sha256=AUDIT_SHA256),
        diagnosis=dict(path=str(DIAGNOSIS),sha256=DIAGNOSIS_SHA256),
        actual_children=5,qualified_children=0,unqualified_stock=stock,fixture_never_created=True)
