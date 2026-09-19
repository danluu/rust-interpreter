"""Bind separately preserved274 executables to the actual post1456 inventories.

Only finite saved metadata and current named identities are read here. No
compiler, target imports, handle probes, archive duplication or deletion.
"""
import ast
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
PREVIOUS=ROOT/'experiments/runtime-exporter07-closed-cache-retirement-01/plan.json'
WORK=X/'.work/runtime-exporter07-closed-cache-retirement-01'
CAPSULE=ROOT/'results/runtime-exporter07-closed-cache-executable-preservation-01'
FIELDS=('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')


def identity(p):
    s=Path(p).lstat();return {k:getattr(s,'st_'+k) for k in FIELDS}


def main():
    assert not (HERE/'plan.json').exists()
    raw=PREVIOUS.read_bytes();assert hashlib.sha256(raw).hexdigest()=='8720f4814a6ab357e751163e37720689e2e5ebf764e820ab2ec053d15faf3d10'
    plan=json.loads(raw);old=copy.deepcopy(plan);frozen=plan['frozen_files']
    def bind(p,wanted=None):
        p=Path(p);before=identity(p);assert p.resolve(strict=True)==p and p.is_file() and before['size']<=32*2**20
        data=p.read_bytes();sha=hashlib.sha256(data).hexdigest();assert identity(p)==before and (wanted is None or wanted==sha)
        frozen[str(p)]=dict(identity=before,sha256=sha);return json.loads(data) if p.suffix=='.json' else None
    bind(PREVIOUS)
    terminal=bind(WORK/'receipt.json','e0cb5b09b3f6bea5163ec2844d2a6d1634d46153f924c5376dcb7028399e4adf')
    previous_execution=ROOT/'.work/runtime-exporter07-closed-cache-retirement-execution-01/record.json'
    parent=bind(previous_execution,'1c451a41d343e9bfdc2650d3a8e07fe105af8055ad9c9392925c3d4a38e92927')
    proof_path=X/'.work/runtime-exporter07-closed-cache-retirement-independent-readback-01.json'
    proof=bind(proof_path,'2c45299ef4d41412f39038582ff235030a1a5d8160f4d64ca39341e403245030')
    assert terminal['status']=='passed' and parent['status']=='finished' and parent['returncode']==0 and not parent['child_may_be_live']
    assert proof['status']=='verified' and (proof['removed_files'],proof['retained_files'],proof['retained_directories'])==(1456,9952,6059)
    manifest=bind(CAPSULE/'manifest.json','7d0aa50bfa7c266b7758ad5f83213e8797629ba0dca08019e0c1d8430ce33b39')
    capsule_record=bind(CAPSULE/'record.json','c3450057aeb0fd4462ec0dbf79e457ba25d431c7568b85244c63b779cb228d34')
    bind(CAPSULE/'READBACK.json','a6d2dd11dbb7b8197d8fc78e99ceaf323ce658f3e4fddac28146261046c8d596')
    bind(CAPSULE/'selection.json');bind(CAPSULE/'started.json')
    preservation_execution=X/'.work/runtime-exporter07-cache-executable-preservation-execution-01/record.json'
    preserved=bind(preservation_execution,'47aa40a61a17e11ba9d4bbd767ea80a3d5d9e772a176ba3b163240d983b63925')
    assert preserved['status']=='finished' and preserved['returncode']==0 and not preserved['child_may_be_live']
    assert manifest['status']=='preserved-not-retired' and manifest['selected_files']==274
    bind(capsule_record['source']['path'],capsule_record['source']['sha256'])
    members={r['path']:r for r in manifest['members']};assert len(members)==274
    assert identity(manifest['archive']['path'])==manifest['archive']['identity']
    total=0
    for scope,actual in zip(plan['scopes'],terminal['roots'],strict=True):
        assert scope['root']==actual['root'];ref=actual['remaining_inventory'];bind(ref['path'],ref['sha256'])
        payload=gzip.decompress(Path(ref['path']).read_bytes());remaining=json.loads(payload);assert remaining['root']==scope['root'] and set(remaining)=={'root','rows'}
        rows=remaining['rows'];assert set(scope['retained_files'])=={n for n,r in rows.items() if r['kind']=='file'}
        selected=[];retained=[];allocated=logical=retained_bytes=0
        for name,row in rows.items():
            if row['kind']!='file':continue
            path=str(Path(scope['root'])/name)
            if path in members:
                member=members[path];assert row['identity']==member['identity'] and row['sha256']==member['sha256']
                assert Path(name).suffix=='' and row['identity']['mode']&0o111 and row['identity']['nlink']==1
                assert identity(path)==row['identity'];allocated+=Path(path).lstat().st_blocks*512;logical+=row['identity']['size'];selected.append(name)
            else:retained.append(name);retained_bytes+=row['identity']['size']
        assert identity(Path(scope['root']).parent)==scope['outer_parent']
        scope.update(inventory=dict(path=ref['path'],sha256=ref['sha256'],bytes=Path(ref['path']).stat().st_size,expanded_bytes=len(payload),expanded_sha256=hashlib.sha256(payload).hexdigest()),root_identity=rows['.']['identity'],
            selected_files=selected,selected_count=len(selected),selected_logical_bytes=logical,selected_allocated_bytes_observation=allocated,
            selection_by_extension={'extensionless-executable-preserved-in-complete-archive':len(selected)},retained_files=retained,retained_count=len(retained),retained_logical_bytes=retained_bytes)
        total+=allocated
    assert sum(s['selected_count'] for s in plan['scopes'])==274 and sum(s['retained_count'] for s in plan['scopes'])==9678 and total==352907264
    pids=set(plan['historical_pids'])|{parent['parent_pid'],parent['child_pid'],preserved['parent_pid'],preserved['child_pid']}
    plan['commands'][-1]['argv'][2]=','.join(map(str,sorted(pids)));plan['historical_pids']=sorted(pids)
    for name in ['retire.py','prepare_plan.py']:ast.parse((HERE/name).read_bytes());bind(HERE/name)
    plan.update(status='concrete-unrun-separate-preserved-executable-retirement-plan',observed_at=time.time(),work=str(X/'.work/runtime-exporter07-cache-executable-retirement-01'),
        selected_files=274,retained_files=9678,selected_logical_bytes=352273936,selected_allocated_bytes_observation=total,
        prior_partial_retirement=dict(plan=str(PREVIOUS),receipt=str(WORK/'receipt.json'),execution=str(previous_execution),independent_readback=str(proof_path)),
        preservation=dict(manifest=str(CAPSULE/'manifest.json'),receipt=str(CAPSULE/'record.json'),readback=str(CAPSULE/'READBACK.json'),execution=str(preservation_execution)))
    plan['transition']=dict(prior_retained_files=9952,now_preserved_in_full_archive=274,remaining_in_place=9678,all_directories_retained=True,
        separate_resource_only_transition=True,prior1456_plan_unchanged=True,prior1456_independent_readback=str(proof_path),preservation=plan['preservation'],
        preserved_outside_roots=old['transition']['preserved_outside_roots'],excluded_legacy=old['transition']['excluded_legacy'],strict_cache_included=False,
        original_native_binaries_remain_byte_exact_in_archive=True,installed_providers_untouched=True)
    plan['limitations']=['Exact274 additional file-only scope after actual1456; prior9,952 retention declaration remains historical and explicit.',
        'Complete gzip274 preservation is authenticated and all member bytes/EOF/CRC verified before and after unlink; archive is retained.',
        'Only current free bytes decide23GiB admission. No actual or guaranteed Git/compression/APFS capacity saving claimed.',
        'Ten exact read-only probes; any historical PID present refuses retirement. No signals/retries.',
        'No provider tree walk;84 exact installed copies checked unchanged. Full9,678 remaining files/all6,059 directories checked after removal.']
    data=(json.dumps(plan,sort_keys=True,indent=2)+'\n').encode()
    with (HERE/'plan.json').open('xb') as out:out.write(data)
    assert (HERE/'plan.json').read_bytes()==data
    print(json.dumps(dict(path=str(HERE/'plan.json'),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),frozen_files=len(frozen),selected_files=274,retained_files=9678),sort_keys=True))


if __name__=='__main__':main()
