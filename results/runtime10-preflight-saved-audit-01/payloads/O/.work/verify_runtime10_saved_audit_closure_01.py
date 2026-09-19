"""Read closed10 report/raw/source bindings; do not repeat provider auditing."""
from pathlib import Path
import hashlib,json,stat
ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
R=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
S=ROOT/'experiments/hir-options-hash-runtime-audit-10'
E=ROOT/'.work/runtime10-saved-audit-preflight-execution-01'
M=ROOT/'.work/runtime10-saved-audit-preflight-manifest-01/manifest.json'
REPORT=R/'.work/hir-options-hash-runtime-preflight-independent-verification-05.json'
FIELDS={'dev','ino','mode','size','mtime_ns','ctime_ns','nlink'}
def encoded(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode()
def row(p):
 p=Path(p);a=p.lstat();b=p.read_bytes();z=p.lstat();identity=lambda i:{k:getattr(i,'st_'+k) for k in FIELDS}
 assert stat.S_ISREG(a.st_mode) and identity(a)==identity(z) and len(b)==a.st_size
 return dict(size=len(b),sha256=hashlib.sha256(b).hexdigest(),identity=identity(a))
def read(p):return json.loads(Path(p).read_text())
def reference(p):return dict(path=str(p),sha256=row(p)['sha256'])
c=read(E/'record.json');a=read(REPORT);m=read(M);pins=c['actual_closure_pins'];iv=read(E/'source-inventory.json')
assert c['status']=='finished' and c['returncode']==0 and c['may_be_live'] is False and c['observation_errors']==[]
assert not any(k in c for k in ['execution_error','publication_error','initial_publication_error'])
assert c['mode']=='audit' and c['phase']==a['phase']=='preflight'
assert c['parent_pid']==a['parent_pid']==52034 and c['pid']==a['pid']==52747
assert c['started_at']<=c['admitted_at']<=c['child_started_at']<=a['started_at']<=a['finished_at']<=c['finished_at']<=c['canonical_released_at']
assert c['finished_at']-c['child_started_at']<=1250 and c['process_signals']==c['compiler_calls']==c['provider_probes']==0
assert a['status']=='verified' and a['actual_children']==2 and a['compiler_calls']==a['provider_probes']==0
assert a['full_current_input_rehash'] is True and a['first_preflight_has_no_circular_audit'] is True
assert all(a[k] is False for k in ['application_qualified','performance_measurement','exporter_qualified','std_mir_prepared'])
assert reference(REPORT)['sha256']==c['result_sha256'] and c['report']==str(REPORT)
assert a['source_manifest']==reference(M) and row(M)['sha256']==pins['manifest_sha256']=='5feeb4ccfd59aa0d848db39ef9d61ebc3f6adb016cf118ba2d533590676ba7c0'
assert a['saved_audit_source']==str(S) and a['source_rows']==m['files']
assert len(m['files'])==303 and sum(x['size'] for x in m['files'].values())==3729679
for name,saved in m['files'].items():assert row(name)==saved,name
for name,digest in iv['sources'].items():assert row(name)['sha256']==digest and m['files'][name]['sha256']==digest
assert len(iv['sources'])==24 and read(c['source_inventory']['path'])==iv and row(c['source_inventory']['path'])['sha256']==c['source_inventory']['sha256']=='23e1317e0ce5cd61e1dbfc57faebf6fd57b8c7452321dee5e10e61528091d39f'
for leaf,source,key in [('source.py',S/'bootstrap.py','source_sha256'),('execution.py',S/'execute.py','execution_source_sha256')]:assert row(E/leaf)['sha256']==row(source)['sha256']==c[key]
assert row(E/'owned_stage.py')['sha256']==c['owned_source_sha256']
for name in ['stdout','stderr']:assert row(E/name)['sha256']==c[name+'_sha256']
assert (E/'stderr').read_bytes()==b'' and read(E/'stdout')==dict(status='verified',path=str(REPORT),sha256=c['result_sha256'])
for key,report_key in [('launch',None),('inputs','inputs_sha256'),('snapshot_plan','snapshot_plan_sha256'),('receipt','receipt_sha256'),('result','result_sha256'),('outer','outer_sha256'),('launcher_record','launcher_record_sha256')]:
 ref=pins['phase'][key];assert row(ref['path'])['sha256']==ref['sha256']
 if report_key:assert a[report_key]==ref['sha256']
wire=read(pins['phase']['inputs']['path'])
assert a['frozen_links']['count']==len(wire['links'])==7447 and a['frozen_links_before_after_equal'] is True
assert a['frozen_links']['frozen_rows_sha256']==hashlib.sha256(encoded(wire['links'])).hexdigest()
completed=a['completed_evidence_directories'];decl=completed['declaration'];observed=completed['observed']
assert completed['before_after_equal'] is True and set(decl['directories'])==set(observed) and len(observed)==6
assert decl['owner']['role']=='failed-hash-driver-01' and decl['association']['completion']=='failed'
assert decl['membership_source']['sha256']=='4a3d78ece513e77a3d1f79723c26f0b30183111c626ecbadfb37e67227a3ed4e'
for name,children in decl['directories'].items():
 q=observed[name];assert q['children']==children and set(q['identity'])==FIELDS and stat.S_ISDIR(q['identity']['mode'])
assert a['failed_saved_audit']==dict(path=str(ROOT/'.work/runtime09-saved-audit-preflight-execution-01/record.json'),sha256='23786949ac2f542f28aefc95f1a8d03a0ba680322cbf8dd765530c8f57ee1b42')
assert a['prior_failed_completed_directory_audit']==dict(path=str(ROOT/'.work/runtime08-saved-audit-preflight-execution-01/record.json'),sha256='71c59ba889fa71da8ea326b1f04723a472db7e1f580b545a13071dcbee12975c')
assert a['prior_failed_saved_audit']==dict(path=str(ROOT/'.work/runtime06-saved-audit-preflight-execution-01/record.json'),sha256='4b7e57aa4a1aa0bf09a6725dd47056497cd7a5ef56b0f3a36f2a77fce60fdb2b')
assert {p.name for p in E.iterdir()}=={'source.py','execution.py','owned_stage.py','source-inventory.json','invocation.json','record.json','stdout','stderr'}
assert row(REPORT)['size']<=4*2**20 and c['maximum_manifest_rows']==320
preparation_root=Path(a['preparation']['path']).parent
sources=read(preparation_root/'source-rows.json')
assert a['preparation_source_table']==dict(files=497,logical_bytes=sum(x['size'] for x in sources.values()),table_sha256=hashlib.sha256(encoded(sources)).hexdigest(),complete_typed_equality=True)
invocation=a['preparation_invocation'];original=invocation['original'];retained=invocation['retained']
assert reference(original['path'])==original and retained==dict(path=str(preparation_root/'invocation.json'),**row(preparation_root/'invocation.json'))
assert encoded(read(original['path']))==encoded(read(retained['path'])) and invocation['complete_typed_equality'] is True and invocation['same_raw_bytes'] is False
outer=Path(pins['phase']['outer']['path']).parent;proof=a['outer_membership']
assert proof['membership']['files']==4 and proof['membership']['directories']==1
assert {p.name for p in outer.iterdir()}=={'plan.json','status.json','command.log','supervisor.log'}
for key,name in [('command_stream','command.log'),('supervisor_stream','supervisor.log')]:assert proof[key]==dict(path=str(outer/name),**row(outer/name))
assert proof['command_stream']['sha256']==read(outer/'status.json')['log_sha256']
assert proof['supervisor_stream']['size']==0 and proof['writer']==reference(R/'scripts/supervise_experiment.py')
assert a['frozen_links_controls']['tests']==24 and a['completed_evidence_directories']['before_after_equal'] is True
result=dict(status='verified-closed-audit10-report',report=reference(REPORT),execution=reference(E/'record.json'),parent_pid=52034,child_pid=52747,returncode=0,canonical_released_at=c['canonical_released_at'],manifest=reference(M),manifest_files=303,manifest_logical_bytes=3729679,source_inventory=c['source_inventory'],full_manifest_byte_identity_readback=True,source_files=24,source_hashes_unchanged=True,complete_raw_source_membership=True,original_frozen_links=7447,completed_directory_entries=6,directory_observations=completed,actual_source_probe_children=2,old_failures_retained=[a['prior_failed_saved_audit'],a['prior_failed_completed_directory_audit'],a['failed_saved_audit']],scope='Independent report/raw/source/manifest and actual phase metadata closure readback only. The authenticated saved auditor performed the full provider/snapshot verification; this reader does not rerun it. No compiler or provider probes.',reader=reference(Path(__file__)))
out=O/'.work/runtime10-saved-audit-closure-independent-readback-01.json';assert not out.exists();out.write_bytes(encoded(result));print(json.dumps(dict(path=str(out),sha256=row(out)['sha256'],report_sha256=c['result_sha256'],execution_sha256=row(E/'record.json')['sha256'])))
