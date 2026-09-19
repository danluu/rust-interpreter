"""Finite source-only std audit13-association publication; no workload inputs."""
import hashlib
import json
from pathlib import Path
import stat
import time

ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
H=ROOT/'experiments/runtime-std-after-installation07-01'
BASE=ROOT/'results/runtime-std07-source-development-01'
OUT=ROOT/'results/runtime-std07-audit13-source-association-01'
BASE_SHA='c754e6556cde1aeaf5f9557f3f22b30a224b4bce910e546151dd7c21f9b416e6'
ROOT_REVIEW=ROOT/'.work/runtime-std07-audit13-association-root-review-01.json'
ROOT_REVIEW_SHA='1d0585c4332073be05832f4193d88504f0bc899d749ea53b32821931bb5317a6'
NAMES=[
 'bind_runtime_std07_packet_01.py','bind_runtime_std07_packet_01.new-source.diff',
 'bind_runtime_std07_packet_02.py','bind_runtime_std07_packet_02.from-audit12.diff',
 'execute_runtime_std07_packet_binding_01.py','execute_runtime_std07_packet_binding_01.new-source.diff',
 'execute_runtime_std07_packet_binding_02.py','execute_runtime_std07_packet_binding_02.from-audit12.diff',
 'runtime-std07-packet-binding-invocation-template-01.json',
 'runtime-std07-packet-binding-invocation-template-02.json',
 'runtime-std07-packet-binding-invocation-template-02.from-template01.diff',
 'runtime-std07-packet-binding-request-template-03.json',
 'runtime-std07-packet-binding-request-template-04.json',
 'runtime-std07-packet-binding-request-template-04.from-template03.diff',
 'runtime-std07-packet-binding-source-outline-01.json',
 'runtime-std07-packet-binder-source-handoff-01.json',
 'runtime-std07-binding-transport-source-handoff-01.json',
 'runtime-std07-audit13-association-source-handoff-01.json',
 'runtime-std-after-installation07-source-outline-01.json',
 'runtime-std-after-installation07-source-outline-01.md',
 'runtime-std-after-installation07-source-handoff-01.json',
 'runtime-std-after-installation07-source-handoff-02.json',
 'runtime-std-after-installation07-source-handoff-03.json',
 'publish_runtime_std07_audit13_sources_01.py']


def stamp(p):
    s=p.lstat();return [s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink]


def read(p):
    p=Path(p);before=stamp(p)
    assert p.resolve(strict=True)==p and stat.S_ISREG(before[2]) and before[3]<=2*2**20
    b=p.read_bytes();assert len(b)==before[3] and stamp(p)==before
    return b,dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),identity=before)


def write(p,b):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(b)
    saved,row=read(p);assert saved==b and row['identity'][6]==1
    return row


def encoded(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()


def relative(p):
    for name,root in [('ROOT',ROOT),('X',X),('A',A),('O',O)]:
        if p.is_relative_to(root):return 'retained/'+name+'/'+str(p.relative_to(root))
    raise RuntimeError('unexpected source owner: '+str(p))


def main():
    base_bytes,base_ref=read(BASE/'manifest.json');assert base_ref['sha256']==BASE_SHA
    base=json.loads(base_bytes);assert base['payload_files']==27 and base['tests']==12
    by_hash={(r['sha256'],r['bytes']):r for r in base['files']}
    by_original={r['original']:r for r in base['files']}
    _,review_ref=read(ROOT_REVIEW);assert review_ref['sha256']==ROOT_REVIEW_SHA
    handoff=json.loads(read(X/'.work/runtime-std-after-installation07-source-handoff-03.json')[0])
    preserved=handoff['audit13_association']['preserved_exact17'];assert len(preserved)==17
    snapshot_refs=[]
    for value in preserved.values():
        payload,current=read(value['retained']['path']);assert current==value['retained']
        prior=by_original[value['original']['path']]
        archived,archived_row=read(BASE/prior['relative'])
        assert payload==archived and current['sha256']==prior['sha256']
        snapshot_refs.append(dict(snapshot=current,original=value['original'],
            publication_member=prior['relative'],sha256=prior['sha256'],bytes=prior['bytes']))
    selected=[X/'.work'/name for name in NAMES]
    selected.extend(H/Path(p).relative_to(H) for p in by_original if Path(p).is_relative_to(H))
    selected.extend([H/'imports.py.from-audit12.diff',H/'README.md.from-audit12.diff',ROOT_REVIEW,
        ROOT/'.work/runtime-std07-development12-root-readback-01.json',
        O/'.work/runtime-std07-binder-independent-source-review-01.json',
        O/'.work/runtime-std07-schema-selection-independent-review-01.json',
        A/'.work/runtime-std07-supervisor-selection-independent-source-review-01.json'])
    assert len(selected)==len(set(selected)) and len(selected)<=64
    copied=[];references=[];inputs=[];total=0
    for p in sorted(selected):
        payload,current=read(p);inputs.append(current)
        prior=by_hash.get((current['sha256'],current['bytes']))
        if prior:
            archived,_=read(BASE/prior['relative']);assert payload==archived
            references.append(dict(current=current,publication_member=prior['relative']))
        else:
            total+=len(payload);assert total<=4*2**20
            copied.append((p,payload,current,relative(p)))
    assert not OUT.exists() and not OUT.is_symlink();OUT.mkdir()
    rows=[]
    for p,payload,current,name in copied:
        saved=write(OUT/name,payload)
        rows.append(dict(original=current,relative=name,retained=saved))
    manifest=dict(status='verified-source-only-audit13-association-publication',finished_at=time.time(),
        predecessor_publication=base_ref,payload_files=len(rows),payload_bytes=total,files=rows,
        references=references,preserved_original17=snapshot_refs,actual_audit13_pass=None,
        actual_packet_binding=False,actual_std_preparation=False,tests_rerun=False,
        prior_development12_only=True,application_qualified=False,performance_measurement=False)
    manifest_row=write(OUT/'manifest.json',encoded(manifest))
    status=('Source-only audit12→13 association successor. Runtime07 and the report path are unchanged.\n'
        'The binder/transport operational logic is unchanged after literal route/hash reversal.\n'
        'No audit success, packet binding, std preparation or test rerun is claimed.\n'
        'Original17 source bytes and prior development12 evidence remain in the referenced c754 publication;\n'
        'the local original17 snapshot was fully compared against those published members.\n')
    status_row=write(OUT/'STATUS.md',status.encode())
    for current in inputs:
        assert read(current['path'])[1]==current
    for value in snapshot_refs:
        assert read(value['snapshot']['path'])[1]==value['snapshot']
    expected={r['relative'] for r in rows}|{'manifest.json','STATUS.md'}
    actual={str(p.relative_to(OUT)) for p in OUT.rglob('*') if p.is_file()}
    assert actual==expected
    for r in rows:assert read(OUT/r['relative'])[1]==r['retained']
    readback=dict(status='verified',payload_files=len(rows),payload_bytes=total,
        files=len(actual)+1,manifest=manifest_row,status_file=status_row,
        source_eof_sha_and_current_identity=True,retained_eof_sha_and_identity=True,
        exact_membership=True,prior_publication=base_ref,original17_compared=True,
        no_duplicate_prior_payloads=True,finished_at=time.time())
    readback_row=write(OUT/'readback.json',encoded(readback))
    assert {str(p.relative_to(OUT)) for p in OUT.rglob('*') if p.is_file()}==expected|{'readback.json'}
    print(json.dumps(dict(status='verified',output=str(OUT),payload_files=len(rows),payload_bytes=total,
        references=len(references),original17_references=len(snapshot_refs),manifest=manifest_row,readback=readback_row),sort_keys=True))


if __name__=='__main__':main()
