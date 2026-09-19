"""Independent finite readback of actual1456 file-only retirement; no mutation."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import time

R = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
H = R/'experiments/runtime-exporter07-closed-cache-retirement-01'
W = X/'.work/runtime-exporter07-closed-cache-retirement-01'
E = R/'.work/runtime-exporter07-closed-cache-retirement-execution-01'
FIELDS = ('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')
CHECKED = {}


def identity(p):
    s = Path(p).lstat(); return {k:getattr(s,'st_'+k) for k in FIELDS}


def file(p, expected=None):
    p = Path(p); before = identity(p); h = hashlib.sha256(); size = 0
    assert p.resolve(strict=True) == p and p.is_file() and before['size'] <= 32*2**20
    with p.open('rb') as stream:
        while block := stream.read(2**20): size += len(block); h.update(block)
    row = dict(path=str(p),identity=before,sha256=h.hexdigest(),bytes=size)
    assert identity(p) == before and size == before['size'] and (expected is None or row['sha256'] == expected)
    CHECKED[str(p)] = row; return row


def read(p, expected=None): file(p, expected); return json.loads(Path(p).read_bytes())


def main():
    plan = read(H/'plan.json','8720f4814a6ab357e751163e37720689e2e5ebf764e820ab2ec053d15faf3d10')
    file(H/'retire.py','67a941b759603eb243b68ec0706e532530b92b8992f1b99d7ddeee616b76f171')
    parent = read(E/'record.json','1c451a41d343e9bfdc2650d3a8e07fe105af8055ad9c9392925c3d4a38e92927')
    terminal = read(W/'receipt.json',parent['receipt']['sha256'])
    assert parent['status'] == 'finished' and parent['returncode'] == 0 and not parent['child_may_be_live']
    assert terminal['status'] == 'passed' and terminal['pid'] == parent['child_pid'] and terminal['parent_pid'] == parent['parent_pid']
    assert parent['started_at'] <= terminal['started_at'] <= terminal['admitted_at'] <= terminal['finished_at'] <= terminal['canonical_parent_lock_closed_at'] <= parent['finished_at']
    assert terminal['removed_files'] == 1456 and terminal['retained_files'] == 9952 and terminal['removed_directories'] == terminal['signals'] == terminal['compiler_calls'] == 0
    assert not terminal['live_probe_possible'] and terminal['all_directories_retained'] and not terminal['capacity_reservation_claim']
    assert parent['command'] == dict(argv=['/opt/homebrew/bin/python3','-B',str(H/'retire.py'),'--plan-sha256',terminal['plan_sha256']],cwd=str(R),environment=plan['environment'])
    for label in ['stdout','stderr']:
        file(E/label,parent[label]['sha256']); assert (E/label).read_bytes() == b''
    for path,row in plan['frozen_files'].items():
        current = file(path,row['sha256']); assert current['identity'] == row['identity']
    assert len(terminal['children']) == len(plan['commands']) == 10
    previous = terminal['admitted_at']
    for ref,spec in zip(terminal['children'],plan['commands'],strict=True):
        p = Path(ref['path']); child = read(p,ref['sha256']); assert identity(p) == ref['identity']
        assert ref['label'] == spec['label'] and child['argv'] == spec['argv'] and child['cwd'] == str(R) and child['environment'] == plan['environment']
        assert child['parent_pid'] == terminal['pid'] and child['status'] == 'finished' and child['returncode'] == 1 and not child['child_may_be_live']
        assert previous <= child['started_at'] <= child['wait_returned_at'] <= child['observation_finished_at'] <= terminal['finished_at']; previous = child['observation_finished_at']
        assert child['raw_bytes'] == 0 and not child['raw_bound_exceeded']
        for name in ['stdout','stderr']:
            current = file(p.parent/name,child[name]['sha256']); assert current['identity'] == child[name]['identity'] and current['bytes'] == 0
    retained = removed = directories = 0; root_proofs = []
    for i,(scope,result) in enumerate(zip(plan['scopes'],terminal['roots'],strict=True)):
        root = Path(scope['root']); assert result['root'] == str(root)
        file(scope['inventory']['path'],scope['inventory']['sha256']); initial = json.loads(gzip.decompress(Path(scope['inventory']['path']).read_bytes()))
        expected = initial['rows']; ledger_path = W/'ledgers'/f'{i:02d}.jsonl'; file(ledger_path)
        raw = ledger_path.read_bytes(); assert raw.endswith(b'\n'); events = [json.loads(v) for v in raw.splitlines()]
        assert len(events) == 3*len(scope['selected_files'])
        for name,offset in zip(sorted(scope['selected_files']),range(0,len(events),3),strict=True):
            intent,unlinked,validated = events[offset:offset+3]; path = str(root/name); parent_name = str(Path(name).parent)
            assert [r['event'] for r in [intent,unlinked,validated]] == ['intent','unlinked','validated']
            assert all(r['path'] == path and r['relative'] == name for r in [intent,unlinked,validated])
            assert intent['before'] == expected[name]['identity'] and intent['sha256'] == expected[name]['sha256'] and intent['parent_before'] == expected[parent_name]['identity']
            assert {k:v for k,v in unlinked.items() if k not in ['event','time']} == {k:v for k,v in intent.items() if k not in ['event','time']}
            assert previous <= intent['time'] <= unlinked['time'] <= validated['time'] <= terminal['finished_at']; previous = validated['time']
            assert all(validated['after'][k] == intent['before'][k] for k in ['dev','ino','mode','size','mtime_ns']) and validated['after']['nlink'] == 0
            assert all(validated['parent_after'][k] == intent['parent_before'][k] for k in ['dev','ino','mode'])
            expected[parent_name]['identity'] = validated['parent_after']; del expected[name]
            assert not os.path.lexists(root/name); removed += 1
        for kind in ['intent','unlinked','validated']:
            assert result['ledger'][kind] == [str(root/name) for name in sorted(scope['selected_files'])]
        assert not result['ledger']['uncertain'] and result['ledger']['readback_error'] is None
        rr = result['remaining_inventory']; file(rr['path'],rr['sha256']); assert identity(rr['path']) == rr['identity']
        actual = json.loads(gzip.decompress(Path(rr['path']).read_bytes())); assert actual == dict(root=str(root),rows=expected)
        assert identity(root.parent) == scope['outer_parent']
        # The saved proof is reconstructed independently; every surviving named
        # file is additionally reread to EOF and every directory membership checked.
        children = {n:set() for n,v in expected.items() if v['kind']=='directory'}
        for name in expected:
            if name != '.': children[str(Path(name).parent)].add(Path(name).name)
        for name,row in expected.items():
            p = root if name == '.' else root/name
            assert identity(p) == row['identity']
            if row['kind'] == 'file':
                checked = file(p,row['sha256']); assert checked['identity'] == row['identity']; retained += 1
            else: assert set(os.listdir(p)) == children[name]; directories += 1
        root_proofs.append(dict(root=str(root),removed=len(scope['selected_files']),retained=result['retained_files'],remaining=rr,ledger=file(ledger_path)))
    assert (removed,retained,directories) == (1456,9952,6059)
    # Retain references to payload checks compactly; full rows remain in the
    # already authenticated current remaining-inventory gzip documents.
    cache_roots=[Path(s['root']) for s in plan['scopes']]
    evidence=[r for p,r in CHECKED.items() if not any(Path(p).is_relative_to(root) for root in cache_roots)]
    report=dict(status='verified',observed_at=time.time(),reader=file(Path(__file__).resolve()),parent=file(E/'record.json'),receipt=file(W/'receipt.json'),
        plan=file(H/'plan.json'),source=file(H/'retire.py'),removed_files=removed,retained_files=retained,retained_directories=directories,
        readonly_probes=10,all_probe_raw_empty=True,complete_intent_unlinked_validated_chains=True,all_remaining_named_files_current_eof_sha_and7stamps=True,
        all_directory_memberships_current=True,roots=root_proofs,checked_evidence=evidence,provider_payload_rehashed=False,signals=0,deletion_retries=0,
        limitation='Independent saved readback/current exact remaining files; no compiler/probe/deletion replay and no capacity guarantee.')
    out=X/'.work/runtime-exporter07-closed-cache-retirement-independent-readback-01.json';assert not out.exists();out.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print(json.dumps(file(out),sort_keys=True))


if __name__ == '__main__': main()
