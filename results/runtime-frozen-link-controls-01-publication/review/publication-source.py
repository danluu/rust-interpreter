"""Bounded exact-copy publication of closed24; no tests, imports or Git."""
from pathlib import Path
import hashlib
import json
import os
import stat

ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
HELPER=ROOT/'experiments/runtime-frozen-link-reader-01'
CONTROL=ROOT/'experiments/runtime-frozen-link-controls-01'
EVIDENCE=ROOT/'results/runtime-frozen-link-controls-01'
HISTORY=X/'.work/runtime-frozen-link-before-directory-route-01'
OUT=ROOT/'results/runtime-frozen-link-controls-01-publication'
READBACK=X/'.work/runtime-frozen-link-controls-publication-readback-01.json'
FIELDS=('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')


def require(value,message):
    if not value:raise RuntimeError(message)


def file(path):
    path=Path(path);before=path.lstat();identity={k:getattr(before,'st_'+k) for k in FIELDS}
    require(path.resolve(strict=True)==path and stat.S_ISREG(before.st_mode) and before.st_size<=256*1024,'bounded ordinary source')
    raw=path.read_bytes();require(len(raw)==before.st_size and identity=={k:getattr(path.lstat(),'st_'+k) for k in FIELDS},'source changed during full readback')
    return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),identity=identity),raw


def put(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    require(path.read_bytes()==raw,'exact copied readback differs')


def encoded(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()


require(not OUT.exists() and not READBACK.exists(),'fresh publication and readback required')
selected={}
for name in ['links.py','test_links.py','README.md']:selected['source/helper/'+name]=HELPER/name
for name in ['child.py','run_once.py','plan.json','README.md']:selected['source/controls/'+name]=CONTROL/name
evidence_names={'child.py','plan.json','record.json','result.json','run_once.py','source-after.json','source-before.json','started.json','stderr','stdout','manifest.json'}
require({p.name for p in EVIDENCE.iterdir()}==evidence_names|{'tmp'} and not list((EVIDENCE/'tmp').iterdir()),'closed complete actual control namespace')
for name in sorted(evidence_names):selected['evidence/'+name]=EVIDENCE/name
history_names={n+s for n in ['links.py','test_links.py','README.md'] for s in ['','.diff']}
require({p.name for p in HISTORY.iterdir()}==history_names,'complete preserved directory correction history')
for name in sorted(history_names):selected['history/before-directory-route/'+name]=HISTORY/name
for target,path in {
 'history/initial-source-proposal.json':X/'.work/runtime-frozen-link-reader-source-proposal-01.json',
 'review/source-handoff.json':X/'.work/runtime-frozen-link-controls-source-handoff-01.json',
 'review/independent-readback.json':X/'.work/runtime-frozen-link-controls-independent-readback-01.json',
 'review/readback.py':X/'.work/verify_runtime_frozen_link_controls_01.py',
 'review/publication-source.py':Path(__file__),
}.items():selected[target]=path
before={str(path):file(path)[0] for path in selected.values()}
require(len(selected)<=64 and sum(row['bytes'] for row in before.values())<=512*1024,'small publication cap')
require(before[str(EVIDENCE/'result.json')]['sha256']=='cfb7577f2345147a9c5f4d44b7c562d7e92e61bdcc91e7b95fbba48c8ac22497','exact actual24')
require(before[str(X/'.work/runtime-frozen-link-controls-independent-readback-01.json')]['sha256']=='78e01fa9c04b70dc8325039be2c930e37adf9ba25914034d5c98b47b6ea54d6f','exact independent readback')
OUT.mkdir();copied={}
for target,original in sorted(selected.items()):
    row,raw=file(original);require(row==before[str(original)],'source changed after inventory')
    put(OUT/target,raw);copy_row,_=file(OUT/target)
    require(copy_row['sha256']==row['sha256'] and copy_row['bytes']==row['bytes'],'copy byte equality')
    copied[target]=dict(original_path=str(original),source=row,copy=copy_row)
readme='''# Frozen-link helper: 24 actual tests passed

This capsule preserves the complete helper/control source, the initial directory
endpoint draft and its exact correction, one actual 24-test execution, and an
independent saved-byte readback. No test was repeated for publication.

Actual result SHA: cfb7577f2345147a9c5f4d44b7c562d7e92e61bdcc91e7b95fbba48c8ac22497.
Independent readback SHA: 78e01fa9c04b70dc8325039be2c930e37adf9ba25914034d5c98b47b6ea54d6f.
Parent 38915 and child 40259 closed with return code 0. The 24 exact source-derived
test names all passed; no skips, errors or failures occurred. Source hashes and
seven-field identities were equal before, after and at independent readback.
The owned temporary directory was empty. No compiler, provider write, network
operation, process signal or canonical lock was used by the tests.

The helper keeps ordinary Access unchanged. It authenticates exact frozen link
rows while recording and rechecking current ancestor routes throughout an audit.
Directory endpoints retain dev/ino/mode, allowing unrelated child changes;
regular file endpoints retain exact identity and frozen bytes. The original
drafts and their historical unrun descriptions are preserved verbatim. This
README records the later actual test outcome without rewriting those sources.

`publication.json` maps every copied member to its exact original source identity
and hash. `evidence/manifest.json` retains the original complete actual execution
membership. The original empty `tmp` directory is represented by the explicit
empty-directory observation in the independent report; there are no payloads to
copy. The Python interpreter remains an external provider whose actual path,
hash and identity are retained in the original source-before/after records.

The observer initialized its deadline just after the first post-spawn record
publication. Independent timestamps show actual spawn-to-close 0.145524 seconds,
within its stated 60-second observation window; executed sources stay unchanged.

This is helper qualification only. Successful runtime preflight evidence remains
separate, and the fresh full saved audit is not claimed by this capsule. No Git
operations were performed by the publisher.
'''
put(OUT/'README.md',readme.encode())
for original,row in before.items():require(file(original)[0]==row,'original source changed during publication')
publication=dict(status='published-exact-closed-helper-controls',tests=24,members=copied,
 copied_files=len(copied),copied_bytes=sum(r['source']['bytes'] for r in copied.values()),
 generated_readme=file(OUT/'README.md')[0],originals_unchanged=True,target_imports=False,test_reexecution=False,
 external_providers=['Python interpreter row in original source-before/source-after records'],
 empty_original_directories=[str(EVIDENCE/'tmp')],runtime_audit_qualified=False,git_operations=False)
put(OUT/'publication.json',encoded(publication))
expected=set(selected)|{'README.md','publication.json'}
actual={str(p.relative_to(OUT)) for p in OUT.rglob('*') if p.is_file()}
require(actual==expected and all(not p.is_symlink() for p in OUT.rglob('*')),'complete ordinary publication membership')
rows={name:file(OUT/name)[0] for name in sorted(actual)}
require(sum(row['bytes'] for row in rows.values())<=1024*1024,'complete publication below1MiB')
for name,row in rows.items():require(file(OUT/name)[0]==row,'final copied identity/byte readback')
report=dict(status='verified-exact-frozen-link-controls-publication',publication=str(OUT),files=rows,
 file_count=len(rows),bytes=sum(r['bytes'] for r in rows.values()),originals_unchanged=True,
 complete_membership=True,all_source_and_copy_hashes_read_to_EOF=True,tests=24,test_reexecution=False,
 publication_sha256=rows['publication.json']['sha256'],independent_readback_sha256='78e01fa9c04b70dc8325039be2c930e37adf9ba25914034d5c98b47b6ea54d6f',git_operations=False)
put(READBACK,encoded(report))
print(json.dumps(dict(publication=str(OUT),files=len(rows),bytes=report['bytes'],publication_sha256=report['publication_sha256'],readback=str(READBACK),readback_sha256=file(READBACK)[0]['sha256'])))
