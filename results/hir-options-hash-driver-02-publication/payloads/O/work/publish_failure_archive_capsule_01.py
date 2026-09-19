"""Exact approved ordinary copies only; preserves all sources and Git state."""
import hashlib,json,os,stat,time
from pathlib import Path
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
PROPOSAL=O/'.work/hash-driver-failure-retention-publication-proposal-01.json'
EXPECTED='b7e74f4a62b3035dd9cac21ae8b22082b0b0b9a7c3e3ae7c59e982691dea737b'
DEST=ROOT/'results/hir-options-hash-driver-failure-01-publication'
REPORT=O/'.work/hash-driver-failure-retention-publication-verification-01.json'
def require(ok,message):
 if not ok:raise RuntimeError(message)
def identity(path):
 s=path.lstat();return {k:getattr(s,'st_'+k) for k in ['dev','ino','mode','nlink','size','mtime_ns','ctime_ns']}
def digest(data):return hashlib.sha256(data).hexdigest()
def current(row):
 path=Path(row['source']);require(path.resolve(strict=True)==path and identity(path)==row['identity'] and stat.S_ISREG(row['identity']['mode']),'ordinary unchanged source')
 raw=path.read_bytes();require(len(raw)==row['size'] and digest(raw)==row['sha256'] and identity(path)==row['identity'],'complete stable source bytes');return raw
raw=PROPOSAL.read_bytes();require(digest(raw)==EXPECTED,'reviewed exact publication proposal');p=json.loads(raw)
require(p['destination']==str(DEST) and p['status']=='proposed-unpublished' and not DEST.exists() and not DEST.is_symlink() and not REPORT.exists() and not REPORT.is_symlink(),'fresh exact publication')
require(p['file_count']==len(p['files'])==68 and p['source_bytes']==sum(r['size'] for r in p['files'])==1900915,'exact publication scope')
require(p['maximum_files']==128 and p['maximum_source_bytes']==4*2**20 and p['maximum_file_bytes']==2*2**20 and p['maximum_publication_bytes']==6*2**20,'reviewed finite publication bounds')
require(DEST.parent.resolve(strict=True)==DEST.parent and DEST.parent.is_dir(),'ordinary results parent')
paths=set()
for row in p['files']:
 rel=Path(row['destination']);require(not rel.is_absolute() and '..' not in rel.parts and str(rel)==row['destination'] and rel.parts[0]=='payloads' and str(rel) not in paths,'exact unique payload route')
 paths.add(str(rel));current(row)
require(set(p['required_evidence'])<=set(r['source'] for r in p['files']) and len(p['required_evidence'])==6,'complete selected closure evidence')
protected=Path(p['protected_result_directory'])
require(protected==ROOT/'results/hir-options-hash-driver-failure-01' and p['protected_result_files']==len(p['protected_results'])==5,'exact protected original archive directory')
def protect_original_archive():
 require(protected.resolve(strict=True)==protected and protected.is_dir(),'ordinary protected archive directory')
 require({str(q) for q in protected.iterdir()}=={r['source'] for r in p['protected_results']},'exact five original archive files')
 for row in p['protected_results']:current(row)
protect_original_archive()
DEST.mkdir(mode=0o700);outputs=[]
def write(relative,data):
 target=DEST/relative;target.parent.mkdir(parents=True,exist_ok=True);require(target.parent.resolve(strict=True)==target.parent,'ordinary publication parent')
 with target.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
 require(target.read_bytes()==data,'full publication readback');outputs.append(dict(path=str(target),relative=relative,size=len(data),sha256=digest(data)))
for row in p['files']:
 write(row['destination'],current(row));current(row)
encode=lambda value:(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
write('README.md',p['readme'].encode());write('STATUS.md',p['status_document'].encode());write('summary.json',encode(p['summary']));write('publication-proposal.json',raw)
manifest=dict(status='retained-exact-evidence-copies',proposal_sha256=EXPECTED,source_files=p['files'],payload_count=len(p['files']),source_bytes=p['source_bytes'],scope=p['summary']['scope'],generated_files=p['generated_files'],protected_original_archive=p['protected_results'],originals_preserved=True,git_mutations=False)
write('manifest.json',encode(manifest))
require(len(outputs)==73 and sum(r['size'] for r in outputs)<=p['maximum_publication_bytes'],'finite complete publication')
for row in p['files']:current(row)
protect_original_archive()
observed={str(q) for q in DEST.rglob('*') if q.is_file()};require(observed=={r['path'] for r in outputs},'exact final file set')
for row in outputs:
 path=Path(row['path']);require(not path.is_symlink() and path.resolve(strict=True)==path and path.stat().st_size==row['size'] and digest(path.read_bytes())==row['sha256'],'final complete output bytes')
for directory in [DEST.parent,DEST,*sorted((q for q in DEST.rglob('*') if q.is_dir()),reverse=True)]:
 fd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:os.fsync(fd)
 finally:os.close(fd)
report=dict(status='verified-published-copies',finished_at=time.time(),proposal=dict(path=str(PROPOSAL),sha256=EXPECTED),destination=str(DEST),files=outputs,file_count=len(outputs),total_bytes=sum(r['size'] for r in outputs),source_file_count=68,source_bytes=1900915,all_selected_closure_evidence_retained=True,protected_original_archive=p['protected_results'],all5_original_archive_files_byte_and_identity_unchanged=True,source_identities_and_bytes_unchanged=True,full_output_readback=True,git_mutations=False)
with REPORT.open('x') as stream:json.dump(report,stream,sort_keys=True,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
print(json.dumps(dict(report=str(REPORT),sha256=digest(REPORT.read_bytes()),files=len(outputs),total_bytes=report['total_bytes'],manifest_sha256=digest((DEST/'manifest.json').read_bytes()))))
