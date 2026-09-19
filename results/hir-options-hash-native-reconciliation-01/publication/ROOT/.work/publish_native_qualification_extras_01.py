"""Copy bounded closed publication metadata; no archive or provider execution."""
from pathlib import Path
import hashlib,json,os,stat
ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
RESULT=ROOT/'results/hir-options-hash-native-reconciliation-01'
DEST=RESULT/'publication'

def stamp(path):
 s=path.lstat();return [s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink]

def main():
 assert not DEST.exists()
 chosen={}
 for folder in ['native-qualification-publication-preparation-01','native-qualification-publication-launch-execution-01','native-qualification-publication-verification-execution-01','native-qualification-publication-01','experiments/native-qualification-publication-supervisor-01']:
  for p in (ROOT/'.work'/folder).rglob('*'):
   assert not p.is_symlink()
   if p.is_file():chosen[str(p)]=p
 for pattern in ['launch_native_qualification_publication_01*','verify_native_qualification_publication_01*']:
  for p in (ROOT/'.work').glob(pattern):assert p.is_file() and not p.is_symlink();chosen[str(p)]=p
 for p in [ROOT/'.work/prepare_native_qualification_publication_01.py',ROOT/'.work/audit_native_qualification_publication_01.py',ROOT/'.work/native-qualification-publication-independent-verification-01.json',ROOT/'.work/root-native-publication-packet-review-01.json',X/'.work/native-qualification-publication-source-review-01.json',Path(__file__).resolve(),ROOT/'.work/native-qualification-publication-extras-planning-failure-01.json']:
  assert p.is_file() and not p.is_symlink();chosen[str(p)]=p
 assert len(chosen)<=64 and sum(p.stat().st_size for p in chosen.values())<=8*2**20
 plan={}
 for name,p in sorted(chosen.items()):
  before=stamp(p);assert p.resolve()==p and stat.S_ISREG(before[2]) and before[3]<=2*2**20
  data=p.read_bytes();assert stamp(p)==before
  rel=Path('ROOT' if p.is_relative_to(ROOT) else 'X')/p.relative_to(ROOT if p.is_relative_to(ROOT) else X)
  target=DEST/rel
  plan[name]={'destination':str(target),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'stamp':before}
 planpath=ROOT/'.work/native-qualification-publication-extras-plan-01.json';assert not planpath.exists()
 with planpath.open('x') as stream:
  json.dump({'status':'exact-copy-plan','files':plan,'count':len(plan),'bytes':sum(r['bytes'] for r in plan.values()),'maximum_files':64,'maximum_file_bytes':2*2**20,'maximum_total_bytes':8*2**20},stream,sort_keys=True,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
 DEST.mkdir()
 for name,row in plan.items():
  p=Path(name);assert stamp(p)==row['stamp']
  data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==row['sha256'] and len(data)==row['bytes'] and stamp(p)==row['stamp']
  target=Path(row['destination']);target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
  assert target.read_bytes()==data and target.stat().st_nlink==1 and [target.stat().st_dev,target.stat().st_ino]!=row['stamp'][:2]
 manifest={'status':'verified-exact-publication-copies','files':plan,'count':len(plan),'bytes':sum(r['bytes'] for r in plan.values()),'original_paths_unchanged':True,'archive_audit_precedes_publication_metadata':True}
 mp=RESULT/'publication-manifest.json'
 with mp.open('x') as stream:json.dump(manifest,stream,sort_keys=True,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
 assert set(str(p) for p in DEST.rglob('*') if p.is_file())=={r['destination'] for r in plan.values()}
 print(json.dumps({'files':len(plan),'bytes':manifest['bytes'],'manifest_sha256':hashlib.sha256(mp.read_bytes()).hexdigest(),'plan_sha256':hashlib.sha256(planpath.read_bytes()).hexdigest()}))

if __name__=='__main__':main()
