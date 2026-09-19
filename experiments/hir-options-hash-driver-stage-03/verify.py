"""Independent saved-evidence audit of one compile and two hash-driver runs.

No controller/core import, process launch, provider probe, signal or workload.
The caller supplies the reviewed launch digest and actual explicit-wait launcher
record. All selected bytes are rehashed before the two pure parsers are loaded.
"""
import argparse
import ast
import copy
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import stat
import struct
import sys
import time
from types import ModuleType

HERE=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/hir-options-hash-driver-stage-03')
ROOT=HERE.parents[1]
ORIGINAL_VERIFIER=dict(path=str(ROOT/'experiments/hir-options-hash-driver-stage-02/verify.py'),
    sha256='cbff690675b8697855bb87b0e09d9b77495fc0b8968855301e1a88612ec62a3f')
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
N=X/'.work/hir-options-hash-compiler-01'
S=N/'source'
HOST='aarch64-apple-darwin'
D2=S/'build'/HOST/'stage0'
E2=S/'build'/HOST/'stage1'
B3=N/'beta-sysroot'
NATIVE_SOURCE=A/'experiments/hir-options-hash-native-controls-03'
NATIVE_WORK=A/'.work/hir-options-hash-native-controls-03'
RECON_SOURCE=A/'experiments/hir-options-hash-native-reconciliation-01'
RECON_WORK=A/'.work/hir-options-hash-native-controls-reconciliation-01'
NATIVE_FAILURE_AUDIT=dict(path=str(A/'.work/native-controls-failure-verification-03.json'),
    sha256='1058d64e64d75748a3da12115a8400a01daa5cd499b39b09c8d29520eaab4f24')
ARTIFACTS=N/'hash-driver-02'
WORK=ROOT/'.work/hir-options-hash-driver-02'
OUTER=ROOT/'.work/experiments/hir-options-hash-driver-supervisor-02'
OUT=ROOT/'.work/hir-options-hash-driver-independent-verification-02.json'
DRIVER=X/'experiments/hir-options-hash/controls/driver-v2.rs'
FIXTURE=X/'experiments/hir-options-hash/controls/fixture.rs'
SOURCE_HASHES={DRIVER:'17ce949e8005bc185245a444a3dfc046944c1f2d5bc7297ae8f1939d25a779e9',
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

def audit_json_bytes(value):
    """Bound the canonical representation before extending its byte buffer."""
    pending=[(value,0)];nodes=0
    while pending:
        item,depth=pending.pop();nodes+=1
        require(nodes<=4_000_000 and depth<=64,'bounded audit JSON structure required')
        kind=type(item)
        if kind is dict:
            require(all(type(key) is str for key in item),'JSON object keys must be strings')
            pending.extend((child,depth+1) for child in item.values())
        elif kind is list:pending.extend((child,depth+1) for child in item)
        elif kind is float:require(math.isfinite(item),'finite JSON numbers required')
        else:require(kind in (str,int,bool,type(None)),'ordinary JSON values required')
    output=bytearray()
    encoder=json.JSONEncoder(sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
    for piece in encoder.iterencode(value):
        data=piece.encode('utf-8');require(len(output)+len(data)+1<=64*2**20,'canonical audit JSON exceeds bound')
        output.extend(data)
    output.extend(b'\n')
    return bytes(output)

def complete_file_table(document, *, expected_base):
    """Independently authenticate and reconstruct the single-level file table.

    This deliberately does not import the producer's file-table helper. The
    stored base and delta remain selected proof bytes; later frozen() checks
    still verify every reconstructed file against the live ordinary input.
    """
    def canonical_path(name):
        require(type(name) is str and name.startswith('/') and not name.startswith('//') and name!='/'
            and str(Path(name))==name and '..' not in Path(name).parts
            and not any(ord(char)<32 or ord(char)==127 for char in name)
            and len(name.encode('utf-8'))<=4096,'canonical bounded file-table path required')
    document=json.loads(audit_json_bytes(document),object_pairs_hook=unique)
    require(type(document) is dict and {'file_table_base','file_table_integrity'}<=set(document),
        'compact file-table representation required')
    reference=document['file_table_base']
    require(type(expected_base) is dict and set(expected_base)=={'path','sha256'}
        and type(expected_base['path']) is str and type(expected_base['sha256']) is str
        and re.fullmatch('[a-f0-9]{64}',expected_base['sha256']), 'explicit expected base required')
    require(type(reference) is dict and encoded(reference)==encoded(expected_base),'exact expected file-table base required')
    canonical_path(reference['path'])
    delta=document['files'];integrity=document['file_table_integrity']
    require(type(delta) is dict and len(delta)<=180000 and reference['path'] in delta,'bounded delta with base-file row required')
    require(type(integrity) is dict and set(integrity)=={'sha256','count','total_bytes'}
        and type(integrity['count']) is int and 0<=integrity['count']<=180000
        and type(integrity['total_bytes']) is int and 0<=integrity['total_bytes']<=8*2**30
        and type(integrity['sha256']) is str and re.fullmatch('[a-f0-9]{64}',integrity['sha256']),
        'bounded typed full-table integrity required')
    path=Path(reference['path']);directories=[];routes=[];descriptor=None
    flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW
    directory_identity=lambda s:(s.st_dev,s.st_ino,s.st_mode)
    file_identity=lambda s:{key:getattr(s,'st_'+key) for key in FIELDS}
    try:
        directories.append(os.open('/',flags))
        for part in path.parts[1:-1]:
            parent=directories[-1];child=os.open(part,flags,dir_fd=parent);directories.append(child)
            observed=directory_identity(os.fstat(child));require(stat.S_ISDIR(observed[2]),'ordinary base ancestor required')
            routes.append((parent,part,child,observed))
        parent=directories[-1];before=file_identity(os.stat(path.name,dir_fd=parent,follow_symlinks=False))
        require(stat.S_ISREG(before['mode']) and before['size']<=64*2**20,'bounded ordinary base JSON required')
        descriptor=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
        require(file_identity(os.fstat(descriptor))==before,'base changed while opening')
        pieces=[];size=0;hasher=hashlib.sha256()
        while True:
            block=os.read(descriptor,min(2**20,64*2**20+1-size))
            if not block:break
            size+=len(block);require(size<=64*2**20,'base exceeded read bound');pieces.append(block);hasher.update(block)
        require(size==before['size'] and hasher.hexdigest()==reference['sha256']
            and file_identity(os.fstat(descriptor))==before
            and file_identity(os.stat(path.name,dir_fd=parent,follow_symlinks=False))==before,'complete base bytes or identity differ')
        for parent,name,held,observed in routes:
            require(directory_identity(os.fstat(held))==observed
                and directory_identity(os.stat(name,dir_fd=parent,follow_symlinks=False))==observed,'base ancestor route changed')
        base=json.loads(b''.join(pieces),object_pairs_hook=unique,
            parse_constant=lambda value:(_ for _ in ()).throw(ValueError(value)))
        base=json.loads(audit_json_bytes(base),object_pairs_hook=unique)
        require(type(base) is dict and not {'file_table_base','file_table_integrity'}&set(base)
            and type(base.get('files')) is dict and reference['path'] not in base['files'],'ordinary nonnested base required')
        require(not set(base['files'])&set(delta) and len(base['files'])+len(delta)<=180000,'disjoint bounded file-table extension required')
        require(encoded(delta[reference['path']])==encoded(dict(size=size,sha256=reference['sha256'],identity=before)),
            'base-file identity must remain in delta')
        result=copy.deepcopy(document);files=base['files']|result['files'];total=0
        for name,row in files.items():
            canonical_path(name)
            require(type(row) is dict and set(row)=={'sha256','size','identity'}
                and type(row['size']) is int and 0<=row['size']<=2**30
                and type(row['sha256']) is str and re.fullmatch('[a-f0-9]{64}',row['sha256']), 'exact typed file row required')
            ident=row['identity']
            require(type(ident) is dict and set(ident)==set(FIELDS)
                and all(type(ident[key]) is int and ident[key]>=0 for key in FIELDS)
                and ident['ino']>0 and ident['nlink']>0 and stat.S_ISREG(ident['mode'])
                and ident['size']==row['size'],'exact ordinary seven-field file identity required')
            total+=row['size'];require(total<=8*2**30,'expanded declared bytes exceed bound')
        canonical=audit_json_bytes(files)
        require(encoded(integrity)==encoded(dict(sha256=hashlib.sha256(canonical).hexdigest(),count=len(files),total_bytes=total)),
            'complete reconstructed file-table integrity differs')
        for value,selection_files in [(base,base['files']),(result,files)]:
            require(type(value.get('links')) is dict and type(value.get('absent_paths')) is list
                and type(value.get('snapshot_inputs')) is list,'complete selection/route metadata required')
            for name in value['links']:canonical_path(name)
            for key in ['absent_paths','snapshot_inputs']:
                for name in value[key]:canonical_path(name)
                require(len(value[key])==len(set(value[key])),'duplicate absence or selected input')
            require(set(value['snapshot_inputs'])<=set(selection_files) and not set(selection_files)&set(value['links'])
                and not (set(selection_files)|set(value['links']))&set(value['absent_paths']),'complete disjoint file/link/absence selection required')
        result['files']=files
        del result['file_table_base'];del result['file_table_integrity']
        require(file_identity(os.fstat(descriptor))==before and identity(path)==before
            and path.resolve(strict=True)==path,'base changed during full reconstruction')
        for parent,name,held,observed in routes:
            require(directory_identity(os.fstat(held))==observed
                and directory_identity(os.stat(name,dir_fd=parent,follow_symlinks=False))==observed,
                'base ancestor changed during full reconstruction')
        return result
    finally:
        if descriptor is not None:os.close(descriptor)
        for descriptor in reversed(directories):os.close(descriptor)


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

def workload_identity(row,role,finished):
    observed=row['identity']
    ps_start=(' '.join(observed['ps'].split(None,9)[3:8])
        if observed['ps_returncode']==0 and observed['ps'].strip() else None)
    return dict(role=role,pid=row['pid'],observed_ps_start=ps_start,
        started_at=row['started_at'],finished_at=finished)

def distinct_workloads(rows):
    require(len(rows)==3 and len({row['role'] for row in rows})==3,'three independently recorded workload roles')
    for index,row in enumerate(rows):
        for earlier in rows[:index]:
            if earlier['pid']==row['pid']:
                require(earlier['finished_at']<=row['started_at'],'reused numeric PID has overlapping command lifetimes')
                if earlier['observed_ps_start'] is not None and row['observed_ps_start'] is not None:
                    require(earlier['observed_ps_start']!=row['observed_ps_start'],'reused numeric PID lacks distinct observed process starts')

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

def snapshot_helper_qualification(freeze):
    source=A/'experiments/bounded-proof-snapshots-v2'
    controls=A/'experiments/bounded-proof-snapshot-controls-v2-01'
    work=A/'.work/bounded-proof-snapshot-controls-v2-01'
    audit_path=A/'.work/proof-snapshot-controls-v2-independent-verification-01.json'
    inputs=read(frozen(controls/'inputs.json',freeze));launch=read(frozen(controls/'launch.json',freeze))
    terminal=read(frozen(work/'receipt.json',freeze));result=read(frozen(work/'result.json',freeze))
    audit=read(frozen(audit_path,freeze));child=read(frozen(work/'command/receipt.json',freeze))
    require(len(inputs['files'])==14,'complete original snapshot control inputs')
    for name,row in inputs['files'].items():
        path=frozen(name,freeze)
        require(sha(path)==row['sha256'] and stamp(path)==row['stamp'],'original snapshot control source/input association')
    for name,resolved in inputs['routes'].items():
        require(str(Path(name).resolve(strict=True))==resolved and resolved in inputs['files'],
            'original snapshot control executor/input routes')
    names=[]
    for name in ['proof_snapshots.py','test_proof_snapshots.py','test_reference_reuse.py']:
        path=frozen(source/name,freeze)
        require(inputs['files'][str(path)]['sha256']==sha(path),'snapshot helper differs from tested source')
        if name.startswith('test_'):
            for cls in ast.parse(raw(path),filename=str(path)).body:
                if isinstance(cls,ast.ClassDef):
                    names.extend(path.stem+'.'+cls.name+'.'+test.name for test in cls.body
                        if isinstance(test,ast.FunctionDef) and test.name.startswith('test_'))
    names=sorted(names)
    require(len(names)==len(set(names))==22 and names==inputs['expected_names']==result['expected_names'],
        'exact twenty-two original and reference snapshot controls')
    require(terminal['status']==result['status']=='passed' and audit['status']=='verified'
        and terminal['controls_passed']==result['tests_run']==audit['controls']==launch['controls']==22
        and terminal['inputs_sha256']==launch['inputs_sha256']==sha(controls/'inputs.json')
        and terminal['result_sha256']==audit['result_sha256']==sha(work/'result.json')
        and audit['receipt_sha256']==sha(work/'receipt.json')
        and all(result[key]==0 for key in ['failures','errors','skipped','expected_failures',
            'unexpected_successes','child_processes','compiler_calls']), 'actual qualified snapshot helper')
    require(terminal['commands']==[dict(path=str(work/'command/receipt.json'),pid=child['pid'],sha256=sha(work/'command/receipt.json'))]
        and child['status']=='finished' and child['returncode']==0 and child['command']==inputs['command']
        and child['cwd']==str(source) and child['environment']==inputs['environment']
        and child['supervisor_pid']==terminal['pid'] and child['parent_pid']==terminal['parent_pid']
        and terminal['admitted_at']<=child['started_at']<=child['finished_at']<=terminal['finished_at'],
        'actual snapshot test command association')
    for stream in ['stdout','stderr']:
        path=frozen(work/'command'/stream,freeze)
        require(sha(path)==child[stream+'_sha256']==audit['raw_sha256'][stream],'snapshot control raw bytes')
    stderr=raw(work/'command/stderr').decode('utf-8','strict')
    actual=re.findall(r'^test_[A-Za-z0-9_]+ \(([^)]+)\) \.\.\. ok$',stderr,re.M)
    require(not raw(work/'command/stdout') and sorted(actual)==names
        and re.search(r'^Ran 22 tests in [0-9.]+s\n\nOK\n$',stderr,re.M), 'actual snapshot control names and completion')
    return dict(helper_sha256=sha(source/'proof_snapshots.py'),controls=22,audit_sha256=sha(audit_path))

def file_table_helper_qualification(freeze):
    source=ROOT/'experiments/frozen-file-table-delta-01'
    controls=ROOT/'experiments/frozen-file-table-delta-controls-01'
    work=ROOT/'.work/frozen-file-table-delta-controls-01'
    audit_path=ROOT/'.work/frozen-file-table-delta-controls-independent-verification-01.json'
    inputs=read(frozen(controls/'inputs.json',freeze));launch=read(frozen(controls/'launch.json',freeze))
    terminal=read(frozen(work/'receipt.json',freeze));result=read(frozen(work/'result.json',freeze))
    audit=read(frozen(audit_path,freeze));child=read(frozen(work/'command/receipt.json',freeze))
    for name,row in inputs['files'].items():
        path=frozen(name,freeze)
        require(sha(path)==row['sha256'] and stamp(path)==row['stamp'],'original file-table control input association')
    for name,resolved in inputs['routes'].items():
        require(str(Path(name).resolve(strict=True))==resolved and resolved in inputs['files'],
            'original file-table control executor/input routes')
    names=[]
    for name in ['file_table.py','test_file_table.py']:
        path=frozen(source/name,freeze)
        require(inputs['files'][str(path)]['sha256']==sha(path),'file-table helper differs from tested source')
        if name.startswith('test_'):
            for cls in ast.parse(raw(path),filename=str(path)).body:
                if isinstance(cls,ast.ClassDef):
                    names.extend(path.stem+'.'+cls.name+'.'+test.name for test in cls.body
                        if isinstance(test,ast.FunctionDef) and test.name.startswith('test_'))
    names=sorted(names)
    require(len(names)==len(set(names))==29 and names==inputs['expected_names']==result['expected_names']
        and names==sorted(audit['exact_names']),'exact twenty-nine file-table controls')
    require(terminal['status']==result['status']=='passed' and audit['status']=='verified'
        and terminal['controls_passed']==result['tests_run']==audit['controls']==launch['controls']==29
        and terminal['inputs_sha256']==launch['inputs_sha256']==sha(controls/'inputs.json')
        and terminal['result_sha256']==audit['result_sha256']==sha(work/'result.json')
        and audit['receipt_sha256']==sha(work/'receipt.json')
        and all(type(result[key]) is int and result[key]==0 for key in ['failures','errors','skipped',
            'expected_failures','unexpected_successes','child_processes','compiler_calls']), 'actual qualified file-table helper')
    require(terminal['commands']==[dict(path=str(work/'command/receipt.json'),pid=child['pid'],sha256=sha(work/'command/receipt.json'))]
        and child['status']=='finished' and type(child['returncode']) is int and child['returncode']==0
        and child['command']==inputs['command'] and child['cwd']==str(source) and child['environment']==inputs['environment']
        and child['supervisor_pid']==terminal['pid'] and child['parent_pid']==terminal['parent_pid']
        and terminal['admitted_at']<=child['started_at']<=child['finished_at']<=terminal['finished_at'],
        'actual file-table test command association')
    for stream in ['stdout','stderr']:
        path=frozen(work/'command'/stream,freeze)
        require(sha(path)==child[stream+'_sha256']==audit['raw_sha256'][stream],'file-table control raw bytes')
    stderr=raw(work/'command/stderr').decode('utf-8','strict')
    actual=re.findall(r'^test_[A-Za-z0-9_]+ \(([^)]+)\) \.\.\. ok$',stderr,re.M)
    require(not raw(work/'command/stdout') and sorted(actual)==names
        and re.search(r'^Ran 29 tests in [0-9.]+s\n\nOK\n$',stderr,re.M),'actual file-table control names and completion')
    return dict(controls=29,receipt_sha256=sha(work/'receipt.json'),result_sha256=sha(work/'result.json'),
        audit=dict(path=str(audit_path),sha256=sha(audit_path)),
        helper=dict(path=str(source/'file_table.py'),sha256=sha(source/'file_table.py')))

def ordinary_snapshot_route(path,directory=False):
    path=Path(path)
    require(path.is_absolute() and '..' not in path.parts and path.resolve(strict=True)==path,'canonical snapshot route')
    for ancestor in path.parents:
        require(stat.S_ISDIR(ancestor.lstat().st_mode),'snapshot ancestor must be an ordinary directory')
    info=identity(path)
    require(stat.S_ISDIR(info['mode']) if directory else stat.S_ISREG(info['mode']) and info['nlink']==1,
        'ordinary single-link snapshot file or directory')
    return info

def snapshot_blob(path,row):
    path=Path(path);before=ordinary_snapshot_route(path)
    require(before['size']==row['compressed_bytes'] and sha(path)==row['sha256'],'compressed snapshot bytes')
    size=0;digest=hashlib.sha256()
    with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW),'rb') as raw_stream:
        require({k:getattr(os.fstat(raw_stream.fileno()),'st_'+k) for k in FIELDS}==before,'opened snapshot identity')
        with gzip.GzipFile(fileobj=raw_stream,mode='rb') as stream:
            while block:=stream.read(min(2**20,row['logical_bytes']-size+1)):
                size+=len(block);require(size<=row['logical_bytes'],'gzip expansion bound');digest.update(block)
        require({k:getattr(os.fstat(raw_stream.fileno()),'st_'+k) for k in FIELDS}==before,'read snapshot identity')
    require(size==row['logical_bytes'] and digest.hexdigest()==row['logical_sha256']
        and ordinary_snapshot_route(path)==before,'full snapshot logical SHA and gzip EOF/CRC')

def verified_reference(ref,freeze):
    require(set(ref)=={'path','sha256'} and re.fullmatch('[a-f0-9]{64}',ref['sha256']), 'exact frozen proof reference')
    path=frozen(ref['path'],freeze);require(sha(path)==ref['sha256'],'referenced proof bytes')
    return read(path)

def canonical_inherited_record(row):
    """Normalize only the two actual historical file-record encodings.

    Stamp order is dev, ino, mode, size, mtime_ns, ctime_ns, nlink.  Retain
    every identity field; matching only content SHA and size is insufficient.
    No filesystem access, coercion, record mutation or aliasing is performed.
    """
    require(type(row) is dict and set(row) in ({'sha256','stamp'},{'sha256','size','identity'}),
        'exact historical file-record schema required')
    require(type(row['sha256']) is str and re.fullmatch('[a-f0-9]{64}',row['sha256']),
        'lowercase SHA-256 file-record digest required')
    if 'stamp' in row:
        values=row['stamp']
        require(type(values) is list and len(values)==7 and all(type(value) is int for value in values),
            'exact seven-integer historical stamp required')
        info=dict(zip(('dev','ino','mode','size','mtime_ns','ctime_ns','nlink'),values,strict=True))
        size=info['size']
    else:
        require(type(row['size']) is int and type(row['identity']) is dict
            and set(row['identity'])==set(FIELDS), 'exact canonical size and complete identity required')
        info=dict(row['identity']);size=row['size']
    require(all(type(info[key]) is int for key in FIELDS), 'integer file identity fields required')
    require(info['dev']>=0 and info['ino']>0 and 0<=info['mode']<=0o177777 and stat.S_ISREG(info['mode'])
        and info['nlink']>=1 and info['mtime_ns']>=0 and info['ctime_ns']>=0
        and 0<=size<=2**30 and size==info['size'], 'bounded ordinary file identity required')
    return dict(sha256=row['sha256'],size=size,identity={key:info[key] for key in FIELDS})

def inherited_inputs(source,freeze):
    inherited=read(frozen(source/'inputs.json',freeze))
    require(sha(frozen(source/'plan.json',freeze))==inherited['plan_sha256'],'predecessor plan hash')
    catalogs=[inherited]
    if 'base_inputs' in inherited:
        require(source==RECON_SOURCE and inherited['base_inputs']==dict(path=str(NATIVE_SOURCE/'inputs.json'),
            sha256='8569abb81a61e34b6b5a892116af5218557ceb0436ab8dbf8a31f2aec55b1b1d'), 'exact native reconciliation base')
        base=verified_reference(inherited['base_inputs'],freeze)
        require('base_inputs' not in base and sha(frozen(NATIVE_SOURCE/'plan.json',freeze))==base['plan_sha256'],
            'one immutable original native input catalog')
        catalogs.append(base)
    for catalog in catalogs:
        for path,row in catalog['files'].items():
            current=freeze['files'].get(path)
            require(type(current) is dict and set(current)=={'sha256','size','identity'},
                'current inherited input must retain the canonical complete row')
            require(encoded(canonical_inherited_record(current))==encoded(canonical_inherited_record(row)),
                'complete typed inherited SHA/size/identity closure')
        for path,row in catalog.get('links',{}).items():
            require(freeze['links'].get(path)==row,'complete inherited provider link closure')
        require(set(catalog.get('absent_paths',[]))<=set(freeze['absent_paths']),
            'complete inherited absence guards')
    return inherited

def verified_native_reconciliation(freeze,plan):
    """Keep the failed command owner distinct from the passed read-only reader."""
    terminal=read(frozen(RECON_WORK/'receipt.json',freeze))
    result=read(frozen(RECON_WORK/'native-controls.json',freeze))
    original=read(frozen(NATIVE_WORK/'receipt.json',freeze))
    native_plan=read(frozen(NATIVE_SOURCE/'plan.json',freeze))
    recon_plan=read(frozen(RECON_SOURCE/'plan.json',freeze))
    inherited=inherited_inputs(RECON_SOURCE,freeze)
    audit=verified_reference(plan['independent_audits']['native'],freeze)
    error="ValueError('wrong-B3 failure is not compiler metadata incompatibility')"
    require(sha(NATIVE_WORK/'receipt.json')=='76fe70afd8eb6486b445e39366de2dd1ffd52ed9578e63203dc7cf74a679a272'
        and original['status']=='failed' and original['error']==error and len(original['commands'])==20
        and not (NATIVE_WORK/'native-controls.json').exists() and not (NATIVE_WORK/'native-controls.json').is_symlink(),
        'original late-parser failure remains unchanged and result absent')
    failure=verified_reference(NATIVE_FAILURE_AUDIT,freeze)
    require(failure['status']=='verified-retained-failure' and failure['receipt_sha256']==sha(NATIVE_WORK/'receipt.json')
        and failure['failure']==error and failure['children']==20 and failure['historical_failed_children']==11
        and failure['total_actual_native_children']==31 and failure['qualified_native_children']==0
        and failure['native_roles_and_behavior_qualified'] is False and failure['source_restored'] is True
        and failure['frozen_parser_rejection_reproduced'] is True,'honest original failure audit')
    command_evidence=dict(source=str(NATIVE_SOURCE),evidence=str(NATIVE_WORK),
        receipt_sha256=sha(NATIVE_WORK/'receipt.json'),inputs_sha256=sha(NATIVE_SOURCE/'inputs.json'),
        plan_sha256=sha(NATIVE_SOURCE/'plan.json'),snapshot_plan_sha256=sha(NATIVE_SOURCE/'snapshot-plan.json'),
        status='failed',error=error,commands=original['commands'],failure_audit=NATIVE_FAILURE_AUDIT)
    require(terminal['status']=='passed' and terminal['read_only_reconciliation'] is True and terminal['commands']==[]
        and terminal['actual_workload_children']==0 and terminal['saved_actual_children']==20
        and terminal['historical_failed_children']==11 and terminal['native_roles_and_behavior_qualified'] is True
        and terminal['result_sha256']==sha(RECON_WORK/'native-controls.json')
        and terminal['inputs_sha256']==sha(RECON_SOURCE/'inputs.json')
        and terminal['plan_sha256']==inherited['plan_sha256']==sha(RECON_SOURCE/'plan.json')
        and audit['status']=='verified' and audit['receipt_sha256']==sha(RECON_WORK/'receipt.json')
        and audit['result_sha256']==sha(RECON_WORK/'native-controls.json')
        and original['finished_at']<=terminal['started_at']<=terminal['admitted_at']<=terminal['finished_at'],
        'separate completed zero-workload native reconciliation')
    require(recon_plan['read_only_reconciliation'] is True and recon_plan['actual_workload_children']==0
        and recon_plan['reconciliation_evidence_roots']==sorted(set(native_plan['evidence_roots'])|{str(RECON_WORK)})
        and set(recon_plan['reconciliation_evidence_roots'])<=set(plan['evidence_roots'])
        and result['status']=='native-roles-and-behavior-qualified'
        and result['source_restored'] is original['source_restored'] is True
        and all(result[key] is False for key in ['hash_driver_qualified','run_make_qualified','application_qualified']),
        'reconciliation scope and complete aggregate evidence accounting')
    require(terminal['command_evidence']==result['command_evidence']==recon_plan['command_evidence']==command_evidence
        and result['qualified_native_children']==20 and result['total_actual_native_children']==31
        and result['history']==original['commands'][:18] and result['wrong_B3_commands']==original['commands'][18:],
        'complete original twenty-command association without rerun')
    reconciliation=terminal['reconciliation']
    require(set(reconciliation)=={'source','base_inputs','original_parser','parser','parser_controls','failure_audit'}
        and reconciliation==result['reconciliation']==recon_plan['reconciliation']
        and reconciliation['source']==str(RECON_SOURCE) and reconciliation['base_inputs']==inherited['base_inputs']
        and reconciliation['failure_audit']==NATIVE_FAILURE_AUDIT
        and reconciliation['original_parser']==dict(path=str(NATIVE_SOURCE/'observations.py'),sha256=sha(frozen(NATIVE_SOURCE/'observations.py',freeze)))
        and reconciliation['parser']==dict(path=str(RECON_SOURCE/'wrong_beta.py'),sha256=sha(frozen(RECON_SOURCE/'wrong_beta.py',freeze))),
        'original rejected parser and distinct corrected parser provenance')
    controls=reconciliation['parser_controls'];control_source=Path(controls['source']);control_work=Path(controls['evidence'])
    require(set(controls)=={'source','evidence','receipt_sha256','result_sha256','controls','audit'}
        and control_source==A/'experiments/native-wrong-beta-controls-01'
        and control_work==A/'.work/native-wrong-beta-controls-01'
        and controls['audit']==dict(path=str(A/'.work/native-wrong-beta-controls-independent-verification-01.json'),
            sha256='b8d689dd8573ac4676ae4e43b0266d0af84fd10ac265854dfc00fa90a2f0d835'),
        'exact actual eleven-control parser qualification')
    control_inputs=read(frozen(control_source/'inputs.json',freeze))
    control_receipt=read(frozen(control_work/'receipt.json',freeze));control_result=read(frozen(control_work/'result.json',freeze))
    control_audit=verified_reference(controls['audit'],freeze)
    require(control_inputs['files'][str(RECON_SOURCE/'wrong_beta.py')]['sha256']==reconciliation['parser']['sha256']
        and control_receipt['status']==control_result['status']=='passed' and control_audit['status']=='verified'
        and control_receipt['inputs_sha256']==sha(control_source/'inputs.json')
        and controls['receipt_sha256']==control_audit['receipt_sha256']==sha(control_work/'receipt.json')
        and controls['result_sha256']==control_receipt['result_sha256']==control_audit['result_sha256']==sha(control_work/'result.json')
        and type(controls['controls']) is int and controls['controls']==11
        and controls['controls']==control_receipt['controls_passed']==control_result['tests_run']==control_audit['controls']
        and all(control_result[key]==0 for key in ['failures','errors','skipped','expected_failures',
            'unexpected_successes','child_processes','compiler_calls']), 'corrected parser actual control qualification')
    additions={'read_only_reconciliation','actual_workload_children','base_inputs','command_evidence',
        'reconciliation','wrong_beta_providers','wrong_beta_lib','reconciliation_evidence_roots'}
    require(set(recon_plan)==set(native_plan)|additions and not set(native_plan)&additions
        and encoded({key:recon_plan[key] for key in native_plan})==encoded(native_plan),
        'original native recipe and value types preserved by reconciliation plan')
    return dict(terminal=terminal,result=result,original=original,plan=native_plan,
        qualification=dict(source=str(RECON_SOURCE),evidence=str(RECON_WORK),
            receipt=dict(path=str(RECON_WORK/'receipt.json'),sha256=sha(RECON_WORK/'receipt.json')),
            result=dict(path=str(RECON_WORK/'native-controls.json'),sha256=sha(RECON_WORK/'native-controls.json')),
            audit=plan['independent_audits']['native']))

def verify_original_snapshot_catalog(freeze,plan,limits):
    """Rebuild both original v1 catalogs without importing the producer binder."""
    supplied=plan['snapshot_reuse'];records=[];roots={};proofs=[];paths=set()
    require(set(supplied)=={'policy','priority','predecessors','records','evidence_roots'}
        and supplied['policy']=='hash-proof-reference-selection-v1' and supplied['priority']==['beta','native'],
        'exact closed snapshot catalog policy')
    require(plan['evidence_roots']==sorted(set(plan['evidence_roots'])),'unique accounted evidence roots')
    predecessors=[('beta',A/'experiments/hir-options-hash-beta-composition-08',A/'.work/hir-options-hash-beta-composition-08'),
        ('native',NATIVE_SOURCE,NATIVE_WORK)]
    for role,source,evidence in predecessors:
        require(str(evidence) in plan['evidence_roots'],'referenced predecessor already counted by aggregate monitor')
        root=evidence/'source-snapshots';root_identity=ordinary_snapshot_route(root,directory=True)
        association=dict(role=role,source=str(source),evidence=str(evidence),snapshot_root=str(root))
        def load(name,path):
            ordinary_snapshot_route(path);frozen(path,freeze)
            association[name]=dict(path=str(path),sha256=sha(path));return read(path)
        receipt=load('receipt',evidence/'receipt.json')
        audit_ref=plan['independent_audits']['beta'] if role=='beta' else NATIVE_FAILURE_AUDIT
        audit=load('audit',Path(audit_ref['path']))
        require(association['audit']==audit_ref and audit['receipt_sha256']==sha(evidence/'receipt.json')
            and receipt['started_at']<=receipt['admitted_at']<=receipt['finished_at'],'original snapshot writer audit association')
        if role=='beta':require(receipt['status']=='passed' and audit['status']=='verified','qualified beta snapshot writer')
        else:
            native=verified_native_reconciliation(freeze,plan)
            require(receipt==native['original'],'reconciled original snapshot writer remains failed')
            association['qualification']=native['qualification']
        original=load('inputs',source/'inputs.json');snapshot=load('projection',source/'snapshot-plan.json')
        retained=load('retained_projection',evidence/'snapshot-plan.json');manifest=load('manifest',evidence/'source-snapshots.json')
        require(snapshot==retained and association['projection']['sha256']==association['retained_projection']['sha256']==receipt['snapshot_plan_sha256']
            and association['inputs']['sha256']==snapshot['inputs_sha256']==receipt['inputs_sha256']
            and association['manifest']['sha256']==receipt['source_snapshots_sha256'],'original completed snapshot hashes')
        helper=snapshot['helper'];require(sha(frozen(helper['path'],freeze))==helper['sha256']==original['files'][helper['path']]['sha256'],
            'original snapshot helper frozen bytes')
        projection=snapshot['projection']
        require(projection['policy']==manifest['policy']=='bounded-gzip-proof-snapshots-v1'
            and snapshot['limits']==projection['limits']==limits and manifest['projection_sha256']==hashlib.sha256(encoded(projection)).hexdigest()
            and manifest['full_gzip_eof'] is True and manifest['full_logical_readback'] is True,'original v1 snapshot projection')
        names=original['snapshot_inputs']
        require(type(names) is list and all(type(name) is str for name in names)
            and len(names)==len(set(names)) and set(names)<=set(original['files']) and str(source/'inputs.json') not in names,
            'original complete logical selection')
        files={name:dict(path=name,**original['files'][name]) for name in sorted(names)}
        files[str(source/'inputs.json')]=dict(path=str(source/'inputs.json'),**freeze['files'][str(source/'inputs.json')])
        require(projection['files']==files and len(files)<=limits['maximum_files'],'unchanged original logical input mappings')
        sizes={}
        for row in files.values():
            require(row['sha256'] not in sizes or sizes[row['sha256']]==row['size'],'equal original hash sizes')
            sizes[row['sha256']]=row['size']
        blobs=projection['blobs'];require(set(blobs)==set(sizes) and manifest['blobs']==blobs,'complete original physical blob set')
        require(set(p.name for p in root.iterdir())=={key+'.gz' for key in blobs},'exact predecessor physical directory membership')
        expected_files={name:dict(path=str(root/(row['sha256']+'.gz')),sha256=row['sha256'],size=row['size'],encoding='gzip') for name,row in files.items()}
        require(manifest['files']==expected_files and projection['logical_bytes']==sum(row['size'] for row in files.values())<=limits['maximum_logical_bytes']
            and projection['unique_logical_bytes']==sum(sizes.values()) and projection['manifest_reservation_bytes']==2*limits['maximum_manifest_bytes'],
            'original mapping and logical accounting')
        compressed=0;allocated=0
        for key,row in sorted(blobs.items()):
            require(set(row)=={'filename','logical_sha256','logical_bytes','sha256','compressed_bytes'}
                and re.fullmatch('[a-f0-9]{64}',key) and row['logical_sha256']==key and row['filename']==key+'.gz'
                and type(row['logical_bytes']) is int and 0<=row['logical_bytes']==sizes[key]<=limits['maximum_file_bytes']
                and type(row['compressed_bytes']) is int and 0<row['compressed_bytes']<=limits['maximum_compressed_bytes'],
                'original bounded exact blob descriptor')
            path=frozen(root/row['filename'],freeze);info=ordinary_snapshot_route(path)
            require(str(path) not in paths,'duplicate original physical blob path');paths.add(str(path))
            snapshot_blob(path,row);records.append(dict(path=str(path),identity=info,blob=row,evidence_root=str(root)))
            compressed+=row['compressed_bytes'];allocated+=(row['compressed_bytes']+4095)//4096*4096
        require(compressed==projection['compressed_bytes']==manifest['compressed_bytes']<=limits['maximum_compressed_bytes']
            and allocated==projection['compressed_allocated_bytes'] and ordinary_snapshot_route(root,directory=True)==root_identity,
            'original compressed accounting and stable root identity')
        roots[str(root)]=root_identity;proofs.append(association)
    reconstructed=dict(policy='hash-proof-reference-selection-v1',priority=['beta','native'],predecessors=proofs,records=records,evidence_roots=roots)
    require(reconstructed==supplied,'independently reconstructed full predecessor catalog differs')
    return reconstructed

def snapshots(freeze,terminal,launch,plan):
    require(all(path.stat().st_size<=4*2**20 for path in [HERE/'snapshot-plan.json',WORK/'snapshot-plan.json',WORK/'source-snapshots.json']),'bounded snapshot documents')
    projection_plan=read(HERE/'snapshot-plan.json');projection=projection_plan['projection'];manifest=read(WORK/'source-snapshots.json')
    require(sha(HERE/'snapshot-plan.json')==sha(WORK/'snapshot-plan.json')==launch['snapshot_plan_sha256']==terminal['snapshot_plan_sha256']
        and sha(WORK/'source-snapshots.json')==terminal['source_snapshots_sha256'],'snapshot projection/manifest hashes')
    require(projection_plan['inputs_sha256']==sha(HERE/'inputs.json') and projection_plan['evidence_cap_bytes']==256*2**20
        and projection_plan['remaining_evidence_reservation_bytes']==32*2**20,'snapshot reservation policy')
    helper=A/'experiments/bounded-proof-snapshots-v2/proof_snapshots.py'
    limits=dict(maximum_files=1024,maximum_file_bytes=64*2**20,maximum_logical_bytes=512*2**20,
        maximum_compressed_bytes=128*2**20,maximum_manifest_bytes=4*2**20)
    require(projection_plan['limits']==projection['limits']==limits
        and projection_plan['helper']==dict(path=str(helper),sha256=freeze['files'][str(helper)]['sha256']),'qualified snapshot helper/policy')
    qualification=snapshot_helper_qualification(freeze)
    require(manifest['policy']==projection['policy']=='bounded-gzip-proof-snapshots-v2'
        and manifest['projection_sha256']==hashlib.sha256(encoded(projection)).hexdigest()
        and manifest['blobs']==projection['blobs'] and manifest['full_logical_readback'] is True and manifest['full_gzip_eof'] is True,'snapshot projection exactness')
    wanted=set(freeze['snapshot_inputs'])|{str(HERE/'inputs.json')}
    require(len(wanted)<=1024 and wanted==set(projection['files'])==set(manifest['files']),'complete logical snapshots')
    bindings=verify_snapshot_catalog(freeze,plan,limits)
    selected={};used_roots=set();inodes=set()
    wanted_sizes={}
    for row in projection['files'].values():
        require(row['sha256'] not in wanted_sizes or wanted_sizes[row['sha256']]==row['size'],'logical alias size consistency')
        wanted_sizes[row['sha256']]=row['size']
    for ref in bindings['records']:
        key=ref['blob']['logical_sha256']
        if key in wanted_sizes and key not in selected:
            inode=(ref['identity']['dev'],ref['identity']['ino'])
            require(ref['blob']['logical_bytes']==wanted_sizes[key] and inode not in inodes,'exact unique reused physical input')
            selected[key]=ref;inodes.add(inode);used_roots.add(ref['evidence_root'])
    roots={name:bindings['evidence_roots'][name] for name in sorted(used_roots)}
    require(projection_plan['reuse_selection']==dict(records=[selected[key] for key in sorted(selected)],evidence_roots=roots)
        and projection['reuse']==manifest['reuse']==selected
        and projection['evidence_roots']==manifest['evidence_roots']==roots,'independent deterministic beta-first reuse selection')
    blobs=projection['blobs'];require(set(blobs)==set(wanted_sizes),'complete unique logical snapshot payloads')
    storage={key:(dict(kind='reused',path=selected[key]['path']) if key in selected else dict(kind='stored')) for key in blobs}
    physical={key:(storage[key] if key in selected else dict(kind='stored',path=str(WORK/'source-snapshots'/(key+'.gz')))) for key in blobs}
    require(projection['storage']==storage and manifest['storage']==physical,'complete physical stored/reused snapshot routes')
    new_root=WORK/'source-snapshots';new_identity=ordinary_snapshot_route(new_root,directory=True)
    new_names={row['filename'] for key,row in blobs.items() if key not in selected}
    require(set(p.name for p in new_root.iterdir())==new_names,'only newly stored physical blobs in new directory')
    logical=0
    for name,row in projection['files'].items():
        require(row['path']==name and row['size']<=64*2**20 and sha(name)==row['sha256'] and identity(name)==row['identity'],'snapshot original selected bytes')
        if name!=str(HERE/'inputs.json'):require(row==dict(path=name,**freeze['files'][name]),'snapshot frozen mapping')
        require(manifest['files'][name]==dict(path=physical[row['sha256']]['path'],sha256=row['sha256'],size=row['size'],encoding='gzip'),'logical snapshot route')
        require(projection['blobs'][row['sha256']]['logical_bytes']==row['size'],'logical alias to physical blob size')
        logical+=row['size']
    require(logical==projection['logical_bytes']<=512*2**20
        and projection['unique_logical_bytes']==sum(wanted_sizes.values())
        and projection['manifest_reservation_bytes']==2*limits['maximum_manifest_bytes'],'logical proof accounting');compressed=0;new=0;allocated=0;new_allocated=0
    for digest,row in projection['blobs'].items():
        require(set(row)=={'filename','logical_sha256','logical_bytes','sha256','compressed_bytes'}
            and re.fullmatch('[a-f0-9]{64}',digest) and row['logical_sha256']==digest and row['filename']==digest+'.gz'
            and re.fullmatch('[a-f0-9]{64}',row['sha256']) and type(row['logical_bytes']) is int
            and 0<=row['logical_bytes']==wanted_sizes[digest]<=64*2**20
            and type(row['compressed_bytes']) is int and 0<row['compressed_bytes']<=128*2**20,'bounded gzip blob')
        path=Path(physical[digest]['path'])
        if digest in selected:
            ref=selected[digest]
            require(ref['blob']==row and identity(path)==ref['identity']
                and identity(ref['evidence_root'])==roots[ref['evidence_root']],'exact frozen reused bytes/root before readback')
        snapshot_blob(path,row);compressed+=row['compressed_bytes'];allocation=(row['compressed_bytes']+4095)//4096*4096
        allocated+=allocation
        if digest not in selected:new+=row['compressed_bytes'];new_allocated+=allocation
        else:require(identity(path)==selected[digest]['identity'],'reused blob identity after readback')
    require(compressed==projection['compressed_bytes']==manifest['compressed_bytes'] and compressed<=128*2**20,'compressed proof bound')
    require(new==projection['new_compressed_bytes']==manifest['new_compressed_bytes']
        and compressed-new==projection['reused_compressed_bytes']==manifest['reused_compressed_bytes']
        and allocated==projection['compressed_allocated_bytes'] and new_allocated==projection['new_compressed_allocated_bytes'],
        'total and new physical snapshot accounting')
    for root,expected in roots.items():require(ordinary_snapshot_route(root,directory=True)==expected,'referenced root changed during readback')
    require(ordinary_snapshot_route(new_root,directory=True)==new_identity
        and set(p.name for p in new_root.iterdir())==new_names,'new snapshot directory changed during readback')
    reservation=new_allocated+4096*len(new_names)+2*4*2**20+32*2**20
    admission=terminal['snapshot_admission'];require(reservation==projection_plan['projected_reservation_bytes']==admission['projected_reservation_bytes']
        and admission['existing_evidence_bytes']+reservation<=admission['evidence_cap_bytes']==256*2**20,'actual snapshot admission')
    require(projection_plan['measured_existing_evidence_bytes']+reservation<=256*2**20,'prepared aggregate reservation')
    return dict(logical_files=len(wanted),physical_blobs=len(blobs),new_physical_blobs=len(new_names),reused_physical_blobs=len(selected),
        logical_bytes=logical,compressed_bytes=compressed,new_compressed_bytes=new,reused_compressed_bytes=compressed-new,
        new_compressed_allocated_bytes=new_allocated,projected_reservation_bytes=reservation,
        helper_qualification=qualification,full_gzip_eof_crc=True,full_logical_hashes=True)

# Independently decoded complete plan; no producer helper import.
METADATA_PLAN_REFERENCE=dict(path=str(X/'experiments/hir-options-hash/compiler-metadata-03/plan.json'),
    sha256='250b19e48b158efe78e726e78223791cb4ff55b5b5d2b9eaa59b41ba2b1727c2')
FAILED_SOURCE=ROOT/'experiments/hir-options-hash-driver-stage-02'
FAILED_WORK=ROOT/'.work/hir-options-hash-driver-01'
FAILED_ARTIFACTS=N/'hash-driver-01'
FAILED_OUTER=ROOT/'.work/experiments/hir-options-hash-driver-supervisor-01'
FAILED_DISPATCH=ROOT/'.work/hash-driver-launch-execution-01'
FAILED_AUDIT=ROOT/'.work/hir-options-hash-driver-failure-verification-01.json'


def complete_plan(document, *, expected_reference, read_reference):
    wire=json.loads(audit_json_bytes(document),object_pairs_hook=unique)
    require(type(wire) is dict and set(wire)=={'policy','member','reference','remainder','integrity'}
        and wire['policy']=='external-json-member-v1' and wire['member']=='metadata_plan',
        'exact independently reconstructed metadata-plan envelope')
    reference=wire['reference'];require(type(reference) is dict and set(reference)=={'path','sha256'}
        and audit_json_bytes(reference)==audit_json_bytes(expected_reference),'exact admitted metadata-plan reference')
    name=reference['path'];digest=reference['sha256']
    require(type(name) is str and name.startswith('/') and not name.startswith('//') and name!='/'
        and str(Path(name))==name and '..' not in Path(name).parts and len(name.encode())<=4096
        and all(ord(c)>=32 and ord(c)!=127 for c in name)
        and type(digest) is str and re.fullmatch('[a-f0-9]{64}',digest),'bounded ordinary reference tokens')
    require(type(wire['remainder']) is dict and 'metadata_plan' not in wire['remainder'],'disjoint complete plan member')
    check=wire['integrity'];require(type(check) is dict and set(check)=={'sha256','bytes'}
        and type(check['sha256']) is str and re.fullmatch('[a-f0-9]{64}',check['sha256'])
        and type(check['bytes']) is int and 0<check['bytes']<=64*2**20,'typed full-plan integrity')
    value=read_reference(name);require(type(value) is bytes and len(value)<=64*2**20
        and hashlib.sha256(value).hexdigest()==digest,'exact referenced metadata bytes')
    metadata=json.loads(value,object_pairs_hook=unique,
        parse_constant=lambda value:(_ for _ in ()).throw(ValueError(value)))
    audit_json_bytes(metadata)
    full=wire['remainder'];full['metadata_plan']=metadata
    data=audit_json_bytes(full)
    require(len(data)==check['bytes'] and hashlib.sha256(data).hexdigest()==check['sha256'],'full typed plan reconstruction')
    return full


def failed_owner_history(freeze,plan):
    owner=plan['failed_driver']
    require(type(owner) is dict and set(owner)=={'role','source','evidence','audit'}
        and owner['role']=='failed-hash-driver-01' and owner['source']==str(FAILED_SOURCE)
        and owner['evidence']==str(FAILED_WORK) and owner['audit']==dict(path=str(FAILED_AUDIT),
            sha256='ee81a129d5d1742074619ea31b75ad06512abd110dd102dc0ac8bec8c3eda8b3'),
        'exact explicit failed predecessor role and routes')
    audit=verified_reference(owner['audit'],freeze)
    terminal=read(frozen(FAILED_WORK/'receipt.json',freeze))
    old_plan=read(frozen(FAILED_SOURCE/'plan.json',freeze));launch=read(frozen(FAILED_SOURCE/'launch.json',freeze))
    require(encoded(old_plan['metadata_plan'])==encoded(plan['metadata_plan'])
        and encoded(old_plan['independent_audits'])==encoded(plan['independent_audits']),
        'complete metadata and four actual prerequisite audits unchanged')
    compiled=read(frozen(FAILED_WORK/'compile/receipt.json',freeze))
    outer=read(frozen(FAILED_OUTER/'status.json',freeze));dispatch=read(frozen(FAILED_DISPATCH/'record.json',freeze))
    require(audit['status']=='verified-retained-failure' and audit['owner_status']==terminal['status']=='failed'
        and audit['source']==str(FAILED_SOURCE) and audit['evidence']==str(FAILED_WORK)
        and audit['receipt_sha256']==sha(FAILED_WORK/'receipt.json')
        and audit['compile_receipt_sha256']==sha(FAILED_WORK/'compile/receipt.json')
        and audit['actual_children']==audit['actual_compiler_children']==1
        and audit['actual_driver_processes']==audit['qualified_hash_driver_processes']==0,
        'actual failed compiler remains unqualified')
    require(all(audit[k] is False and terminal[k] is False for k in ['hash_driver_qualified','application_qualified','performance_measurement','runtime_installation'])
        and all(audit[k] is True for k in ['full_frozen_byte_rehash','full_provider_inventories','full_sdk_inventory',
            'complete_failed_raw_history','full_snapshot_selection','retained_snapshot_owner_only','compiler_failure_preserved'])
        and audit['compressed_snapshots']['full_gzip_eof_crc'] is audit['compressed_snapshots']['full_logical_hashes'] is True,
        'complete audited failed owner without qualification substitution')
    wanted=historical_commands(old_plan)
    require(old_plan['children']==wanted and len(wanted)==3
        and sha(FAILED_SOURCE/'launch.json')==audit['launch_sha256']=='e315c703101fb5d8e9f732a10db9b07883792057c0f833b71979cf54efcbfc43'
        and sha(FAILED_SOURCE/'inputs.json')==audit['inputs_sha256']==terminal['inputs_sha256']==launch['inputs_sha256']
        and sha(FAILED_SOURCE/'plan.json')==audit['plan_sha256']==launch['plan_sha256']
        and terminal['error']=="AssertionError('unexpected compiler-stage return code')",'original failed exact plan')
    require(compiled['status']=='failed' and type(compiled['returncode']) is int and compiled['returncode']==1
        and compiled['expected']==[0] and compiled['error']==terminal['error'] and compiled['command']==wanted[0]['argv']
        and compiled['cwd']==str(S) and compiled['environment']==wanted[0]['environment']
        and compiled['supervisor_pid']==terminal['pid'] and compiled['parent_pid']==terminal['parent_pid']
        and terminal['admitted_at']<=compiled['started_at']<=compiled['finished_at']<=terminal['finished_at'],
        'one original failed compiler receipt')
    missing=[];process_identity(compiled,wanted[0]['argv'],terminal['pid'],missing,'failed-compile',strict=True)
    for stream in ['stdout','stderr']:
        frozen(FAILED_WORK/'compile'/stream,freeze)
        require(sha(FAILED_WORK/'compile'/stream)==compiled[stream+'_sha256'],'original failed compiler raw')
    require(not raw(FAILED_WORK/'compile/stdout') and compiled['stderr_sha256']=='789be46bc0f46a221859863de9fa28103a928ba8c4d5b51bd83e101dde06698f',
        'exact original E0277 marker diagnostic')
    for row in compiled['samples']:
        require(row['free_bytes']>=9*2**30 and row['namespace_allocated_bytes']<=14*2**30
            and row['evidence_allocated_bytes']<=256*2**20 and not row['allocation_errors']
            and row['evidence_root']==str(FAILED_WORK) and row['evidence_roots']==old_plan['evidence_roots'],
            'historical original resource scope preserved')
    require(compiled['samples'] and terminal['free_bytes_before']>=24*2**30,'original admission and sample history')
    require(outer['status']=='finished' and outer['returncode']==1 and outer['child_pid']==terminal['pid']
        and outer['supervisor_pid']==terminal['parent_pid'] and outer['command']==launch['command'][6:]
        and outer['cwd']==str(ROOT) and outer['plan_sha256']==sha(frozen(FAILED_OUTER/'plan.json',freeze))
        and outer['log_sha256']==sha(frozen(FAILED_OUTER/'command.log',freeze))
        and outer['child_started_at']<=terminal['started_at']<=terminal['admitted_at']<=terminal['finished_at']<=outer['finished_at'],
        'original failed outer closure')
    require(dispatch['status']=='terminal-observed' and dispatch['returncode']==1 and dispatch['launcher_returncode']==0
        and dispatch['outer_sha256']==sha(FAILED_OUTER/'status.json') and dispatch['command']==launch['command']
        and dispatch['cwd']==str(ROOT) and dispatch['environment']==launch['environment']
        and dispatch['supervisor_pid']==outer['supervisor_pid'] and dispatch['controller_pid']==terminal['pid']
        and dispatch['launch_sha256']==audit['launch_sha256']
        and sha(frozen(dispatch['launcher_source_path'],freeze))==dispatch['launcher_source_sha256']
        and dispatch['started_at']<=dispatch['launcher_finished_at']<=dispatch['finished_at']
        and outer['finished_at']<=dispatch['terminal_observed_at']<=dispatch['finished_at'],'original launcher owns failed closure')
    for stream in ['stdout','stderr']:
        require(sha(frozen(FAILED_DISPATCH/stream,freeze))==dispatch[stream+'_sha256'],'original launcher raw')
    handoff=read(FAILED_DISPATCH/'stdout')
    require(handoff==dispatch['supervisor_handoff'] and handoff['directory']==str(FAILED_OUTER)
        and handoff['supervisor_pid']==outer['supervisor_pid'],'original detached wrapper handoff')
    require(audit['closure']==dict(outer_status='finished',outer_returncode=1,outer_sha256=sha(FAILED_OUTER/'status.json'),
        launcher_status='terminal-observed',launcher_returncode=0,actual_returncode=1,
        launcher_record_sha256=sha(FAILED_DISPATCH/'record.json'),actual_outer_closed=True,actual_wrapper_closed=True,
        supervisor_pid=terminal['parent_pid'],controller_pid=terminal['pid']),'actual failure audit closure association')
    absent=[FAILED_WORK/'result.json',FAILED_WORK/'serial',FAILED_WORK/'parallel',FAILED_WORK/'linker-command.json',
        FAILED_WORK/'driver-loader-closure.json',FAILED_ARTIFACTS/'hash-control-driver']
    require(all(not p.exists() and not p.is_symlink() for p in absent),'failed predecessor gained a result or workload output')
    require(set(p.name for p in FAILED_WORK.iterdir())=={'receipt.json','compile','source-snapshots','source-snapshots.json','snapshot-plan.json'}
        and set(p.name for p in (FAILED_WORK/'compile').iterdir())=={'receipt.json','stdout','stderr'},'original failed evidence membership')
    require(set(p.name for p in FAILED_ARTIFACTS.iterdir())=={'fixture.rs','serial','parallel','tmp'}
        and sha(frozen(FAILED_ARTIFACTS/'fixture.rs',freeze))==SOURCE_HASHES[FIXTURE]
        and all((FAILED_ARTIFACTS/name).resolve(strict=True)==FAILED_ARTIFACTS/name and (FAILED_ARTIFACTS/name).is_dir()
            and not list((FAILED_ARTIFACTS/name).iterdir()) for name in ['serial','parallel','tmp']), 'unchanged failed artifact closure')
    require(inventory(FAILED_ARTIFACTS)==audit['artifacts'],'complete failed artifact identity inventory')
    return dict(owner=owner,audit=audit,terminal=terminal,plan=old_plan,launch=launch,
        receipt_sha256=sha(FAILED_WORK/'receipt.json'),actual_children=1,qualified_children=0)


def verify_snapshot_catalog(freeze,plan,limits):
    supplied=plan['snapshot_reuse'];failed=failed_owner_history(freeze,plan);old_plan=failed['plan']
    prior=verify_original_snapshot_catalog(freeze,old_plan,limits)
    require(encoded(old_plan['snapshot_reuse'])==encoded(prior),'complete original inherited catalog retained')
    compact=read(frozen(FAILED_SOURCE/'inputs.json',freeze))
    original=complete_file_table(compact,expected_base=dict(path=str(NATIVE_SOURCE/'inputs.json'),
        sha256='8569abb81a61e34b6b5a892116af5218557ceb0436ab8dbf8a31f2aec55b1b1d'))
    for name,row in original['files'].items():
        require(name in freeze['files'] and encoded(row)==encoded(freeze['files'][name]),'complete failed-owner original file identity inherited')
    require(set(old_plan['evidence_roots'])<=set(plan['evidence_roots']) and str(FAILED_WORK) in plan['evidence_roots'],
        'original physical accounting remains complete')
    proof=retained_failed_snapshots(original,failed['terminal'],failed['launch'],old_plan)
    require(encoded(proof)==encoded(failed['audit']['compressed_snapshots']),'complete independent failed snapshot readback matches audit')
    manifest=read(frozen(FAILED_WORK/'source-snapshots.json',freeze));snapshot=read(frozen(FAILED_SOURCE/'snapshot-plan.json',freeze))
    root=FAILED_WORK/'source-snapshots';info=ordinary_snapshot_route(root,directory=True)
    require(str(root) not in prior['evidence_roots'],'new failed-owner physical root')
    association=dict(role='failed-hash-driver-01',source=str(FAILED_SOURCE),evidence=str(FAILED_WORK),completion='failed',
        inherited_catalog_sha256=hashlib.sha256(encoded(prior)).hexdigest())
    for key,path in [('receipt',FAILED_WORK/'receipt.json'),('audit',FAILED_AUDIT),('inputs',FAILED_SOURCE/'inputs.json'),
        ('plan',FAILED_SOURCE/'plan.json'),('projection',FAILED_SOURCE/'snapshot-plan.json'),
        ('retained_projection',FAILED_WORK/'snapshot-plan.json'),('manifest',FAILED_WORK/'source-snapshots.json')]:
        association[key]=dict(path=str(path),sha256=sha(frozen(path,freeze)))
    association['helper']=snapshot['helper'];association['snapshot_root']=str(root)
    association['file_table_base']=compact['file_table_base']
    require(association['audit']==failed['owner']['audit'] and failed['audit']['inputs_sha256']==association['inputs']['sha256']
        and failed['audit']['plan_sha256']==association['plan']['sha256']
        and failed['audit']['snapshot_plan_sha256']==association['projection']['sha256']==association['retained_projection']['sha256']
        and failed['audit']['source_snapshots_sha256']==association['manifest']['sha256'],'all failed audit snapshot associations')
    records=list(prior['records']);paths={row['path'] for row in records};physical={(r['identity']['dev'],r['identity']['ino']) for r in records}
    for key,blob in sorted(manifest['blobs'].items()):
        storage=manifest['storage'][key]
        if storage['kind']=='reused':continue
        require(storage==dict(kind='stored',path=str(root/(key+'.gz'))),'exact failed stored route')
        path=frozen(storage['path'],freeze);current=ordinary_snapshot_route(path)
        require(str(path) not in paths and (current['dev'],current['ino']) not in physical,'unique newly inherited failed physical blob')
        snapshot_blob(path,blob);paths.add(str(path));physical.add((current['dev'],current['ino']))
        records.append(dict(path=str(path),identity=current,blob=blob,evidence_root=str(root)))
    roots=dict(prior['evidence_roots']);roots[str(root)]=info
    answer=dict(policy='closed-failed-proof-snapshot-catalog-v2',priority=prior['priority']+['failed-hash-driver-01'],
        predecessors=prior['predecessors']+[association],records=records,evidence_roots=dict(sorted(roots.items())))
    require(encoded(answer)==encoded(supplied),'complete independently reconstructed failed-owner catalog')
    require(ordinary_snapshot_route(root,directory=True)==info,'failed snapshot root unchanged')
    return answer


def continuation_qualification(freeze,plan):
    source=ROOT/'experiments/hash-continuation-controls-01';work=ROOT/'.work/hash-continuation-controls-01'
    audit_path=ROOT/'.work/hash-continuation-controls-independent-verification-01.json'
    catalog=ROOT/'experiments/completed-proof-snapshot-catalog-02/catalog.py';reference=HERE/'plan_reference.py'
    tests=[catalog.with_name('test_catalog.py'),catalog.with_name('test_failed_catalog.py'),reference.with_name('test_plan_reference.py')]
    inputs=read(frozen(source/'inputs.json',freeze));launch=read(frozen(source/'launch.json',freeze))
    terminal=read(frozen(work/'receipt.json',freeze));result=read(frozen(work/'result.json',freeze))
    child=read(frozen(work/'command/receipt.json',freeze));audit=read(frozen(audit_path,freeze))
    require(type(inputs['files']) is dict and len(inputs['files'])<=64
        and sum(row['stamp'][3] for row in inputs['files'].values())<=16*2**20,'bounded complete continuation control closure')
    for name,row in inputs['files'].items():
        current=frozen(name,freeze);require(sha(current)==row['sha256'] and stamp(current)==row['stamp'],'complete tested input identity and bytes')
    for name,target in inputs['routes'].items():
        require(str(Path(name).resolve(strict=True))==target and target in inputs['files'],'tested executable routes')
    names=[]
    for path in [catalog,reference,*tests]:
        frozen(path,freeze);require(inputs['files'][str(path)]['sha256']==sha(path),'exact helper/reader tested source')
    for path in tests:
        for cls in ast.parse(raw(path),filename=str(path)).body:
            if isinstance(cls,ast.ClassDef):
                names.extend(path.stem+'.'+cls.name+'.'+test.name for test in cls.body
                    if isinstance(test,ast.FunctionDef) and test.name.startswith('test_'))
    names=sorted(names)
    require(len(names)==len(set(names))==70 and names==inputs['expected_names']==result['expected_names']==sorted(audit['exact_names']),
        'complete independent seventy-control identities')
    require(terminal['status']==result['status']=='passed' and audit['status']=='verified'
        and all(type(value) is int and value==70 for value in [terminal['controls_passed'],result['tests_run'],audit['controls'],launch['controls']])
        and terminal['inputs_sha256']==launch['inputs_sha256']==sha(source/'inputs.json')
        and terminal['result_sha256']==audit['result_sha256']==sha(work/'result.json')
        and audit['receipt_sha256']==sha(work/'receipt.json'),'actual independent control qualification')
    require(all(type(result[key]) is int and result[key]==0 for key in ['failures','errors','skipped','expected_failures',
        'unexpected_successes','child_processes','compiler_calls'])
        and all(type(terminal[key]) is int and terminal[key]==0 for key in ['compiler_calls','provider_probes','B3_compositions']),
        'no missing controls or extra workloads')
    require(child['status']=='finished' and type(child['returncode']) is int and child['returncode']==0
        and child['command']==inputs['command'] and child['environment']==inputs['environment']
        and child['cwd']==str(catalog.parent) and child['supervisor_pid']==terminal['pid'] and child['parent_pid']==terminal['parent_pid']
        and terminal['started_at']<=terminal['admitted_at']<=child['started_at']<=child['finished_at']<=terminal['finished_at']
        and terminal['commands']==[dict(path=str(work/'command/receipt.json'),pid=child['pid'],sha256=sha(work/'command/receipt.json'))],
        'actual one-child continuation control recipe')
    for stream in ['stdout','stderr']:
        require(sha(frozen(work/'command'/stream,freeze))==child[stream+'_sha256']==audit['raw_sha256'][stream],'actual continuation control raw')
    stderr=raw(work/'command/stderr').decode('utf-8','strict')
    actual=re.findall(r'^test_[A-Za-z0-9_]+ \(([^)]+)\) \.\.\. ok$',stderr,re.M)
    require(not raw(work/'command/stdout') and sorted(actual)==names
        and re.search(r'^Ran 70 tests in [0-9.]+s\n\nOK\n$',stderr,re.M),'all raw outcomes and actual test names')
    proof=dict(controls=70,audit=dict(path=str(audit_path),sha256=sha(audit_path)),
        inputs=dict(path=str(source/'inputs.json'),sha256=sha(source/'inputs.json')),
        receipt=dict(path=str(work/'receipt.json'),sha256=sha(work/'receipt.json')),
        result=dict(path=str(work/'result.json'),sha256=sha(work/'result.json')),
        sources={str(p):sha(p) for p in [catalog,reference,*tests]})
    require(encoded(proof)==encoded(plan['continuation_controls']),'complete actual continuation proof bound to plan')
    return proof


def driver_derivation(freeze):
    original=frozen(X/'experiments/hir-options-hash/controls/driver.rs',freeze)
    before=raw(original);after=raw(frozen(DRIVER,freeze))
    require(hashlib.sha256(before).hexdigest()=='3953c595bb37a6c05661d9a399599bf5529b6a847629d2e1aa4c47eb8314605b'
        and hashlib.sha256(after).hexdigest()==SOURCE_HASHES[DRIVER],'exact original and successor driver bytes')
    replacements=[(b'use rustc_data_structures::sync::{is_dyn_thread_safe, par_join};',
        b'use rustc_data_structures::sync::{IntoDynSyncSend, is_dyn_thread_safe, par_join};'),
        (b'let barrier = Barrier::new(2);',b'let barrier = IntoDynSyncSend(Barrier::new(2));')]
    candidate=before
    for old,new in replacements:
        require(candidate.count(old)==1,'unique exact synchronization wrapper replacement');candidate=candidate.replace(old,new)
    require(candidate==after,'only exact marker import and barrier wrapper changed')
    return dict(original=dict(path=str(original),sha256=hashlib.sha256(before).hexdigest()),
        derived=dict(path=str(DRIVER),sha256=hashlib.sha256(after).hexdigest()),
        policy='exact-two-barrier-dynsync-adapter-replacements',all_other_driver_bytes_unchanged=True)


def historical_commands(plan):
    require(plan['roles']==dict(build_compiler=str(D2),build_sysroot=str(B3),runtime_compiler=str(E2),application_sysroot=str(E2)),'exact compiler roles')
    pair=plan['ordered_driver_pair'];require(type(pair) is list and len(pair)==2,'ordered driver pair')
    dylib,rmeta=map(Path,pair);require(dylib.parent==rmeta.parent==B3/'lib/rustlib'/HOST/'lib'
        and re.fullmatch(r'librustc_driver-[a-f0-9]+\.dylib',dylib.name) and rmeta==dylib.with_suffix('.rmeta'),'exact driver pair route')
    env=plan['environment'];require(env['TMPDIR']==str(FAILED_ARTIFACTS/'tmp') and env['SDKROOT']==plan['sdk'],'owned temporary directory and SDK')
    require(set(env)<={'PATH','HOME','USER','LOGNAME','LANG','LC_ALL','TZ','TMPDIR','SDKROOT','PYTHONDONTWRITEBYTECODE','PYTHONNOUSERSITE','__CF_USER_TEXT_ENCODING'},'ambient driver environment')
    binary=FAILED_ARTIFACTS/'hash-control-driver'
    compile_argv=[str(D2/'bin/rustc'),'--sysroot='+str(B3),'--edition=2024','--crate-name=hash_cache_control_driver','--print=link-args',str(X/'experiments/hir-options-hash/controls/driver.rs'),
        '--extern','rustc_driver='+pair[0],'--extern','rustc_driver='+pair[1],'-Lnative='+str(E2/'lib'),'-Clinker='+plan['clang'],
        '-C','link-arg=-Wl,-rpath,'+str(E2/'lib'),'-o',str(binary)]
    return [dict(argv=compile_argv,cwd=str(S),environment=env|{'RUSTC_BOOTSTRAP':'1'}),
        *[dict(argv=[str(binary),str(E2),str(FAILED_ARTIFACTS/'fixture.rs'),str(FAILED_ARTIFACTS/mode),mode],cwd=str(S),
            environment=env|{'DYLD_PRINT_LIBRARIES':'1'}) for mode in ['serial','parallel']]]


def retained_failed_snapshots(freeze,terminal,launch,plan):
    require(all(path.stat().st_size<=4*2**20 for path in [FAILED_SOURCE/'snapshot-plan.json',FAILED_WORK/'snapshot-plan.json',FAILED_WORK/'source-snapshots.json']),'bounded snapshot documents')
    projection_plan=read(FAILED_SOURCE/'snapshot-plan.json');projection=projection_plan['projection'];manifest=read(FAILED_WORK/'source-snapshots.json')
    require(sha(FAILED_SOURCE/'snapshot-plan.json')==sha(FAILED_WORK/'snapshot-plan.json')==launch['snapshot_plan_sha256']==terminal['snapshot_plan_sha256']
        and sha(FAILED_WORK/'source-snapshots.json')==terminal['source_snapshots_sha256'],'snapshot projection/manifest hashes')
    require(projection_plan['inputs_sha256']==sha(FAILED_SOURCE/'inputs.json') and projection_plan['evidence_cap_bytes']==256*2**20
        and projection_plan['remaining_evidence_reservation_bytes']==32*2**20,'snapshot reservation policy')
    helper=A/'experiments/bounded-proof-snapshots-v2/proof_snapshots.py'
    limits=dict(maximum_files=1024,maximum_file_bytes=64*2**20,maximum_logical_bytes=512*2**20,
        maximum_compressed_bytes=128*2**20,maximum_manifest_bytes=4*2**20)
    require(projection_plan['limits']==projection['limits']==limits
        and projection_plan['helper']==dict(path=str(helper),sha256=freeze['files'][str(helper)]['sha256']),'qualified snapshot helper/policy')
    qualification=snapshot_helper_qualification(freeze)
    require(manifest['policy']==projection['policy']=='bounded-gzip-proof-snapshots-v2'
        and manifest['projection_sha256']==hashlib.sha256(encoded(projection)).hexdigest()
        and manifest['blobs']==projection['blobs'] and manifest['full_logical_readback'] is True and manifest['full_gzip_eof'] is True,'snapshot projection exactness')
    wanted=set(freeze['snapshot_inputs'])|{str(FAILED_SOURCE/'inputs.json')}
    require(len(wanted)<=1024 and wanted==set(projection['files'])==set(manifest['files']),'complete logical snapshots')
    bindings=verify_original_snapshot_catalog(freeze,plan,limits)
    selected={};used_roots=set();inodes=set()
    wanted_sizes={}
    for row in projection['files'].values():
        require(row['sha256'] not in wanted_sizes or wanted_sizes[row['sha256']]==row['size'],'logical alias size consistency')
        wanted_sizes[row['sha256']]=row['size']
    for ref in bindings['records']:
        key=ref['blob']['logical_sha256']
        if key in wanted_sizes and key not in selected:
            inode=(ref['identity']['dev'],ref['identity']['ino'])
            require(ref['blob']['logical_bytes']==wanted_sizes[key] and inode not in inodes,'exact unique reused physical input')
            selected[key]=ref;inodes.add(inode);used_roots.add(ref['evidence_root'])
    roots={name:bindings['evidence_roots'][name] for name in sorted(used_roots)}
    require(projection_plan['reuse_selection']==dict(records=[selected[key] for key in sorted(selected)],evidence_roots=roots)
        and projection['reuse']==manifest['reuse']==selected
        and projection['evidence_roots']==manifest['evidence_roots']==roots,'independent deterministic beta-first reuse selection')
    blobs=projection['blobs'];require(set(blobs)==set(wanted_sizes),'complete unique logical snapshot payloads')
    storage={key:(dict(kind='reused',path=selected[key]['path']) if key in selected else dict(kind='stored')) for key in blobs}
    physical={key:(storage[key] if key in selected else dict(kind='stored',path=str(FAILED_WORK/'source-snapshots'/(key+'.gz')))) for key in blobs}
    require(projection['storage']==storage and manifest['storage']==physical,'complete physical stored/reused snapshot routes')
    new_root=FAILED_WORK/'source-snapshots';new_identity=ordinary_snapshot_route(new_root,directory=True)
    new_names={row['filename'] for key,row in blobs.items() if key not in selected}
    require(set(p.name for p in new_root.iterdir())==new_names,'only newly stored physical blobs in new directory')
    logical=0
    for name,row in projection['files'].items():
        require(row['path']==name and row['size']<=64*2**20 and sha(name)==row['sha256'] and identity(name)==row['identity'],'snapshot original selected bytes')
        if name!=str(FAILED_SOURCE/'inputs.json'):require(row==dict(path=name,**freeze['files'][name]),'snapshot frozen mapping')
        require(manifest['files'][name]==dict(path=physical[row['sha256']]['path'],sha256=row['sha256'],size=row['size'],encoding='gzip'),'logical snapshot route')
        require(projection['blobs'][row['sha256']]['logical_bytes']==row['size'],'logical alias to physical blob size')
        logical+=row['size']
    require(logical==projection['logical_bytes']<=512*2**20
        and projection['unique_logical_bytes']==sum(wanted_sizes.values())
        and projection['manifest_reservation_bytes']==2*limits['maximum_manifest_bytes'],'logical proof accounting');compressed=0;new=0;allocated=0;new_allocated=0
    for digest,row in projection['blobs'].items():
        require(set(row)=={'filename','logical_sha256','logical_bytes','sha256','compressed_bytes'}
            and re.fullmatch('[a-f0-9]{64}',digest) and row['logical_sha256']==digest and row['filename']==digest+'.gz'
            and re.fullmatch('[a-f0-9]{64}',row['sha256']) and type(row['logical_bytes']) is int
            and 0<=row['logical_bytes']==wanted_sizes[digest]<=64*2**20
            and type(row['compressed_bytes']) is int and 0<row['compressed_bytes']<=128*2**20,'bounded gzip blob')
        path=Path(physical[digest]['path'])
        if digest in selected:
            ref=selected[digest]
            require(ref['blob']==row and identity(path)==ref['identity']
                and identity(ref['evidence_root'])==roots[ref['evidence_root']],'exact frozen reused bytes/root before readback')
        snapshot_blob(path,row);compressed+=row['compressed_bytes'];allocation=(row['compressed_bytes']+4095)//4096*4096
        allocated+=allocation
        if digest not in selected:new+=row['compressed_bytes'];new_allocated+=allocation
        else:require(identity(path)==selected[digest]['identity'],'reused blob identity after readback')
    require(compressed==projection['compressed_bytes']==manifest['compressed_bytes'] and compressed<=128*2**20,'compressed proof bound')
    require(new==projection['new_compressed_bytes']==manifest['new_compressed_bytes']
        and compressed-new==projection['reused_compressed_bytes']==manifest['reused_compressed_bytes']
        and allocated==projection['compressed_allocated_bytes'] and new_allocated==projection['new_compressed_allocated_bytes'],
        'total and new physical snapshot accounting')
    for root,expected in roots.items():require(ordinary_snapshot_route(root,directory=True)==expected,'referenced root changed during readback')
    require(ordinary_snapshot_route(new_root,directory=True)==new_identity
        and set(p.name for p in new_root.iterdir())==new_names,'new snapshot directory changed during readback')
    reservation=new_allocated+4096*len(new_names)+2*4*2**20+32*2**20
    admission=terminal['snapshot_admission'];require(reservation==projection_plan['projected_reservation_bytes']==admission['projected_reservation_bytes']
        and admission['existing_evidence_bytes']+reservation<=admission['evidence_cap_bytes']==256*2**20,'actual snapshot admission')
    require(projection_plan['measured_existing_evidence_bytes']+reservation<=256*2**20,'prepared aggregate reservation')
    return dict(logical_files=len(wanted),physical_blobs=len(blobs),new_physical_blobs=len(new_names),reused_physical_blobs=len(selected),
        logical_bytes=logical,compressed_bytes=compressed,new_compressed_bytes=new,reused_compressed_bytes=compressed-new,
        new_compressed_allocated_bytes=new_allocated,projected_reservation_bytes=reservation,
        helper_qualification=qualification,full_gzip_eof_crc=True,full_logical_hashes=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--launch-sha256',required=True);parser.add_argument('--launcher-record',required=True,type=Path);args=parser.parse_args()
    require(Path.cwd()==ROOT and sys.dont_write_bytecode and not sys.flags.optimize and not OUT.exists(),'fresh explicit audit owner/Python')
    require(re.fullmatch('[a-f0-9]{64}',args.launch_sha256) and sha(HERE/'launch.json')==args.launch_sha256,'reviewed exact launch digest')
    require(args.launcher_record.is_relative_to(ROOT/'.work') and args.launcher_record.name=='record.json','explicit owned launcher record')
    started=time.time();launch=read(HERE/'launch.json');compact_freeze=read(HERE/'inputs.json')
    require(sha(HERE/'inputs.json')==launch['inputs_sha256'],'exact compact input bytes required before reconstruction')
    freeze=complete_file_table(compact_freeze,expected_base=dict(path=str(NATIVE_SOURCE/'inputs.json'),
        sha256='8569abb81a61e34b6b5a892116af5218557ceb0436ab8dbf8a31f2aec55b1b1d'))
    plan=complete_plan(read(HERE/'plan.json'),expected_reference=METADATA_PLAN_REFERENCE,
        read_reference=lambda path:raw(frozen(path,freeze),64*2**20))
    continuation=continuation_qualification(freeze,plan)
    failed_predecessor=failed_owner_history(freeze,plan)
    driver_source_derivation=driver_derivation(freeze)
    terminal=read(WORK/'receipt.json');result=read(WORK/'result.json');outer=read(OUTER/'status.json');dispatch=read(args.launcher_record)
    require(sha(HERE/'inputs.json')==launch['inputs_sha256']==terminal['inputs_sha256'] and sha(HERE/'plan.json')==freeze['plan_sha256']==launch['plan_sha256'],'launch/freeze/plan association')
    require(terminal['status']=='passed-awaiting-independent-audit' and result['status']=='hash-driver-observations-passed-awaiting-independent-audit'
        and sha(WORK/'result.json')==terminal['result_sha256'] and terminal['candidate_revision']==result['candidate_revision']==plan['candidate_revision']==REVISION
        and result['source_identity']==plan['source_identity'],'completed exact candidate stage')
    require(all(encoded(terminal[key])==encoded(result[key])==encoded(plan[key])
        for key in ['failed_driver','continuation_controls']),'actual terminal/result retain full failed history and control qualification')
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
    require(sha(frozen(ORIGINAL_VERIFIER['path'],freeze))==ORIGINAL_VERIFIER['sha256'],
        'exact original frozen verifier retained; successor is separately authenticated')
    require(sha(frozen(Path(__file__).resolve(),freeze))==sha(Path(__file__).resolve()),'current independent verifier frozen exactly')
    file_table_proof=file_table_helper_qualification(freeze)
    for name,row in freeze['links'].items():
        path=Path(name);require(path.is_symlink() and stamp(path)==row['stamp'] and os.readlink(path)==row['target']
            and str(path.resolve(strict=True))==row['resolved'],'frozen provider link')
    for name in freeze['absent_paths']:require(not Path(name).exists() and not Path(name).is_symlink(),'frozen absence')
    for name,resolved in plan['executor_routes'].items():require(str(Path(name).resolve(strict=True))==resolved,'executor route')
    require(set(plan['immutable_trees'])==set(map(str,[D2,E2,B3])),'complete immutable roots')
    for name,catalog in plan['immutable_trees'].items():require(inventory(name)==read(frozen(catalog,freeze)),'full provider tree membership/bytes')
    prior={'compiler':(X/'experiments/hir-options-hash/compiler-build-continuation-03',X/'.work/hir-options-hash-compiler-build-continuation-03'),
        'beta':(A/'experiments/hir-options-hash-beta-composition-08',A/'.work/hir-options-hash-beta-composition-08'),
        'native':(RECON_SOURCE,RECON_WORK),
        'run_make':(O/'experiments/hir-options-hash-run-make-stage-02',O/'.work/hir-options-hash-run-make-01')}
    require(set(plan['independent_audits'])==set(prior),'all four prerequisite audits')
    for name,(source,evidence) in prior.items():
        ref=plan['independent_audits'][name];audit=read(frozen(ref['path'],freeze));receipt=read(frozen(evidence/'receipt.json',freeze))
        require(sha(ref['path'])==ref['sha256'] and audit['status']=='verified' and receipt['status']=='passed'
            and audit['receipt_sha256']==sha(evidence/'receipt.json'),'passed exact prerequisite audit')
        inherited_inputs(source,freeze)
    native_proof=verified_native_reconciliation(freeze,plan)
    native_plan,native,native_result=native_proof['plan'],native_proof['original'],native_proof['result']
    original_path=S/'compiler/rustc/src/main.rs';private_path=N/'native-controls-03/stock-main.rs'
    original=raw(frozen(original_path,freeze));private=raw(frozen(private_path,freeze))
    removed=b'#![expect(unused_crate_dependencies)]\n'
    require(len(original)==2128 and hashlib.sha256(original).hexdigest()=='bfa21d3eced1a7ae4de80cb17e7f8840be640bfdfa96bff32fd6c63282d2c2ab'
        and original.splitlines(keepends=True)[3]==removed and original.count(removed)==1
        and private==b''.join(original.splitlines(keepends=True)[:3]+original.splitlines(keepends=True)[4:])
        and hashlib.sha256(private).hexdigest()=='2830149bab94db375ec164229320f060096bd5c1ba2576045148bfc090fdcd68',
        'independent exact private stock source derivation')
    derivation=dict(source=str(original_path),original_sha256=hashlib.sha256(original).hexdigest(),original_size=len(original),
        destination=str(private_path),derived_sha256=hashlib.sha256(private).hexdigest(),derived_size=len(private),
        removed_line=4,removed_bytes=removed.decode(),policy='remove-exact-cargo-unused-crate-expectation-v1')
    require(native_plan['stock_source_derivation']==native['stock_source_derivation']==native_result['stock_source_derivation']==derivation
        and native_result['stock_source']==native['stock_source'] and native['stock_source']['path']==str(private_path)
        and native['stock_source']['sha256']==derivation['derived_sha256'] and native['stock_source']['size']==len(private),
        'actual private wrapper association')
    failed_proofs=native_result['prior_failed_attempts']
    require(type(failed_proofs) is list and len(failed_proofs)==2
        and failed_proofs==native_plan['prior_failed_attempts'],'both ordered failed histories')
    for failed_proof,(suffix,count,digest,error) in zip(failed_proofs,[
        ('01',5,'af25ceeda3cf32cf63d73b3fd2cee05726267166e0babd58587b884815256f3e',"ValueError('stock build emitted diagnostics')"),
        ('02',6,'c5f873179ed772de997771fd1c89f409876a79ca520d01ff5f8a288c2f6c879f',"ValueError('stock direct private edge is outside exact E2 closure')")],strict=True):
        failed_audit_path=A/('.work/native-controls-failure-verification-'+suffix+'.json')
        failed_audit=read(frozen(failed_audit_path,freeze));failed_work=A/('.work/hir-options-hash-native-controls-'+suffix)
        failed=read(frozen(failed_work/'receipt.json',freeze))
        require(sha(failed_audit_path)==digest and failed_audit['status']==failed_proof['status']=='verified-retained-failure'
            and failed_audit['children']==count and failed_audit['fixture_never_created'] is True
            and failed['status']=='failed' and failed['error']==error and len(failed['commands'])==count
            and failed_audit['receipt_sha256']==sha(failed_work/'receipt.json')==failed_proof['receipt_sha256']
            and failed_proof['evidence']==str(failed_work)
            and failed_proof['source']==str(A/('experiments/hir-options-hash-native-controls-'+suffix))
            and failed_proof['audit']==dict(path=str(failed_audit_path),sha256=digest)
            and failed_proof['actual_children']==count and failed_proof['qualified_children']==0
            and failed_proof['fixture_never_created'] is True and failed_audit['native_roles_and_behavior_qualified'] is False,
            'independent failed-history association')
    require(native_result['qualified_native_children']==len(native['commands'])==20
        and native_result['total_actual_native_children']==31,'eleven failed-history children and twenty qualified children')
    preflight=read(HERE/'metadata-preflight.json')
    require(preflight['status']=='passed' and preflight['inputs_sha256']==sha(HERE/'inputs.json')
        and preflight['snapshot_plan_sha256']==launch['snapshot_plan_sha256']
        and preflight['workload_children']==0 and preflight['work_created'] is False
        and terminal['prerequisites']==preflight['prerequisites'],'retained prerequisite readback')
    require(encoded(preflight['file_table_qualification'])==encoded(file_table_proof)
        and encoded(preflight['file_table_base'])==encoded(compact_freeze['file_table_base'])
        and encoded(preflight['file_table_integrity'])==encoded(compact_freeze['file_table_integrity'])
        and type(preflight['delta_files']) is int and preflight['delta_files']==len(compact_freeze['files']),
        'actual file-table qualification and complete reconstruction preflight binding')
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
    workload_identities=[workload_identity(compiled,'compile',compiled['finished_at'])]
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
        workload_identities.append(workload_identity(row,mode,row['child_finished_at']))
    distinct_workloads(workload_identities)
    require(set(p.name for p in WORK.iterdir())=={'receipt.json','result.json','compile','serial','parallel',
        'linker-command.json','driver-loader-closure.json','source-snapshots','source-snapshots.json','snapshot-plan.json'},'exact three-child evidence membership')
    require(set(p.name for p in (WORK/'compile').iterdir())=={'receipt.json','stdout','stderr'},'compile evidence membership')
    for mode in ['serial','parallel']:
        require(set(p.name for p in (WORK/mode).iterdir())=={'receipt.json','stdout','stderr','probes','validated-readback.json'},'driver evidence membership')
        for index in ['000','001']:
            require(set(p.name for p in (WORK/mode/'probes'/index).iterdir())=={'receipt.json','stdout','stderr'},'probe evidence membership')
    snapshot_proof=snapshots(freeze,terminal,launch,plan)
    artifacts=inventory(ARTIFACTS)
    for path,row in CHECKED.items():require(identity(path)==row['identity'],'audit input changed before completion')
    report=dict(status='verified',receipt_sha256=sha(WORK/'receipt.json'),result_sha256=sha(WORK/'result.json'),
        launch_sha256=args.launch_sha256,inputs_sha256=sha(HERE/'inputs.json'),snapshot_plan_sha256=sha(HERE/'snapshot-plan.json'),
        candidate_revision=REVISION,source_identity=plan['source_identity'],actual_children=3,compilation_count=1,driver_process_count=2,
        contexts_per_process=8,stdout_records_per_process=9,child_pids=pids,workload_identities=workload_identities,
        processes=proofs,unavailable_contemporaneous_observations=missing,
        historical_failed_compiler_children=1,total_actual_hash_children=4,
        failed_predecessor=dict(owner=plan['failed_driver'],receipt_sha256=failed_predecessor['receipt_sha256'],actual_children=1,qualified_children=0),
        continuation_controls=continuation,metadata_plan_reference=METADATA_PLAN_REFERENCE,driver_source_derivation=driver_source_derivation,
        launcher_identity=launcher_identity,wrapper_identity_limitation=dispatch['wrapper_identity_limitation'],
        frozen_files=len(freeze['files']),frozen_bytes=sum(r['size'] for r in freeze['files'].values()),frozen_links=len(freeze['links']),
        full_frozen_byte_rehash=True,full_provider_inventories=True,static_and_actual_loaders_verified=True,compressed_snapshots=snapshot_proof,
        file_table=dict(base=compact_freeze['file_table_base'],integrity=compact_freeze['file_table_integrity'],
            delta_files=len(compact_freeze['files']),qualification=file_table_proof,independent_reconstruction=True),
        native_reconciliation=dict(qualification=native_proof['qualification'],original_failed_receipt_sha256=sha(NATIVE_WORK/'receipt.json'),
            saved_actual_children=20,reconciliation_workload_children=0,historical_failed_children=11),
        artifacts=artifacts,hash_driver_qualified=True,application_qualified=False,performance_measurement=False,runtime_installation=False,
        interpretation='Each serial/parallel process is independently checked. Hashes are not compared across modes. Printed linker command is not a separately observed linker PID. System images retain the stated dyld-cache assumption.',
        started_at=started,finished_at=time.time(),verifier_sha256=sha(Path(__file__).resolve()),
        original_verifier=ORIGINAL_VERIFIER,
        execution='Saved evidence and current-file reads only; no process, compiler, provider, controller or driver execution.')
    with OUT.open('x') as stream:json.dump(report,stream,indent=2,sort_keys=True);stream.write('\n')
    print(json.dumps(dict(path=str(OUT),sha256=sha(OUT),actual_children=3,contexts_per_process=8)))

if __name__=='__main__':main()
