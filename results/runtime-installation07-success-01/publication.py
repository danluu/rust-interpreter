"""Unrun finite installation07 publisher derived from the closed failure06 copier."""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tarfile
import time

ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
R=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
OUT=ROOT/'results/runtime-installation07-success-01'
SCOPE=A/'.work/runtime-installation07-publication-scope-03.json'
SCOPE_SHA='9a204a5839edb9d9a7f02b74a6d4a770f7c6bf15fc65cb61e6487a3100c3d760'
FIELDS=('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')
PINS={SCOPE:SCOPE_SHA}

def stamp(path):
    value=path.lstat()
    return {k:getattr(value,'st_'+k) for k in FIELDS}


def read(path):
    assert path.is_absolute() and path.resolve(strict=True)==path
    before=stamp(path)
    assert stat.S_ISREG(before['mode']) and before['nlink']==1 and before['size']<=16*2**20
    with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW),'rb') as stream:
        assert {k:getattr(os.fstat(stream.fileno()),'st_'+k) for k in FIELDS}==before
        data=stream.read(16*2**20+1)
        assert {k:getattr(os.fstat(stream.fileno()),'st_'+k) for k in FIELDS}==before
    assert stamp(path)==before and len(data)==before['size']
    row=dict(identity=before,size=len(data),sha256=hashlib.sha256(data).hexdigest())
    if path in PINS:assert row['sha256']==PINS[path]
    return data,row


def tree(root):
    assert root.resolve(strict=True)==root
    rows={'.':stamp(root)};assert stat.S_ISDIR(rows['.']['mode'])
    pending=[root]
    while pending:
        parent=pending.pop()
        before=stamp(parent)
        for path in sorted(parent.iterdir()):
            value=stamp(path)
            assert stat.S_ISREG(value['mode']) or stat.S_ISDIR(value['mode'])
            rows[str(path.relative_to(root))]=value
            if stat.S_ISDIR(value['mode']):pending.append(path)
        assert stamp(parent)==before
    assert all(stamp(root/name)==row for name,row in rows.items())
    return rows


def encoded(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()


def write(path,data):
    with path.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
    assert read(path)[0]==data


def member(path):
    label,base=next((label,base) for label,base in [('ROOT',ROOT),('A',A),('O',O),('R',R),('X',X)] if path.is_relative_to(base))
    return str(Path('payloads')/label/path.relative_to(base))


def main():
    started=time.time()
    assert Path.cwd()==ROOT and not os.path.lexists(OUT)
    scope=json.loads(read(SCOPE)[0]);assert scope['output']==str(OUT)
    assert scope['status']=='source-plan-only-no-capsule-created'
    assert scope['future_audit12']['included'] is True and scope['future_audit12']['outcome']=='failed-closed1-no-report'
    assert scope['future_audit12']['report']['sha256'] is None
    audit_record=json.loads(read(Path(scope['future_audit12']['execution']['path']))[0])
    assert read(Path(scope['future_audit12']['execution']['path']))[1]['sha256']==scope['future_audit12']['execution']['sha256']
    assert audit_record['status']=='finished' and audit_record['returncode']==1 and audit_record['may_be_live'] is False and audit_record['observation_errors']==[]
    trees={Path(p):value for p,value in scope['source_trees'].items()}
    assert {p:tree(p) for p in trees}==trees
    saved={}
    for expected in scope['files']:
        path=Path(expected['path']);data,row=read(path)
        assert dict(path=str(path),**row)==expected
        saved[path]=(data,row)
    assert (len(saved),sum(row['size'] for _,row in saved.values()))==(scope['selected_files'],scope['selected_bytes'])
    planning_history=['runtime-installation07-publication-scope-01.json', 'runtime-installation07-publication-scope-02.json', 'plan_runtime_installation07_publication_01.py', 'plan_runtime_installation07_publication_01.py.before-storage-label.py', 'plan_runtime_installation07_publication_01.py.storage-label.diff', 'plan_runtime_installation07_publication_02.py', 'plan_runtime_installation07_publication_03.py', 'plan_runtime_installation07_publication_03.py.from-plan02.diff', 'plan_runtime_installation07_publication_03.py.before-local-name.py', 'plan_runtime_installation07_publication_03.py.local-name.diff', 'publish_runtime_installation07_success_01.py']
    for path in [Path(__file__),SCOPE,*(A/'.work'/name for name in planning_history)]:
        assert path not in saved;saved[path]=read(path)
    saved=dict(sorted(saved.items()))
    bounds=scope['bounds'];assert len(saved)<=bounds['source_files'] and sum(row['size'] for _,row in saved.values())<=bounds['source_bytes']
    for source in scope['published_source_references']:
        path=ROOT/source['publication'];data,row=read(path)
        assert row['sha256']==source['sha256'] and row['size']==source['size']
        assert read(Path(source['path']))[0]==data
    refs=scope['completed_refs']
    for key in ('launcher','outer','receipt','result','preparation'):
        assert read(Path(refs[key]['path']))[1]['sha256']==refs[key]['sha256']
    receipt=json.loads(saved[Path(refs['receipt']['path'])][0]);assert receipt['status']=='passed' and len(receipt['children'])==15
    result=json.loads(saved[Path(refs['result']['path'])][0]);assert result['status']=='passed'
    oldreadback=A/'.work/runtime-installation07-closed-independent-readback-01.json'
    closed=json.loads(saved[oldreadback][0]);assert closed['installation_itself_passed'] is True
    prefix=Path(refs['publication']['ready']['path']).parent
    metadata=closed['publication_metadata']
    expected_metadata={name:{k:value[i] for i,k in enumerate(('dev','ino','mode','size','mtime_ns','ctime_ns','nlink'))} for name,value in metadata.items()}
    assert tree(prefix)==expected_metadata
    OUT.mkdir()
    with (OUT/'evidence.tar.gz').open('xb') as output:
        with gzip.GzipFile(filename='',mode='wb',fileobj=output,mtime=0,compresslevel=6) as compressed:
            with tarfile.open(mode='w|',fileobj=compressed,format=tarfile.PAX_FORMAT) as archive:
                for path,(data,row) in saved.items():
                    assert read(path)==(data,row)
                    entry=tarfile.TarInfo(member(path));entry.size=len(data);entry.mode=0o444;entry.mtime=0
                    archive.addfile(entry,io.BytesIO(data));assert read(path)==(data,row)
        output.flush();os.fsync(output.fileno())
    archive_raw,archive_row=read(OUT/'evidence.tar.gz')
    with gzip.GzipFile(fileobj=io.BytesIO(archive_raw),mode='rb') as stream:
        expanded=stream.read(bounds['expanded_tar_bytes']+1)
        assert len(expanded)<=bounds['expanded_tar_bytes'] and stream.read(1)==b''
    expected={member(path):(path,data,row) for path,(data,row) in saved.items()}
    with tarfile.open(fileobj=io.BytesIO(expanded),mode='r:') as archive:
        entries=archive.getmembers();assert [e.name for e in entries]==list(expected)
        for entry in entries:
            path,data,row=expected[entry.name]
            assert entry.isfile() and entry.size==len(data) and entry.mode==0o444
            payload=archive.extractfile(entry).read(bounds['single_file_bytes']+1)
            assert payload==data and hashlib.sha256(payload).hexdigest()==row['sha256']
            assert read(path)==(data,row)
    assert {p:tree(p) for p in trees}==trees and tree(prefix)==expected_metadata
    manifest=dict(status='lossless-closed-installation07-evidence',archive=dict(path='evidence.tar.gz',**archive_row),
        files=[dict(path=str(path),member=member(path),**row) for path,(_,row) in saved.items()],
        source_trees=scope['source_trees'],published_source_references=scope['published_source_references'],
        snapshot_retention=scope['snapshot_retention'],source_payload_bytes=sum(row['size'] for _,row in saved.values()),
        full_gzip_eof=True,all_members_rehashed=True,originals_unchanged=True,provider_payload_reads=False,
        prefix_metadata_source=refs['publication'],installed_prefix_metadata_unchanged=True,bounds=bounds)
    write(OUT/'manifest.json',encoded(manifest))
    summary=dict(status='installation07-passed-independent-audit12-failed',actual_children=15,
        loader_children=10,compiler_information_children=3,expected_E0080_children=2,closure=refs,
        scope=scope['scope'],manifest_sha256=read(OUT/'manifest.json')[1]['sha256'],archive_sha256=archive_row['sha256'],
        archive_bytes=archive_row['size'],members=len(saved),primary_tree_files=sum(v['files'] for v in scope['tree_counts'].values()),primary_tree_bytes=sum(v['bytes'] for v in scope['tree_counts'].values()),audit12=scope['future_audit12'],
        preparation_scope='Original actual preparation performed full guards; independent packet/snapshot readback retained verbatim.',
        completion_scope='Exact fifteen child raw/recipe closures and current publication metadata. Provider payloads not reread. Independent audit12 failed closed; its report is absent at the retained failure observation.',
        external_retention='All external snapshot/provider/prefix references and source hashes remain in the exact saved packet/catalog/admission; 302 reused blobs and installed binary payloads are not duplicated.',
        compiler_or_provider_calls_during_publication=0,pid=os.getpid(),started_at=started,finished_at=time.time())
    write(OUT/'summary.json',encoded(summary))
    write(OUT/'STATUS.md',b'Installation07 passed with all fifteen expected children: ten explicit ARM64 loader probes, three compiler information probes and two expected E0080 source probes. The separate saved audit12 failed closed with return code1 and produced no report. Its undeclared provider-identity path traceback is retained. No std, exporter, application or performance qualification is claimed.\n\nThe deterministic archive retains all 322 files from the eight closed packet/execution/manifest trees, publication metadata and bounded readbacks. It includes the 230 new compressed snapshots; 302 reused snapshots and all provider/binary payloads retain exact external references. Already committed source and control evidence is referenced by commit, path and SHA instead of recursively copied. The bounded completion readback checks current installed metadata; it is not a provider-payload rehash.\n\nPublication verifies gzip EOF, exact archive membership, every retained byte and current original stamps. All originals remain unchanged. Parent Git publication must verify the complete finite output set and every HEAD blob, including the archive.\n')
    write(OUT/'publication.py',saved[Path(__file__)][0])
    assert {p.name for p in OUT.iterdir()}=={'evidence.tar.gz','manifest.json','summary.json','STATUS.md','publication.py'}
    outputs={p.name:read(p)[1] for p in sorted(OUT.iterdir())}
    assert sum(row['size'] for row in outputs.values())<=bounds['output_bytes']
    assert all(read(path)==pair for path,pair in saved.items())
    assert {p:tree(p) for p in trees}==trees and tree(prefix)==expected_metadata
    report=dict(status='verified-lossless-installation07-publication',directory=str(OUT),outputs=outputs,summary=summary,
        full_gzip_eof=True,exact_members_and_current_source_stamps=True,provider_payload_reads=False,source_mutations=False)
    report_path=A/'.work/runtime-installation07-success-publication-readback-02.json'
    write(report_path,encoded(report))
    print(json.dumps(dict(path=str(report_path),sha256=read(report_path)[1]['sha256'],members=len(saved))))


if __name__=='__main__':main()
