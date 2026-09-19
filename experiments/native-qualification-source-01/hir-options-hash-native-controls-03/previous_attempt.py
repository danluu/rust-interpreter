"""Read-only ordered bindings for both failed native attempts; no qualification."""
import hashlib
import json
from pathlib import Path

A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
SOURCE=A/'experiments/hir-options-hash-native-controls-02'
ATTEMPTS=[
    ('01',5,'af25ceeda3cf32cf63d73b3fd2cee05726267166e0babd58587b884815256f3e',
     'edb807bfe3d24db7ea327750e57bf6034b1a2a42eb36acc6a59f5f4efbdf17fd',
     "ValueError('stock build emitted diagnostics')",'native-stock-wrapper-lint-source-review-01.json',
     'db4f73adb8985b96a6219d375c5e3994af4973e2c54038965e0e65d42d8ebf08'),
    ('02',6,'c5f873179ed772de997771fd1c89f409876a79ca520d01ff5f8a288c2f6c879f',
     '33958301017e8d2107ee94dbe431fb4402deabd1d4a1fa8b2298038e4a2b1b0c',
     "ValueError('stock direct private edge is outside exact E2 closure')",'native02-loader-edge-diagnosis-01.json',
     'dc77f0b49bb29d3f37635ab5f159e3a2cab21b38480c917eb8d443f27774482b')]


def require(ok,message):
    if not ok:raise ValueError(message)


def validate(check,files):
    def data(path,expected=None):
        path=Path(check(Path(path)));require(path.stat().st_size<=64*2**20,'bounded prior proof required')
        raw=path.read_bytes();require(expected is None or hashlib.sha256(raw).hexdigest()==expected,'prior proof digest differs')
        return json.loads(raw)
    proofs=[]
    for number,count,audit_sha,inputs_sha,error,diagnosis_name,diagnosis_sha in ATTEMPTS:
        source=A/('experiments/hir-options-hash-native-controls-'+number)
        work=A/('.work/hir-options-hash-native-controls-'+number)
        audit_path=A/('.work/native-controls-failure-verification-'+number+'.json')
        audit=data(audit_path,audit_sha);old=data(source/'inputs.json',inputs_sha)
        require(all(files.get(name)==row for name,row in old['files'].items()),'complete old native closure omitted or changed')
        require(audit['status']=='verified-retained-failure' and audit['children']==count and audit['intended_children']==20
            and audit['unexecuted_indices']==list(range(count,20)) and audit['all_child_returncodes_zero'] is True
            and audit['fixture_never_created'] is True and audit['native_roles_and_behavior_qualified'] is False
            and audit['inputs_sha256']==inputs_sha and audit['error']==error,'honest failed native audit required')
        for name,row in audit['evidence_files'].items():
            check(Path(name));require(files[name]==row,'closed prior evidence changed')
        stock=audit['unqualified_stock'];check(Path(stock['path']))
        require(stock['qualified'] is False and files[stock['path']]=={key:stock[key] for key in ['identity','sha256','size']},
            'unqualified prior stock changed')
        terminal=data(work/'receipt.json',audit['receipt_sha256'])
        require(terminal['status']=='failed' and terminal['error']==error and len(terminal['commands'])==count
            and terminal['source_restored'] is False and all(terminal[k]==[] for k in ['fixture_compilations','native_executions','hits']),
            'old failure changed or relabeled')
        for index,ref in enumerate(terminal['commands']):
            child=data(ref['path'],ref['sha256'])
            require(Path(ref['path'])==work/'commands'/f'{index:03}'/'receipt.json' and child['status']=='finished'
                and child['returncode']==0,'old actual command outcome differs')
        for name in ['plan.json','launch.json','snapshot-plan.json','metadata-preflight.json']:data(source/name)
        diagnosis=O/'.work'/diagnosis_name;data(diagnosis,diagnosis_sha)
        verifier=A/('.work/verify_native_controls_failure_'+number+'.py')
        execution_root=A/('.work/native-controls-failure-verification-execution-'+number)
        for path in [verifier,*[execution_root/name for name in ['record.json','stdout','stderr']]]:check(path)
        execution=data(execution_root/'record.json')
        require(execution['returncode']==0 and execution['source_sha256']==files[str(verifier)]['sha256']==audit['verifier_sha256'],
            'prior audit execution differs')
        root=Path(stock['path']).parent
        expected={'smoke-rustc'} if number=='01' else {'smoke-rustc','stock-main.rs'}
        require(set(p.name for p in root.iterdir())==expected and not root.is_symlink(),'old native root membership changed')
        require(set(p.name for p in (work/'commands').iterdir())=={f'{i:03}' for i in range(count)},'old command membership changed')
        require(not (work/'native-controls.json').exists() and not list((work/'artifacts').iterdir()),'old failure gained qualification evidence')
        if number=='02':
            derived=audit['private_stock_source'];check(Path(derived['path']))
            require(files[derived['path']]=={key:derived[key] for key in ['identity','sha256','size']}
                and derived==terminal['stock_source'] and derived['sha256']=='2830149bab94db375ec164229320f060096bd5c1ba2576045148bfc090fdcd68'
                and audit['historical_failed_children']==5 and audit['total_actual_native_children']==11
                and audit['qualified_native_children']==0,'second failure derivation or scope differs')
        proofs.append(dict(source=str(source),evidence=str(work),status='verified-retained-failure',
            receipt_sha256=audit['receipt_sha256'],inputs_sha256=inputs_sha,audit=dict(path=str(audit_path),sha256=audit_sha),
            diagnosis=dict(path=str(diagnosis),sha256=diagnosis_sha),actual_children=count,qualified_children=0,
            unqualified_stock=stock,fixture_never_created=True))
    require([row['actual_children'] for row in proofs]==[5,6] and sum(row['actual_children'] for row in proofs)==11,
        'ordered prior failed11 scope differs')
    return proofs
