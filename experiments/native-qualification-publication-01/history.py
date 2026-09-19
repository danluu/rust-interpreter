"""Read only the saved native/reconciliation proof; no controller or provider API."""
import gzip
import hashlib
import json
from pathlib import Path

A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
SCOPE=A/'.work/native-qualification-publication-scope-02.json'
SCOPE_SHA='ba41bc923eded61ac0d1c044aeaec2c80466d9d4af3b255009d1c4ecffd8d308'
QUAL=A/'.work/hir-options-hash-native-controls-reconciliation-01'
AUDIT=A/'.work/native-reconciliation-independent-verification-01.json'
AUDIT_SHA='6e95c8845fd761757d6db80e375673e126208466fa54ed678a32d3a2a036685e'
FAILED_AUDITS=['af25ceeda3cf32cf63d73b3fd2cee05726267166e0babd58587b884815256f3e',
 'c5f873179ed772de997771fd1c89f409876a79ca520d01ff5f8a288c2f6c879f',
 '1058d64e64d75748a3da12115a8400a01daa5cd499b39b09c8d29520eaab4f24']


def require(ok,message):
    if not ok:raise RuntimeError(message)


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def read(path):
    path=Path(path);require(path.stat().st_size<=64*2**20,'bounded saved JSON')
    return json.loads(path.read_bytes())


def encoded(value):return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()


def snapshots(source,work,terminal,disk):
    projection=read(source/'snapshot-plan.json')['projection'];manifest=read(work/'source-snapshots.json')
    freeze=read(source/'inputs.json')
    require(sha(work/'snapshot-plan.json')==sha(source/'snapshot-plan.json')==terminal['snapshot_plan_sha256']
        and sha(work/'source-snapshots.json')==terminal['source_snapshots_sha256'],'snapshot terminal bindings differ')
    require(manifest['policy']==projection['policy']=='bounded-gzip-proof-snapshots-v1'
        and manifest['blobs']==projection['blobs'] and manifest['projection_sha256']==hashlib.sha256(encoded(projection)).hexdigest()
        and manifest['full_logical_readback'] is True and manifest['full_gzip_eof'] is True,'snapshot projection policy differs')
    require(set(projection['files'])==set(manifest['files'])==set(freeze['snapshot_inputs'])|{str(source/'inputs.json')},
        'full original logical snapshot set differs')
    root=work/'source-snapshots'
    require(set(p.name for p in root.iterdir())=={row['filename'] for row in projection['blobs'].values()},
        'all original compressed proof blobs required')
    total=0
    for digest,row in projection['blobs'].items():
        path=root/row['filename'];disk()
        require(row['filename']==digest+'.gz' and row['logical_sha256']==digest
            and path.stat().st_size==row['compressed_bytes'] and sha(path)==row['sha256']
            and row['logical_bytes']<=64*2**20,'original compressed blob differs')
        length=0;h=hashlib.sha256()
        with gzip.open(path,'rb') as stream:
            while block:=stream.read(min(2**20,row['logical_bytes']-length+1)):
                disk();length+=len(block);require(length<=row['logical_bytes'],'bounded gzip expansion exceeded');h.update(block)
        require(length==row['logical_bytes'] and h.hexdigest()==digest,'full inner gzip hash/EOF differs')
        total+=row['compressed_bytes']
    for name,row in projection['files'].items():
        expected=freeze['files'].get(name)
        if name==str(source/'inputs.json'):
            require(row['sha256']==sha(source/'inputs.json') and row['size']==(source/'inputs.json').stat().st_size,'own freeze snapshot differs')
        else:require(row==dict(path=name,**expected),'full original snapshot alias differs')
        require(manifest['files'][name]==dict(path=str(root/(row['sha256']+'.gz')),sha256=row['sha256'],size=row['size'],encoding='gzip'),
            'logical snapshot path differs')
    require(total==projection['compressed_bytes']==manifest['compressed_bytes'],'compressed snapshot total differs')
    return dict(logical_files=len(projection['files']),physical_gzip_files=len(projection['blobs']),compressed_bytes=total,
                full_logical_hashes=True,full_gzip_eof=True)


def raw(work,child):
    for name in ['stdout','stderr']:
        require((work/name).stat().st_size<=8*2**20 and sha(work/name)==child[name+'_sha256'],'actual raw bytes differ')


def chain(source,work,outer,launcher,code):
    terminal=read(work/'receipt.json');launch=read(source/'launch.json');supervisor=read(outer/'status.json');dispatch=read(launcher/'record.json')
    require(supervisor['status']=='finished' and supervisor['returncode']==code
        and supervisor['child_pid']==terminal['pid'] and supervisor['supervisor_pid']==terminal['parent_pid']
        and supervisor['command']==launch['command'][6:] and supervisor['cwd']==str(A)
        and supervisor['plan_sha256']==sha(outer/'plan.json') and supervisor['log_sha256']==sha(outer/'command.log')
        and supervisor['child_started_at']<=terminal['started_at']<=terminal['admitted_at']<=terminal['finished_at']<=supervisor['finished_at'],
        'closed original outer association differs')
    require(dispatch['command']==launch['command'] and dispatch['environment']==launch['environment']
        and dispatch['launch_sha256']==sha(source/'launch.json')
        and dispatch['launcher_source_sha256']==sha(dispatch['launcher_source_path']), 'original launcher binding differs')
    if dispatch['status']=='terminal-observed':
        require(dispatch['returncode']==code and dispatch['launcher_returncode']==0
            and dispatch['outer_sha256']==sha(outer/'status.json') and dispatch['controller_pid']==terminal['pid']
            and dispatch['supervisor_pid']==terminal['parent_pid'] and supervisor['finished_at']<=dispatch['finished_at'],
            'actual terminal observation differs')
    else:
        require(dispatch['status']=='finished' and dispatch['returncode']==0,'legacy wrapper completion differs')
    raw(launcher,dispatch);handoff=read(launcher/'stdout')
    require(handoff['supervisor_pid']==supervisor['supervisor_pid'] and handoff['directory']==str(outer),'wrapper handoff differs')
    return terminal


def validate_all(disk=lambda:None):
    require(sha(SCOPE)==SCOPE_SHA,'exact reviewed standalone payload scope required');scope=read(SCOPE)
    failures=[]
    for number,count,audit_sha in zip(['01','02','03'],[5,6,20],FAILED_AUDITS,strict=True):
        source=A/('experiments/hir-options-hash-native-controls-'+number);work=A/('.work/hir-options-hash-native-controls-'+number)
        terminal=chain(source,work,A/('.work/experiments/hir-options-hash-native-controls-supervisor-'+number),
            A/('.work/native-controls-launch-execution-'+number),1)
        audit_path=A/('.work/native-controls-failure-verification-'+number+'.json');audit=read(audit_path);plan=read(source/'plan.json')
        require(sha(audit_path)==audit_sha and audit['status']=='verified-retained-failure'
            and audit['receipt_sha256']==sha(work/'receipt.json') and terminal['status']=='failed'
            and len(terminal['commands'])==count and audit['children']==count
            and not (work/'native-controls.json').exists(),'honest original failed prefix differs')
        require(set(p.name for p in (work/'commands').iterdir())=={f'{i:03}' for i in range(count)},'original child membership differs')
        previous=terminal['admitted_at']
        for index,ref in enumerate(terminal['commands']):
            path=work/'commands'/f'{index:03}'/'receipt.json';child=read(path);wanted=plan['children'][index];disk()
            require(ref['path']==str(path) and ref['sha256']==sha(path) and ref['pid']==child['pid']
                and ref['command']==child['command']==wanted['argv'] and child['cwd']==wanted['cwd']
                and child['environment']==wanted['environment'] and child['status']=='finished'
                and child['returncode'] in wanted['expected'] and child['supervisor_pid']==terminal['pid']
                and child['parent_pid']==terminal['parent_pid'] and previous<=child['started_at']<=child['finished_at']<=terminal['finished_at'],
                'complete saved native command chain differs')
            raw(path.parent,child);previous=child['finished_at']
        failures.append(dict(attempt=number,status='failed',actual_commands=count,receipt_sha256=sha(work/'receipt.json'),
            error=terminal['error'],audit_sha256=audit_sha,snapshots=snapshots(source,work,terminal,disk)))
    source=A/'experiments/hir-options-hash-native-reconciliation-01';plan=read(source/'plan.json')
    receipt=chain(source,QUAL,A/'.work/experiments/hir-options-hash-native-controls-reconciliation-supervisor-01',
        A/'.work/native-reconciliation-launch-execution-01',0)
    result=read(QUAL/'native-controls.json');audit=read(AUDIT)
    require(sha(AUDIT)==AUDIT_SHA and audit['status']=='verified' and audit['receipt_sha256']==sha(QUAL/'receipt.json')
        and audit['result_sha256']==receipt['result_sha256']==sha(QUAL/'native-controls.json')
        and receipt['status']=='passed' and receipt['commands']==[] and type(receipt['actual_workload_children']) is int
        and receipt['actual_workload_children']==0 and receipt['saved_actual_children']==20 and receipt['historical_failed_children']==11,
        'separate actual zero-command reconciliation required')
    require(result['qualified_native_children']==20 and result['total_actual_native_children']==31
        and result['source_restored'] is True and result['status']=='native-roles-and-behavior-qualified'
        and receipt['native_roles_and_behavior_qualified'] is True
        and encoded(plan['command_evidence'])==encoded(receipt['command_evidence'])==encoded(result['command_evidence'])
        and encoded(plan['reconciliation'])==encoded(receipt['reconciliation'])==encoded(result['reconciliation']),
        'separate successful native qualification differs')
    old=read(A/'.work/hir-options-hash-native-controls-03/receipt.json')
    require(result['history']==old['commands'][:18] and result['wrong_B3_commands']==old['commands'][18:]
        and plan['command_evidence']['receipt_sha256']==failures[2]['receipt_sha256'], 'original command owner replaced')
    manifest=read(QUAL/'delta-proof.json')
    require(sha(QUAL/'delta-proof.json')==receipt['delta_proof_sha256'] and len(manifest['files'])==125
        and len(manifest['physical'])==89 and set(p.name for p in (QUAL/'delta-proof').iterdir())==set(manifest['physical']),
        'all new byte-bearing delta proofs required')
    for key,row in manifest['physical'].items():
        disk();require(row['path']==str(QUAL/'delta-proof'/key) and sha(row['path'])==key==row['sha256']
            and Path(row['path']).stat().st_size==row['size'],'new delta physical bytes differ')
    for row in manifest['files'].values():
        require(row['path']==str(QUAL/'delta-proof'/row['sha256'])
            and row['size']==manifest['physical'][row['sha256']]['size'],'new delta logical alias differs')
    controls=[]
    for name,count in [('native-stock-source-controls-02',4),('native-loader-route-controls-01',9),('native-wrong-beta-controls-01',11)]:
        control=read(A/'.work'/name/'receipt.json');result_control=read(A/'.work'/name/'result.json')
        require(control['status']==result_control['status']=='passed' and control['controls_passed']==result_control['tests_run']==count
            and control['result_sha256']==sha(A/'.work'/name/'result.json')
            and all(result_control[key]==0 for key in ['failures','errors','skipped','expected_failures','unexpected_successes','compiler_calls']),
            'actual source controls differ')
        controls.append(dict(source=name,controls=count,receipt_sha256=sha(A/'.work'/name/'receipt.json'),
            result_sha256=sha(A/'.work'/name/'result.json')))
    return dict(failed_native_attempts=failures,reconciled_native=dict(receipt_sha256=sha(QUAL/'receipt.json'),
        result_sha256=sha(QUAL/'native-controls.json'),audit_sha256=AUDIT_SHA,actual_new_workload_commands=0,
        saved_qualified_commands=20,total_actual_native_commands=31,delta_logical_files=125,delta_physical_files=89),
        controls=controls,qualified_output_payloads=scope['qualified_output_payloads'],original_failed_auditor_attempt_retained=True,
        rejected_unrun_stock_controls_retained=True,performance_qualification=False)
