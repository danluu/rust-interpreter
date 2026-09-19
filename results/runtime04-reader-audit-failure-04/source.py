"""Independent saved strict-rehearsal readback; no producer/helper imports.

Closed, pinned prior audits retain their historical scope. This reader rehashes
the new physical union, rebuilds every snapshot mapping and historical-copy
reference, and checks the explicit observed refusals. It grants no runtime or
retirement authority and never resolves a historical path through a live API.
"""
import argparse
import ast
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import stat
import sys
import time

ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
R=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
HERE=ROOT/'experiments/runtime04-historical-copy-reader-rehearsal-03'
WORK=ROOT/'.work/runtime04-historical-copy-reader-rehearsal-03'
PREP=ROOT/'.work/runtime04-historical-copy-reader-preparation-execution-03'
EXEC=ROOT/'.work/runtime04-historical-copy-reader-rehearsal-execution-03'
RUNTIME=X/'experiments/hir-options-hash/runtime-installation-04'
HASH=ROOT/'experiments/hir-options-hash-driver-stage-03'
HASH_WORK=ROOT/'.work/hir-options-hash-driver-02'
COPY_ROOT=O/'.work/hir-options-hash-run-make-01/retained'
REPORT=ROOT/'.work/runtime04-historical-copy-reader-independent-verification-04.json'
CANONICAL=Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
P=Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
BASE=dict(path=str(A/'experiments/hir-options-hash-native-controls-03/inputs.json'),
    sha256='8569abb81a61e34b6b5a892116af5218557ceb0436ab8dbf8a31f2aec55b1b1d')
ORIGINAL_SHA='c06e016829f0c98e579aace635ded04858ac8890ebe43bb6014d1f4df52aa010'
PROPOSAL=dict(path=str(X/'.work/runtime04-retained-copy-retirement-proposal-01.json'),
    sha256='e0599d87ab842b9e18932fddb54bb63aaf850cd2366279f67507e875731b3481')
HASH_AUDIT=dict(path=str(ROOT/'.work/hir-options-hash-driver-independent-verification-02.json'),
    sha256='9540ad45b5423f793e323bac31d593f1c1b030fe0e1dd5fc3665565277885ebb')
CONTROLS={
    52:dict(source=str(ROOT/'experiments/runtime-prerequisite-controls-04'),
        work=str(ROOT/'.work/runtime-prerequisite-controls-04'),
        audit=dict(path=str(ROOT/'.work/runtime-prerequisite-controls-independent-verification-04.json'),
        sha256='4cb7aa612c5ae53ada77dd41db870adb5b8dfa742005aa297dd483fca9531dcc')),
    40:dict(source=str(ROOT/'experiments/retained-proof-copy-controls-01'),
        work=str(ROOT/'.work/retained-proof-copy-controls-01'),
        audit=dict(path=str(ROOT/'.work/retained-proof-copy-controls-independent-verification-01.json'),
        sha256='c803f6e6e663c3fc8a081829e3c07deb9098692206a91269c36b2fe6fc08290a')),
    70:dict(source=str(ROOT/'experiments/hash-continuation-controls-01'),
        work=str(ROOT/'.work/hash-continuation-controls-01'),
        audit=dict(path=str(ROOT/'.work/hash-continuation-controls-independent-verification-01.json'),
        sha256='c0d5f127f802d9369ebcfb53f3658fda143aa35e7df641792ab483cb3f6b6a41'))}
SOURCES={'README.md': '36fbcca857df02814068ef52b89e0574cd9785a7d4057bad2f52c1481eebc8be', 'common.py': 'efca7434d8e0ef81a9d87de63a57cd4f130b8579963946b8191f0437521c22db', 'prepare.py': 'f32b6bb0c5cbd53416ca64a1733a4bc8155e4be7010cbc204bb351299c53f2e7', 'producer-import-delta.json': '5663849e8f77ec544f8d6f30d2b6da95facee2d7b4a9f6ba8703bb67a6abc500', 'reader-closure-delta.json': 'be103989ec8061b5e073767b5ccf539e737755d4a481eaa864529ddc06dcc292', 'reader-dependency-census.json': 'fc938adaca126d93a01b2669370f1e18efc500adf84260ba931f2c852d17828b', 'rehearse.py': '21d485a8b975ac0ac56d31589977a769c57f02e32e4f4e8bf6fbf8088905c0b6'}
# Only actual closed-record/packet/result constants are bound after review.
EXPECTED_LAUNCH='89c38791a7e927f30cb2b2b4dcfadc0dc90bc2a54aa33156b922da1249d49ca4'
EXPECTED_PREPARATION_RECORD='74c8d0e9833fcd945a5711f64c5cb8b8bd88a860bd691be273cc6f131bb62078'
EXPECTED_EXECUTION_RECORD='4326a5029150369e4a23bbc786388d26f6f041e2a818db1701f9953adfba3e4e'
EXPECTED_RESULT='10b88b94df6c8df07e2ccba1cfc04e9c702d5606e114a3c2a71e378975433b41'
FIELDS=('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')
START=time.monotonic()
LAST=0
SAMPLES=[]
CHECKED={}


def require(ok,message):
    if not ok:raise RuntimeError(message)


def encoded(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def same(a,b):return encoded(a)==encoded(b)
def digest(data):return hashlib.sha256(data).hexdigest()


def unique(pairs):
    result={}
    for key,value in pairs:
        require(key not in result,'duplicate JSON key');result[key]=value
    return result


def decode(data):
    return json.loads(data,object_pairs_hook=unique,
        parse_constant=lambda value:(_ for _ in ()).throw(ValueError(value)))


def guard():
    global LAST
    require(time.monotonic()-START<=1200,'finite independent readback bound')
    if time.monotonic()-LAST>=1:
        free=shutil.disk_usage(ROOT).free;require(free>=9*2**30,'live9GiB independent readback floor')
        SAMPLES.append(dict(time=time.time(),free_bytes=free));LAST=time.monotonic()


def identity(path):
    info=Path(path).lstat();return {key:getattr(info,'st_'+key) for key in FIELDS}


def typed_identity(row,directory=False):
    require(type(row) is dict and set(row)==set(FIELDS)
        and all(type(v) is int and v>=0 for v in row.values())
        and row['ino']>0 and row['nlink']>0
        and (stat.S_ISDIR if directory else stat.S_ISREG)(row['mode']),'ordinary seven-field identity')


def file(path,expected=None,limit=2**30,collect=False):
    guard();path=Path(path);before=identity(path);typed_identity(before)
    require(path.is_absolute() and path.resolve(strict=True)==path and before['size']<=limit,'bounded canonical ordinary file')
    h=hashlib.sha256();pieces=[];count=0
    with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW),'rb') as stream:
        require(same({k:getattr(os.fstat(stream.fileno()),'st_'+k) for k in FIELDS},before),'opened identity differs')
        while True:
            chunk=stream.read(2**20)
            if not chunk:break
            count+=len(chunk);require(count<=limit,'stream exceeds bound');h.update(chunk)
            if collect:pieces.append(chunk)
            guard()
        require(same({k:getattr(os.fstat(stream.fileno()),'st_'+k) for k in FIELDS},before),'read identity differs')
    row=dict(size=count,sha256=h.hexdigest(),identity=before)
    require(count==before['size'] and same(identity(path),before),'named file changed')
    if expected is not None:require(same(row,expected),'frozen current file differs: '+str(path))
    require(str(path) not in CHECKED or same(CHECKED[str(path)],row),
        'repeated read cannot replace the original identity/hash baseline')
    CHECKED[str(path)]=row
    return b''.join(pieces) if collect else row


def raw(path):return file(path,limit=64*2**20,collect=True)
def read(path):return decode(raw(path))
def sha(path):return file(path)['sha256']
def ref(path):return dict(path=str(path),sha256=sha(path))


def pinned(reference):
    require(set(reference)=={'path','sha256'} and sha(reference['path'])==reference['sha256'],'pinned saved reference differs')
    return read(reference['path'])


def membership(root,names):
    root=Path(root);before=identity(root);typed_identity(before,True)
    require(root.resolve(strict=True)==root and sorted(p.name for p in root.iterdir())==sorted(names),
        'exact ordinary output membership differs: '+str(root))
    require(same(identity(root),before),'directory changed while enumerated')
    return before


def expand(wire):
    require(same(wire['file_table_base'],BASE),'exact ordinary native base required')
    base=pinned(BASE);require('file_table_base' not in base and 'file_table_integrity' not in base
        and not set(base['files'])&set(wire['files']),'nonrecursive disjoint file table')
    require(same(wire['files'][BASE['path']],file(BASE['path'])),'base file itself must remain current delta')
    rows=dict(base['files'],**wire['files'])
    require(len(rows)<=180000 and sum(r['size'] for r in rows.values())<=8*2**30,'full table caps')
    require(same(wire['file_table_integrity'],dict(sha256=digest(encoded(rows)),count=len(rows),
        total_bytes=sum(r['size'] for r in rows.values()))),'typed complete table integrity')
    return dict({k:v for k,v in wire.items() if k not in ['file_table_base','file_table_integrity','files']},files=rows)


def full_plan():
    wire=read(HASH/'plan.json');reference=dict(path=str(X/'experiments/hir-options-hash/compiler-metadata-03/plan.json'),
        sha256='250b19e48b158efe78e726e78223791cb4ff55b5b5d2b9eaa59b41ba2b1727c2')
    require(set(wire)=={'policy','member','reference','remainder','integrity'}
        and wire['policy']=='external-json-member-v1' and wire['member']=='metadata_plan'
        and same(wire['reference'],reference) and 'metadata_plan' not in wire['remainder'],'exact plan reference envelope')
    full=dict(wire['remainder'],metadata_plan=pinned(reference));data=encoded(full)
    require(same(wire['integrity'],dict(bytes=len(data),sha256=digest(data))),'typed full plan reconstruction')
    return full


def current_table(freeze):
    for name,row in freeze['files'].items():
        require(set(row)=={'size','sha256','identity'} and type(row['size']) is int and row['size']>=0,'typed physical row')
        file(name,row)
    for name,row in freeze['links'].items():
        actual=identity(name);stamp=[actual[k] for k in ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']]
        require(stat.S_ISLNK(actual['mode']) and same(stamp,row['stamp']) and os.readlink(name)==row['target']
            and str(Path(name).resolve(strict=True))==row['resolved'],'current symlink association')
    for name in freeze['absent_paths']:require(not os.path.lexists(name),'current required absence')
    for name,target in freeze.get('executor_routes',{}).items():require(str(Path(name).resolve(strict=True))==target,'executor route differs')


def recheck():
    for name,row in CHECKED.items():require(same(identity(name),row['identity']),'audited current input changed before publication')


def controls(count,freeze):
    owner=CONTROLS[count];source=Path(owner['source']);work=Path(owner['work'])
    audit=pinned(owner['audit']);receipt=read(work/'receipt.json');result=read(work/'result.json');wire=read(source/'inputs.json')
    require(audit['status']=='verified' and type(audit['controls']) is int and audit['controls']==count
        and audit['receipt_sha256']==sha(work/'receipt.json') and audit['result_sha256']==sha(work/'result.json')
        and receipt['status']=='passed' and type(receipt['controls_passed']) is int and receipt['controls_passed']==count
        and receipt['result_sha256']==audit['result_sha256'] and receipt['inputs_sha256']==sha(source/'inputs.json'),
        'closed actual control qualification differs')
    for name,row in wire['files'].items():
        expected=dict(sha256=row['sha256'],size=row['stamp'][3],identity=dict(zip(
            ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink'],row['stamp'],strict=True)))
        file(name,expected);require(same(freeze['files'][name],expected),'qualified control input omitted from current union')
    require(type(result['tests_run']) is int and result['tests_run']==count,'actual test count differs')
    names=wire['expected_names'];wanted_modules={name.split('.')[0] for name in names};actual_names=[]
    test_paths={
        52:[RUNTIME/'test_prerequisite_successor.py',RUNTIME/'test_copy_references.py'],
        40:[ROOT/'experiments/retained-proof-copy-references-01/test_references.py'],
        70:[ROOT/'experiments/completed-proof-snapshot-catalog-02/test_catalog.py',
            ROOT/'experiments/completed-proof-snapshot-catalog-02/test_failed_catalog.py',
            HASH/'test_plan_reference.py']}[count]
    require({path.stem for path in test_paths}==wanted_modules and all(str(path) in wire['files'] for path in test_paths),
        'exact tested module routes; historical duplicate basenames retain their own provenance')
    for path in test_paths:
        module=path.stem
        tree=ast.parse(raw(path))
        actual_names.extend(module+'.'+cls.name+'.'+method.name for cls in tree.body if isinstance(cls,ast.ClassDef)
            for method in cls.body if isinstance(method,ast.FunctionDef) and method.name.startswith('test_'))
    require(names==sorted(actual_names)==result['expected_names']==sorted(audit['exact_names']) and len(names)==count,
        'complete source-derived actual control names')
    child=read(work/'command/receipt.json');stdout=raw(work/'command/stdout');stderr=raw(work/'command/stderr')
    observed=re.findall(r'^test_[A-Za-z0-9_]+ \(([^)]+)\) \.\.\. ok$',stderr.decode(),re.M)
    require(sorted(observed)==names and len(observed)==count and not stdout
        and re.search(r'^Ran '+str(count)+r' tests in [0-9.]+s\n\nOK\n$',stderr.decode(),re.M)
        and child['status']=='finished' and child['returncode']==0 and same(child['command'],wire['command'])
        and child['stdout_sha256']==audit['raw_sha256']['stdout']==digest(stdout)
        and child['stderr_sha256']==audit['raw_sha256']['stderr']==digest(stderr),
        'actual distinct control raw names and command closure')
    require(all(same(result[key],0) for key in ['failures','errors','skipped','expected_failures',
        'unexpected_successes','child_processes','compiler_calls']),'no skipped or extra test work')
    return owner['audit']


def gzip_proof(row):
    path=Path(row['path']);blob=row['blob'];before=file(path)
    require(same(before,dict(size=blob['compressed_bytes'],sha256=blob['sha256'],identity=row['identity']))
        and before['identity']['nlink']==1 and path.parent==Path(row['evidence_root'])
        and path.name==blob['filename']==blob['logical_sha256']+'.gz','exact physical gzip descriptor')
    count=0;h=hashlib.sha256()
    with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW),'rb') as stream:
        require(same({k:getattr(os.fstat(stream.fileno()),'st_'+k) for k in FIELDS},before['identity']),'gzip opened identity')
        with gzip.GzipFile(fileobj=stream,mode='rb') as decoded:
            while True:
                chunk=decoded.read(2**20)
                if not chunk:break
                count+=len(chunk);require(count<=blob['logical_bytes']<=64*2**20,'bounded logical gzip stream')
                h.update(chunk);guard()
        require(stream.tell()==blob['compressed_bytes'],'complete compressed EOF')
    require(count==blob['logical_bytes'] and h.hexdigest()==blob['logical_sha256']
        and same(identity(path),before['identity']),'full logical EOF or identity differs')


def owner_snapshots(owner,prior_records,freeze,expected_status):
    """Independently rebuild one complete original v1 or v2 physical addition."""
    source=Path(owner['source']);work=Path(owner['evidence']);root=work/'source-snapshots'
    for key in ['receipt','inputs','projection','retained_projection','manifest','audit']:
        pinned(owner[key])
    receipt=read(work/'receipt.json');audit=read(owner['audit']['path'])
    require(receipt['status']==expected_status and audit['receipt_sha256']==sha(work/'receipt.json'),
        'original owner status/audit remains distinct')
    if 'qualification' in owner:
        qualifier=owner['qualification'];qa=pinned(qualifier['audit']);qr=pinned(qualifier['receipt']);pinned(qualifier['result'])
        require(qr['status']=='passed' and qa['status']=='verified' and qr['actual_workload_children']==0
            and qa['receipt_sha256']==qualifier['receipt']['sha256'] and qa['result_sha256']==qualifier['result']['sha256'],
            'separate zero-child native qualification differs')
    wire=read(source/'inputs.json');old=expand(wire) if 'file_table_base' in wire else wire
    snapshot=read(source/'snapshot-plan.json');projection=snapshot['projection'];manifest=read(work/'source-snapshots.json')
    require(sha(source/'snapshot-plan.json')==sha(work/'snapshot-plan.json')==receipt['snapshot_plan_sha256']
        and sha(work/'source-snapshots.json')==receipt['source_snapshots_sha256']
        and sha(source/'inputs.json')==snapshot['inputs_sha256']==receipt['inputs_sha256']
        and manifest['projection_sha256']==digest(encoded(projection))
        and manifest['full_gzip_eof'] is manifest['full_logical_readback'] is True,'original snapshot receipt association')
    names=old['snapshot_inputs'];require(len(names)==len(set(names)) and str(source/'inputs.json') not in names,'complete unique old selection')
    selected={name:dict(path=name,**old['files'][name]) for name in sorted(names)}
    selected[str(source/'inputs.json')]=dict(path=str(source/'inputs.json'),**file(source/'inputs.json'))
    require(same(selected,projection['files']),'complete original logical selection differs')
    for name,row in selected.items():require(same({k:row[k] for k in ['size','sha256','identity']},freeze['files'][name]),
        'selected logical source must remain strictly current')
    limits=dict(maximum_files=1024,maximum_file_bytes=64*2**20,maximum_logical_bytes=512*2**20,
        maximum_compressed_bytes=128*2**20,maximum_manifest_bytes=4*2**20)
    require(same(snapshot['limits'],limits) and same(projection['limits'],limits)
        and len(selected)<=1024 and sum(r['size'] for r in selected.values())<=512*2**20
        and all(len(encoded(d))<=4*2**20 for d in [snapshot,projection,manifest]),'unchanged complete snapshot caps')
    blobs=projection['blobs'];require(same(blobs,manifest['blobs']) and set(blobs)=={r['sha256'] for r in selected.values()},'complete blob groups')
    by_digest={}
    for row in prior_records:by_digest.setdefault(row['blob']['logical_sha256'],row)
    reused={key:by_digest[key] for key in blobs if key in by_digest} if 'storage' in projection else {}
    if 'storage' in projection:
        selected_roots={r['evidence_root']:identity(r['evidence_root']) for r in reused.values()}
        require(same(projection['reuse'],reused) and same(manifest['reuse'],reused)
            and same(projection['evidence_roots'],selected_roots) and same(manifest['evidence_roots'],selected_roots),
            'deterministic first-owner reuse and counted roots')
    mapping={};new=[];stored=[];total=allocated=newbytes=newallocated=0;physical={}
    for key,b in sorted(blobs.items()):
        require(set(b)=={'filename','logical_sha256','logical_bytes','sha256','compressed_bytes'}
            and b['logical_sha256']==key and b['filename']==key+'.gz'
            and all(type(b[k]) is int and 0<=b[k]<=64*2**20 for k in ['logical_bytes','compressed_bytes']),
            'bounded typed blob descriptor')
        if key in reused:
            row=reused[key];require(same(b,row['blob']),'reused blob differs');kind='reused'
        else:
            path=root/b['filename'];actual=file(path)
            require(actual['sha256']==b['sha256'] and actual['size']==b['compressed_bytes'],'new blob current bytes differ')
            row=dict(path=str(path),identity=actual['identity'],blob=b,evidence_root=str(root));new.append(row)
            stored.append(path.name);newbytes+=b['compressed_bytes'];newallocated+=((b['compressed_bytes']+4095)//4096)*4096;kind='stored'
        physical[key]=dict(kind=kind,path=row['path'])
        if 'storage' in projection:
            require(same(projection['storage'][key],dict(kind=kind,**({'path':row['path']} if kind=='reused' else {}))),
                'stored/reused declaration differs')
        total+=b['compressed_bytes'];allocated+=((b['compressed_bytes']+4095)//4096)*4096
    for name,row in selected.items():
        require(blobs[row['sha256']]['logical_bytes']==row['size'],'logical alias size differs')
        mapping[name]=dict(path=physical[row['sha256']]['path'],sha256=row['sha256'],size=row['size'],encoding='gzip')
    require(same(mapping,manifest['files']) and same(projection['compressed_bytes'],total)
        and same(projection['compressed_allocated_bytes'],allocated) and same(manifest['compressed_bytes'],total)
        and same(projection['logical_bytes'],sum(r['size'] for r in selected.values()))
        and same(projection['unique_logical_bytes'],sum(b['logical_bytes'] for b in blobs.values())),
        'complete logical mapping/accounting differs')
    if 'storage' in projection:
        require(same(manifest['storage'],physical)
            and same(projection['new_compressed_allocated_bytes'],newallocated)
            and all(same(obj[key],value) for obj in [projection,manifest] for key,value in
                dict(new_compressed_bytes=newbytes,reused_compressed_bytes=total-newbytes).items()),'new-only physical accounting differs')
    require(total<=128*2**20 and same(projection['manifest_reservation_bytes'],8*2**20),'unchanged compressed and document caps')
    root_identity=membership(root,stored)
    return new,root_identity


def catalogs(plan,old,freeze):
    prior=plan['snapshot_reuse'];require(prior['priority']==['beta','native','failed-hash-driver-01']
        and prior['policy']=='closed-failed-proof-snapshot-catalog-v2' and len(prior['records'])==464,'exact completed prior catalog')
    rebuilt=[];roots={}
    for owner,status in zip(prior['predecessors'],['passed','failed','failed'],strict=True):
        rows,stamp=owner_snapshots(owner,rebuilt,freeze,status);rebuilt.extend(rows);roots[owner['snapshot_root']]=stamp
    require(same(rebuilt,prior['records']) and same(roots,prior['evidence_roots']),'complete beta/native/failed prior reconstruction')
    terminal=read(HASH_WORK/'receipt.json');result=read(HASH_WORK/'result.json');audit=pinned(HASH_AUDIT)
    require(audit['status']=='verified' and audit['receipt_sha256']==sha(HASH_WORK/'receipt.json')
        and audit['result_sha256']==sha(HASH_WORK/'result.json')==terminal['result_sha256']
        and terminal['hash_driver_qualified'] is True and terminal['inputs_sha256']==ORIGINAL_SHA
        and terminal['application_qualified'] is terminal['performance_measurement'] is False,
        'distinct actually successful hash02 owner required')
    association=dict(role='hash',source=str(HASH),evidence=str(HASH_WORK),result_digest_field='result_sha256',
        inherited_catalog_sha256=digest(encoded(prior)))
    for key,path in [('receipt',HASH_WORK/'receipt.json'),('result',HASH_WORK/'result.json'),('audit',Path(HASH_AUDIT['path'])),
        ('inputs',HASH/'inputs.json'),('plan',HASH/'plan.json'),('projection',HASH/'snapshot-plan.json'),
        ('retained_projection',HASH_WORK/'snapshot-plan.json'),('manifest',HASH_WORK/'source-snapshots.json')]:association[key]=ref(path)
    association.update(file_table_base=BASE,helper=read(HASH/'snapshot-plan.json')['helper'],snapshot_root=str(HASH_WORK/'source-snapshots'))
    added,stamp=owner_snapshots(association,rebuilt,freeze,'passed-awaiting-independent-audit')
    require(len(added)==54,'actual successful hash02 retained54 new physical blobs')
    roots[association['snapshot_root']]=stamp
    complete=dict(policy=prior['policy'],priority=prior['priority']+['hash'],predecessors=prior['predecessors']+[association],
        records=rebuilt+added,evidence_roots=dict(sorted(roots.items())))
    require(len(complete['records'])==518 and len({r['path'] for r in complete['records']})==518
        and len({(r['identity']['dev'],r['identity']['ino']) for r in complete['records']})==518,'no duplicate physical path/inode credit')
    for row in complete['records']:gzip_proof(row)
    return prior,complete


def historical_references(plan,old,freeze,prior,chosen):
    work=COPY_ROOT.parent;source=O/'experiments/hir-options-hash-run-make-stage-02'
    receipt=read(work/'receipt.json');result=read(work/'result.json');retention=read(work/'retained-inputs.json')
    auditref=plan['independent_audits']['run_make'];audit=pinned(auditref);recipe=read(source/'plan.json')
    require(receipt['status']==result['status']=='passed' and audit['status']=='verified'
        and audit['receipt_sha256']==sha(work/'receipt.json') and receipt['result_sha256']==sha(work/'result.json')
        and result['retained_inputs_sha256']==sha(work/'retained-inputs.json')
        and result['plan_sha256']==sha(source/'plan.json') and result['inputs_sha256']==sha(source/'inputs.json')
        and same(result['actual_commands'],receipt['commands']) and same(result['source_identity'],plan['source_identity']),
        'closed original retention owner association')
    for document in [receipt,result]:
        require(document['native_recipe_qualified'] is True and all(same(document[k],v) for k,v in
            dict(recipe_compilations=1,recipe_executions=1,nested_commands=230).items())
            and all(document[k] is False for k in ['hash_driver_qualified','application_qualified','performance_measurement']),
            'actual run-make owner scope changed')
    expected={name:dict(sha256=row['sha256'],bytes=row['stamp'][3]) for name,row in recipe['retained_selection'].items()}
    for path in [source/'plan.json',source/'inputs.json']:
        row=old['files'][str(path)];expected[str(path)]=dict(sha256=row['sha256'],bytes=row['size'])
    entries=[]
    for index,name in enumerate(sorted(expected)):
        entries.append(dict(source=name,retained=str(COPY_ROOT/(f'{index:04d}-'+Path(name).name)),**expected[name]))
    require(len(entries)==61 and same({k:retention[k] for k in ['status','files','logical_bytes']},dict(status='retained',files=entries,
        logical_bytes=sum(r['bytes'] for r in entries))),'complete immutable61 retention map')
    owner=dict(source=str(source),evidence=str(work),receipt=ref(work/'receipt.json'),audit=auditref,retention=ref(work/'retained-inputs.json'))
    by_digest={}
    for row in prior['records']:by_digest.setdefault(row['blob']['logical_sha256'],row)
    indexed={row['retained']:row for row in entries};records={};witnesses={}
    live=set(pinned(BASE)['files'])|set(read(X/'experiments/hir-options-hash/compiler-metadata-03/inputs.json')['files'])|set(old['snapshot_inputs'])
    live.update(row['source'] for row in entries)
    for predecessor in prior['predecessors']:live.update(pinned(predecessor['manifest'])['files'])
    require(not set(chosen)&live and live<=set(freeze['files']),'all executable/source/SDK/selected current inputs retained')
    for name in chosen:
        row=old['files'][name];entry=indexed[name];current=freeze['files'][entry['source']];witness=by_digest[row['sha256']]
        require(row['size']==entry['bytes']==current['size']==witness['blob']['logical_bytes']
            and row['sha256']==entry['sha256']==current['sha256'] and row['identity']['nlink']==1
            and not row['identity']['mode']&0o111,'exact non-executable original/source/witness bytes')
        records[name]=dict(kind='historical-proof-copy',original_record=row,retention_entry=entry,
            current_source=dict(path=entry['source'],**current),witness=witness);witnesses[witness['path']]=witness
    return dict(policy='historical-retained-proof-copy-references-v1',owner=owner,copy_root=str(COPY_ROOT),records=records,
        witnesses=dict(sorted(witnesses.items())),historical_files=21,historical_logical_bytes=sum(old['files'][n]['size'] for n in chosen),
        original_file_table_sha256=digest(encoded(old['files'])),current_physical_files=109322,
        new_physical_payload_bytes=0,retirement_authorized=False,allocation_credit_bytes=0)



def producer_delta(freeze,old,result,plan):
    delta=read(HERE/'producer-import-delta.json')
    require(sha(HERE/'producer-import-delta.json')==SOURCES['producer-import-delta.json']
        and result['producer_import_delta_sha256']==SOURCES['producer-import-delta.json']
        and same(plan['producer_import_delta'],ref(HERE/'producer-import-delta.json')),
        'actual authenticated producer delta association')
    bindings=pinned(delta['runtime_bindings']);previous=pinned(delta['predecessor_bindings'])
    require(same(delta['factory'],dict(path=str(RUNTIME/'imports.py'),
        sha256='574196f8f73a422b225b73c5bad9b59634e674b7b23b1ee30daca4b830120451'))
        and sha(delta['factory']['path'])==delta['factory']['sha256'],'exact raw factory source binding')
    require(delta['runtime_bindings']['path']==str(RUNTIME/'source-bindings.json')
        and delta['runtime_bindings']['sha256']=='9947b9cbaa1fbf1634c466abea4841ae25f2f4db567df00306f065d7c01fefcb'
        and delta['predecessor_bindings']['path']==str(RUNTIME.with_name('runtime-installation-01')/'source-bindings.json')
        and delta['predecessor_bindings']['sha256']=='e6e7f5024699fd0eedacb7cab28d2cbf9f99a605a19a1c7a5939cd7d8ba702ea'
        and delta['factory']['sha256']=='574196f8f73a422b225b73c5bad9b59634e674b7b23b1ee30daca4b830120451'
        and same(delta['original_inputs'],dict(path=str(HASH/'inputs.json'),sha256=ORIGINAL_SHA)),
        'immutable import provenance catalogs differ')
    paths=[R/'scripts'/(name+'.py') for name in ['custom_compiler','workflow_io','std_mir','compare_saved_runtime',
        'toolchain_lookup','runtime_compiler','std_mir_source_paths','verified_std_diagnostics']]
    paths.append(R/'experiments/runtime-compiler-installation/source_qualification.py')
    paths.extend(RUNTIME.with_name('runtime-installation-01')/(name+'.py') for name in ['recipe','discovery','controller','monitor'])
    require(set(delta['files'])==set(map(str,paths))==set(delta['provenance'])
        and not set(delta['files'])&set(old['files']),'separate exact13 producer-current rows')
    for name,row in delta['files'].items():
        require(same(freeze['files'][name],row),'producer source omitted from physical freeze')
        file(name,row)
        if str(Path(name).parent)==str(RUNTIME.with_name('runtime-installation-01')):
            require(same(row,bindings['predecessor_sources'][name]),'old qualified full producer identity')
            provenance=dict(catalog=delta['runtime_bindings']['path'],table='predecessor_sources',kind='existing-full-identity')
        else:
            require(same(previous['references'][name],dict(bytes=row['size'],sha256=row['sha256'])),
                'authenticated old bytes with new current producer identity')
            provenance=dict(catalog=delta['predecessor_bindings']['path'],table='references',kind='existing-bytes-new-current-identity')
        require(same(provenance,delta['provenance'][name]),'explicit producer provenance class')
    failure=delta['historical_failure'];record=pinned(failure['record'])
    require(sha(failure['stderr']['path'])==failure['stderr']['sha256'],'exact raw failure traceback bytes')
    require(record['status']=='finished' and same(record['returncode'],1) and record['parent_pid']==70927
        and record['pid']==82759 and 'canonical_released_at' not in record
        and 'result_sha256' not in record and len(failure['files'])==14,'honest closed failure01 retained')
    for name,row in failure['files'].items():file(name,row);require(same(freeze['files'][name],row),'original failure history omitted')
    old_source=ROOT/'experiments/runtime04-historical-copy-reader-rehearsal-01'
    require(all(not os.path.lexists(old_source/name) for name in ['plan.json','inputs.json','launch.json','preparation.json']),
        'failed01 cannot acquire a synthetic packet')
    return dict(path=str(HERE/'producer-import-delta.json'),sha256=SOURCES['producer-import-delta.json'],
        files=13,bytes=sum(r['size'] for r in delta['files'].values()),historical_failure=failure['record'])


def reader_dependencies(freeze,old,plan,result,preparation):
    """Independently bind completed-owner additions and closed failed02 history."""
    source=ROOT/'experiments/runtime04-historical-copy-reader-rehearsal-02'
    preparation_dir=ROOT/'.work/runtime04-historical-copy-reader-preparation-execution-02'
    execution_dir=ROOT/'.work/runtime04-historical-copy-reader-rehearsal-execution-02'
    artifact=X/'.work/hir-options-hash-compiler-01/hash-driver-02'
    delta_ref=dict(path=str(HERE/'reader-closure-delta.json'),sha256=SOURCES['reader-closure-delta.json'])
    census_ref=dict(path=str(HERE/'reader-dependency-census.json'),sha256=SOURCES['reader-dependency-census.json'])
    delta=pinned(delta_ref);census=pinned(census_ref)
    require(same(plan['reader_closure_delta'],delta_ref) and same(plan['reader_dependency_census'],census_ref)
        and all(doc['reader_closure_delta_sha256']==delta_ref['sha256']
            and doc['reader_dependency_census_sha256']==census_ref['sha256'] for doc in [result,preparation]),
        'new actual packet/preparation/result dependency association')
    expected={str(HASH/'launch.json'),str(artifact/'hash-control-driver'),str(artifact/'fixture.rs')}
    require(delta['policy']=='explicit-completed-reader-closure-delta-v1'
        and set(delta['files'])==expected and same(delta['qualified_hash_audit'],HASH_AUDIT)
        and delta['qualified_hash_result']['path']==str(HASH_WORK/'result.json')
        and delta['publication_proposal']['path']==str(ROOT/'results/hir-options-hash-driver-02/proposal.json')
        and delta['original_rehearsal']['path']==str(source/'inputs.json')
        and same(delta['census'],census_ref),'exact completed owner and original failed Reader routes')
    previous_wire=pinned(delta['original_rehearsal']);previous=expand(previous_wire)
    require(not expected&set(previous['files']) and not expected&set(old['files'])
        and all(same(row,freeze['files'][name]) for name,row in previous['files'].items()),
        'original02 omission preserved while complete previous physical context remains current')
    audit=pinned(HASH_AUDIT);qualified=pinned(delta['qualified_hash_result'])
    publication=pinned(delta['publication_proposal'])
    published={row['path']:{key:row[key] for key in ['sha256','size','identity']} for row in publication['files']}
    require(len(published)==len(publication['files']) and audit['status']=='verified'
        and audit['result_sha256']==delta['qualified_hash_result']['sha256'],
        'actual qualification and publication member identity association')
    for name,row in delta['files'].items():
        require(same(freeze['files'][name],row) and same(published[name],row),'new ordinary row differs from prior qualified publication')
        file(name,row)
        if name==str(HASH/'launch.json'):
            require(row['sha256']==audit['launch_sha256'],'actual completed launch SHA differs')
        else:
            base=Path(name).name;record=audit['artifacts'][base]
            require(record['kind']=='file' and record['sha256']==row['sha256']
                and same(record['stamp'],[row['identity'][key] for key in
                    ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']])
                and qualified['binary_sha256' if base=='hash-control-driver' else 'fixture_sha256']==row['sha256'],
                'existing actual driver artifact identity/result differs')
    history=delta['historical_failed_rehearsal'];closed=pinned(history['record'])
    require(history['record']['path']==str(execution_dir/'record.json')
        and history['stdout']['path']==str(execution_dir/'stdout') and history['stderr']['path']==str(execution_dir/'stderr')
        and same(history['actual_parent_pid'],82686) and same(history['actual_child_pid'],84047)
        and same(history['returncode'],1) and history['status']=='finished'
        and history['result_created'] is history['canonical_released_at_recorded'] is False,
        'original02 failed closure must retain its scope')
    require(len(history['files'])==29,'complete29 original packet and preparation/rehearsal execution rows')
    for name,row in history['files'].items():
        require(same(freeze['files'][name],row),'original02 source/raw missing from successor physical table');file(name,row)
    for root in [source,preparation_dir,execution_dir]:
        wanted={str(Path(name).relative_to(root)) for name in history['files'] if root in Path(name).parents}
        actual=set()
        for path in root.rglob('*'):
            require(not path.is_symlink(),'old closed evidence cannot acquire a symlink')
            if path.is_file():actual.add(str(path.relative_to(root)))
            else:require(path.is_dir(),'ordinary closed evidence tree')
        require(actual==wanted,'complete old source/packet/execution tree membership')
    for reference in [history['record'],history['stdout'],history['stderr']]:
        require(sha(reference['path'])==reference['sha256']==history['files'][reference['path']]['sha256'],
            'old failure raw is bound to its saved execution')
    require(closed['status']=='finished' and same(closed['returncode'],1)
        and closed['pid']==84047 and closed['parent_pid']==82686 and closed['mode']=='rehearse'
        and closed['execution_source_sha256']==history['execution_source_sha256']==sha(execution_dir/'source/execution.py')
        and closed['stdout_sha256']==history['stdout']['sha256'] and closed['stderr_sha256']==history['stderr']['sha256']
        and same(closed['observation_errors'],[]) and 'canonical_released_at' not in closed
        and 'result_sha256' not in closed and closed.get('may_be_live') is not True
        and closed['started_at']<=closed['admitted_at']<=closed['child_started_at']
            <=closed['observation_finished_at']<=closed['finished_at']
        and closed['result']==str(ROOT/'.work/runtime04-historical-copy-reader-rehearsal-02/result.json')
        and not os.path.lexists(closed['result']), 'original failed Reader is closed without synthetic result/release')
    oldprep=pinned(delta['prior_preparation'])
    require(delta['prior_preparation']['path']==str(preparation_dir/'record.json')
        and oldprep['status']=='finished' and same(oldprep['returncode'],0)
        and oldprep['result_sha256']==sha(source/'preparation.json')
        and oldprep['finished_at']<=oldprep['canonical_released_at']<=closed['started_at'],
        'original preparation passed before original Reader failure')
    oldlaunch=read(source/'launch.json')
    require(oldlaunch['inputs_sha256']==delta['original_rehearsal']['sha256']
        and oldlaunch['plan_sha256']==sha(source/'plan.json')==previous_wire['plan_sha256']
        and same(closed['source_sha256'],oldprep['source_sha256'])
        and all(sha(source/name)==sha(execution_dir/'source'/name)==sha(preparation_dir/'source'/name)==value
            for name,value in closed['source_sha256'].items()),'complete retained original02 source/packet history')
    diagnostic=raw(execution_dir/'stderr');first=decode(diagnostic.splitlines()[0])
    require(first['error']==repr(KeyError(str(HASH/'launch.json')))
        and first['pid']==closed['pid'] and first['parent_pid']==closed['parent_pid']
        and same(first['passed_environment'],closed['environment'])
        and b'Traceback (most recent call last):' in diagnostic and raw(execution_dir/'stdout')==b'',
        'exact original missing-launch failure and environments retained')
    require(census['status']=='reviewed-static-reader-dependency-census-not-execution'
        and same(census['original_rehearsal_inputs'],delta['original_rehearsal'])
        and same(census['required_additions'],delta['files'])
        and census['missing_from_original_rehearsal']==sorted(expected)
        and census['required_paths']==sorted(set(census['required_paths'])) and len(census['required_paths'])==1256
        and set(census['required_paths'])<=set(freeze['files'])
        and set(census['required_paths'])-set(previous['files'])==expected
        and set(census['required_paths'])=={name for paths in census['groups'].values() for name in paths},
        'complete reviewed dependency census is physically admitted without virtual reads')
    for name,row in census['source_files'].items():
        require(same(freeze['files'][name],row),'dependency-census source changed');data=file(name,row,collect=True)
        tree=ast.parse(data)
        calls=[dict(line=node.lineno,expression=ast.unparse(node)) for node in ast.walk(tree) if isinstance(node,ast.Call)
            and ((isinstance(node.func,ast.Attribute) and node.func.attr in
                ['frozen','file','read_bytes','read_json','sha','record','verify_reference','closure','prerequisites','guard'])
              or (isinstance(node.func,ast.Name) and node.func.id in
                ['file_record','directory_record','read_json','read_bytes','sha','expand_inputs','check_absent']))]
        require(same(calls,census['physical_call_inventory'][name]),'independent physical-call source inventory differs')
    for reference in [delta['original_rehearsal'],delta['qualified_hash_audit'],delta['qualified_hash_result'],
                      delta['publication_proposal'],delta['prior_preparation'],delta_ref,census_ref]:
        require(reference['path'] in freeze['files'] and freeze['files'][reference['path']]['sha256']==reference['sha256'],
            'new dependency provenance must itself be frozen')
    return dict(delta=delta_ref,census=census_ref,additional_current_rows=3,required_paths=1256,
        qualified_outputs=delta['files'],original_failed_rehearsal=history['record'],
        original_failure_source_and_raw_files=29,original_preparation=delta['prior_preparation'],
        failure_environment=first,original_canonical_release_timestamp_recorded=False)


def execution(directory,expected,mode,result_path):
    record=pinned(dict(path=str(directory/'record.json'),sha256=expected))
    membership(directory,['record.json','stdout','stderr','source']);membership(directory/'source',list(SOURCES)+['owned_stage.py','execution.py'])
    for name,value in SOURCES.items():require(sha(directory/'source'/name)==sha(HERE/name)==value,'retained original rehearsal source')
    require(record['status']=='finished' and record['returncode']==0 and record['mode']==mode
        and not any(k in record for k in ['execution_error','initial_child_publication_error','may_be_live'])
        and same(record.get('observation_errors',[]),[])
        and record['cwd']==str(ROOT) and record['canonical_lock']==str(CANONICAL)
        and same(record['source_sha256'],SOURCES) and record['result']==str(result_path)
        and record['result_sha256']==sha(result_path) and sha(directory/'stderr')==record['stderr_sha256']==digest(b'')
        and sha(directory/'stdout')==record['stdout_sha256'],'closed explicit reader execution')
    require(record['started_at']<=record['admitted_at']<=record['child_started_at']<=record['observation_finished_at']
        <=record['finished_at']<=record['canonical_released_at'] and all(type(record[k]) is int and record[k]>0
        for k in ['parent_pid','parent_parent_pid','parent_pgid','pid']),'actual parent/child closure chronology')
    require(record['execution_source_sha256']==sha(directory/'source/execution.py')
        and record['owned_source_sha256']==sha(directory/'source/owned_stage.py')
        =='7021a15d3b806ab908f03276051d9d9ca9c9e208bbf8933a60229c9fb35bb68e','execution and owned source readback')
    constants={}
    for node in ast.parse(raw(directory/'source/execution.py')).body:
        if (isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name)
                and node.targets[0].id in ['SOURCES','EXPECTED_LAUNCH']):
            constants[node.targets[0].id]=ast.literal_eval(node.value)
    require(same(constants['SOURCES'],SOURCES) and constants['EXPECTED_LAUNCH']==(None if mode=='prepare' else EXPECTED_LAUNCH),
        'retained dispatcher actual source association')
    command=record['command'];require(command[:4]==[str(P),'-B',str(HERE/('prepare.py' if mode=='prepare' else 'rehearse.py')),'--canonical-fd']
        and type(command[4]) is str and command[4].isdigit() and command[5]=='--passed-environment-json'
        and same(decode(command[6]),record['environment']),'actual child command/environment association')
    tail=[] if mode=='prepare' else ['--inputs-sha256',sha(HERE/'inputs.json'),'--plan-sha256',sha(HERE/'plan.json')]
    require(command[7:]==tail and record['entry_free_bytes']>=16*2**30 and record['free_bytes_before']>=16*2**30
        and record['free_bytes_after']>=9*2**30 and all(r['free_bytes']>=9*2**30 for r in record['disk_samples'])
        and same(record['capacity'],dict(entry_gib=16,live_gib=9,floor_gib=8)),'finite admitted bounds')
    require(all(same(record[k],v) for k,v in dict(wait_seconds=600,maximum_child_cpu_seconds=900,
        maximum_child_read_seconds=1200,maximum_observation_seconds=1250,
        maximum_child_file_bytes=(64 if mode=='prepare' else 4)*2**20).items()),'unchanged finite execution bounds')
    return record


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--canonical-fd',type=int,required=True);args=parser.parse_args()
    require(Path.cwd()==ROOT and sys.dont_write_bytecode and not sys.flags.optimize and Path(sys.executable).resolve()==P,'exact independent auditor owner')
    held=os.fstat(args.canonical_fd);named=CANONICAL.lstat()
    require((held.st_dev,held.st_ino)==(named.st_dev,named.st_ino) and held.st_nlink==1,'inherited canonical lock')
    resource.setrlimit(resource.RLIMIT_CPU,(900,900));resource.setrlimit(resource.RLIMIT_FSIZE,(4*2**20,4*2**20))
    require(all(type(v) is str and re.fullmatch('[0-9a-f]{64}',v) for v in
        [EXPECTED_LAUNCH,EXPECTED_PREPARATION_RECORD,EXPECTED_EXECUTION_RECORD,EXPECTED_RESULT]),'actual closure pins remain unbound')
    require(not os.path.lexists(REPORT),'fresh independent report')
    started=time.time();membership(HERE,list(SOURCES)+['plan.json','inputs.json','preparation.json','launch.json'])
    membership(WORK,['result.json'])
    launch=pinned(dict(path=str(HERE/'launch.json'),sha256=EXPECTED_LAUNCH));plan=read(HERE/'plan.json')
    result=pinned(dict(path=str(WORK/'result.json'),sha256=EXPECTED_RESULT));preparation=read(HERE/'preparation.json')
    prep=execution(PREP,EXPECTED_PREPARATION_RECORD,'prepare',HERE/'preparation.json')
    actual=execution(EXEC,EXPECTED_EXECUTION_RECORD,'rehearse',WORK/'result.json')
    require(prep['canonical_released_at']<=actual['started_at'] and result['pid']==actual['pid']
        and result['parent_pid']==actual['parent_pid'] and actual['admitted_at']<=result['started_at']<=result['finished_at']<=actual['finished_at'],
        'actual preparation/rehearsal parent and terminal association')
    require(result['status']=='passed-strict-callback-rehearsal-awaiting-independent-audit'
        and result['inputs_sha256']==launch['inputs_sha256']==sha(HERE/'inputs.json')
        and result['plan_sha256']==launch['plan_sha256']==sha(HERE/'plan.json')
        and launch['reader_sha256']==SOURCES['rehearse.py'] and launch['common_sha256']==SOURCES['common.py'],
        'actual prepared source/result packet association')
    wire=read(HERE/'inputs.json');freeze=expand(wire)
    require(wire['plan_sha256']==sha(HERE/'plan.json') and sha(HASH/'inputs.json')==ORIGINAL_SHA,'raw physical/original input bindings')
    old_wire=read(HASH/'inputs.json');old=expand(old_wire);original_plan=full_plan();proposal=pinned(PROPOSAL)
    chosen=sorted(str(COPY_ROOT/name) for name in proposal['selected']);require(len(chosen)==len(set(chosen))==21,'exact21 proposal')
    recovery={r['path']:r for r in proposal['recovery']}
    require(set(recovery)==set(chosen) and proposal['target_root']==str(COPY_ROOT)
        and all(Path(name).parent==COPY_ROOT and same(recovery[name]['original_record'],old['files'][name]) for name in chosen),
        'exact old21 selection rows')
    require(len(old['files'])==109343 and len(set(old['files'])-set(chosen))==109322
        and all(same(row,freeze['files'][name]) for name,row in old['files'].items() if name not in chosen)
        and not set(chosen)&(set(freeze['files'])|set(freeze['absent_paths'])|set(freeze['snapshot_inputs'])|set(old['snapshot_inputs'])),
        'complete strictly current old-minus21 physical partition')
    require(all(same(freeze['links'][name],row) for name,row in old['links'].items())
        and set(old['absent_paths'])<=set(freeze['absent_paths']), 'original links and absences remain current')
    current_table(freeze)
    producer=producer_delta(freeze,old,result,plan)
    dependencies=reader_dependencies(freeze,old,plan,result,preparation)
    for count in CONTROLS:controls(count,freeze)
    prior,complete=catalogs(original_plan,old,freeze)
    references=historical_references(original_plan,old,freeze,prior,chosen)
    require(same(result['historical_references'],references) and same(result['completed_catalog_records'],518)
        and same(result['prior_catalog_records'],464) and result['completed_catalog_sha256']==digest(encoded(complete)),
        'independent historical references and successful catalog differ')
    presence={name:identity(name) for name in chosen}
    require(all(same(presence[name],old['files'][name]['identity']) for name in chosen)
        and same(result['copy_presence'],presence) and same(plan['copy_presence'],presence),'still-present original21 identity observations')
    APIs=['Frozen.file','Frozen.record','Frozen.read_bytes','Frozen.read_json','Frozen.sha','Stage.frozen','Stage.read_bytes','Stage.read_json']
    denials=[dict(path=name,api=api,rejected=True) for name in chosen for api in APIs]
    collector=[dict(path=name,api='RuntimeDiscovery.add',rejected=True) for name in chosen]
    require(same(result['physical_api_denials'],denials) and same(result['collector_denials'],collector)
        and same(plan['collector_denials'],collector),'complete168+21 exact current-API refusals')
    require(same(plan['historical_names'],chosen) and same(plan['original_snapshot_inputs'],old['snapshot_inputs'])
        and same(result['original_file_table_integrity'],old_wire['file_table_integrity'])
        and same(result['source_sha256'],SOURCES) and result['proposal_sha256']==PROPOSAL['sha256']
        and result['historical_source_stage03_wire_sha256']==ORIGINAL_SHA,'original associations and source observations')
    for key,value in dict(complete_original_rows=109343,current_context_rows=109322,historical_copies=21,
        current_physical_files=len(freeze['files']),current_physical_bytes=sum(r['size'] for r in freeze['files'].values()),
        witness_count=len(references['witnesses']),provider_probes=0,compiler_calls=0,runtime_packets_created=0,
        runtime_work_created=0,retired_files=0).items():require(same(result[key],value),'typed result count '+key)
    require(result['bootstrap_policy']=='continued-catalog-before-reader' and all(result[k] is True for k in
        ['no_live_api_virtualization','full_current_input_rehash','full_current_recipe_check','full_compressed_and_logical_EOF'])
        and result['runtime_admission'] is result['retirement_authorized'] is False,'observed rehearsal scope')
    require(result['selected_paths']==chosen and result['selected_paths_sha256']==digest(encoded(chosen))
        and result['protected_paths_sha256']==digest(encoded(sorted(set(old['files'])-set(chosen)))),'exact selected/protected sets')
    absent=[str(RUNTIME/name) for name in ['preflight-plan-01','installation-plan-01']]
    absent.extend(str(R/'.work'/('hir-options-hash-runtime-'+phase+'-04')) for phase in ['preflight','installation'])
    require(result['runtime_absent']==plan['runtime_absent']==absent and all(not os.path.lexists(p) for p in absent),'runtime namespaces remain absent')
    for doc,record,keys in [(preparation,prep,['passed','before_runtime_imports','after_runtime_imports','at_completion']),
        (result,actual,['passed','before_runtime_imports','after_runtime_imports','after_reader_construction','after_full_reader_check','at_completion'])]:
        env=doc['environments'];require(set(env)==set(keys) and all(type(v) is dict and all(type(k) is type(x) is str for k,x in v.items()) for v in env.values())
            and same(env['passed'],record['environment']),'exact observed/passed environment schema')
        observations=doc['import_environments']
        require(set(observations)=={'before_authentication','before_factory_definitions','after_factory_definitions'}
            and all(type(v) is dict and all(type(k) is type(x) is str for k,x in v.items()) for v in observations.values()),
            'exact observed import-stage environment records')
        require(same(doc['io_policy']['blocked_events'],0),'read-only audit-hook recorded forbidden API')
    require(same(preparation['io_policy']['written_paths'],[str(HERE/'plan.json'),str(HERE/'inputs.json')])
        and preparation['io_policy']['created_directories']==[] and result['io_policy']['written_paths']==[]
        and result['io_policy']['created_directories']==[str(WORK)],'policy observations apply before output serialization')
    # Complete membership above is independent of these prefix-only observations.
    recheck();require(all(same(identity(name),presence[name]) for name in chosen),'copies changed before report')
    output=dict(status='verified-strict-callback-rehearsal',started_at=started,finished_at=time.time(),pid=os.getpid(),parent_pid=os.getppid(),
        proposal_sha256=PROPOSAL['sha256'],historical_source_stage03_wire_sha256=ORIGINAL_SHA,
        complete_original_rows=109343,current_context_rows=109322,historical_copies=21,
        bootstrap_policy='continued-catalog-before-reader',no_live_api_virtualization=True,runtime_admission=False,retirement_authorized=False,
        result=ref(WORK/'result.json'),preparation_execution=ref(PREP/'record.json'),rehearsal_execution=ref(EXEC/'record.json'),
        launch=ref(HERE/'launch.json'),inputs=ref(HERE/'inputs.json'),plan=ref(HERE/'plan.json'),
        actual52=CONTROLS[52]['audit'],helper40=CONTROLS[40]['audit'],continuation70=CONTROLS[70]['audit'],successful_hash02=HASH_AUDIT,
        selected_paths=chosen,selected_paths_sha256=result['selected_paths_sha256'],protected_paths_sha256=result['protected_paths_sha256'],
        current_physical_files=len(freeze['files']),current_physical_bytes=sum(r['size'] for r in freeze['files'].values()),
        full_current_input_rehash=True,full_catalog_logical_mapping=True,full_compressed_and_logical_EOF=True,
        prior_catalog_records=464,completed_catalog_records=518,completed_catalog_sha256=digest(encoded(complete)),
        historical_references_sha256=digest(encoded(references)),witness_count=len(references['witnesses']),
        copy_presence=presence,collector_denials=21,physical_api_denials=168,runtime_absent=absent,
        producer_import_delta=producer,reader_dependencies=dependencies,
        preparation_environments=preparation['environments'],rehearsal_environments=result['environments'],
        preparation_import_environments=preparation['import_environments'],rehearsal_import_environments=result['import_environments'],
        io_policy_scope='Producer observations stop before output serialization; exact output membership was independently checked.',
        full_output_membership=True,identity_limitation=actual['identity_limitation'],
        compiler_calls=0,provider_probes=0,retired_files=0,samples=SAMPLES,auditor_sha256=sha(__file__))
    data=encoded(output);require(len(data)<=4*2**20,'bounded independent report')
    with REPORT.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
    require(raw(REPORT)==data,'independent report durable readback')
    print(encoded(dict(status=output['status'],report=str(REPORT),sha256=digest(data))).decode(),end='')


if __name__=='__main__':main()
