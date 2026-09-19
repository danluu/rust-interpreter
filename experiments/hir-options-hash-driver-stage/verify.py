"""Independent saved-evidence audit of one compile and two hash-driver runs.

No controller/core import, process launch, provider probe, signal or workload.
The caller supplies the reviewed launch digest and actual explicit-wait launcher
record. All selected bytes are rehashed before the two pure parsers are loaded.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import struct
import sys
import time
from types import ModuleType

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
N=X/'.work/hir-options-hash-compiler-01'
S=N/'source'
HOST='aarch64-apple-darwin'
D2=S/'build'/HOST/'stage0'
E2=S/'build'/HOST/'stage1'
B3=N/'beta-sysroot'
ARTIFACTS=N/'native-controls/hash-driver-01'
WORK=ROOT/'.work/hir-options-hash-driver-01'
OUTER=ROOT/'.work/experiments/hir-options-hash-driver-supervisor-01'
OUT=ROOT/'.work/hir-options-hash-driver-independent-verification-01.json'
DRIVER=X/'experiments/hir-options-hash/controls/driver.rs'
FIXTURE=X/'experiments/hir-options-hash/controls/fixture.rs'
SOURCE_HASHES={DRIVER:'3953c595bb37a6c05661d9a399599bf5529b6a847629d2e1aa4c47eb8314605b',
    FIXTURE:'d7f59ad74eb839ba84ce5ef1e8493bdd6f36d0304f240c080582a17824bfbb3d'}
REVISION='4de35bdacef0e3cd18a66bc30b5459c19e09b118'
FIELDS=('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')
CHECKED={}

def require(ok,message):
    if not ok:raise RuntimeError(message)

def unique(pairs):
    result={}
    for key,value in pairs:
        require(key not in result,'duplicate JSON key');result[key]=value
    return result

def identity(path):
    s=Path(path).lstat();return {k:getattr(s,'st_'+k) for k in FIELDS}

def stamp(path):
    row=identity(path);return [row[k] for k in ('dev','ino','mode','size','mtime_ns','ctime_ns','nlink')]

def sha(path):
    path=Path(path);before=identity(path)
    require(path.resolve(strict=True)==path and stat.S_ISREG(before['mode']) and before['size']<=2**30,'bounded ordinary input: '+str(path))
    if str(path) in CHECKED and CHECKED[str(path)]['identity']==before:return CHECKED[str(path)]['sha256']
    with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW),'rb') as stream:
        require({k:getattr(os.fstat(stream.fileno()),'st_'+k) for k in FIELDS}==before,'opened input changed')
        digest=hashlib.file_digest(stream,'sha256').hexdigest()
        require({k:getattr(os.fstat(stream.fileno()),'st_'+k) for k in FIELDS}==before,'read input changed')
    require(identity(path)==before,'hashed input changed')
    CHECKED[str(path)]=dict(identity=before,sha256=digest);return digest

def raw(path,limit=2**20):
    path=Path(path);before=identity(path)
    require(path.resolve(strict=True)==path and stat.S_ISREG(before['mode']) and before['size']<=limit,'bounded ordinary read')
    data=path.read_bytes();require(identity(path)==before and len(data)==before['size'],'read changed')
    return data

def read(path):
    return json.loads(raw(path,256*2**20),object_pairs_hook=unique,
        parse_constant=lambda value:(_ for _ in ()).throw(ValueError(value)))

def encoded(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()

def frozen(path,freeze):
    path=Path(path);row=freeze['files'][str(path)]
    require(identity(path)==row['identity'] and row['size']==path.stat().st_size and sha(path)==row['sha256'],'frozen input differs: '+str(path))
    return path

def file_proof(path):
    return dict(sha256=sha(path),stamp=stamp(path))

def inventory(root):
    root=Path(root);require(root.resolve(strict=True)==root and root.is_dir(),'ordinary inventory root')
    result={}
    def failed(error):raise error
    for parent,dirs,files in os.walk(root,followlinks=False,onerror=failed):
        for name in dirs+files:
            path=Path(parent)/name;info=path.lstat();key=str(path.relative_to(root))
            require(len(result)<50000,'inventory member bound')
            if stat.S_ISLNK(info.st_mode):
                target=path.resolve(strict=True);require(target.is_relative_to(N),'provider link escapes namespace')
                result[key]=dict(kind='link',target=os.readlink(path),resolved=str(target),stamp=stamp(path))
            elif stat.S_ISREG(info.st_mode):result[key]=dict(kind='file',**file_proof(path))
            else:require(stat.S_ISDIR(info.st_mode),'special inventory entry');result[key]=dict(kind='directory')
    return result

def macho(path):
    """Independent bounded arm64 Mach-O dylib/rpath projection, no otool call."""
    data=raw(path,2**30);offset=0
    if data[:4] in (b'\xca\xfe\xba\xbe',b'\xca\xfe\xba\xbf'):
        require(len(data)>=8,'truncated fat header');count=struct.unpack_from('>I',data,4)[0]
        width=32 if data[3]==0xbf else 20
        require(0<count<32 and 8+count*width<=len(data),'fat architecture bounds')
        found=[];table_end=8+count*width
        for i in range(count):
            base=8+i*width
            start,length=struct.unpack_from('>QQ' if width==32 else '>II',data,base+8)
            alignment=struct.unpack_from('>I',data,base+(24 if width==32 else 16))[0]
            require(start>=table_end and length>=32 and start+length<=len(data)
                and alignment<=31 and start%(1<<alignment)==0,'fat slice range/table/alignment bounds')
            if width==32:require(struct.unpack_from('>I',data,base+28)[0]==0,'fat64 reserved field')
            if struct.unpack_from('>I',data,base)[0]==0x100000c:found.append((start,length))
        require(len(found)==1,'one arm64 slice required');start,length=found[0]
        data=data[start:start+length]
    require(offset+32<=len(data) and data[offset:offset+4]==b'\xcf\xfa\xed\xfe'
        and struct.unpack_from('<I',data,offset+4)[0]==0x100000c,'arm64 Mach-O required')
    count,size=struct.unpack_from('<II',data,offset+16);position=offset+32;end=position+size
    require(count<4096 and end<=len(data),'load command bounds');deps=[];rpaths=[]
    for _ in range(count):
        require(position+8<=end,'load header bounds');kind,width=struct.unpack_from('<II',data,position)
        require(width>=8 and width%8==0 and position+width<=end and kind!=0x27,'load width/alignment or DYLD_ENVIRONMENT')
        if kind in (0xc,0xd,0x80000018,0x8000001f,0x20,0x80000023,0x8000001c):
            minimum=12 if kind==0x8000001c else 24
            require(width>=minimum,'load fixed header bounds');start=struct.unpack_from('<I',data,position+8)[0]
            require(minimum<=start<width,'load string offset');value=data[position+start:position+width]
            require(b'\0' in value,'terminated load string');token=value.split(b'\0',1)[0].decode('utf-8','strict')
            require(token and all(ord(char)>=32 and ord(char)!=127 for char in token),'ordinary control-free load token')
            if kind!=0xd:(rpaths if kind==0x8000001c else deps).append(token)
        position+=width
    require(position==end and deps,'complete load command table');return deps,rpaths

def closure(binary,admitted):
    """Rebuild the recorded pure loader graph, including every search result."""
    result=dict(executable=str(binary),cwd=str(S),dyld_library_path='',files={},searches={},nodes={},system_libraries=[],static_only=True)
    active=set();systems=set()
    def route(token,loaded):
        if token.startswith('@loader_path/'):return loaded.parent/token[len('@loader_path/'):]
        if token.startswith('@executable_path/'):return binary.parent/token[len('@executable_path/'):]
        require(token.startswith('/'),'unsupported loader token');return Path(token)
    def present(path):
        exists=path.exists() or path.is_symlink();result['searches'][str(path)]=exists
        if exists:
            resolved=path.resolve(strict=True);require(resolved.is_relative_to(N),'loader route escapes namespace');sha(resolved);return resolved
        return None
    def visit(path,inherited=()):
        path=path.resolve(strict=True);context=(str(path),inherited)
        if context in active:return
        active.add(context);require(len(active)<=128,'loader graph bound')
        proof=file_proof(path)
        if path!=binary:require(admitted.get(str(path))==proof,'unadmitted loader provider')
        result['files'][str(path)]=proof;deps,rpaths=macho(path)
        result['nodes'][str(path)]=dict(dependencies=deps,rpaths=rpaths)
        expanded=tuple(str(route(token,path)) for token in rpaths)+inherited
        for token in deps:
            overrides=[S/Path(token).name]
            if token.startswith(('/usr/lib/','/System/Library/')):
                require(not any(present(candidate) is not None for candidate in overrides),'private system override');systems.add(token);continue
            candidates=list(overrides)
            if token.startswith('@rpath/'):candidates.extend(Path(base)/token[len('@rpath/'):] for base in expanded)
            else:candidates.append(route(token,path))
            found={p for candidate in candidates if (p:=present(candidate)) is not None}
            require(len(found)==1,'ambiguous or missing private loader route');target=next(iter(found))
            if target!=path:visit(target,expanded)
        require(file_proof(path)==proof,'loader image changed')
    visit(binary);result['system_libraries']=sorted(systems)
    result['system_assumption']='System dyld-cache images are bound to the producer platform; no private file-hash or dynamic-loader trace claim.'
    return result

def commands(plan):
    require(plan['roles']==dict(build_compiler=str(D2),build_sysroot=str(B3),runtime_compiler=str(E2),application_sysroot=str(E2)),'exact compiler roles')
    pair=plan['ordered_driver_pair'];require(type(pair) is list and len(pair)==2,'ordered driver pair')
    dylib,rmeta=map(Path,pair);require(dylib.parent==rmeta.parent==B3/'lib/rustlib'/HOST/'lib'
        and re.fullmatch(r'librustc_driver-[a-f0-9]+\.dylib',dylib.name) and rmeta==dylib.with_suffix('.rmeta'),'exact driver pair route')
    env=plan['environment'];require(env['TMPDIR']==str(ARTIFACTS/'tmp') and env['SDKROOT']==plan['sdk'],'owned temporary directory and SDK')
    require(set(env)<={'PATH','HOME','USER','LOGNAME','LANG','LC_ALL','TZ','TMPDIR','SDKROOT','PYTHONDONTWRITEBYTECODE','PYTHONNOUSERSITE','__CF_USER_TEXT_ENCODING'},'ambient driver environment')
    binary=ARTIFACTS/'hash-control-driver'
    compile_argv=[str(D2/'bin/rustc'),'--sysroot='+str(B3),'--edition=2024','--crate-name=hash_cache_control_driver','--print=link-args',str(DRIVER),
        '--extern','rustc_driver='+pair[0],'--extern','rustc_driver='+pair[1],'-Lnative='+str(E2/'lib'),'-Clinker='+plan['clang'],
        '-C','link-arg=-Wl,-rpath,'+str(E2/'lib'),'-o',str(binary)]
    return [dict(argv=compile_argv,cwd=str(S),environment=env|{'RUSTC_BOOTSTRAP':'1'}),
        *[dict(argv=[str(binary),str(E2),str(ARTIFACTS/'fixture.rs'),str(ARTIFACTS/mode),mode],cwd=str(S),
            environment=env|{'DYLD_PRINT_LIBRARIES':'1'}) for mode in ['serial','parallel']]]

def linker(data,plan):
    require(0<len(data)<=2**20 and data.endswith(b'\n') and data.count(b'\n')==1,'complete printed linker command')
    words=shlex.split(data.decode('utf-8','strict'));require(words[:1]==['env'],'printed linker env prefix');words=words[1:];removed=[];env={}
    while words[:1]==['-u']:
        require(len(words)>1 and re.fullmatch('[A-Za-z_][A-Za-z_0-9]*',words[1]),'linker env removal');removed.append(words[1]);words=words[2:]
    require(len(removed)==len(set(removed)),'duplicate linker env removal')
    while words and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*=.*',words[0],re.S):
        key,value=words.pop(0).split('=',1);require(key not in env,'duplicate linker env');env[key]=value
    require(words and words[0]==plan['clang'],'actual clang provider')
    def values(flag):return [words[i+1] for i,value in enumerate(words[:-1]) if value==flag]
    require(values('-o')==[str(ARTIFACTS/'hash-control-driver')] and values('-arch')==['arm64']
        and words.count(plan['ordered_driver_pair'][0])==1 and plan['ordered_driver_pair'][1] not in words
        and str(E2/'lib') in values('-L') and words.count('-Wl,-rpath,'+str(E2/'lib'))==1
        and env.get('SDKROOT')==plan['sdk'],'printed link roles/SDK')
    return dict(raw_sha256=hashlib.sha256(data).hexdigest(),argv=words,environment=env,removed=removed,observation_only=True)

def process_identity(row,command,parent,missing,role,strict=False):
    observed=row['identity'];pid=row['pid']
    if observed['ps_returncode']==0 and observed['ps'].strip():
        fields=observed['ps'].split(None,9)
        require(len(fields)==10 and list(map(int,fields[:3]))==[pid,parent,pid] and fields[8]=='??'
            and fields[9]==' '.join(command),'actual PID/parent/group/start/tty/argv')
        time.strptime(' '.join(fields[3:8]),'%a %b %d %H:%M:%S %Y')
    else:
        require(not strict and observed['ps_returncode']==1 and not observed['ps'].strip(),'unexplained missing PS observation')
        missing.append(dict(role=role,pid=pid,observation='ps',limitation='Contemporaneous PS identity unavailable; recorded launch is not an observed PID identity.'))
    if observed['cwd_returncode']==0:
        require(observed['cwd'].splitlines()==[f'p{pid}','fcwd','n'+str(S)],'actual working directory')
    else:
        require(not strict and observed['cwd_returncode']==1 and observed['cwd']=='','unexplained missing cwd observation')
        missing.append(dict(role=role,pid=pid,observation='cwd',limitation='Contemporaneous cwd unavailable; no observed cwd success inferred.'))

def samples(rows,plan):
    require(type(rows) is list and rows,'actual resource observations required')
    for row in rows:
        require(row['free_bytes']>=9*2**30 and row['namespace_allocated_bytes']<=14*2**30
            and row['evidence_allocated_bytes']<=256*2**20 and not row['allocation_errors']
            and row['evidence_root']==str(WORK) and row['evidence_roots']==plan['evidence_roots'],'actual resource gates')

def import_parsers(freeze):
    def load(name,path,dependencies=None):
        frozen(path,freeze);source=raw(path,2*2**20)
        require(hashlib.sha256(source).hexdigest()==freeze['files'][str(path)]['sha256'],'pure source bytes changed')
        missing=object();saved={key:sys.modules.get(key,missing) for key in (dependencies or {})}
        module=ModuleType(name);module.__file__=str(path);module.__package__=None
        try:
            sys.modules.update(dependencies or {});exec(compile(source,str(path),'exec'),module.__dict__)
        finally:
            for key,value in saved.items():
                if value is missing:sys.modules.pop(key,None)
                else:sys.modules[key]=value
        return module
    observed=load('_hash_verify_observations',ROOT/'experiments/hir-driver-observations/observations.py')
    return load('_hash_verify_loader_trace',ROOT/'experiments/hir-driver-observations/loader_trace.py',{'observations':observed})

def snapshots(freeze,terminal,launch):
    require(all(path.stat().st_size<=4*2**20 for path in [HERE/'snapshot-plan.json',WORK/'snapshot-plan.json',WORK/'source-snapshots.json']),'bounded snapshot documents')
    projection_plan=read(HERE/'snapshot-plan.json');projection=projection_plan['projection'];manifest=read(WORK/'source-snapshots.json')
    require(sha(HERE/'snapshot-plan.json')==sha(WORK/'snapshot-plan.json')==launch['snapshot_plan_sha256']==terminal['snapshot_plan_sha256']
        and sha(WORK/'source-snapshots.json')==terminal['source_snapshots_sha256'],'snapshot projection/manifest hashes')
    require(projection_plan['inputs_sha256']==sha(HERE/'inputs.json') and projection_plan['evidence_cap_bytes']==256*2**20
        and projection_plan['remaining_evidence_reservation_bytes']==32*2**20,'snapshot reservation policy')
    helper=ROOT/'experiments/bounded-proof-snapshots/proof_snapshots.py'
    require(projection_plan['limits']==dict(maximum_files=1024,maximum_file_bytes=64*2**20,maximum_logical_bytes=512*2**20,
        maximum_compressed_bytes=128*2**20,maximum_manifest_bytes=4*2**20)
        and projection_plan['helper']==dict(path=str(helper),sha256=freeze['files'][str(helper)]['sha256']),'qualified snapshot helper/policy')
    require(manifest['policy']==projection['policy']=='bounded-gzip-proof-snapshots-v1'
        and manifest['projection_sha256']==hashlib.sha256(encoded(projection)).hexdigest()
        and manifest['blobs']==projection['blobs'] and manifest['full_logical_readback'] is True and manifest['full_gzip_eof'] is True,'snapshot projection exactness')
    wanted=set(freeze['snapshot_inputs'])|{str(HERE/'inputs.json')}
    require(len(wanted)<=1024 and wanted==set(projection['files'])==set(manifest['files']),'complete logical snapshots')
    require(set(p.name for p in (WORK/'source-snapshots').iterdir())=={r['filename'] for r in projection['blobs'].values()},'complete snapshot blobs')
    logical=0
    for name,row in projection['files'].items():
        require(row['path']==name and row['size']<=64*2**20 and sha(name)==row['sha256'] and identity(name)==row['identity'],'snapshot original selected bytes')
        if name!=str(HERE/'inputs.json'):require(row==dict(path=name,**freeze['files'][name]),'snapshot frozen mapping')
        require(manifest['files'][name]==dict(path=str(WORK/'source-snapshots'/(row['sha256']+'.gz')),sha256=row['sha256'],size=row['size'],encoding='gzip'),'logical snapshot route')
        require(projection['blobs'][row['sha256']]['logical_bytes']==row['size'],'logical alias to physical blob size')
        logical+=row['size']
    require(logical<=512*2**20,'logical proof bound');compressed=0
    for digest,row in projection['blobs'].items():
        require(re.fullmatch('[a-f0-9]{64}',digest) and row['logical_sha256']==digest and row['filename']==digest+'.gz'
            and 0<=row['logical_bytes']<=64*2**20,'bounded gzip blob')
        path=WORK/'source-snapshots'/row['filename'];require(path.stat().st_nlink==1 and path.stat().st_size==row['compressed_bytes']
            and sha(path)==row['sha256'],'compressed blob hash');size=0;h=hashlib.sha256()
        with gzip.open(path,'rb') as stream:
            while block:=stream.read(min(2**20,row['logical_bytes']-size+1)):
                size+=len(block);require(size<=row['logical_bytes'],'gzip expansion bound');h.update(block)
        require(size==row['logical_bytes'] and h.hexdigest()==digest,'full logical hash and gzip EOF/CRC');compressed+=row['compressed_bytes']
    require(compressed==projection['compressed_bytes']==manifest['compressed_bytes'] and compressed<=128*2**20,'compressed proof bound')
    reservation=compressed+4096*len(wanted)+2*4*2**20+32*2**20
    admission=terminal['snapshot_admission'];require(reservation==projection_plan['projected_reservation_bytes']==admission['projected_reservation_bytes']
        and admission['existing_evidence_bytes']+reservation<=admission['evidence_cap_bytes']==256*2**20,'actual snapshot admission')
    return dict(logical_files=len(wanted),physical_blobs=len(projection['blobs']),logical_bytes=logical,compressed_bytes=compressed,full_gzip_eof_crc=True,full_logical_hashes=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--launch-sha256',required=True);parser.add_argument('--launcher-record',required=True,type=Path);args=parser.parse_args()
    require(Path.cwd()==ROOT and sys.dont_write_bytecode and not sys.flags.optimize and not OUT.exists(),'fresh explicit audit owner/Python')
    require(re.fullmatch('[a-f0-9]{64}',args.launch_sha256) and sha(HERE/'launch.json')==args.launch_sha256,'reviewed exact launch digest')
    require(args.launcher_record.is_relative_to(ROOT/'.work') and args.launcher_record.name=='record.json','explicit owned launcher record')
    started=time.time();launch=read(HERE/'launch.json');freeze=read(HERE/'inputs.json');plan=read(HERE/'plan.json')
    terminal=read(WORK/'receipt.json');result=read(WORK/'result.json');outer=read(OUTER/'status.json');dispatch=read(args.launcher_record)
    require(sha(HERE/'inputs.json')==launch['inputs_sha256']==terminal['inputs_sha256'] and sha(HERE/'plan.json')==freeze['plan_sha256']==launch['plan_sha256'],'launch/freeze/plan association')
    require(terminal['status']=='passed-awaiting-independent-audit' and result['status']=='hash-driver-observations-passed-awaiting-independent-audit'
        and sha(WORK/'result.json')==terminal['result_sha256'] and terminal['candidate_revision']==result['candidate_revision']==plan['candidate_revision']==REVISION
        and result['source_identity']==plan['source_identity'],'completed exact candidate stage')
    require(all(terminal[k] is False for k in ['hash_driver_qualified','application_qualified','performance_measurement','runtime_installation'])
        and result['application_qualified'] is result['performance_measurement'] is False,'pre-audit qualification scope')
    require(outer['status']=='finished' and outer['returncode']==0 and outer['child_pid']==terminal['pid'] and outer['supervisor_pid']==terminal['parent_pid']
        and outer['command']==launch['command'][6:] and outer['cwd']==str(ROOT)
        and outer['plan_sha256']==sha(OUTER/'plan.json') and outer['log_sha256']==sha(OUTER/'command.log'),'actual outer closure')
    require(outer['child_started_at']<=terminal['started_at']<=terminal['admitted_at']<=terminal['finished_at']<=outer['finished_at']
        and terminal['free_bytes_before']>=24*2**30 and terminal['free_bytes_after']>=9*2**30,'actual stage time/admission')
    require(dispatch['status']=='terminal-observed' and dispatch['returncode']==0 and dispatch['launcher_returncode']==0
        and dispatch['started_at']<=dispatch['launcher_finished_at']<=dispatch['finished_at']
        and outer['finished_at']<=dispatch['terminal_observed_at']<=dispatch['finished_at']
        and dispatch['outer_sha256']==sha(OUTER/'status.json') and dispatch['command']==launch['command']
        and dispatch['cwd']==str(ROOT) and dispatch['environment']==launch['environment'] and dispatch['launch_sha256']==args.launch_sha256
        and sha(dispatch['launcher_source_path'])==dispatch['launcher_source_sha256'],'explicit launcher completion')
    for stream in ['stdout','stderr']:require(sha(args.launcher_record.parent/stream)==dispatch[stream+'_sha256'],'launcher raw hash')
    handoff=read(args.launcher_record.parent/'stdout');require(handoff['supervisor_pid']==outer['supervisor_pid'] and handoff['directory']==str(OUTER),'launcher handoff')
    require(dispatch['supervisor_handoff']==handoff and dispatch['outer_status']==outer['status']
        and dispatch['supervisor_pid']==outer['supervisor_pid'] and dispatch['controller_pid']==terminal['pid']
        and dispatch['entry_free_bytes']>=24*2**30 and dispatch['maximum_wrapper_seconds']==30
        and dispatch['maximum_observation_seconds']==1800,'launcher actual terminal/admission policy')
    launcher_identity=dispatch['launcher_identity']
    require(launcher_identity['source']=='in-process observation' and launcher_identity['pid']==dispatch['launcher_pid']
        and launcher_identity['parent_pid']==dispatch['launcher_parent_pid'] and launcher_identity['cwd']==str(ROOT)
        and Path(launcher_identity['argv'][0]).resolve(strict=True)==Path(dispatch['launcher_source_path'])
        and launcher_identity['argv'][1:]==['--launch-sha256',args.launch_sha256]
        and dispatch['wrapper_identity_limitation']=='Popen PID retained; no separate contemporaneous wrapper ps/cwd probe.',
        'honest launcher/wrapper identity observations')
    require(len(freeze['files'])<=180000 and sum(r['size'] for r in freeze['files'].values())<=8*2**30,'full frozen closure bound')
    for name in freeze['files']:frozen(name,freeze)
    frozen(Path(__file__).resolve(),freeze)
    for name,row in freeze['links'].items():
        path=Path(name);require(path.is_symlink() and stamp(path)==row['stamp'] and os.readlink(path)==row['target']
            and str(path.resolve(strict=True))==row['resolved'],'frozen provider link')
    for name in freeze['absent_paths']:require(not Path(name).exists() and not Path(name).is_symlink(),'frozen absence')
    for name,resolved in plan['executor_routes'].items():require(str(Path(name).resolve(strict=True))==resolved,'executor route')
    require(set(plan['immutable_trees'])==set(map(str,[D2,E2,B3])),'complete immutable roots')
    for name,catalog in plan['immutable_trees'].items():require(inventory(name)==read(frozen(catalog,freeze)),'full provider tree membership/bytes')
    prior={'compiler':(X/'experiments/hir-options-hash/compiler-build-continuation-03',X/'.work/hir-options-hash-compiler-build-continuation-03'),
        'beta':(A/'experiments/hir-options-hash-beta-composition-08',A/'.work/hir-options-hash-beta-composition-08'),
        'native':(A/'experiments/hir-options-hash-native-controls-01',A/'.work/hir-options-hash-native-controls-01'),
        'run_make':(O/'experiments/hir-options-hash-run-make-stage-02',O/'.work/hir-options-hash-run-make-01')}
    require(set(plan['independent_audits'])==set(prior),'all four prerequisite audits')
    for name,(source,evidence) in prior.items():
        ref=plan['independent_audits'][name];audit=read(frozen(ref['path'],freeze));receipt=read(frozen(evidence/'receipt.json',freeze))
        require(sha(ref['path'])==ref['sha256'] and audit['status']=='verified' and receipt['status']=='passed'
            and audit['receipt_sha256']==sha(evidence/'receipt.json'),'passed exact prerequisite audit')
        inherited=read(frozen(source/'inputs.json',freeze));require(sha(frozen(source/'plan.json',freeze))==inherited['plan_sha256'],'predecessor plan hash')
        for path,row in inherited['files'].items():require(freeze['files'][path]['sha256']==row['sha256'],'complete inherited proof closure')
    preflight=read(HERE/'metadata-preflight.json')
    require(preflight['status']=='passed' and preflight['inputs_sha256']==sha(HERE/'inputs.json')
        and preflight['snapshot_plan_sha256']==launch['snapshot_plan_sha256']
        and preflight['workload_children']==0 and preflight['work_created'] is False
        and terminal['prerequisites']==preflight['prerequisites'],'retained prerequisite readback')
    for key,value in dict(compiler_actual_children=26,compiler_successful_children=25,beta_commands=19,
        run_make_top_level_commands=2,run_make_nested_commands=230).items():
        require(terminal['prerequisites'][key]==value,'prerequisite history counts')
    for source,digest in SOURCE_HASHES.items():require(sha(frozen(source,freeze))==digest,'unchanged driver/fixture source')
    wanted=commands(plan);require(plan['children']==wanted and launch['expected_children']==3 and launch['driver_processes']==2 and launch['contexts_per_process']==8,'exact three-child plan')
    require(result['compilation_count']==1 and result['driver_process_count']==2 and result['contexts_per_process']==8,'actual core process counts')
    missing=[];compiled=read(WORK/'compile/receipt.json')
    require(compiled['status']=='finished' and compiled['returncode']==0 and compiled['expected']==[0]
        and compiled['command']==wanted[0]['argv'] and compiled['cwd']==str(S) and compiled['environment']==wanted[0]['environment']
        and compiled['supervisor_pid']==terminal['pid'] and compiled['parent_pid']==terminal['parent_pid']
        and terminal['admitted_at']<=compiled['started_at']<=compiled['finished_at']<=terminal['finished_at']
        and sha(WORK/'compile/receipt.json')==result['compile_receipt_sha256'],'actual compile association')
    process_identity(compiled,wanted[0]['argv'],terminal['pid'],missing,'compile');samples(compiled['samples'],plan)
    output=raw(WORK/'compile/stdout');require(not raw(WORK/'compile/stderr') and sha(WORK/'compile/stdout')==compiled['stdout_sha256']
        and sha(WORK/'compile/stderr')==compiled['stderr_sha256'],'actual compile raw')
    require(linker(output,plan)==read(WORK/'linker-command.json') and sha(WORK/'linker-command.json')==result['linker_observation_sha256'],'actual printed linker proof')
    binary=ARTIFACTS/'hash-control-driver';require(binary.stat().st_nlink==1 and os.access(binary,os.X_OK)
        and sha(binary)==result['binary_sha256'] and sha(ARTIFACTS/'fixture.rs')==result['fixture_sha256']==SOURCE_HASHES[FIXTURE],'actual driver binary/fixture')
    graph=closure(binary,plan['runtime_private_providers']);require(graph==read(WORK/'driver-loader-closure.json')
        and sha(WORK/'driver-loader-closure.json')==result['closure_sha256'],'independent static loader closure')
    require({k:v for k,v in graph['files'].items() if k!=str(binary)}==plan['runtime_private_providers'],'exact private runtime set')
    trace=import_parsers(freeze);proofs=[];previous=compiled['finished_at'];pids=[compiled['pid']]
    require(len(result['processes'])==2,'exact two result references')
    for wanted_row,ref in zip(wanted[1:],result['processes'],strict=True):
        mode=wanted_row['argv'][-1];directory=WORK/mode;row=read(directory/'receipt.json')
        require(ref['mode']==row['mode']==mode and ref['pid']==row['pid'] and sha(directory/'receipt.json')==ref['receipt_sha256']
            and row['supervisor_pid']==terminal['pid'] and row['parent_pid']==terminal['parent_pid']
            and previous<=row['started_at']<=row['controller_finished_at']<=row['child_finished_at']<=terminal['finished_at'],'actual driver ownership/order/time')
        process_identity(row,wanted_row['argv'],terminal['pid'],missing,mode,strict=True);samples(row['samples'],plan)
        require(len(row['probes'])==2 and sorted(p.name for p in (directory/'probes').iterdir())==['000','001'],'only initial identity probes')
        for i,probe in enumerate(row['probes']):
            base=directory/'probes'/f'{i:03}';actual=read(base/'receipt.json');probe_env=dict(wanted_row['environment']);probe_env.pop('DYLD_PRINT_LIBRARIES')
            argv=(['/bin/ps','-p',str(row['pid']),'-o','pid=,ppid=,pgid=,lstart=,tty=,command='] if i==0 else ['/usr/sbin/lsof','-a','-p',str(row['pid']),'-d','cwd','-Fn'])
            require(probe['path']==str(base/'receipt.json') and probe['receipt']==actual and actual['status']=='finished' and actual['returncode']==0
                and actual['command']==argv and actual['cwd']==str(S) and actual['environment']==probe_env
                and actual['parent_pid']==terminal['pid'] and actual['process_group']==actual['pid'] and actual['terminal'] is None
                and row['started_at']<=actual['started_at']<=actual['finished_at']<=row['controller_finished_at'],'actual bounded identity probe')
            stdout=raw(base/'stdout');stderr=raw(base/'stderr')
            require(not stderr and sha(base/'stdout')==actual['stdout_sha256'] and sha(base/'stderr')==actual['stderr_sha256'],'identity probe raw')
            require((stdout.decode().strip() if i==0 else stdout.decode())==row['identity']['ps' if i==0 else 'cwd'],'probe to original identity binding')
        proof=trace.process(row,raw(directory/'stdout'),raw(directory/'stderr'),command=wanted_row['argv'],cwd=str(S),environment=wanted_row['environment'],allowed_private=set(graph['files']))
        require(proof==read(directory/'validated-readback.json') and sha(directory/'validated-readback.json')==ref['readback_sha256'],'complete nine-record/loader readback')
        proofs.append(proof);pids.append(row['pid']);previous=row['child_finished_at']
    require(len(set(pids))==3,'three distinct actual workload PIDs')
    require(set(p.name for p in WORK.iterdir())=={'receipt.json','result.json','compile','serial','parallel',
        'linker-command.json','driver-loader-closure.json','source-snapshots','source-snapshots.json','snapshot-plan.json'},'exact three-child evidence membership')
    require(set(p.name for p in (WORK/'compile').iterdir())=={'receipt.json','stdout','stderr'},'compile evidence membership')
    for mode in ['serial','parallel']:
        require(set(p.name for p in (WORK/mode).iterdir())=={'receipt.json','stdout','stderr','probes','validated-readback.json'},'driver evidence membership')
        for index in ['000','001']:
            require(set(p.name for p in (WORK/mode/'probes'/index).iterdir())=={'receipt.json','stdout','stderr'},'probe evidence membership')
    snapshot_proof=snapshots(freeze,terminal,launch)
    artifacts=inventory(ARTIFACTS)
    for path,row in CHECKED.items():require(identity(path)==row['identity'],'audit input changed before completion')
    report=dict(status='verified',receipt_sha256=sha(WORK/'receipt.json'),result_sha256=sha(WORK/'result.json'),
        launch_sha256=args.launch_sha256,inputs_sha256=sha(HERE/'inputs.json'),snapshot_plan_sha256=sha(HERE/'snapshot-plan.json'),
        candidate_revision=REVISION,source_identity=plan['source_identity'],actual_children=3,compilation_count=1,driver_process_count=2,
        contexts_per_process=8,stdout_records_per_process=9,child_pids=pids,processes=proofs,unavailable_contemporaneous_observations=missing,
        launcher_identity=launcher_identity,wrapper_identity_limitation=dispatch['wrapper_identity_limitation'],
        frozen_files=len(freeze['files']),frozen_bytes=sum(r['size'] for r in freeze['files'].values()),frozen_links=len(freeze['links']),
        full_frozen_byte_rehash=True,full_provider_inventories=True,static_and_actual_loaders_verified=True,compressed_snapshots=snapshot_proof,
        artifacts=artifacts,hash_driver_qualified=True,application_qualified=False,performance_measurement=False,runtime_installation=False,
        interpretation='Each serial/parallel process is independently checked. Hashes are not compared across modes. Printed linker command is not a separately observed linker PID. System images retain the stated dyld-cache assumption.',
        started_at=started,finished_at=time.time(),verifier_sha256=sha(Path(__file__).resolve()),
        execution='Saved evidence and current-file reads only; no process, compiler, provider, controller or driver execution.')
    with OUT.open('x') as stream:json.dump(report,stream,indent=2,sort_keys=True);stream.write('\n')
    print(json.dumps(dict(path=str(OUT),sha256=sha(OUT),actual_children=3,contexts_per_process=8)))

if __name__=='__main__':main()
