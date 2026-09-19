"""Bounded independent saved preparation readback; build an unexecuted audit argv."""
import hashlib
import json
import os
from pathlib import Path
import resource
import shlex
import stat
import time

ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
R=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
H=ROOT/'experiments/hir-options-hash-runtime-audit-13'
S=ROOT/'experiments/runtime-installation-after-preflight05-03'
M=ROOT/'.work/runtime13-saved-audit-installation-manifest-01'
E=ROOT/'.work/runtime13-saved-audit-installation-manifest-preparation-execution-01'
INV=ROOT/'.work/runtime13-saved-audit-source-inventory-01.json'
CENSUS=O/'.work/runtime13-prospective-supplemental-census-01.json'
FIELDS=('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')
OBSERVED={}


def identity(st):
    return {name:getattr(st,'st_'+name) for name in FIELDS}


def raw(path, expected=None):
    path=Path(path)
    assert path.is_absolute() and path.resolve(strict=True)==path
    before=identity(path.lstat())
    assert stat.S_ISREG(before['mode']) and before['size']<=10*2**20
    with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK),'rb') as f:
        assert identity(os.fstat(f.fileno()))==before
        data=f.read(10*2**20+1)
        assert identity(os.fstat(f.fileno()))==before
    assert identity(path.lstat())==before and len(data)==before['size']
    row=dict(identity=before,size=len(data),sha256=hashlib.sha256(data).hexdigest())
    assert expected is None or row['sha256']==expected
    assert str(path) not in OBSERVED or OBSERVED[str(path)]==row
    OBSERVED[str(path)]=row
    return data


def same(a,b):
    return json.dumps(a,sort_keys=True,separators=(',',':'),allow_nan=False)==json.dumps(b,sort_keys=True,separators=(',',':'),allow_nan=False)


def read(path, expected=None):
    def unique(pairs):
        value={}
        for key,item in pairs:
            assert key not in value
            value[key]=item
        return value
    return json.loads(raw(path,expected),object_pairs_hook=unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def ref(path):
    return dict(path=str(path),**OBSERVED[str(path)])


def main():
    resource.setrlimit(resource.RLIMIT_CPU,(60,60))
    resource.setrlimit(resource.RLIMIT_FSIZE,(4*2**20,4*2**20))
    started=time.time()
    execution=ROOT/'.work/runtime13-saved-audit-installation-execution-01'
    output=R/'.work/hir-options-hash-runtime-installation-independent-verification-07.json'
    rec=read(execution/'record.json','1f4d4a70657aa071fb85540f97b8ecbfeed3dcde85e340360b5065e7a3ed7d43')
    result=read(output,'878a1f363e6ca5e3acdcb16645c79d8412a260e8721a9fe75eacd7823a481728')
    before={p.name:identity(p.lstat()) for p in execution.iterdir()}
    assert set(before)=={'record.json','stdout','stderr','source.py','execution.py','owned_stage.py','source-inventory.json','invocation.json'}
    assert rec['status']=='finished' and type(rec['returncode']) is int and rec['returncode']==0
    assert rec['may_be_live'] is False and rec['observation_errors']==[]
    assert not any(k in rec for k in ['execution_error','publication_error','initial_publication_error'])
    assert rec['mode']=='audit' and rec['phase']=='installation' and rec['cwd']==str(R) and rec['report']==str(output)
    assert result['status']=='verified' and result['phase']=='installation'
    assert rec['pid']==result['pid']==88456 and rec['parent_pid']==result['parent_pid']==87740
    assert rec['started_at']<=rec['admitted_at']<=rec['child_started_at']<=result['started_at']<=result['finished_at']<=rec['finished_at']<=rec['canonical_released_at']<=time.time()
    assert rec['admitted_at']-rec['started_at']<=600 and rec['finished_at']-rec['child_started_at']<=1250
    assert rec['capacity']==dict(entry_gib=16,live_gib=9,floor_gib=8)
    assert rec['canonical_lock']=='/Users/danluu/dev/rust-interp/.work/benchmark.lock'
    assert rec['maximum_manifest_rows']==368 and rec['maximum_manifest_payload_bytes']==8*2**20
    for key in ['compiler_calls','provider_probes','process_signals','network_calls']:assert rec[key]==0
    for key in ['runtime_admission','retirement_authorized']:assert rec[key] is False
    assert raw(execution/'stderr',rec['stderr_sha256'])==b''
    assert read(execution/'stdout',rec['stdout_sha256'])==dict(status='verified',path=str(output),sha256=OBSERVED[str(output)]['sha256'])
    assert rec['result_sha256']==OBSERVED[str(output)]['sha256']
    manifest=read(M/'manifest.json','22b62cf3de500e0bd6d5ad4b6d465c3b803eda25889df8d3da3b7366593bb2e4')
    prep=read(M/'preparation.json','e23f5df3dd4f962b96b127d2bc9293befd0732fd9d67aebbd4d6bc6a4d65a495')
    prep_rec=read(E/'record.json','0b73ce43a4e9f2fab103ff9cf2e124380daa00a5a219103002de3847e6828bc2')
    assert prep_rec['canonical_released_at']<=rec['started_at']
    assert result['source_manifest']==dict(path=str(M/'manifest.json'),sha256=OBSERVED[str(M/'manifest.json')]['sha256'])
    assert same(result['source_rows'],manifest['files']) and len(result['source_rows'])==326
    assert sum(v['size'] for v in result['source_rows'].values())==7185333
    inventory=read(INV,'2286f48fcb8e41c8f50138a592a1500f73095c8b9abaa67aed5c47a2abbe1cbd')
    assert same(read(execution/'source-inventory.json'),inventory) and len(inventory['sources'])==30
    for name,digest in inventory['sources'].items():
        raw(name,digest);assert same(OBSERVED[name],manifest['files'][name]),name
    assert raw(execution/'source.py',rec['source_sha256'])==raw(H/'bootstrap.py')
    assert raw(execution/'execution.py',rec['execution_source_sha256'])==raw(H/'execute.py')
    raw(execution/'owned_stage.py','7021a15d3b806ab908f03276051d9d9ca9c9e208bbf8933a60229c9fb35bb68e')
    invocation=read(execution/'invocation.json')
    assert invocation['mode']=='audit' and invocation['phase']=='installation' and invocation['source_inventory']==str(INV)
    expected=read(O/'.work/runtime13-manifest-preparation-independent-readback-01.json','fb522ccb8a0f58872f8f4a0bf8ed895b7f8897cc11474bcf4b53470d09247f0a')
    assert rec['parent_argv']==expected['command'][2:]
    assert rec['actual_closure_pins']['manifest_sha256']==result['source_manifest']['sha256']
    assert rec['actual_closure_pins']['preparation_sha256']==OBSERVED[str(M/'preparation.json')]['sha256']
    assert rec['actual_closure_pins']['preparation_record_sha256']==OBSERVED[str(E/'record.json')]['sha256']
    phase={}
    for name,reference in rec['actual_closure_pins']['phase'].items():
        normalized=name.replace('_','-');assert reference['path']==expected['phase_dependencies'][normalized]['path']
        assert reference['sha256']==expected['phase_dependencies'][normalized]['sha256']
        phase[name]=read(reference['path'],reference['sha256'])
    terminal=phase['receipt'];outer=phase['outer'];launcher=phase['launcher_record'];runtime_result=phase['result']
    assert terminal['status']=='passed' and terminal['phase']=='installation' and len(terminal['children'])==15
    assert outer['status']=='finished' and outer['returncode']==0 and launcher['status']=='terminal-observed' and launcher['returncode']==launcher['launcher_returncode']==0
    assert terminal['pid']==outer['child_pid']==launcher['controller_pid']==83231
    assert terminal['parent_pid']==outer['supervisor_pid']==launcher['supervisor_pid']==83187
    assert terminal['finished_at']<=outer['finished_at']<=launcher['terminal_observed_at']<=rec['started_at']
    for key in ['inputs','receipt','result','outer','snapshot_plan']:
        assert result[key+'_sha256']==rec['actual_closure_pins']['phase'][key]['sha256']
    assert result['launcher_record_sha256']==rec['actual_closure_pins']['phase']['launcher_record']['sha256']
    child_rows=[]
    for index,reference in enumerate(terminal['children']):
        childpath=Path(reference['path']);child=read(childpath,reference['sha256'])
        assert child['pid']==reference['pid']==result['process_identities'][index]['pid']
        assert child['returncode']==reference['returncode'] and child['returncode'] in child['expected']
        assert child['started_at']<=child['finished_at']<=terminal['finished_at']
        for stream in ['stdout','stderr']:raw(childpath.parent/stream,child[stream+'_sha256'])
        if index<10:
            assert child['command'][:4]==['/usr/bin/otool','-arch','arm64','-l'] and child['returncode']==0
        child_rows.append(dict(index=index,pid=child['pid'],returncode=child['returncode'],receipt=ref(childpath)))
    assert [c['returncode'] for c in child_rows].count(0)==13 and [c['returncode'] for c in child_rows].count(1)==2
    assert result['actual_children']==result['phase_result']['direct_children']==15
    assert result['saved_audit_source']==str(H) and result['full_current_input_rehash'] is True
    assert result['original_prepared_files']==113547 and result['preparation_source_table']['files']==519
    assert result['preparation_source_table']['complete_typed_equality'] is True
    assert result['frozen_links_before_after_equal'] is True and result['frozen_links']['count']==7447
    assert result['completed_evidence_directories']['before_after_equal'] is True
    for key in ['application_qualified','exporter_qualified','std_mir_prepared','performance_measurement']:
        assert result[key] is result['phase_result'][key] is False
    assert result['compiler_calls']==result['provider_probes']==0 and result['phase_result']['native_reexecution'] is False
    for key,count in [('actual53',53),('phase45',45),('startup39',39),('retry_controls',33),('installation_controls',25),('native_loader_controls',48)]:
        control=result[key];assert control['controls']==count
        retained=next(c for c in prep['controls'] if c.get('controls')==count)
        assert all(same(v,retained[k]) for k,v in control.items())
    assert result['frozen_links_controls']['tests']==24
    scope=result['provider_directory_scope']
    admission=read(scope['admission']['path'],scope['admission']['sha256'])
    ready=read(scope['readiness']['path'],scope['readiness']['sha256'])
    routes=read(S/'routes.json','d339e74a11edb948f3cf4bcc0afbbba76887cc61aed125c8bb8bf62b1633723a')
    plan=read(Path(routes['packet'])/'plan.json',result['plan_sha256'])
    spec=read(plan['specification']['path'],plan['specification']['sha256'])
    assert same(admission['identity'],ready['identity']) and same(admission['identity']['admission'],spec)
    assert same(result['installation_resources'],plan['installation_resources']) and same(result['installation_resources'],terminal['installation_resources'])
    assert same(result['native_loader_policy'],spec['loader_probe'])
    encoded=lambda v:(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode()
    key=hashlib.sha256(encoded(admission['identity'])[:-1]).hexdigest()
    assert key==terminal['runtime_key']==runtime_result['key']==ready['key']==result['phase_result']['runtime_key']
    directories={};components=[]
    names=('dev','ino','mode','size','mtime_ns','ctime_ns','nlink')
    for component,snapshot in zip(spec['components'],admission['snapshots'],strict=True):
        root=Path(component['root']);required={str(root)}
        for name in [*component['files'],*component['links']]:
            required.update(str(q) for q in (root/name).parents if q==root or root in q.parents)
        own={str(root/name):dict(zip(names,values,strict=True)) for name,values in snapshot['directories'].items()}
        assert required<=set(own)
        for path,identity_row in own.items():
            assert all(type(v) is int for v in identity_row.values()) and stat.S_ISDIR(identity_row['mode'])
            assert path not in directories or directories[path]==identity_row
            directories[path]=identity_row
        components.append(dict(root=str(root),directories=len(own),required_ancestors=len(required),additional_declared_directories=len(set(own)-required)))
    assert components==scope['components'] and [c['directories'] for c in components]==[10,933,1]
    assert [c['required_ancestors'] for c in components]==[8,933,1] and len(directories)==scope['directories']==944
    assert hashlib.sha256(encoded(directories)).hexdigest()==scope['declaration_sha256']
    proof=result['phase_result'];assert proof['admission_sha256']==scope['admission']['sha256'] and proof['ready_sha256']==scope['readiness']['sha256']
    assert proof['qualification_sha256']==proof['result_sha256']==result['result_sha256']
    assert proof['ordinary_files_independently_hashed']==sum(len(s['files']) for s in admission['snapshots'])==3708
    assert proof['runtime_bytes_independently_hashed']==sum(v[3] for s in admission['snapshots'] for v in s['files'].values())==636631680
    assert proof['installed_directories']==1+sum(stat.S_ISDIR(row[2]) for row in ready['stamps'].values())==943
    for flag in ['exact_before_after_inventory','fresh_independent_inodes','immutable_modes_checked']:assert proof[flag] is True
    assert result['snapshots']['full_gzip_eof'] is result['snapshots']['full_logical_hashes'] is True
    assert {p.name:identity(p.lstat()) for p in execution.iterdir()}==before
    for name,row in OBSERVED.items():assert identity(Path(name).lstat())==row['identity']
    dest=O/'.work/runtime13-closed-audit-independent-readback-01.json'
    report=dict(status='verified-closed-audit13-saved-readback',pid=os.getpid(),parent_pid=os.getppid(),started_at=started,finished_at=time.time(),
        audit=ref(output),execution=ref(execution/'record.json'),preparation=ref(M/'preparation.json'),manifest=ref(M/'manifest.json'),
        source_inventory=ref(INV),auditor_parent=87740,auditor_child=88456,closed_returncode=0,canonical_released_at=rec['canonical_released_at'],
        complete_execution_membership=before,sources_unchanged=30,manifest_rows_equal=326,runtime07_children=child_rows,
        provider_directory_scope=scope,complete_directory_declaration_reconstructed=True,phase_claims=proof,
        negative_claims=dict(application=False,exporter=False,std=False,performance=False),observed_files=OBSERVED,
        scope='Closed saved source/raw/metadata readback and report-claim association only. The completed audit performed provider/runtime byte hashing; this independent readback did not repeat a provider walk, payload hash, compiler or audit.',
        provider_walks=0,provider_commands=0,compiler_calls=0,target_imports=0)
    data=(json.dumps(report,sort_keys=True,indent=2)+'\n').encode()
    with dest.open('xb') as stream:stream.write(data)
    print(json.dumps(dict(path=str(dest),sha256=hashlib.sha256(data).hexdigest(),files=len(OBSERVED),bytes=len(data),pid=os.getpid())))


if __name__=='__main__':main()
