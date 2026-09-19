"""Bounded saved-evidence IO and exact source adoption; no provider execution."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
RUNTIME=X/'experiments/hir-options-hash/runtime-installation-04'
HASH=ROOT/'experiments/hir-options-hash-driver-stage-03'
HASH_WORK=ROOT/'.work/hir-options-hash-driver-02'
WORK=ROOT/'.work/runtime04-historical-copy-reader-rehearsal-03'
AUDIT=ROOT/'.work/hir-options-hash-driver-independent-verification-02.json'
AUDIT_SHA='9540ad45b5423f793e323bac31d593f1c1b030fe0e1dd5fc3665565277885ebb'
CONTROL=ROOT/'experiments/runtime-prerequisite-controls-04'
CONTROL_WORK=ROOT/'.work/runtime-prerequisite-controls-04'
CONTROL_AUDIT=ROOT/'.work/runtime-prerequisite-controls-independent-verification-04.json'
CONTROL_AUDIT_SHA='4cb7aa612c5ae53ada77dd41db870adb5b8dfa742005aa297dd483fca9531dcc'
ORIGINAL_SHA='c06e016829f0c98e579aace635ded04858ac8890ebe43bb6014d1f4df52aa010'
OWNED=X/'experiments/stable-cgu/owned_stage.py'
OWNED_SHA='7021a15d3b806ab908f03276051d9d9ca9c9e208bbf8933a60229c9fb35bb68e'
CANONICAL=Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
RUNTIME_SOURCES={'README.md': '1bdc904b499c0e61235212160c49d297b0d424fca4fda40be290273c7dafe162', 'copies.py': 'e81fe5230c239d370670af1907743eb2680b40eab0273622a775eb50259938fb', 'entry.py': 'ee8127d53f294b14aa5243c9ff008557ea0a3f148c91a413ab6cafdcb60881b8', 'frozen.py': '09410397e5f4a7c85282de841003afcd0aeadfd76b3cc617244162ed1be60775', 'imports.py': '574196f8f73a422b225b73c5bad9b59634e674b7b23b1ee30daca4b830120451', 'preflight_history.py': '367274e5fc7c25340aba1d14011a026b82819f2c2ee0f70618027241682230fb', 'prepare.py': 'd8c8af0637e19ea5423f962a0c254bed75105d5ff2a65fbab4dd53dd7ec541c7', 'prerequisites.py': 'f0bec62bf5526c7ec3b3b28500cb304e98a35e0f89f3b45208b5fb086f0a888e', 'source-bindings.json': '9947b9cbaa1fbf1634c466abea4841ae25f2f4db567df00306f065d7c01fefcb', 'test_copy_references.py': '0dea2fc636e08932dc606c6531afa1cb1100e77df394f79204124ffec80c8985', 'test_prerequisite_successor.py': '7c90ec9507dba63be3694b1e20b1d3cb03e97ab99a97bd77a0fcd48cb53841ea'}
FIELDS=('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')
START=time.monotonic()
SAMPLES=[]
LAST_SAMPLE=0
IMPORT_DELTA_ROWS={}
IMPORT_OBSERVATIONS={}
PRODUCER_DELTA_SHA='5663849e8f77ec544f8d6f30d2b6da95facee2d7b4a9f6ba8703bb67a6abc500'
READER_DELTA_SHA='be103989ec8061b5e073767b5ccf539e737755d4a481eaa864529ddc06dcc292'
READER_CENSUS_SHA='fc938adaca126d93a01b2669370f1e18efc500adf84260ba931f2c852d17828b'


def require(ok,message):
    if not ok:raise RuntimeError(message)


def encoded(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode()


def same(left,right):return encoded(left)==encoded(right)


def identity(path):
    info=Path(path).lstat();return {key:getattr(info,'st_'+key) for key in FIELDS}


def guard():
    global LAST_SAMPLE
    require(time.monotonic()-START<=1200,'finite1200s read-only observation bound')
    if time.monotonic()-LAST_SAMPLE>=1:
        free=shutil.disk_usage(ROOT).free;require(free>=9*2**30,'live9GiB rehearsal floor')
        SAMPLES.append(dict(time=time.time(),free_bytes=free));LAST_SAMPLE=time.monotonic()


def raw(path,limit=64*2**20):
    guard();path=Path(path);before=identity(path)
    require(path.is_absolute() and path.resolve(strict=True)==path and stat.S_ISREG(before['mode'])
        and before['size']<=limit,'bounded ordinary saved-evidence file required')
    with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW),'rb') as stream:
        require({key:getattr(os.fstat(stream.fileno()),'st_'+key) for key in FIELDS}==before,'opened evidence changed')
        data=stream.read(limit+1)
        require(len(data)==before['size'] and len(data)<=limit,'bounded evidence length changed')
        require({key:getattr(os.fstat(stream.fileno()),'st_'+key) for key in FIELDS}==before,'read evidence changed')
    require(identity(path)==before,'evidence route changed');return data


def sha(path):return hashlib.sha256(raw(path)).hexdigest()


def unique(pairs):
    result={}
    for key,value in pairs:
        require(key not in result,'duplicate saved JSON key');result[key]=value
    return result


def read(path):return json.loads(raw(path),object_pairs_hook=unique,
    parse_constant=lambda value:(_ for _ in ()).throw(ValueError(value)))


def write(path,value,limit=4*2**20):
    data=encoded(value);require(len(data)<=limit,'bounded rehearsal document')
    with Path(path).open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())


def load(name,path):
    spec=importlib.util.spec_from_file_location('_runtime04_rehearsal_'+name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module


def reader_closure():
    """Bind the three actual completed-owner omissions and failed rehearsal02.

    This reads only existing immutable files. It grants no workload admission,
    does not reinterpret the old missing file as present, and never virtualizes
    any file API. The unchanged Reader still requires ordinary physical rows.
    """
    delta=read(HERE/'reader-closure-delta.json')
    require(sha(HERE/'reader-closure-delta.json')==READER_DELTA_SHA,'reviewed Reader closure delta changed')
    prior=ROOT/'experiments/runtime04-historical-copy-reader-rehearsal-02'
    execution=ROOT/'.work/runtime04-historical-copy-reader-rehearsal-execution-02'
    preparation=ROOT/'.work/runtime04-historical-copy-reader-preparation-execution-02'
    artifacts=X/'.work/hir-options-hash-compiler-01/hash-driver-02'
    expected={str(HASH/'launch.json'),str(artifacts/'hash-control-driver'),str(artifacts/'fixture.rs')}
    require(delta['policy']=='explicit-completed-reader-closure-delta-v1' and set(delta['files'])==expected
        and delta['original_rehearsal']['path']==str(prior/'inputs.json')
        and delta['qualified_hash_audit']==dict(path=str(AUDIT),sha256=AUDIT_SHA)
        and delta['qualified_hash_result']['path']==str(HASH_WORK/'result.json')
        and delta['publication_proposal']['path']==str(ROOT/'results/hir-options-hash-driver-02/proposal.json'),
        'exact completed owner closure routes required')
    for ref in [delta['original_rehearsal'],delta['qualified_hash_audit'],delta['qualified_hash_result'],
                delta['publication_proposal'],delta['prior_preparation']]:
        require(sha(ref['path'])==ref['sha256'],'Reader closure provenance changed')
    audit=read(AUDIT);result=read(HASH_WORK/'result.json');original=read(prior/'inputs.json')
    published={row['path']:{k:row[k] for k in ['sha256','size','identity']}
        for row in read(delta['publication_proposal']['path'])['files']}
    require(audit['status']=='verified' and audit['result_sha256']==delta['qualified_hash_result']['sha256']
        and not expected&set(original['files']),'original omission and passed owner must stay distinct')
    for name,row in delta['files'].items():
        require(set(row)=={'sha256','size','identity'} and row['size']==row['identity']['size']
            and same(published[name],row) and identity(name)==row['identity']
            and sha(name)==row['sha256'] and identity(name)==row['identity'],
            'actual completed output identity or bytes changed')
        if name==str(HASH/'launch.json'):
            require(row['sha256']==audit['launch_sha256'],'actual audited launch differs')
        else:
            basename=Path(name).name;item=audit['artifacts'][basename]
            require(item['kind']=='file' and item['sha256']==row['sha256']
                and item['stamp']==[row['identity'][k] for k in
                    ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']]
                and result['binary_sha256' if basename=='hash-control-driver' else 'fixture_sha256']==row['sha256'],
                'qualified artifact provenance differs')
    history=delta['historical_failed_rehearsal']
    require(history['record']['path']==str(execution/'record.json')
        and history['stdout']['path']==str(execution/'stdout') and history['stderr']['path']==str(execution/'stderr')
        and history['actual_parent_pid']==82686 and history['actual_child_pid']==84047
        and history['returncode']==1 and history['status']=='finished'
        and history['result_created'] is False and history['canonical_released_at_recorded'] is False,
        'honest failed02 closure required')
    require(len(history['files'])==29,'complete original packet and both execution trees required')
    for name,row in history['files'].items():
        require(identity(name)==row['identity'] and sha(name)==row['sha256']
            and identity(name)==row['identity'],'failed02 evidence changed')
    for ref in [history['record'],history['stdout'],history['stderr']]:
        require(history['files'][ref['path']]['sha256']==ref['sha256'],'failed02 raw association differs')
    record=read(execution/'record.json');old_preparation=read(preparation/'record.json')
    require(record['status']=='finished' and type(record['returncode']) is int and record['returncode']==1
        and record['pid']==84047 and record['parent_pid']==82686 and record['mode']=='rehearse'
        and record['execution_source_sha256']==history['execution_source_sha256']
        and record['stdout_sha256']==history['stdout']['sha256']
        and record['stderr_sha256']==history['stderr']['sha256']
        and record['observation_errors']==[] and 'canonical_released_at' not in record
        and record['child_started_at']<=record['observation_finished_at']<=record['finished_at']
        and not Path(record['result']).exists() and not Path(record['result']).is_symlink(),
        'failed02 must remain closed, failed and without a result')
    require(old_preparation['status']=='finished' and old_preparation['returncode']==0
        and delta['prior_preparation']['path']==str(preparation/'record.json')
        and old_preparation['finished_at']<=old_preparation['canonical_released_at'],
        'actual passed preparation remains separate from failed Reader')
    diagnostic=raw(execution/'stderr')
    first=json.loads(diagnostic.splitlines()[0])
    require(first['error']==repr(KeyError(str(HASH/'launch.json')))
        and first['pid']==record['pid'] and first['parent_pid']==record['parent_pid']
        and b'Traceback (most recent call last):' in diagnostic and raw(execution/'stdout')==b'',
        'original missing-launch rejection must remain explicit')
    for root in [prior,preparation,execution]:
        expected_names={str(Path(name).relative_to(root)) for name in history['files'] if root in Path(name).parents}
        actual={str(path.relative_to(root)) for path in root.rglob('*') if path.is_file()}
        require(actual==expected_names,'closed prior packet/execution membership changed')
    reference=delta['census'];require(reference==dict(path=str(HERE/'reader-dependency-census.json'),sha256=READER_CENSUS_SHA)
        and sha(reference['path'])==READER_CENSUS_SHA,'reviewed complete dependency census changed')
    census=read(reference['path'])
    require(census['status']=='reviewed-static-reader-dependency-census-not-execution'
        and census['original_rehearsal_inputs']==delta['original_rehearsal']
        and same(census['required_additions'],delta['files'])
        and census['missing_from_original_rehearsal']==sorted(expected)
        and census['required_paths']==sorted(set(census['required_paths']))
        and len(census['required_paths'])==1256,'exact reviewed Reader dependency census required')
    return delta,census


def authenticate():
    """Authenticate current qualified runtime source and original import rows."""
    require(type(CONTROL_AUDIT_SHA) is str and len(CONTROL_AUDIT_SHA)==64
        and sha(CONTROL_AUDIT)==CONTROL_AUDIT_SHA,'actual52 audit remains unbound or changed')
    audit=read(CONTROL_AUDIT);terminal=read(CONTROL_WORK/'receipt.json')
    require(audit['status']=='verified' and type(audit['controls']) is int and audit['controls']==52
        and audit['receipt_sha256']==sha(CONTROL_WORK/'receipt.json')
        and terminal['status']=='passed' and terminal['controls_passed']==52
        and audit['result_sha256']==terminal['result_sha256']==sha(CONTROL_WORK/'result.json')
        and terminal['inputs_sha256']==sha(CONTROL/'inputs.json'),'actual completed52 association required')
    require(type(RUNTIME_SOURCES) is dict and len(RUNTIME_SOURCES)==11,'exact runtime source pins required')
    for name,digest in RUNTIME_SOURCES.items():require(sha(RUNTIME/name)==digest,'qualified runtime source changed')
    require(sha(AUDIT)==AUDIT_SHA and read(AUDIT)['status']=='verified'
        and read(AUDIT)['receipt_sha256']==sha(HASH_WORK/'receipt.json')
        and read(HASH_WORK/'receipt.json')['status']=='passed-awaiting-independent-audit','actual hash02 owner required')
    require(sha(HASH/'inputs.json')==ORIGINAL_SHA,'exact historical hash table required')
    wire=read(HASH/'inputs.json');base=wire['file_table_base']
    require(sha(base['path'])==base['sha256'],'exact ordinary native base bytes required')
    old=read(base['path']);require('file_table_base' not in old and not set(old['files'])&set(wire['files']),'nonrecursive disjoint base')
    full=dict(old['files'],**wire['files'])
    require(same(wire['file_table_integrity'],dict(sha256=hashlib.sha256(encoded(full)).hexdigest(),
        count=len(full),total_bytes=sum(row['size'] for row in full.values()))) and len(full)==109343,
        'independent original full-table reconstruction differs')
    proposal=X/'.work/runtime04-retained-copy-retirement-proposal-01.json'
    require(sha(proposal)=='e0599d87ab842b9e18932fddb54bb63aaf850cd2366279f67507e875731b3481',
        'exact reviewed historical-copy proposal required before source imports')
    selected=read(proposal)
    copy_root=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918/.work/hir-options-hash-run-make-01/retained')
    historical={row['path']:row['original_record'] for row in selected['recovery']}
    require(len(historical)==len(selected['recovery'])==21 and selected['target_root']==str(copy_root)
        and set(historical)=={str(copy_root/name) for name in selected['selected']}
        and all(Path(name).parent==copy_root and same(row,full[name]) for name,row in historical.items()),
        'exact original21 source-auth exclusion required')
    # stage.dependencies imports several transitive local modules without using
    # the factory callback. Authenticate their entire possible local Python
    # closure before any definitions import, not after discovery.
    for name,row in full.items():
        if name.startswith('/Users/danluu/dev/') and Path(name).suffix=='.py' and name not in historical:
            require(identity(name)==row['identity'] and sha(name)==row['sha256']
                and identity(name)==row['identity'],'local Python source changed before definitions import')
    # These 13 producer modules were never members of the old hash table.
    # Their immutable byte provenance is separate from new current identities.
    delta=read(HERE/'producer-import-delta.json')
    require(sha(HERE/'producer-import-delta.json')==PRODUCER_DELTA_SHA,'reviewed producer delta changed')
    bindings=read(RUNTIME/'source-bindings.json')
    prior_path=RUNTIME.with_name('runtime-installation-01')/'source-bindings.json'
    prior_row=bindings['predecessor_sources'][str(prior_path)]
    require(identity(prior_path)==prior_row['identity'] and sha(prior_path)==prior_row['sha256'],
        'immutable original source-reference catalog changed')
    prior=read(prior_path)
    require(same(delta['runtime_bindings'],dict(path=str(RUNTIME/'source-bindings.json'),sha256=RUNTIME_SOURCES['source-bindings.json']))
        and same(delta['predecessor_bindings'],dict(path=str(prior_path),sha256=prior_row['sha256']))
        and same(delta['factory'],dict(path=str(RUNTIME/'imports.py'),sha256=RUNTIME_SOURCES['imports.py']))
        and same(delta['original_inputs'],dict(path=str(HASH/'inputs.json'),sha256=ORIGINAL_SHA)),
        'producer source catalogs/factory/original association differs')
    owner=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
    scripts=['custom_compiler','workflow_io','std_mir','compare_saved_runtime','toolchain_lookup',
        'runtime_compiler','std_mir_source_paths','verified_std_diagnostics']
    selected=[owner/'scripts'/(name+'.py') for name in scripts]
    selected.append(owner/'experiments/runtime-compiler-installation/source_qualification.py')
    selected.extend(prior_path.parent/(name+'.py') for name in ['recipe','discovery','controller','monitor'])
    require(set(delta['files'])==set(map(str,selected))==set(delta['provenance'])
        and not set(delta['files'])&set(full),'exact disjoint13 producer imports required')
    for name,row in delta['files'].items():
        require(identity(name)==row['identity'] and sha(name)==row['sha256']
            and identity(name)==row['identity'] and row['size']==row['identity']['size'],
            'producer import changed before definitions')
        if Path(name).parent==prior_path.parent:
            expected=dict(catalog=str(RUNTIME/'source-bindings.json'),table='predecessor_sources',kind='existing-full-identity')
            require(same(row,bindings['predecessor_sources'][name]),'original qualified module identity differs')
        else:
            expected=dict(catalog=str(prior_path),table='references',kind='existing-bytes-new-current-identity')
            require(same(prior['references'][name],dict(bytes=row['size'],sha256=row['sha256'])),
                'producer original byte provenance differs')
        require(same(delta['provenance'][name],expected),'producer provenance class differs')
    IMPORT_DELTA_ROWS.update(delta['files'])
    reader_closure()
    IMPORT_OBSERVATIONS['before_factory_definitions']=dict(os.environ)
    def check_source(path):
        path=Path(path)
        require(str(path) not in historical,'historical copy cannot be imported as live source')
        if path.parent==RUNTIME:
            require(path.name in RUNTIME_SOURCES and sha(path)==RUNTIME_SOURCES[path.name],'unreviewed runtime import')
        else:
            row=IMPORT_DELTA_ROWS[str(path)] if str(path) in IMPORT_DELTA_ROWS else full[str(path)]
            require(identity(path)==row['identity'] and sha(path)==row['sha256'] and path.stat().st_size==row['size'],
                'historical imported source changed')
        return path
    for name in ['entry.py','imports.py','frozen.py']:check_source(RUNTIME/name)
    entry=load('entry',RUNTIME/'entry.py');factory=load('imports',RUNTIME/'imports.py');frozen=load('frozen',RUNTIME/'frozen.py')
    modules=factory.definitions(HASH,check_source)
    IMPORT_OBSERVATIONS['after_factory_definitions']=dict(os.environ)
    return entry,factory,frozen,modules


def readonly_policy(mode):
    """Fail closed on accidental workload calls or undeclared writes.

    This observes the reviewed Python code's audit events; it is not a general
    security sandbox for arbitrary native code.
    """
    require(mode in ['prepare','rehearse'],'exact read-only phase required')
    allowed={str(HERE/name) for name in ['plan.json','inputs.json','launch.json','preparation.json']} if mode=='prepare' else {str(WORK/'result.json')}
    state=dict(blocked_events=0,written_paths=[],created_directories=[])
    def blocked(message):
        state['blocked_events']+=1;raise RuntimeError(message)
    def audit(event,args):
        if event.startswith(('subprocess.','os.exec','os.posix_spawn')) or event in ['os.system','socket.connect','os.kill','os.killpg']:
            blocked('read-only rehearsal cannot launch workloads, network or signals')
        if event in ['os.remove','os.unlink','os.rmdir','os.rename','os.chmod','os.chown','os.truncate',
                     'os.utime','os.link','os.symlink','os.chdir','os.chroot']:
            blocked('read-only rehearsal cannot mutate existing paths')
        if event=='open':
            name,open_mode,flags=args
            if flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
                if not isinstance(name,(str,bytes)):blocked('unattributed writable descriptor')
                path=Path(os.fsdecode(name)).absolute()
                if str(path) not in allowed or path.resolve(strict=False)!=path:blocked('undeclared rehearsal output')
                if str(path) not in state['written_paths']:state['written_paths'].append(str(path))
        if event=='os.mkdir':
            name,permissions,directory_fd=args
            if mode!='rehearse' or directory_fd!=-1 or Path(os.fsdecode(name)).absolute()!=WORK:
                blocked('undeclared rehearsal directory')
            state['created_directories'].append(str(WORK))
    sys.addaudithook(audit)
    return state


def present(original,historical,frozen):
    """Presence is observed separately; it never creates a physical input row."""
    result={}
    for name in sorted(historical):
        guard();row=original['files'][name];actual=frozen.identity(name)
        require(same(actual,row['identity']) and stat.S_ISREG(actual['mode'])
            and actual['nlink']==1 and Path(name).resolve(strict=True)==Path(name),
            'original21 copy must still be present and unchanged during rehearsal')
        result[name]=actual
    require(len(result)==21,'exact21 original copy presence required');return result


def deny(names,apis):
    observed=[]
    for name in sorted(names):
        for label,callback in apis.items():
            try:callback(name)
            except KeyError as error:
                require(error.args==(name,),'unexpected dictionary error during denial')
            except RuntimeError as error:
                require(str(error) in ['historical proof copy has no current-file API','unfrozen hash input: '+name],
                    'unexpected error during physical denial')
            else:raise RuntimeError('historical copy was accepted by physical API: '+label)
            observed.append(dict(path=name,api=label,rejected=True))
    return observed


def runtime_absent():
    owner=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
    paths=[RUNTIME/'preflight-plan-01',RUNTIME/'installation-plan-01']
    paths.extend(owner/'.work'/('hir-options-hash-runtime-'+phase+'-04') for phase in ['preflight','installation'])
    for path in paths:require(not path.exists() and not path.is_symlink(),'runtime packet/WORK must remain absent')
    return list(map(str,paths))


def observed_main(callback):
    """Retain exact failure-time environments without creating a partial packet."""
    IMPORT_OBSERVATIONS['before_authentication']=dict(os.environ)
    try:callback()
    except BaseException as error:
        position=sys.argv.index('--passed-environment-json')
        report=dict(status='failed-read-only-attempt-no-qualification',error=repr(error),
            pid=os.getpid(),parent_pid=os.getppid(),observed_at=time.time(),
            passed_environment=json.loads(sys.argv[position+1]),
            import_environments=IMPORT_OBSERVATIONS,environment_at_failure=dict(os.environ),
            runtime_admission=False,retirement_authorized=False)
        data=encoded(report);require(len(data)<=256*2**10,'bounded failure environment observation')
        print(data.decode(),file=sys.stderr,end='',flush=True)
        raise
