"""Independent saved-byte readback; never imports/runs the helper or test child."""
from pathlib import Path
import ast
import hashlib
import json
import math
import os
import re
import stat
import time

ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
H=ROOT/'experiments/runtime-frozen-link-controls-01'
S=ROOT/'experiments/runtime-frozen-link-reader-01'
E=ROOT/'results/runtime-frozen-link-controls-01'
OUTPUT=X/'.work/runtime-frozen-link-controls-independent-readback-01.json'
EXPECTED_RESULT='cfb7577f2345147a9c5f4d44b7c562d7e92e61bdcc91e7b95fbba48c8ac22497'
FIELDS=('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')
checked={}


def require(value,message):
    if not value:raise RuntimeError(message)


def file(path):
    path=Path(path);before=path.lstat();identity={k:getattr(before,'st_'+k) for k in FIELDS}
    require(path.resolve(strict=True)==path and stat.S_ISREG(before.st_mode) and before.st_size<=64*2**20,'bounded ordinary exact file')
    descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(descriptor,'rb') as stream:
        require({k:getattr(os.fstat(stream.fileno()),'st_'+k) for k in FIELDS}==identity,'opened identity differs')
        raw=stream.read(64*2**20+1)
        require({k:getattr(os.fstat(stream.fileno()),'st_'+k) for k in FIELDS}==identity,'opened identity changed')
    require(len(raw)==before.st_size and {k:getattr(path.lstat(),'st_'+k) for k in FIELDS}==identity,'named file changed')
    row=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),identity=identity)
    require(str(path) not in checked or checked[str(path)]==row,'first source observation changed')
    checked.setdefault(str(path),row)
    return row,raw


def read(path):
    row,raw=file(path);require(len(raw)<=4*2**20,'bounded saved JSON')
    def unique(pairs):
        result={}
        for k,v in pairs:
            require(k not in result,'duplicate JSON field');result[k]=v
        return result
    return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda n:(_ for _ in ()).throw(ValueError(n)))


result=read(E/'result.json');require(file(E/'result.json')[0]['sha256']==EXPECTED_RESULT,'exact actual result')
require(result['status']=='verified-frozen-link-controls' and type(result['tests']) is int and result['tests']==24,'actual complete test status')
manifest=read(E/'manifest.json')
expected_files={'child.py','plan.json','record.json','result.json','run_once.py','source-after.json','source-before.json','started.json','stderr','stdout'}
require(set(manifest)==expected_files,'exact output manifest membership')
require({p.name for p in E.iterdir()}==expected_files|{'manifest.json','tmp'} and (E/'tmp').is_dir()
    and not (E/'tmp').is_symlink() and not list((E/'tmp').iterdir()),'complete ordinary closed membership and empty temporary root')
for name,row in manifest.items():require(file(E/name)[0]==row,'full closed raw/source manifest readback')
for key,name in [('record','record.json'),('source_before','source-before.json'),('source_after','source-after.json'),('stdout','stdout'),('stderr','stderr')]:
    require(result[key]==dict(path=str(E/name),sha256=file(E/name)[0]['sha256']),'actual result reference')
plan=read(H/'plan.json');record=read(E/'record.json');started=read(E/'started.json')
before=read(E/'source-before.json');after=read(E/'source-after.json')
require(result['plan']==dict(path=str(H/'plan.json'),sha256=file(H/'plan.json')[0]['sha256']) and record['plan_sha256']==result['plan']['sha256'],'plan association')
require(before==after==result['sources'] and result['source_unchanged'] is True,'complete original before/after source equality')
for name,row in before.items():require(file(name)[0]==row,'all source identities/hashes remain current')
for name,row in plan['sources'].items():require(before[name]==row,'actual sources agree with frozen source plan')
require(set(before)==set(plan['sources'])|{str(H/'plan.json'),str(H/'run_once.py'),plan['python_resolved']},'complete source/interpreter membership')
require(str(Path(plan['python']).resolve(strict=True))==plan['python_resolved'],'original interpreter route')
for name in ['child.py','plan.json','run_once.py']:
    require(file(H/name)[0]['sha256']==file(E/name)[0]['sha256'],'retained executed source bytes')
tree=ast.parse(file(S/'test_links.py')[1])
names=sorted('test_links.'+c.name+'.'+n.name for c in tree.body if isinstance(c,ast.ClassDef)
    for n in c.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_'))
require(len(names)==len(set(names))==24 and names==plan['test_names']==result['test_names'],'exact source-derived test IDs')
require(record['command']==plan['command'] and record['cwd']==plan['cwd']==str(S),'exact actual child invocation')
require(type(record['returncode']) is int and record['returncode']==0 and record['status']=='closed'
    and record['may_be_live'] is False and record['observation_errors']==[],'actual child closed successfully')
require(record['signals']==[] and type(record['retries']) is int and record['retries']==0
    and record['canonical_lock_access'] is False and record['compiler_calls']==0,'finite test scope')
for key,value in [('cpu_seconds',30),('observer_seconds',60),('file_bytes',256*1024),('namespace_bytes',8*2**20)]:
    require(type(record[key]) is int and record[key]==value,'exact small test bounds')
times=[record[k] for k in ['started_at','spawned_at','observation_finished_at','finished_at']]
require(all(type(v) in (int,float) and math.isfinite(v) for v in times) and times==sorted(times),'finite ordered actual times')
elapsed=record['finished_at']-record['spawned_at'];require(0<=elapsed<60,'actual complete execution stayed within observer bound')
for key in ['command','cwd','environment','parent_pid','parent_parent_pid','pid','started_at','spawned_at','plan_sha256']:
    require(started[key]==record[key],'started/closed process identity association')
require(started['status']=='running' and started['may_be_live'] is True,'original starting observation retained')
raw=file(E/'stdout')[1].decode();require(file(E/'stderr')[1]==b'','empty actual child stderr')
for name in ['stdout','stderr']:require(record[name]==file(E/name)[0],'closed raw identity/hash association')
lines=raw.splitlines();expected=[n.rsplit('.',1)[1]+' ('+n+') ... ok' for n in names]
require([s for s in lines if s.startswith('test_')]==expected,'all24 exact raw distinct passing names')
footer=[s for s in lines if s.startswith('FROZEN_LINK_CONTROL_RESULT ')];require(len(footer)==1,'single actual child footer')
proof=json.loads(footer[0].split(' ',1)[1]);require(proof==result['child_proof'],'exact saved child proof')
require(proof['test_names']==names and proof['tests']==24 and proof['errors']==proof['failures']==proof['skipped']==0 and proof['status']=='passed','complete actual suite')
require(proof['child_pid']==record['pid'] and proof['parent_pid']==record['parent_pid'] and proof['cwd']==record['cwd'],'actual parent/child identity')
require(proof['test_sources']==plan['test_sources'],'actual child source qualification')
policy=proof['io_policy'];require(policy['owned_tmp']==str(E/'tmp') and policy['temporary_members_after']==[]
    and type(policy['mutation_events']) is int and 0<policy['mutation_events']<1024
    and policy['provider_writes'] is False and policy['subprocess_calls'] is False
    and policy['network_calls'] is False and policy['signal_calls'] is False and policy['denied_events']==[],'owned temporary audit policy')
require(re.search(r'\nRan 24 tests in [0-9]+\.[0-9]+s\n\nOK\nFROZEN_LINK_CONTROL_RESULT ',raw) is not None,'exact suite closure text')
require(result['runtime_audit_qualified'] is False and result['provider_writes'] is False and result['network'] is False,'qualification scope stays helper-only')
for name,row in list(checked.items()):require(file(name)[0]==row,'final complete readback unchanged')
report=dict(status='verified-frozen-link-controls-readback',observed_at=time.time(),tests=24,test_names=names,
 result=dict(path=str(E/'result.json'),sha256=EXPECTED_RESULT),record=result['record'],plan=result['plan'],
 helper=dict(path=str(S/'links.py'),sha256=file(S/'links.py')[0]['sha256']),
 test_source=dict(path=str(S/'test_links.py'),sha256=file(S/'test_links.py')[0]['sha256']),
 actual_parent_pid=record['parent_pid'],actual_child_pid=record['pid'],actual_returncode=0,
 actual_spawn_to_close_seconds=elapsed,source_before_equals_after_equals_current=True,all_raw_names_exact=True,
 complete_closed_output_files=11,temporary_directory_empty=True,readback_files=len(checked),
 readback_bytes=sum(r['bytes'] for r in checked.values()),checked_files=checked,
 passed_environment=record['environment'],observed_child_environment=proof['observed_environment'],
 observer_source_note='Executed runner initializes its deadline just after first started-record publication; actual spawn-to-close was independently below60s. No executed source rewrite.',
 compiler_execution=False,test_reexecution=False,target_imports=False,runtime_audit_qualified=False)
require(not OUTPUT.exists(),'fresh independent report')
OUTPUT.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(report=str(OUTPUT),sha256=hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),files=len(checked),bytes=report['readback_bytes'],elapsed=elapsed)))
