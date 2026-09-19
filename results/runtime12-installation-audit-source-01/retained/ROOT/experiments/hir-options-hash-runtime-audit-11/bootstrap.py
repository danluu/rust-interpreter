"""Bounded source-authenticated saved runtime auditor entry; source draft only.

The external explicit-wait wrapper must pin this source and pass a separately
reviewed manifest digest, completed phase digests and its canonical descriptor.
No command, provider probe, runtime constructor or compression is invoked here.
"""
import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import shutil
import stat
import sys
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
HERE = ROOT/'experiments/hir-options-hash-runtime-audit-11'
QUALIFIED_AUDIT = ROOT/'experiments/hir-options-hash-runtime-audit-05'
ATTEMPT = ROOT/'experiments/runtime-installation-after-preflight05-02'
PREFLIGHT_SOURCE = ROOT/'experiments/runtime-preflight-retry-05'
ROUTES_PATH = ATTEMPT/'routes.json'
ROUTES_SHA = 'ef75ddf2057ebd395a159623d387b01051ee1479363bf9c878f7641b99ec0dd2'
SOURCE_PREFLIGHT_SHA = 'e2ec858a1e52e6b7573807d8834673699efcdf29ccdd801a84a973322cd9179a'
OLD = ROOT/'experiments/hir-options-hash-runtime-audit-04'
SOURCE = X/'experiments/hir-options-hash/runtime-installation-04'
CONTROL = ROOT/'experiments/runtime-saved-audit-controls-05'
CONTROL_WORK = ROOT/'.work/runtime-saved-audit-controls-05'
CONTROL_AUDIT = ROOT/'.work/runtime-saved-audit-controls-independent-verification-05.json'
PHASE_AUDIT = ROOT/'.work/hir-options-hash-runtime-audit-controls-independent-verification-04.json'
PHASE_SHA = 'c86c5f2e33c0aeed5b67fd75256e20f47626b21bdbb494bcd4eb6b74af57b25d'
STARTUP = ROOT/'experiments/runtime04-environment-adapter-01'
STARTUP_CONTROL = ROOT/'experiments/runtime-startup-environment-controls-01'
STARTUP_WORK = ROOT/'.work/runtime-startup-environment-controls-01'
STARTUP_AUDIT = ROOT/'.work/runtime-startup-environment-controls-independent-verification-01.json'
RETRY_CONTROL = ROOT/'experiments/runtime-preflight-retry-controls-05'
RETRY_WORK = ROOT/'.work/runtime-preflight-retry-controls-05'
RETRY_AUDIT = ROOT/'.work/runtime-preflight-retry-controls-independent-verification-05.json'
RETRY_COUNT = 33  # Source-derived count; no future qualification digest is invented.
RETRY_FILES = ('entry.py','controller.py','audit_owner.py','routes.json','prepare.py','prepare_once.py','launch.py')
INSTALLATION_CONTROL = ROOT/'experiments/runtime-installation-controls-07'
INSTALLATION_WORK = ROOT/'.work/runtime-installation-controls-07'
INSTALLATION_AUDIT = ROOT/'.work/runtime-installation-controls-independent-verification-07.json'
INSTALLATION_COUNT = 25  # Source-derived; separate completed actual proof required.
LINK_SOURCE = ROOT/'experiments/runtime-frozen-link-reader-01'
LINK_CONTROL = ROOT/'experiments/runtime-frozen-link-controls-01'
LINK_RESULT = ROOT/'results/runtime-frozen-link-controls-01/result.json'
LINK_COUNT = 24  # Separate direct control proof; no actual53 relabeling.

BASE = dict(path='/Users/danluu/dev/rust-interp-runtime-application-admission-20260918/experiments/hir-options-hash-native-controls-03/inputs.json',
            sha256='8569abb81a61e34b6b5a892116af5218557ceb0436ab8dbf8a31f2aec55b1b1d')
CANONICAL = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
FIELDS = ('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')
START = time.monotonic()
SAMPLES = []
LAST = 0
OBSERVED = {}


def require(value, message):
    if not value:
        raise RuntimeError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


def same(left, right):
    return encoded(left) == encoded(right)


def stamp(info):
    return {key:getattr(info,'st_'+key) for key in FIELDS}


def guard():
    global LAST
    require(time.monotonic()-START <= 1200, 'finite1200s independent readback bound')
    if time.monotonic()-LAST >= 1:
        free = shutil.disk_usage(R).free
        require(free >= 9*2**30, 'live9GiB independent readback floor')
        SAMPLES.append(dict(time=time.time(),free_bytes=free)); LAST=time.monotonic()


def raw(value, expected=None):
    """Small bootstrap read before qualified audit_io can be imported."""
    p = Path(value)
    require(p.is_absolute() and p != Path('/') and '..' not in p.parts
            and str(p) == os.fspath(value), 'canonical bootstrap route required')
    flags = os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NONBLOCK
    descriptors = [os.open('/', flags)]; links=[]
    route = lambda info:(info.st_dev,info.st_ino,info.st_mode)
    try:
        for name in p.parts[1:-1]:
            parent=descriptors[-1]; before=os.stat(name,dir_fd=parent,follow_symlinks=False)
            require(stat.S_ISDIR(before.st_mode),'ordinary bootstrap ancestor')
            child=os.open(name,flags,dir_fd=parent);descriptors.append(child)
            require(route(os.fstat(child))==route(before),'bootstrap ancestor changed during open')
            links.append((parent,name,child,route(before)))
        parent=descriptors[-1]; before=stamp(os.stat(p.name,dir_fd=parent,follow_symlinks=False))
        require(stat.S_ISREG(before['mode']) and before['size']<=64*2**20,'bounded ordinary bootstrap file')
        fd=os.open(p.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
        with os.fdopen(fd,'rb') as stream:
            require(same(stamp(os.fstat(stream.fileno())),before),'bootstrap opened leaf differs')
            parts=[];count=0
            while True:
                chunk=stream.read(2**20)
                if not chunk:break
                count+=len(chunk);require(count<=64*2**20,'bootstrap file grew beyond bound')
                parts.append(chunk);guard()
            guard();require(same(stamp(os.fstat(stream.fileno())),before),'bootstrap read leaf changed')
        require(same(stamp(os.stat(p.name,dir_fd=parent,follow_symlinks=False)),before),'bootstrap named leaf changed')
        for parent,name,child,saved in links:
            require(route(os.fstat(child))==saved and route(os.stat(name,dir_fd=parent,follow_symlinks=False))==saved,
                    'bootstrap ancestor route changed')
        data=b''.join(parts);row=dict(size=len(data),sha256=hashlib.sha256(data).hexdigest(),identity=before)
        require(len(data)==before['size'] and (expected is None or row['sha256']==expected),'exact bootstrap bytes required')
        require(str(p) not in OBSERVED or same(OBSERVED[str(p)],row),'bootstrap input changed after first read')
        OBSERVED.setdefault(str(p),row)
        return data
    finally:
        for fd in reversed(descriptors):os.close(fd)


def read(value, expected=None):
    def unique(pairs):
        result={}
        for key,item in pairs:
            require(key not in result,'duplicate bootstrap JSON key');result[key]=item
        return result
    return json.loads(raw(value,expected),object_pairs_hook=unique,
        parse_constant=lambda value:(_ for _ in ()).throw(ValueError(value)))


@contextmanager
def aliases(values):
    missing=object();before={name:sys.modules.get(name,missing) for name in values}
    sys.modules.update(values)
    try:
        yield
    finally:
        for name,value in before.items():
            if value is missing:sys.modules.pop(name,None)
            else:sys.modules[name]=value


def load(name, p, rows, dependencies=None):
    p=Path(p);require(str(p) in rows,'explicit authenticated source row required')
    raw(p,rows[str(p)]['sha256']);require(same(OBSERVED[str(p)],rows[str(p)]),'source identity changed before import')
    spec=importlib.util.spec_from_file_location('_runtime11_audit_'+name,p)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module
    with aliases(dependencies or {}):spec.loader.exec_module(module)
    return module


def qualification(reference, source, work, count, required, rows):
    """Pinned independent audit precedes importing its tested helper sources."""
    for p in [Path(reference['path']),source/'inputs.json',work/'receipt.json',work/'result.json']:
        require(str(p) in rows,'qualification closure is missing from supplemental manifest')
        raw(p,rows[str(p)]['sha256']);require(same(OBSERVED[str(p)],rows[str(p)]),'qualification identity changed')
    audit=read(reference['path'],reference['sha256']);receipt=read(work/'receipt.json');result=read(work/'result.json')
    tested=read(source/'inputs.json')
    require(audit['status']=='verified' and type(audit['controls']) is int and audit['controls']==count
        and receipt['status']==result['status']=='passed'
        and type(receipt['controls_passed']) is int and receipt['controls_passed']==count
        and type(result['tests_run']) is int and result['tests_run']==count
        and audit['receipt_sha256']==OBSERVED[str(work/'receipt.json')]['sha256']
        and receipt['result_sha256']==audit['result_sha256']==OBSERVED[str(work/'result.json')]['sha256']
        and receipt['inputs_sha256']==OBSERVED[str(source/'inputs.json')]['sha256'], 'actual completed qualification differs')
    for p in required:
        name=str(p);row=rows[name];old=tested['files'][name]
        require(old['sha256']==row['sha256'] and same(old['stamp'],[row['identity'][k] for k in
            ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']]), 'helper is not the actual tested source')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['installation'],required=True)
    parser.add_argument('--canonical-fd',type=int,required=True)
    parser.add_argument('--source-preflight-audit-sha256',required=True)
    parser.add_argument('--source-manifest',type=Path,required=True);parser.add_argument('--source-manifest-sha256',required=True)
    for name in ['launch','inputs','snapshot-plan','receipt','result','outer','launcher-record']:
        parser.add_argument('--'+name+'-sha256',required=True)
    args=parser.parse_args()
    require(type(RETRY_COUNT) is int and RETRY_COUNT > 0, 'retry control count remains unbound')
    require(type(LINK_COUNT) is int and LINK_COUNT > 0, 'frozen-link control count remains unbound')
    require(Path.cwd()==R and sys.dont_write_bytecode and not sys.flags.optimize,'fixed owner/unoptimized Python-B')
    require(shutil.disk_usage(R).free>=16*2**30,'fresh16GiB independent readback admission')
    held=os.fstat(args.canonical_fd);named=CANONICAL.lstat()
    require((held.st_dev,held.st_ino)==(named.st_dev,named.st_ino) and held.st_nlink==1,'exact inherited canonical descriptor')
    resource.setrlimit(resource.RLIMIT_CPU,(900,900));resource.setrlimit(resource.RLIMIT_FSIZE,(4*2**20,4*2**20))
    for key,value in vars(args).items():
        if key.endswith('_sha256'):require(re.fullmatch('[a-f0-9]{64}',value),'concrete reviewed SHA required')
    manifest=read(args.source_manifest,args.source_manifest_sha256)
    require(set(manifest)=={'policy','files','actual53','phase45','preparation','preparation_launcher','startup_controls','retry_controls','frozen_links_controls','installation_controls','source_preflight_audit'}
        and manifest['policy']=='runtime06-installation-complete-saved-audit-source-manifest-v1'
        and type(manifest['files']) is dict and len(manifest['files'])<=320
        and sum(row['size'] for row in manifest['files'].values())<=8*2**20,
        'bounded separately reviewed audit source manifest required')
    rows=manifest['files']
    require(str(ROUTES_PATH) in rows and rows[str(ROUTES_PATH)]['sha256']==ROUTES_SHA, 'fixed attempt descriptor is not in authenticated manifest')
    routes=read(ROUTES_PATH,ROUTES_SHA)
    require(routes['phase']==args.phase and routes['qualified_source']==str(SOURCE)
        and routes['attempt_source']==str(ATTEMPT), 'attempt and qualified source routes differ')
    preparation_root=Path(routes['preparation_execution'])
    for key in ['preparation','preparation_launcher','startup_controls','retry_controls','frozen_links_controls','installation_controls','source_preflight_audit']:
        ref=manifest[key]
        require(type(ref) is dict and set(ref)=={'path','sha256'} and str(ref['path']) in rows
            and rows[ref['path']]['sha256']==ref['sha256'], 'complete explicit actual preparation/startup reference required')
    require(manifest['preparation']['path']==str(preparation_root/'record.json')
        and manifest['preparation_launcher']['path']==str(ATTEMPT/'prepare_once.py')
        and manifest['startup_controls']['path']==str(STARTUP_AUDIT)
        and manifest['retry_controls']['path']==str(RETRY_AUDIT)
        and manifest['frozen_links_controls']['path']==str(LINK_RESULT)
        and manifest['installation_controls']['path']==str(INSTALLATION_AUDIT), 'exact phase-specific preparation/startup routes')
    prior=routes['preflight']
    require(same(manifest['source_preflight_audit'],dict(path=prior['report'],sha256=args.source_preflight_audit_sha256)),
        'externally pinned completed preflight05 reference differs')
    predecessor=read(prior['descriptor']['path'],prior['descriptor']['sha256'])
    require(prior['descriptor']['path']==str(PREFLIGHT_SOURCE/'routes.json')
        and predecessor['phase']=='preflight' and predecessor['attempt_source']==str(PREFLIGHT_SOURCE)
        and all(prior[key]==predecessor[key] for key in ['packet','work','supervisor','launcher_execution','preparation_execution','report']),
        'exact completed preflight05 routes required')
    require(args.source_preflight_audit_sha256 == SOURCE_PREFLIGHT_SHA, 'actual completed audit10 digest required')
    prior_audit=read(prior['report'],args.source_preflight_audit_sha256)
    require(prior_audit['status']=='verified' and prior_audit['phase']=='preflight'
        and type(prior_audit['actual_children']) is int and prior_audit['actual_children']==2
        and same(prior_audit['attempt'],prior['descriptor']), 'actual completed preflight05 independent audit required')
    for field,path in [('inputs_sha256',Path(prior['packet'])/'inputs.json'),('plan_sha256',Path(prior['packet'])/'plan.json'),
                       ('receipt_sha256',Path(prior['work'])/'receipt.json'),('result_sha256',Path(prior['work'])/'source-probe/result.json'),
                       ('outer_sha256',Path(prior['supervisor'])/'status.json'),('launcher_record_sha256',Path(prior['launcher_execution'])/'record.json')]:
        raw(path,prior_audit[field])
    require(manifest['actual53']['path']==str(CONTROL_AUDIT)
        and same(manifest['phase45'],dict(path=str(PHASE_AUDIT),sha256=PHASE_SHA)), 'exact qualification routes')
    own=[HERE/name for name in ['bootstrap.py','audit.py']] + [QUALIFIED_AUDIT/name for name in ['audit_io.py','reader.py']]
    require(all(str(p) in rows for p in own) and Path(__file__)==HERE/'bootstrap.py','explicit exact enclosing source rows')
    for p in own:raw(p,rows[str(p)]['sha256']);require(same(OBSERVED[str(p)],rows[str(p)]),'enclosing source changed')
    qualification(manifest['actual53'],CONTROL,CONTROL_WORK,53,
        [QUALIFIED_AUDIT/name for name in ['reader.py','audit_io.py','test_reader.py','test_audit_io.py']],rows)
    qualification(manifest['phase45'],ROOT/'experiments/hir-options-hash-runtime-audit-controls-04',
        ROOT/'.work/hir-options-hash-runtime-audit-controls-04',45,
        [OLD/name for name in ['recipe.py','preflight.py','final_runtime.py']],rows)
    qualification(manifest['startup_controls'],STARTUP_CONTROL,STARTUP_WORK,39,
        [STARTUP/name for name in ['environment.py','audit_owner.py','test_environment.py','test_audit_owner.py']],rows)
    qualification(manifest['retry_controls'],RETRY_CONTROL,RETRY_WORK,RETRY_COUNT,
        [PREFLIGHT_SOURCE/name for name in [*RETRY_FILES,'test_retry.py']],rows)
    qualification(manifest['installation_controls'],INSTALLATION_CONTROL,INSTALLATION_WORK,INSTALLATION_COUNT,
        [ATTEMPT/name for name in [*RETRY_FILES,'test_installation.py']],rows)
    for name,row in rows.items():raw(name,row['sha256']);require(same(OBSERVED[name],row),'complete supplemental source closure changed')
    io_module=load('io',QUALIFIED_AUDIT/'audit_io.py',rows)
    io_module.table(rows)
    packet=Path(routes['packet']);work=Path(routes['work'])
    outer=Path(routes['supervisor']);launcher=Path(routes['launcher_execution'])
    wire=read(packet/'inputs.json',args.inputs_sha256);require(same(wire['file_table_base'],BASE),'exact native base required')
    base=read(BASE['path'],BASE['sha256'])
    require('file_table_base' not in base and 'file_table_integrity' not in base
        and not set(base['files'])&set(wire['files']),'nonrecursive disjoint native base/delta')
    full=dict(base['files'],**wire['files']);io_module.table(full)
    require(same(wire['files'][BASE['path']],OBSERVED[BASE['path']])
        and same(wire['file_table_integrity'],dict(count=len(full),total_bytes=sum(r['size'] for r in full.values()),
            sha256=hashlib.sha256(encoded(full)).hexdigest())), 'complete typed compact integrity differs')
    prepared=dict({k:v for k,v in wire.items() if k not in ['files','file_table_base','file_table_integrity']},files=full)
    plan=read(packet/'plan.json',prepared['plan_sha256'])
    require(same(plan['attempt'],dict(path=str(ROUTES_PATH),sha256=ROUTES_SHA)), 'plan attempt reference differs')
    historical=sorted(prepared['historical_copies']['records'])
    extra=dict(rows);extra[str(args.source_manifest)]=OBSERVED[str(args.source_manifest)]
    inspection=io_module.inspection_union(prepared,extra,historical_paths=historical)
    roots=[packet,work,outer,launcher,preparation_root]
    if args.phase=='installation':
        require(re.fullmatch('[a-f0-9]{64}',plan['runtime_key']),'derived installation key required')
        roots.append(R/'.work/runtime-compilers'/plan['runtime_key'])
    # The orchestration module imports stdlib definitions only. Its bytes are
    # authenticated before deriving metadata authorization; no producer import.
    audit=load('orchestration',HERE/'audit.py',inspection['value']['files'])
    # Fail on an incomplete preparation closure before producer imports or
    # expensive current-provider guards; repeat this exact check at the tail.
    preparation_rows_path=preparation_root/'source-rows.json'
    require(str(preparation_rows_path) in rows, 'retained preparation source table must be authenticated')
    preparation_rows=read(preparation_rows_path,rows[str(preparation_rows_path)]['sha256'])
    require(same(OBSERVED[str(preparation_rows_path)],rows[str(preparation_rows_path)]),
        'retained preparation source table identity differs')
    audit.preparation_source_equality(preparation_rows,inspection['value']['files'])
    def completed_bytes(value):
        name=str(value);table=inspection['value']['files']
        require(name in table,'completed-owner authority is outside frozen ordinary rows')
        data=raw(name,table[name]['sha256'])
        require(same(OBSERVED[name],table[name]),'completed-owner authority identity changed')
        return data
    declared=audit.completed_directory_declarations(plan,inspection['value']['files'],
        read_json=lambda name:json.loads(completed_bytes(name)),read_bytes=completed_bytes,
        sha=lambda name:hashlib.sha256(completed_bytes(name)).hexdigest())
    entries={name:dict(zip(['dev','ino','mode','size','mtime_ns','ctime_ns','nlink'],row['stamp'],strict=True))
        for name,row in prepared['links'].items()}
    entries.update(plan['snapshot_reuse']['evidence_roots'])
    # Source provider directory observations are metadata only. All payloads
    # remain exact frozen file rows; final_runtime compares these observations
    # to the saved admission stamps after the complete provider Reader guard.
    specification=read(plan['specification']['path'],plan['specification']['sha256'])
    for component in specification['components']:
        root=io_module.path(component['root']);directories={root}
        for name in [*component['files'],*component['links']]:
            p=root/name;require(root in p.parents,'provider member escapes component')
            directories.update(parent for parent in p.parents if parent==root or root in parent.parents)
        for p in directories:
            with io_module.parent_descriptor(p) as (parent,leaf):
                row=stamp(os.stat(leaf,dir_fd=parent,follow_symlinks=False));io_module.typed_identity(row,'directory')
            require(str(p) not in entries or same(entries[str(p)],row),'metadata entry identity conflict')
            entries[str(p)]=row
    for name in declared['directories']:
        p=io_module.path(name)
        require(name not in inspection['value']['files'] and name not in historical
            and not any(p==root or root in p.parents for root in roots),
            'completed directory must remain exact metadata outside output subtrees')
        with io_module.parent_descriptor(p) as (parent,leaf):
            observed=stamp(os.stat(leaf,dir_fd=parent,follow_symlinks=False))
            io_module.typed_identity(observed,'directory')
        require(name not in entries or same(entries[name],observed),'completed metadata identity conflicts')
        entries[name]=observed
    io=io_module.Access(inspection['value']['files'],historical_paths=historical,entries=entries,output_roots=roots,guard=guard)
    completed_evidence=dict(declaration=declared,observed=audit.completed_directory_readback(declared,io))
    # Helper29 authentication and complete expansion are performed by the
    # unchanged qualified runtime Reader before any ordinary history checks.
    # This bootstrap's independent union never substitutes raw-wire digests.
    for name in io.files:
        if name.startswith('/Users/danluu/dev/') and name.endswith('.py'):io.file(name)
    reader=load('reader',QUALIFIED_AUDIT/'reader.py',io.files)
    # Replay exact source/raw control names through the qualified independent
    # reader before importing either startup policy or owner implementation.
    startup_proof=reader.controls(source=STARTUP_CONTROL,work=STARTUP_WORK,
        audit_path=manifest['startup_controls']['path'],
        source_paths=[STARTUP/'environment.py',STARTUP/'audit_owner.py'],
        test_paths=[STARTUP/'test_environment.py',STARTUP/'test_audit_owner.py'],
        read_json=io.read_json,read_bytes=io.read_bytes,sha=io.sha,identity=io.identity)
    require(type(startup_proof['controls']) is int and startup_proof['controls']==39
        and same(startup_proof['audit'],manifest['startup_controls']), 'actual startup controls differ before import')
    retry_proof=reader.controls(source=RETRY_CONTROL,work=RETRY_WORK,
        audit_path=manifest['retry_controls']['path'],
        source_paths=[PREFLIGHT_SOURCE/name for name in RETRY_FILES],test_paths=[PREFLIGHT_SOURCE/'test_retry.py'],
        read_json=io.read_json,read_bytes=io.read_bytes,sha=io.sha,identity=io.identity)
    require(type(retry_proof['controls']) is int and retry_proof['controls']==RETRY_COUNT
        and same(retry_proof['audit'],manifest['retry_controls']), 'actual separate retry controls differ before import')
    installation_proof=reader.controls(source=INSTALLATION_CONTROL,work=INSTALLATION_WORK,
        audit_path=manifest['installation_controls']['path'],
        source_paths=[ATTEMPT/name for name in RETRY_FILES],test_paths=[ATTEMPT/'test_installation.py'],
        read_json=io.read_json,read_bytes=io.read_bytes,sha=io.sha,identity=io.identity)
    require(type(installation_proof['controls']) is int and installation_proof['controls']==INSTALLATION_COUNT
        and same(installation_proof['audit'],manifest['installation_controls']), 'actual separate installation controls differ before import')
    link_proof=audit.frozen_link_controls(manifest['frozen_links_controls'],read_json=io.read_json,
        read_bytes=io.read_bytes,sha=io.sha,identity=io.identity)
    require(type(link_proof['tests']) is int and link_proof['tests']==LINK_COUNT,
        'actual separate frozen-link controls differ before import')
    link_reader=load('frozen_links',LINK_SOURCE/'links.py',io.files)
    environment=load('startup_environment',STARTUP/'environment.py',io.files)
    startup_owner=load('startup_owner',ATTEMPT/'audit_owner.py',io.files,{'environment':environment})
    resource_module=load('installation_resources',ATTEMPT/'controller.py',io.files)
    phase_modules={name:load(name,OLD/(name+'.py'),io.files) for name in ['recipe','preflight','final_runtime']}
    factory=load('factory',SOURCE/'imports.py',io.files);entry=load('entry',ATTEMPT/'entry.py',io.files)
    expected=dict(launch=args.launch_sha256,inputs=args.inputs_sha256,snapshot_plan=args.snapshot_plan_sha256,
        receipt=args.receipt_sha256,result=args.result_sha256,outer=args.outer_sha256,
        launcher_record=str(launcher/'record.json'),launcher_record_sha256=args.launcher_record_sha256,
        preparation=manifest['preparation'],preparation_launcher=manifest['preparation_launcher'],
        source_preflight_audit=manifest['source_preflight_audit'])
    report_path=Path(routes['report']);require(not os.path.lexists(report_path),'fresh independent report')
    result=audit.verify(phase=args.phase,expected=expected,prepared=prepared,inspection=inspection,io=io,
        reader=reader,factory=factory,entry=entry,actual53=manifest['actual53'],
        startup_owner=startup_owner,actual39=manifest['startup_controls'],actual_retry=manifest['retry_controls'],
        actual_installation=manifest['installation_controls'],resource_module=resource_module,
        link_reader=link_reader,actual_links=manifest['frozen_links_controls'],
        completed_evidence=completed_evidence,guard=guard,**phase_modules)
    result.update(pid=os.getpid(),parent_pid=os.getppid(),source_manifest=dict(path=str(args.source_manifest),
        sha256=args.source_manifest_sha256),source_rows=rows,samples=SAMPLES)
    # Every initial source/packet observation is checked once more; no current
    # identity is invented for the retired paths.
    for name,row in list(OBSERVED.items()):raw(name,row['sha256']);require(same(OBSERVED[name],row),'bootstrap observation changed')
    data=encoded(result);require(len(data)<=4*2**20,'bounded independent report')
    with report_path.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
    require(raw(report_path)==data,'exclusive report readback differs')
    print(encoded(dict(status='verified',path=str(report_path),sha256=hashlib.sha256(data).hexdigest())).decode(),end='')


if __name__=='__main__':
    main()
