"""Run the nine reviewed provider-directory regressions once; no runtime audit."""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import sys
import time

ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
SOURCE=ROOT/'experiments/hir-options-hash-runtime-audit-13'
OUT=ROOT/'results/runtime13-direct-regressions-01'
INVENTORY=ROOT/'.work/runtime13-saved-audit-source-inventory-01.json'
INVENTORY_SHA='2286f48fcb8e41c8f50138a592a1500f73095c8b9abaa67aed5c47a2abbe1cbd'
PYTHON=Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
FIELDS=('dev','ino','mode','size','mtime_ns','ctime_ns','nlink')

def require(ok,message):
    if not ok:raise RuntimeError(message)

def row(p):
    p=Path(p);before=p.lstat();data=p.read_bytes();after=p.lstat()
    identity=lambda s:{k:getattr(s,'st_'+k) for k in FIELDS}
    require(identity(before)==identity(after) and before.st_size==len(data),'source changed while read')
    return dict(size=len(data),sha256=hashlib.sha256(data).hexdigest(),identity=identity(before))

def save(name,value):
    p=OUT/name;data=(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
    require(len(data)<=1024*1024,'bounded record')
    tmp=OUT/(name+'.next')
    with tmp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(tmp,p)
    require(p.read_bytes()==data,'record publication differs')

def limits():
    resource.setrlimit(resource.RLIMIT_CPU,(30,30))
    resource.setrlimit(resource.RLIMIT_FSIZE,(1024*1024,1024*1024))

require(Path.cwd()==ROOT and sys.dont_write_bytecode and not sys.flags.optimize
    and Path(sys.executable).resolve()==PYTHON,'exact Python/cwd')
require(not os.path.lexists(OUT),'fresh regression namespace')
require(shutil.disk_usage(ROOT).free>=256*1024*1024,'small temp-fixture entry bound')
require(row(INVENTORY)['sha256']==INVENTORY_SHA,'reviewed source inventory changed')
inventory=json.loads(INVENTORY.read_text());require(len(inventory['sources'])==30,'exact30 reviewed audit sources')
expected=dict(inventory['sources'])
before={n:row(n) for n in expected}
require(all(before[n]['sha256']==d for n,d in expected.items()),'reviewed source bytes changed')
for path in [INVENTORY,PYTHON,Path(__file__).resolve()]:before[str(path)]=row(path)
require(len(before)==33 and sum(r['size'] for r in before.values())<=2*1024*1024,'complete bounded regression source table')
names=[]
for module in ['test_tail']:
    tree=ast.parse((SOURCE/(module+'.py')).read_text())
    names.extend(module+'.'+c.name+'.'+f.name for c in tree.body if isinstance(c,ast.ClassDef) and c.name=='ProviderDirectoryTests'
        for f in c.body if isinstance(f,ast.FunctionDef) and f.name.startswith('test_'))
names=sorted(names);require(len(names)==len(set(names))==9,'nine reviewed provider-directory regressions')
OUT.mkdir(mode=0o700);(OUT/'tmp').mkdir(mode=0o700)
(OUT/'source.py').write_bytes(Path(__file__).read_bytes())
resource.setrlimit(resource.RLIMIT_CPU,(60,60));resource.setrlimit(resource.RLIMIT_FSIZE,(1024*1024,1024*1024))
save('sources-before.json',before)
env=dict(PATH='/usr/bin:/bin:/opt/homebrew/bin',LANG='C',LC_ALL='C',TMPDIR=str(OUT/'tmp'),
    PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
argv=[str(PYTHON),'-B','-m','unittest','-v','test_tail.ProviderDirectoryTests']
record=dict(status='prepared',parent_pid=os.getpid(),parent_parent_pid=os.getppid(),started_at=time.time(),
    command=argv,cwd=str(SOURCE),passed_environment=env,tests=names,may_be_live=False,
    limits=dict(child_cpu_seconds=30,child_wall_seconds=60,child_file_bytes=1024*1024,
                owned_temporary_bytes=8*1024*1024,owned_temporary_entries=128,source_files=33,source_bytes=2*1024*1024),
    observation_errors=[],signals=[],retries=0,compiler_calls=0,provider_calls=0)
save('record.json',record)
def note(stage,error):record['observation_errors'].append(dict(stage=stage,error=repr(error),time=time.time()))
def observed_save(stage):
    try:save('record.json',record)
    except BaseException as error:note(stage,error)
with (OUT/'stdout').open('xb') as stdout,(OUT/'stderr').open('xb') as stderr:
    child=subprocess.Popen(argv,cwd=SOURCE,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,preexec_fn=limits)
    deadline=time.monotonic()+60
    record.update(status='running',pid=child.pid,spawned_at=time.time(),may_be_live=True)
    observed_save('spawn')
    while True:
        remaining=deadline-time.monotonic()
        if remaining<=0:
            record.update(status='unclosed',may_be_live=True,observed_at=time.time());observed_save('deadline')
            raise RuntimeError('owned regression child exceeded deadline; no signal or retry')
        try:
            rc=child.wait(timeout=min(1,remaining));break
        except subprocess.TimeoutExpired:
            try:
                paths=list((OUT/'tmp').rglob('*'));require(len(paths)<=128,'bounded owned temp entries')
                require(sum(p.lstat().st_size for p in paths)<=8*1024*1024,'bounded owned temp bytes')
            except BaseException as error:note('temporary-observation',error)
            observed_save('wait')
    record.update(status='closed',returncode=rc,finished_at=time.time(),may_be_live=False)
    observed_save('closed')
for name in ['stdout','stderr']:
    try:record[name]=row(OUT/name)
    except BaseException as error:note('hash-'+name,error)
observed_save('raw-readback')
require(rc==0 and not record['observation_errors'],'regressions failed or observations incomplete')
raw=(OUT/'stderr').read_text();require((OUT/'stdout').read_bytes()==b'','unexpected stdout')
actual=re.findall(r'^test_\w+ \((test_tail\.[^)]+)\) \.\.\. ok$',raw,re.M)
require(sorted(actual)==names and len(actual)==9 and re.search(r'\nRan 9 tests in [0-9.]+s\n\nOK\n\Z',raw),
    'exact actual nine successful unittest names and summary')
require(not list((OUT/'tmp').iterdir()),'temporary fixtures not cleaned')
after={n:row(n) for n in before};save('sources-after.json',after)
require(after==before and row(INVENTORY)['sha256']==INVENTORY_SHA,'reviewed sources changed')
result=dict(status='passed',tests=9,test_names=names,record=row(OUT/'record.json'),
    source_inventory=dict(path=str(INVENTORY),sha256=INVENTORY_SHA),sources_unchanged=True,
    regression_source_files=len(before),regression_source_bytes=sum(r['size'] for r in before.values()),
    temporary_empty=True,compiler_calls=0,provider_calls=0,production_qualification=False)
save('result.json',result)
print(json.dumps(dict(status='passed',parent_pid=os.getpid(),child_pid=child.pid,result_sha256=row(OUT/'result.json')['sha256'])))
