"""Independent bounded raw/source readback; no target imports or rerun."""
import ast
import hashlib
import json
from pathlib import Path
import re
import stat
ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
OUT=ROOT/'results/runtime10-tail-regressions-01'
INVENTORY=ROOT/'.work/runtime10-saved-audit-source-inventory-01.json'
REPORT=O/'.work/runtime10-tail-regressions-independent-readback-01.json'
FIELDS=('dev','ino','mode','size','mtime_ns','ctime_ns','nlink')
def row(p):
    p=Path(p);a=p.lstat();data=p.read_bytes();b=p.lstat()
    stamp=lambda s:{k:getattr(s,'st_'+k) for k in FIELDS}
    assert stat.S_ISREG(a.st_mode) and stamp(a)==stamp(b) and len(data)==a.st_size
    return dict(size=len(data),sha256=hashlib.sha256(data).hexdigest(),identity=stamp(a))
def read(p):return json.loads(Path(p).read_bytes())
assert not REPORT.exists()
assert row(INVENTORY)['sha256']=='23e1317e0ce5cd61e1dbfc57faebf6fd57b8c7452321dee5e10e61528091d39f'
assert {p.name for p in OUT.iterdir()}=={'source.py','sources-before.json','sources-after.json','record.json','stdout','stderr','result.json','tmp'}
assert not list((OUT/'tmp').iterdir())
record=read(OUT/'record.json');result=read(OUT/'result.json');before=read(OUT/'sources-before.json');after=read(OUT/'sources-after.json');inventory=read(INVENTORY)
assert before==after and len(before)==24 and set(before)==set(inventory['sources'])
for name,value in before.items():assert row(name)==value and value['sha256']==inventory['sources'][name]
assert row(OUT/'source.py')['sha256']==row(O/'.work/run_runtime10_tail_regressions_01.py')['sha256']=='bb780b6e04177dcde3d17a77ce92e813f2417385ecb13ae4a49502c3d7f83a5c'
assert record['status']=='closed' and record['returncode']==0 and record['may_be_live'] is False and record['observation_errors']==[]
assert record['parent_pid']==81699 and record['pid']==82415
assert record['started_at']<=record['spawned_at']<=record['finished_at'] and record['finished_at']-record['spawned_at']<=60
assert record['signals']==[] and record['retries']==record['compiler_calls']==record['provider_calls']==0
assert record['command'][1:]==['-B','-m','unittest','-v','test_completed_directories','test_tail']
assert record['cwd']==str(ROOT/'experiments/hir-options-hash-runtime-audit-10')
assert record['limits']==dict(child_cpu_seconds=30,child_wall_seconds=60,child_file_bytes=1024*1024,owned_temporary_bytes=8*1024*1024,owned_temporary_entries=128)
for name in ['stdout','stderr']:assert row(OUT/name)==record[name]
assert (OUT/'stdout').read_bytes()==b''
names=[]
for module in ['test_completed_directories','test_tail']:
    for cls in ast.parse((Path(record['cwd'])/(module+'.py')).read_bytes()).body:
        if isinstance(cls,ast.ClassDef):
            names.extend(module+'.'+cls.name+'.'+m.name for m in cls.body if isinstance(m,ast.FunctionDef) and m.name.startswith('test_'))
names=sorted(names);raw=(OUT/'stderr').read_text();actual=re.findall(r'^test_\w+ \(((?:test_completed_directories|test_tail)\.[^)]+)\) \.\.\. ok$',raw,re.M)
assert len(actual)==len(set(actual))==20 and sorted(actual)==names==record['tests']==result['test_names']
assert re.search(r'\nRan 20 tests in [0-9.]+s\n\nOK\n\Z',raw)
assert result['status']=='passed' and result['tests']==20 and result['sources_unchanged'] is True and result['production_qualification'] is False
assert result['record']==row(OUT/'record.json') and row(OUT/'result.json')['sha256']=='cd2ea42e35d5eb288d5ef20c38847a2a91eb67455528f5987f7f5561783e194a'
report=dict(status='verified',tests=20,parent_pid=81699,child_pid=82415,closed_returncode=0,source_inventory=dict(path=str(INVENTORY),sha256=row(INVENTORY)['sha256']),sources_unchanged=True,exact_raw_names=names,files={str(p):row(p) for p in sorted(OUT.iterdir()) if p.is_file()},verifier=dict(path=__file__,sha256=row(__file__)['sha256']),production_qualification=False,target_imports=False,reruns=0)
REPORT.write_text(json.dumps(report,sort_keys=True,separators=(',',':'))+'\n')
print(json.dumps(dict(report=str(REPORT),sha256=row(REPORT)['sha256'],result_sha256=row(OUT/'result.json')['sha256'],record_sha256=row(OUT/'record.json')['sha256'])))
