"""Copy the exact bounded saved-evidence selection; never execute target sources."""
from pathlib import Path
import hashlib
import json
import os
import resource
import stat
import time

HOME_TASK = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918/.work')
SCOPE = HOME_TASK/'proc-macro-arena-compiler-publication-scope-01.json'
SCOPE_SHA = 'cba43a92ea8058324005b128dfcefbbee6cbeb52c0ec6ad402b589cdc08e3e54'
REPORT = HOME_TASK/'proc-macro-arena-compiler-publication-readback-01.json'
START = time.monotonic()
resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
resource.setrlimit(resource.RLIMIT_FSIZE, (4*2**20, 4*2**20))
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
FIELDS = ('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')

def identity(info):
    return {k:getattr(info,'st_'+k) for k in FIELDS}

def exact_bytes(path):
    assert time.monotonic()-START < 120
    path=Path(path); before=identity(path.lstat())
    assert path.resolve(strict=True)==path and stat.S_ISREG(before['mode']) and before['size']<=4*2**20
    with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW),'rb') as f:
        assert identity(os.fstat(f.fileno()))==before
        data=f.read(4*2**20+1)
        assert identity(os.fstat(f.fileno()))==before
    assert identity(path.lstat())==before and len(data)==before['size']
    return data,{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'identity':before}

def json_bytes(value):
    return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()

scope_bytes, scope_row=exact_bytes(SCOPE); assert scope_row['sha256']==SCOPE_SHA
scope=json.loads(scope_bytes); destination=Path(scope['destination'])
assert destination==Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-compiler-02-publication')
assert not destination.exists() and not REPORT.exists()
assert len(scope['files'])==172 and sum(x['bytes'] for x in scope['files'])==3530960
assert len(scope['files'])<=scope['max_files']==256 and sum(x['bytes'] for x in scope['files'])<=scope['max_payload_bytes']==8*2**20
assert len({r['source'] for r in scope['files']})==len(scope['files'])
assert len({r['destination'] for r in scope['files']})==len(scope['files'])

def check_originals():
    for row in scope['files']:
        _, actual=exact_bytes(row['source'])
        assert all(actual[k]==row[k] for k in ['bytes','sha256','identity'])
    for base, expected in scope['source_tree_membership'].items():
        actual=[]
        for p in sorted(Path(base).rglob('*')):
            assert not p.is_symlink()
            if not p.is_dir():actual.append(str(p.relative_to(base)))
        assert actual==expected

check_originals(); destination.mkdir()
outputs={}
def publish(name,data):
    rel=Path(name); assert not rel.is_absolute() and '..' not in rel.parts and name not in outputs
    target=destination/rel;target.parent.mkdir(parents=True,exist_ok=True)
    assert target.parent.resolve(strict=True)==target.parent
    with target.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    got,row=exact_bytes(target);assert got==data;outputs[name]=row

for row in scope['files']:
    data,current=exact_bytes(row['source']);assert current['sha256']==row['sha256'] and current['identity']==row['identity']
    publish(row['destination'],data)
publish('STATUS.md',scope['generated_status'].encode())
publish('publication-scope.json',scope_bytes)
publish('publish.py',exact_bytes(Path(__file__))[0])
publish('MANIFEST.json',json_bytes({'policy':scope['policy'],'scope_sha256':SCOPE_SHA,'payload_files':172,
    'payload_bytes':3530960,'payloads':scope['files'],'generated':{k:v for k,v in outputs.items() if k in ['STATUS.md','publication-scope.json','publish.py']}}))
check_originals()
for name, row in outputs.items():assert exact_bytes(destination/name)[1]==row
assert {str(p.relative_to(destination)) for p in destination.rglob('*') if p.is_file()}==set(outputs)
report={'status':'passed-full-copy-readback','created_at':time.time(),'destination':str(destination),
    'scope_sha256':SCOPE_SHA,'original_files_unchanged':172,'payload_bytes':3530960,
    'output_files_before_self_copy':len(outputs),'output_bytes_before_self_copy':sum(x['bytes'] for x in outputs.values()),
    'actual_result_sha256':scope['actual_result_sha256'],'independent_readback_sha256':scope['independent_readback_sha256'],
    'prior_failed_attempt_preserved':True,'compiler_calls':0,'provider_payload_copies':0,'files':outputs}
data=json_bytes(report)
with REPORT.open('xb') as f:f.write(data)
assert REPORT.read_bytes()==data
publish('READBACK.json',data)
assert len(outputs)==177 and sum(x['bytes'] for x in outputs.values())<scope['max_capsule_bytes']==16*2**20
assert {str(p.relative_to(destination)) for p in destination.rglob('*') if p.is_file()}==set(outputs)
print(json.dumps({'status':'passed','destination':str(destination),'files':len(outputs),
    'bytes':sum(x['bytes'] for x in outputs.values()),'report':str(REPORT),'report_sha256':hashlib.sha256(data).hexdigest()}))
