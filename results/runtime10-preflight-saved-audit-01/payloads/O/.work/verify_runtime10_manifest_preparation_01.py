"""Independent actual10 raw/source/manifest closure readback; no target imports."""
from pathlib import Path
import hashlib,json,stat
r=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913');o=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918');d=r/'.work/runtime10-saved-audit-preflight-manifest-01';e=r/'.work/runtime10-saved-audit-preflight-manifest-preparation-execution-01';s=r/'experiments/hir-options-hash-runtime-audit-10'
def row(p):
 p=Path(p);a=p.lstat();b=p.read_bytes();z=p.lstat();f=('dev','ino','mode','size','mtime_ns','ctime_ns','nlink');identity=lambda i:{k:getattr(i,'st_'+k) for k in f};assert stat.S_ISREG(a.st_mode) and identity(a)==identity(z) and len(b)==a.st_size
 return dict(size=len(b),sha256=hashlib.sha256(b).hexdigest(),identity=identity(a))
def read(p):return json.loads(Path(p).read_text())
m=read(d/'manifest.json');p=read(d/'preparation.json');c=read(e/'record.json');inv=read(r/'.work/runtime10-saved-audit-source-inventory-01.json')
assert c['status']=='finished' and c['returncode']==0 and c['may_be_live'] is False and c['observation_errors']==[] and c['mode']=='prepare' and c['phase']=='preflight'
assert not any(k in c for k in ['execution_error','publication_error','initial_publication_error'])
assert c['parent_pid']==28977 and c['pid']==30590 and c['started_at']<=c['admitted_at']<=c['child_started_at']<=p['finished_at']<=c['finished_at']<=c['canonical_released_at']
assert c['pid']==p['pid'] and c['parent_pid']==p['parent_pid']
assert c['manifest_sha256']==row(d/'manifest.json')['sha256']==p['manifest']['sha256']=='5feeb4ccfd59aa0d848db39ef9d61ebc3f6adb016cf118ba2d533590676ba7c0'
assert c['result_sha256']==row(d/'preparation.json')['sha256']=='63ba62423d6672d3e34de54b2f521cc1b94bb5c64217632923b3c4a74cb25f2e'
assert m['policy']=='runtime05-complete-preparation-saved-audit-source-manifest-v1' and len(m['files'])==p['files']==303
assert sum(x['size'] for x in m['files'].values())==p['logical_bytes']==3729679
for n,x in m['files'].items():assert row(n)==x,n
for n,sha in inv['sources'].items():assert m['files'][n]['sha256']==row(n)['sha256']==sha
assert read(e/'source-inventory.json')==inv
for leaf,source,key in [('source.py',s/'prepare_manifest.py','source_sha256'),('execution.py',s/'execute.py','execution_source_sha256')]:assert row(e/leaf)['sha256']==row(source)['sha256']==c[key]
assert row(e/'owned_stage.py')['sha256']==c['owned_source_sha256']
for n in ['stdout','stderr']:assert row(e/n)['sha256']==c[n+'_sha256']
assert (e/'stderr').read_bytes()==b''
out=read(e/'stdout');assert out==dict(status='prepared-audit-source-manifest',manifest=p['manifest'],preparation=dict(path=str(d/'preparation.json'),sha256=c['result_sha256']))
assert {x.name for x in e.iterdir()}=={'record.json','stdout','stderr','source.py','execution.py','owned_stage.py','invocation.json','source-inventory.json'}
assert {x.name for x in d.iterdir()}=={'manifest.json','preparation.json'}
census=read(o/'.work/runtime10-complete-prospective-manifest-census-01.json')
assert m['files']==census['files'] and census['file_count']==303
assert c['maximum_manifest_rows']==320 and c['maximum_manifest_payload_bytes']==8*2**20
assert c['capacity']==dict(entry_gib=16,live_gib=9,floor_gib=8) and c['wait_seconds']==600
assert c['maximum_child_cpu_seconds']==900 and c['maximum_child_read_seconds']==1200 and c['maximum_observation_seconds']==1250
assert c['compiler_calls']==c['provider_probes']==c['process_signals']==c['network_calls']==0
assert row(e/'record.json')['sha256']=='42ba348cc43d88d90a1b28b0d17bbd8dd128384329c5286be10ca70423101e97'
# Compare complete preparation497 metadata against original runtime table plus supplement.
wire=read(r/'experiments/runtime-preflight-retry-05/preflight-plan-01/inputs.json')
assert row(r/'experiments/runtime-preflight-retry-05/preflight-plan-01/inputs.json')['sha256']=='d0615f2b4cf9945318b8f8cd15afaec494479306e452ca34cfed7e584d4248a8'
assert row(wire['file_table_base']['path'])['sha256']==wire['file_table_base']['sha256']
base=read(wire['file_table_base']['path']);full=dict(base['files'],**wire['files'])
canonical=lambda value:(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
assert wire['file_table_integrity']==dict(count=len(full),total_bytes=sum(x['size']for x in full.values()),sha256=hashlib.sha256(canonical(full)).hexdigest())
for n,x in m['files'].items():
 if n in full:assert canonical(x)==canonical(full[n])
combined=dict(full,**m['files'])
source_rows=read(Path(m['preparation']['path']).parent/'source-rows.json');assert len(source_rows)==497
assert all(n in combined and canonical(x)==canonical(combined[n]) for n,x in source_rows.items())
report=dict(status='verified-actual-audit10-manifest-preparation',manifest=dict(path=str(d/'manifest.json'),sha256=c['manifest_sha256']),preparation=dict(path=str(d/'preparation.json'),sha256=c['result_sha256']),execution=dict(path=str(e/'record.json'),sha256=row(e/'record.json')['sha256']),parent_pid=c['parent_pid'],child_pid=c['pid'],returncode=0,canonical_released_at=c['canonical_released_at'],manifest_rows=303,logical_bytes=3729679,full_manifest_byte_identity_readback=True,prospective_census_exact=True,complete_preparation_source_rows=497,source_inventory=p['source_inventory'],sources_unchanged=True,complete_raw_source_membership=True,compiler_calls=0,provider_calls=0,reader=dict(path=str(Path(__file__)),sha256=row(Path(__file__))['sha256']),command_error_retained=dict(path=str(o/'.work/runtime10-manifest-invocation-command-error-01.json'),sha256='dfc8ee741c8558261b6ff08f581303de4d76c0b00e1e63a53b5b18f5844b22b5'))
f=o/'.work/runtime10-manifest-preparation-independent-readback-01.json';assert not f.exists();f.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(json.dumps({'path':str(f),'sha256':row(f)['sha256'],'execution_sha256':report['execution']['sha256'],'canonical_released_at':c['canonical_released_at']}))
