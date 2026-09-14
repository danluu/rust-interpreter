"""Inventory explicitly bounded idle public default caches; never removes files."""
from contextlib import ExitStack
from pathlib import Path
import hashlib,json,os,shutil,stat,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write
NAME='default-public-cache-inventory-20260914-01'
STD='bd27cc0f910e0c93a9a6cf088789ef526d36a8697a7717e08d7585f5d19467ef'
SCOPES=[
 ('nushell','nu-protocol',True,'9561f35af8092c0a381df979',[
  'f9560ff06be72ee1dd3627d107d6992589adf9514972816de67f35cc31ab9af4',
  '7da12741d9c15fd05818d892973a34009bd2b8ff9356d31cc69213c5c1960446',
  '68c1b9ad4ca041202480f2838e54ca16f88cc9a07030733434c00745190675c5',
  '5b880fb22b80234e4c0366ad0f7aa7d653aff55279fa1d23cd607d7d468ee8fb']),
 ('nushell','nu-protocol',False,'3b168097df4648b685804584',[
  '7da12741d9c15fd05818d892973a34009bd2b8ff9356d31cc69213c5c1960446']),
 ('nushell','nu-parser',True,'32a94c81432b438b599d1258',[
  '4279c132175e5fdfdae1518d88dcc784a26bc4031afd23bf85b1148ae894a121']),
 ('nushell','nu-parser',False,'7bd6a0125f8991c90ada3e0c',[
  '94f5660371c071c5385601089b28d2a4895793eecd8f721e0530f9c74816e724',
  '4611421adc4cf13428e4fd76dcd9b74ab69e3b5765d40b7dd86b13e672ea507d']),
 ('ruff','ruff_linter',True,'0ddec0702ff037a05cc5ab52',[
  '787a98117e59e093195f9860ca8380951c730e997574b4fb9212a2794feeb404',
  '4279c132175e5fdfdae1518d88dcc784a26bc4031afd23bf85b1148ae894a121',
  '9408cce0aa25e0b33ead2d84f325890db94312553677846b4eea37fff4aafa51',
  '2f1f80699b1b8fae908c9a2b1d2faa45c6d8e81c347ab4c11559c343bc5ee94e',
  'b9c1a08dd9af0e1ab8245aee4c5cc2c65af9eb816ad6aa8adb51edfd4e00e15b']),
]
PINS={'nushell':'9d3157963241cf89447119d34d6e887859f5e7e8','ruff':'d136bd8d002a648de5f344df602e492658306f1e'}
def identity(path):
    s=path.lstat()
    assert stat.S_ISREG(s.st_mode) and path.resolve(strict=True)==path,path
    return dict(device=s.st_dev,inode=s.st_ino,size=s.st_size,blocks=s.st_blocks,
                links=s.st_nlink,mtime_ns=s.st_mtime_ns,mode=s.st_mode)

def check_open(root):
    check=subprocess.run(['lsof','-Fpn','+D',str(root)],text=True,capture_output=True)
    assert not check.stderr and check.returncode in [0,1], (root,check.stderr)
    fields=check.stdout.splitlines()
    # Holding our exact invocation lock is expected; every other open file fails.
    if root.parent.parent==ROOT/'.work/interpreter-workspaces':
        assert len(fields)==3 and fields[0]=='p'+str(os.getpid()) and fields[1].startswith('f') and fields[1][1:].isdigit() and fields[2]=='n'+str(root/'invocation.lock'), (root,fields)
    else:
        assert not fields and check.returncode==1, (root,fields)
    return dict(path=str(root.relative_to(ROOT)),returncode=check.returncode,
                only_open_file_is_own_invocation_lock=True,owner_pid=os.getpid())

def bind(path, expected=None):
    assert path.resolve(strict=True)==path and path.is_file(),path
    digest=sha(path)
    if expected is not None: assert digest==expected,path
    key=str(path.relative_to(ROOT))
    assert key not in proofs or proofs[key]==digest,path
    proofs[key]=digest
    return json.loads(path.read_text()) if path.suffix=='.json' else digest

with ExitStack() as stack:
    lock=stack.enter_context((ROOT/'.work/benchmark.lock').open('a'));acquire_lock(lock,45)
    proofs={};sources={};roots=[];identities=[]
    for project,pin in PINS.items():
        source=ROOT/'.work/sources'/project;marker=bind(source/'.rust-interp-owned.json')
        assert marker['owner']==str(ROOT) and marker['revision']==pin
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==pin
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
        bind(source/'Cargo.toml');bind(source/'Cargo.lock');sources[project]=dict(pin=pin,source=str(source))
    for project,package,std,namespace,keys in SCOPES:
        manifest=ROOT/'.work/sources'/project/'Cargo.toml'
        value='shared-entries-v1\0'+str(manifest)+'\0'+package+'\0True'
        if std:value+='\0std-mir:'+STD
        assert hashlib.sha256(value.encode()).hexdigest()[:24]==namespace
        for key in keys:
            root=ROOT/'.work/interpreter-workspaces'/key/namespace
            assert root.resolve(strict=True)==root and root.is_dir()
            ready=bind(ROOT/'.work/interpreter-tools'/key/'ready.json')
            assert set(ready)=={'rust-interp-vm','rust-interp-mir-export'}
            for file,digest in ready.items():bind(ROOT/'.work/interpreter-tools'/key/file,digest)
            invocation=stack.enter_context((root/'invocation.lock').open('r+'));acquire_lock(invocation,45)
            roots.append(root);identities.append(dict(path=str(root.relative_to(ROOT)),project=project,package=package,test_body=True,std_mir=std,namespace=namespace,tool_key=key))
    assert len(roots)==len(set(roots))==13
    process=subprocess.run(['ps','-axo','pid,ppid,lstart,tty,command'],capture_output=True,text=True,check=True)
    matches=[line for line in process.stdout.splitlines()[1:] if any(str(root) in line for root in roots)]
    assert not matches,'a current process references a selected cache'
    raw=ROOT/'.work'/NAME;raw.mkdir(exist_ok=False)
    eligible=[];protected=dict(proofs);open_checks=[];sizes=[]
    for root in roots:
        open_checks.append(check_open(root));start=len(eligible)
        for p in root.rglob('*'):
            assert not p.is_symlink(),p
            if not p.is_file():continue
            info=identity(p);parts=p.relative_to(root).parts;compiler=False;incremental=False
            for prefix in [('target','debug'),('target','aarch64-apple-darwin','debug')]:
                if parts[:len(prefix)]==prefix and len(parts)>len(prefix):
                    section=parts[len(prefix)];compiler=section in ['incremental','build','deps'];incremental=section=='incremental'
            remove=compiler and (incremental or p.suffix in ['.o','.rlib','.rmeta'])
            remove=remove and not info['mode']&0o111 and p.suffix not in ['.rbc','.dylib','.a','.rs','.toml','.lock'] and '.rbc.' not in p.name
            relative=str(p.relative_to(ROOT))
            if remove and relative not in protected:eligible.append(dict(path=relative,**info))
            else:protected[relative]=sha(p)
        selected=eligible[start:];sizes.append(dict(path=str(root.relative_to(ROOT)),files=len(selected),logical_bytes=sum(r['size'] for r in selected),allocated_bytes=sum(r['blocks']*512 for r in selected)))
        print('inventory',len(sizes),13,sizes[-1]['files'],sizes[-1]['allocated_bytes'],flush=True)
    write(raw/'inventory.json',eligible);write(raw/'protected.json',protected)
    write(raw/'plan.json',dict(owner=str(ROOT),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),script_sha256=sha(Path(__file__)),sources=sources,identities=identities,roots=sizes,open_checks=open_checks,no_current_process_references=True,shared_and_invocation_locks_held=True,
        scope='Read-only inventory of 13 explicit default public Nushell/Ruff compile caches. Ownership is established by this checkout-owned pinned source, exact public manifest/package/standard-MIR namespace reconstruction, canonical cache roots and immutable installed-tool readiness hashes. Historical benchmark completion is not inferred: these are idle default caches, outside the retained fresh measurement namespaces. Only nonexecutable compiler intermediates are candidates; bytecode, executables, installed tools, every other cache file, sources, private or peer paths are protected. No deletion occurs in this inventory.'))
    assert all(sha(ROOT/p)==h for p,h in proofs.items())
    result=dict(status='passed',read_only=True,files_removed=0,roots=13,eligible_files=len(eligible),logical_bytes=sum(r['size'] for r in eligible),allocated_bytes=sum(r['blocks']*512 for r in eligible),protected_files=len(protected),free_bytes=shutil.disk_usage(ROOT).free,raw=str(raw.relative_to(ROOT)),plan_sha256=sha(raw/'plan.json'),inventory_sha256=sha(raw/'inventory.json'),protected_sha256=sha(raw/'protected.json'),performance_measurement=False)
    write(raw/'summary.json',result);print(json.dumps(result),flush=True)
