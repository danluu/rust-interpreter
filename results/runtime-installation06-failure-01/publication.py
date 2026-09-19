"""Finite closed-installation failure retention; no provider payload access."""
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
OUT=ROOT/'results/runtime-installation06-failure-01'
SOURCE=ROOT/'experiments/runtime-installation-after-preflight05-02'
WORK=R/'.work/hir-options-hash-runtime-installation-06'
LAUNCH=R/'.work/hir-options-hash-runtime-installation-launch-execution-06'
OUTER=R/'.work/experiments/hir-options-hash-runtime-installation-supervisor-06'
PREP=R/'.work/hir-options-hash-runtime-installation-preparation-execution-06'
PACKET=SOURCE/'installation-plan-01'
PREFIX=R/'.work/runtime-compilers/ac216a6a0962f84ba7a4c4d02f271e531d34e0810e0f537d5b1a5af7857e79b6'
FIELDS=('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')
TREE_COUNTS={WORK:(62,2722470),LAUNCH:(4,33015),OUTER:(4,5430),PREP:(7,223381),PACKET:(7,10509928)}
PINS={
WORK/'receipt.json':'a54ba5d9f11a9a0d0b06da7d228ee9a60c85a0315ad1edfafd120c35b707045c',
OUTER/'status.json':'d5a5ac8813f7f2dc9c9484d70708a560f6d9adc098f72dd701f64de2bd0fb7b6',
LAUNCH/'record.json':'25a5f628255a1d38a9dd94933f48be92cfc3b0335164fe1f3cc7ba8478412a1b',
PREP/'record.json':'2979f64660c2154d6fda90da711f3c967e15442cdb93191ff854ced5385c90f8',
A/'.work/runtime-installation06-loader-failure-readback-01.json':'0f851a54b1fa002852105006c7510876b626b14d560cc1f3feced795eabb409d',
A/'.work/runtime-installation06-prepared-packet-independent-readback-01.json':'ab33c3718eda57c2d85ba12915e436fc67f5b9bfbb6c973251021646ad3dacfc',
O/'.work/runtime-installation06-loader-origin-independent-review-01.json':'4c0c9cf88e35bfc11f1ef75eb0104027d27731b7ccba38242bf904d366fc4598',
O/'.work/runtime-native-loader-identity-schema-review-01.json':'de09638c26bc53cdf90c168471b23557a0ae455061c1768f1e5b1639c8ffe6a5',
ROOT/'.work/runtime-installation06-preparation-invocation-01.json':'0fb2866a8922cb4ba72ab6270b84b167e3725715c1bfa6a1fc25a3b7984aa32d',
ROOT/'.work/runtime-installation06-preparation-source-binding-review-01.json':'50b388547e42dc1346d4452555e9315fad9734ba5914734ba84101e4d6040c6d',
ROOT/'.work/runtime-installation06-startup-qualified-source-manifest-01.json':'9128c3c39703fda7df985a36e819e76fade41ef38886243f574713fd8b8d9351',
}


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
    trees={str(root):tree(root) for root in TREE_COUNTS}
    paths=set(PINS)
    for root,(count,size) in TREE_COUNTS.items():
        selected=[root/name for name,row in trees[str(root)].items() if stat.S_ISREG(row['mode'])]
        assert (len(selected),sum(trees[str(root)][str(p.relative_to(root))]['size'] for p in selected))==(count,size)
        paths.update(selected)
    names=['entry.py','controller.py','audit_owner.py','prepare.py','prepare_once.py','launch.py','routes.json','test_installation.py']
    paths.update(SOURCE/name for name in [*names,*(name+'.from-05.diff' for name in names),'README.md'])
    paths.update(A/'.work'/name for name in [
        'runtime-installation06-binder04-source-handoff-01.json',
        'runtime-installation06-binder04-independent-readback-01.json',
        'runtime-installation06-launch-command-handoff-01.json',
        'readback_runtime_installation06_preparation_01.py',
        'readback_runtime_installation06_preparation_01.before-catalog-reservation.py',
        'readback_runtime_installation06_preparation_01.before-invocation-serialization.py',
        'readback_runtime_installation06_preparation_01.before-preimport-scope.py',
        'readback_runtime_installation06_preparation_01.catalog-reservation.diff',
        'readback_runtime_installation06_preparation_01.invocation-serialization.diff',
        'readback_runtime_installation06_preparation_01.preimport-scope.diff',
        'diagnose_runtime_installation06_loader_failure_01.py'])
    paths.update([ROOT/'.work/bind_runtime_installation06_preparation_04.py',
        ROOT/'.work/bind_runtime_installation06_preparation_04.from-03.diff',
        O/'.work/runtime-installation06-binder04-preimport-independent-source-slice-01.json',
        R/'scripts/runtime_compiler.py',
        X/'experiments/hir-options-hash/runtime-installation-01/discovery.py',
        X/'experiments/hir-options-hash/runtime-installation-01/recipe.py',
        ROOT/'experiments/hir-options-hash-runtime-audit-04/recipe.py',
        PREFIX/'admission.json',PREFIX/'failure.json',Path(__file__),
        ROOT/'.work/publish_runtime_installation06_failure_01.py',
        ROOT/'.work/runtime-installation06-publication-attempt01-observation.json',
        ROOT/'.work/publish_runtime_installation06_failure_02.from-01.diff'])
    saved={p:read(p) for p in sorted(paths)}
    assert len(saved)<=160 and sum(row['size'] for _,row in saved.values())<=32*2**20
    value=lambda p:json.loads(saved[p][0])
    receipt=value(WORK/'receipt.json');outer=value(OUTER/'status.json');launch=value(LAUNCH/'record.json');prep=value(PREP/'record.json')
    assert receipt['status']=='failed' and receipt['pid']==87781 and receipt['parent_pid']==87735 and len(receipt['children'])==10
    assert receipt['error']=="RuntimeError('actual runtime loader declaration differs')"
    assert outer['status']=='finished' and outer['returncode']==1 and outer['child_pid']==receipt['pid']
    assert launch['status']=='terminal-observed' and launch['returncode']==1 and launch['launcher_returncode']==0
    assert launch['outer_sha256']==PINS[OUTER/'status.json']
    assert receipt['finished_at']<=outer['finished_at']<=launch['terminal_observed_at']<=launch['finished_at']
    assert prep['status']=='finished' and prep['returncode']==0 and prep['preparation_passed'] is True
    failure=value(A/'.work/runtime-installation06-loader-failure-readback-01.json')
    assert failure['all_ten_children_closed_zero'] is True and failure['actual_compiler_cli_children']==failure['actual_source_probe_children']==0
    prefix_before=tree(PREFIX)
    assert prefix_before==failure['partial_prefix_metadata'] and len(prefix_before)==4653
    assert not any(os.path.lexists(PREFIX/name) for name in ['ready.json','qualification.json'])
    assert not os.path.lexists(WORK/'source-probe')
    assert value(PREFIX/'failure.json')=={'error':'actual runtime loader declaration differs','key':receipt['runtime_key']}
    for name in ['stdout','stderr']:
        assert saved[LAUNCH/name][1]['sha256']==launch[name+'_sha256']
        assert saved[PREP/name][1]['sha256']==prep[name+'_sha256']
    OUT.mkdir()
    with (OUT/'evidence.tar.gz').open('xb') as output:
        with gzip.GzipFile(filename='',mode='wb',fileobj=output,mtime=0,compresslevel=6) as compressed:
            with tarfile.open(mode='w|',fileobj=compressed,format=tarfile.PAX_FORMAT) as archive:
                for path,(data,row) in saved.items():
                    assert read(path)==(data,row)
                    entry=tarfile.TarInfo(member(path));entry.size=len(data);entry.mode=0o444;entry.mtime=0
                    archive.addfile(entry,io.BytesIO(data))
                    assert read(path)==(data,row)
        output.flush();os.fsync(output.fileno())
    archive_raw,archive_row=read(OUT/'evidence.tar.gz')
    # Consume the entire bounded gzip including CRC/EOF before parsing any tar.
    with gzip.GzipFile(fileobj=io.BytesIO(archive_raw),mode='rb') as stream:
        expanded=stream.read(48*2**20+1)
        assert len(expanded)<=48*2**20 and stream.read(1)==b''
    expected={member(path):(path,data,row) for path,(data,row) in saved.items()}
    with tarfile.open(fileobj=io.BytesIO(expanded),mode='r:') as archive:
        entries=archive.getmembers()
        assert len(entries)==len(expected) and [e.name for e in entries]==list(expected)
        for entry in entries:
            path,data,row=expected[entry.name]
            assert entry.isfile() and entry.size==len(data) and entry.mode==0o444
            payload=archive.extractfile(entry).read(16*2**20+1)
            assert payload==data and hashlib.sha256(payload).hexdigest()==row['sha256']
            assert read(path)==(data,row)
    assert {str(root):tree(root) for root in TREE_COUNTS}==trees
    assert tree(PREFIX)==prefix_before
    manifest=dict(status='lossless-closed-installation-failure',archive=dict(path='evidence.tar.gz',**archive_row),
        source_trees=trees,files=[dict(path=str(path),member=member(path),**row) for path,(_,row) in saved.items()],
        partial_prefix=str(PREFIX),partial_prefix_metadata=prefix_before,
        source_payload_bytes=sum(row['size'] for _,row in saved.values()),full_gzip_eof=True,all_members_rehashed=True,
        originals_unchanged=True,partial_prefix_payloads_rehashed=False,
        bounds=dict(source_files=160,source_bytes=32*2**20,single_file_bytes=16*2**20,expanded_tar_bytes=48*2**20))
    write(OUT/'manifest.json',encoded(manifest))
    summary=dict(status='failed-installation-six-after-ten-successful-loader-children',preparation_passed=True,
        preparation_record_sha256=PINS[PREP/'record.json'],runtime_qualified=False,actual_children=10,planned_children=15,
        loader_children_closed_zero=10,compiler_cli_children=0,source_probe_children=0,
        receipt_sha256=PINS[WORK/'receipt.json'],outer_sha256=PINS[OUTER/'status.json'],launcher_sha256=PINS[LAUNCH/'record.json'],
        controller_pid=receipt['pid'],supervisor_pid=receipt['parent_pid'],launcher_finished_at=launch['finished_at'],
        failure='actual runtime loader declaration differs',manifest_sha256=read(OUT/'manifest.json')[1]['sha256'],
        archive_sha256=archive_row['sha256'],archive_bytes=archive_row['size'],members=len(saved),
        primary_tree_files=84,primary_tree_bytes=13494224,partial_prefix_entries=4653,
        preparation_scope='Original actual preparation performed full guards. Its independent readback scope is retained verbatim.',
        failure_readback_scope='Ten closed command/raw associations and complete unchanged partial-prefix metadata; no independent partial-prefix payload rehash.',
        external_retention='Provider/compiler/sysroot payloads and reused snapshot/base evidence stay at the exact original paths declared in saved inputs/admission/catalogs. This capsule copies no provider or partial-prefix binary payload.',
        performance_measurement=False,compiler_or_provider_calls_during_publication=0,pid=os.getpid(),started_at=started,finished_at=time.time())
    write(OUT/'summary.json',encoded(summary))
    write(OUT/'STATUS.md',b'# Installation06 failed, retained unchanged\n\nPreparation passed. Installation closed with failure after ten successful loader commands; compiler-info and source probes did not run. Four universal sanitizer libraries returned three architecture sections from `otool -l`; every section separately matched the ARM64 declaration, but the old parser concatenated their edges. No runtime, application or performance qualification is claimed.\n\nThe deterministic archive preserves all 84 files from the five closed evidence/packet trees, source02 and derivation diffs, exact binding/start handoffs, readback code/history, finalized independent reviews, and partial-prefix admission/failure metadata. The manifest carries complete source identities and all 4,653 partial-prefix metadata entries. Full gzip EOF and every member byte were independently read back.\n\nOriginal preparation full guards and the later metadata-only partial-prefix readback are different scopes. The retained partial prefix and external compiler/provider payloads were neither copied nor rehashed by this publication. Their original references and admitted hashes remain in the archived packet/admission. No source, receipt, packet or prefix was changed. No retry occurred.\n\nAll five files in this capsule must be published, including the archive; Git publication and HEAD-byte verification are parent-owned.\n')
    write(OUT/'publication.py',saved[Path(__file__)][0])
    assert {p.name for p in OUT.iterdir()}=={'evidence.tar.gz','manifest.json','summary.json','STATUS.md','publication.py'}
    output_rows={p.name:read(p)[1] for p in sorted(OUT.iterdir())}
    assert sum(row['size'] for row in output_rows.values())<=20*2**20
    assert all(read(path)==pair for path,pair in saved.items())
    assert {str(root):tree(root) for root in TREE_COUNTS}==trees and tree(PREFIX)==prefix_before
    report=dict(status='verified-lossless-publication',directory=str(OUT),outputs=output_rows,summary=summary,
        full_gzip_eof=True,exact_members_and_current_source_stamps=True,exact_five_trees=True,
        prefix_metadata_unchanged=True,provider_payload_reads=False,source_mutations=False)
    report_path=A/'.work/runtime-installation06-failure-publication-readback-01.json'
    write(report_path,encoded(report))
    print(json.dumps(dict(status=report['status'],report=str(report_path),sha256=read(report_path)[1]['sha256'],
        members=len(saved),archive=archive_row,summary_sha256=output_rows['summary.json']['sha256'])))


if __name__=='__main__':main()
