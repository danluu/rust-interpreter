"""Read-only independent exact retention packet audit; no controller imports."""
from pathlib import Path
import ast,hashlib,json,os,shutil,stat,time
R=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913');H=R/'experiments/old-compiler-published-retirement-evidence-01';OLD=R/'experiments/old-compiler-published-retirement-01/plan-01'
OUT=R/'.work/e48-retention-packet-independent-review-01.json'
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def identity(p):return {k:getattr(Path(p).lstat(),'st_'+k) for k in ['dev','ino','mode','nlink','size','mtime_ns','ctime_ns']}
assert not OUT.exists();started=time.time()
assert sha(H/'inputs.json')=='824d1377e3b0cabf2f9beea39852aa98ef7c561caa8fffa92bd759dade3a0c95'
assert sha(H/'launch.json')=='290f6aab9cb41f4222eb174a3cb78d19f49ee10755916a4fb7fdf0ed3d29489b'
assert sha(H/'plan.json')=='7fda2c836ffb60440ab86c72e69924331761d2ccc0923251ac65d4e1dbe1a920'
f,p,l=[read(H/name) for name in ['inputs.json','plan.json','launch.json']]
assert len(f['files'])==165 and len(p['members'])==p['member_count']==164
assert p['logical_bytes']==sum(x['bytes'] for x in p['members'].values())==368657707
assert p['logical_bytes']<p['maximum_logical_bytes']==384*2**20 and p['archive_limit_bytes']==64*2**20
assert p['reservation_bytes']==128*2**20 and p['entry_free_bytes']==9*2**30+p['reservation_bytes'] and p['minimum_free_gib']==9
for name,row in f['files'].items():
 q=Path(name);before=identity(q);assert q.resolve(strict=True)==q and stat.S_ISREG(before['mode']) and before==row['identity'] and sha(q)==row['sha256'] and identity(q)==before,name
 if q.suffix=='.py':ast.parse(q.read_bytes(),filename=str(q))
for name,row in p['members'].items():
 assert name==row['source'].lstrip('/') and row['source'] in f['files']
 assert row['sha256']==f['files'][row['source']]['sha256'] and row['bytes']==f['files'][row['source']]['identity']['size']
live=[R/'.work/compilers',Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/.work/hir-options-hash-compiler-01')]
original=read(OLD/'inputs.json');selected={row['source'] for row in p['members'].values()}
kept={name for name in original['files'] if not any(Path(name).is_relative_to(root) for root in live)}
omitted=set(original['files'])-kept
assert kept<=selected and not any(any(Path(name).is_relative_to(root) for root in live) for name in selected)
assert len(omitted)==p['excluded_live_provider_files'] and sum(original['files'][name]['identity']['size'] for name in omitted)==p['excluded_live_provider_bytes']
for key in ['historical_source_substitutions','historical_freezes','receipt_checks']:assert key in p
for name,checks in p['receipt_checks'].items():
 row=read(name);assert all(row[k]==v for k,v in checks.items())
assert p['children']==0 and p['wait_seconds']==600 and p['canonical_lock']=='/Users/danluu/dev/rust-interp/.work/benchmark.lock'
assert l['command']==['/opt/homebrew/bin/python3','-B',str(R/'scripts/supervise_experiment.py'),'--run-id','old-compiler-published-retirement-evidence-supervisor-01','--','/opt/homebrew/bin/python3','-B',str(H/'archive.py'),'--inputs-sha256',sha(H/'inputs.json')]
assert l['cwd']==str(R) and l['environment']==p['environment']==read(OLD/'plan.json')['environment']
assert [v for i,v in enumerate(os.uname()) if i!=1]==p['platform_identity']
route=Path(p['executor']['path']);assert str(route.resolve(strict=True))==p['executor']['resolved'] and identity(route)==p['executor']['route_identity']
for path in [R/'.work/old-compiler-published-retirement-evidence-01',R/'results/old-compiler-published-retirement-01',R/'.work/experiments/old-compiler-published-retirement-evidence-supervisor-01']:
 assert not path.exists() and not path.is_symlink()
assert sha(H/'archive.py')=='d6f4f4a9025466a313ad1f59d9f6ab58d381eef12d35e51554874d4d089e3eb0'
assert sha(H/'prepare.py')=='8c54a8c2888c1a05e4559d2c9a988f7e668e5e0027097ac2518fb3fde935598b'
free=shutil.disk_usage(R).free;assert free>=p['entry_free_bytes']
record=dict(status='verified-exact-packet',started_at=started,finished_at=time.time(),launch_sha256=sha(H/'launch.json'),inputs_sha256=sha(H/'inputs.json'),plan_sha256=sha(H/'plan.json'),
 input_files=len(f['files']),input_bytes=sum(row['identity']['size'] for row in f['files'].values()),members=len(p['members']),logical_bytes=p['logical_bytes'],
 all_current_hashes_and_stamps=True,original_nonprovider_union_complete=True,nonprovider_original_inputs=len(kept),excluded_live_provider_files=len(omitted),
 archive_source_sha256=sha(H/'archive.py'),preparer_source_sha256=sha(H/'prepare.py'),reservation_bytes=p['reservation_bytes'],fresh_free_bytes=free,
 actual_workloads=0,actual_deletions=0,verifier_sha256=sha(Path(__file__)),scope='Closed e48 evidence only; no live-provider copying or retired-controller import/guard. Parent authorized own exact source/packet review before one archive launch.')
with OUT.open('x') as f:json.dump(record,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps(record,indent=2));print(sha(OUT))
