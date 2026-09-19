#!/usr/bin/env python3
"""Current source/SDK/seed admission; executes metadata probes only."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import stat
import struct
import sys
import tarfile
import time

HERE=Path(__file__).resolve().parent
OWNER=HERE.parents[2]
NAMESPACE=OWNER/'.work/hir-options-hash-compiler-01'
SOURCE=NAMESPACE/'source'
OLD=Path('/Users/danluu/dev/rustc-hir-capture-check-20260913')
WORK=OWNER/'.work/hir-options-hash-compiler-metadata-03'
HOST='aarch64-apple-darwin'
ACQUIRE=OWNER/'experiments/hir-options-hash/build-01'
ACQUIRED=OWNER/'.work/hir-options-hash-acquisition-01/acquired.json'
SDK=Path('/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk')
CLANG=Path('/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang')
LLVM='cea272fa356e94bd2ee2cadf376630aa0683867a'
sys.path[:0]=[str(OWNER/'experiments/stable-cgu'),str(OWNER/'scripts')]
import owned_stage as owned
import custom_cargo_libraries as loaders

def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return owned.sha(Path(p))
def stamp(p):
 s=Path(p).lstat();return [s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink]
def file(p):
 p=Path(p);assert p.resolve(strict=True)==p and stat.S_ISREG(p.lstat().st_mode),p
 s=stamp(p);digest=sha(p);assert stamp(p)==s
 return dict(sha256=digest,stamp=s)
def inventory(root,contents):
 assert root.resolve(strict=True)==root and root.is_dir()
 result={'':dict(kind='directory',stamp=stamp(root))}
 for parent,dirs,files in os.walk(root,followlinks=False):
  for name in sorted(dirs+files):
   p=Path(parent)/name;s=p.lstat();key=str(p.relative_to(root))
   if stat.S_ISLNK(s.st_mode):
    resolved=p.resolve(strict=True)
    assert resolved.is_relative_to(root),('SDK link escapes frozen SDK',p,resolved)
    result[key]=dict(kind='link',stamp=stamp(p),target=os.readlink(p),resolved=str(resolved))
   elif stat.S_ISREG(s.st_mode):result[key]=dict(kind='file',**(file(p) if contents else dict(stamp=stamp(p))))
   else:
    assert stat.S_ISDIR(s.st_mode);result[key]=dict(kind='directory',stamp=stamp(p))
 return result

def macho(path,drop_self_id=False):
 """Pure planning parser; actual otool closure must agree before admission."""
 data=Path(path).read_bytes();offset=0
 magic=data[:4]
 if magic in [b'\xca\xfe\xba\xbe',b'\xca\xfe\xba\xbf']:
  count=struct.unpack_from('>I',data,4)[0];assert 0<count<32
  width=32 if magic[-1]==0xbf else 20
  matches=[]
  for i in range(count):
   cpu=struct.unpack_from('>I',data,8+i*width)[0]
   if cpu==0x100000c:
    offset=struct.unpack_from('>Q' if width==32 else '>I',data,16+i*width)[0];matches.append(offset)
  assert len(matches)==1
 assert data[offset:offset+4]==b'\xcf\xfa\xed\xfe'
 assert struct.unpack_from('<I',data,offset+4)[0]==0x100000c
 count,size=struct.unpack_from('<II',data,offset+16);position=offset+32;end=position+size
 assert end<=len(data) and count<4096
 dependencies=[];rpaths=[]
 for _ in range(count):
  kind,width=struct.unpack_from('<II',data,position);assert width>=8 and position+width<=end
  if kind in [0xc,0xd,0x80000018,0x8000001f,0x20,0x80000023,0x8000001c]:
   start=struct.unpack_from('<I',data,position+8)[0];assert 12<=start<width
   token=data[position+start:position+width].split(b'\0',1)[0].decode();assert token
   if kind!=0xd or not drop_self_id:(rpaths if kind==0x8000001c else dependencies).append(token)
  position+=width
 assert position==end and dependencies
 return dependencies,rpaths

def planned_closure(path,children,environment,drop_self_id=False):
 def inspect(argv,*,text):
  assert text is True
  children.append(dict(argv=argv,cwd=str(OWNER),environment=environment,expected=[0]))
  deps,rpaths=macho(argv[-1],drop_self_id)
  if argv[-2]=='-L':return str(argv[-1])+':\n'+''.join('\t'+x+' (compatibility version 0, current version 0)\n' for x in deps)
  assert argv[-2]=='-l'
  return ''.join('cmd LC_RPATH\n path '+x+' (offset 12)\n' for x in rpaths)
 identity,state=loaders.library_closure(Path(path),HOST,inspect=inspect)
 return dict(identity=identity,state=state)

def linker_loads(argv,raw):
 # otool -L includes LC_ID_DYLIB. This is an identity, not a dependency;
 # retain the original stream and remove only the source-proved self entry
 # for the legacy closure reader. Actual tokens must match frozen Mach-O.
 if argv[-2]!='-L':return raw
 lines=raw.splitlines(keepends=True)
 tokens=[line.strip().split(' (compatibility version ',1)[0] for line in lines if line.startswith('\t')]
 all_tokens,_=macho(argv[-1]);loads,_=macho(argv[-1],True)
 assert tokens==all_tokens
 ids=list(all_tokens)
 for token in loads:ids.remove(token)
 assert len(ids)<=1 and not any(token in loads for token in ids),'self-ID aliases a real dependency'
 return ''.join(line for line in lines if not (line.startswith('\t') and line.strip().split(' (compatibility version ',1)[0] in ids))

from linker_parser import parse as linker_probe

def seed_members(copies):
 result={}
 expanded_bytes=0;member_count=0
 for row in copies:
  p=Path(row['destination'])
  if not p.name.endswith('.tar.xz'):continue
  assert sha(p)==row['sha256']
  if p.name.startswith(('cargo-beta','rust-std-beta','rustc-beta')):component=p.name.split('-beta')[0];root='stage0'
  elif p.name.startswith('rust-dev-'):component='rust-dev';root='ci-llvm'
  else:
   # Historical seed bundle also contains unused rustfmt/nightly archives.
   # Their full hashes stay frozen, but these eight stages may not extract or
   # execute them without a separate current provider admission.
   result[str(p)]=dict(sha256=row['sha256'],active=False,members={});continue
  if component=='rust-std':component+='-'+HOST
  members={}
  with tarfile.open(p,mode='r|xz') as tar:
   seen=set()
   for member in tar:
    member_count+=1;expanded_bytes+=member.size
    assert member_count<=20000 and expanded_bytes<=2*2**30
    parts=Path(member.name).parts
    assert member.name not in seen and not member.name.startswith('/') and '..' not in parts
    seen.add(member.name)
    if len(parts)<3 or parts[1]!=component or member.isdir():continue
    name='/'.join(parts[2:])
    # Bootstrap copies this component. Only executable/library/compiler-rt
    # payload is a provider; package docs/manifests are bound by archive hash.
    if not name.startswith(('bin/','lib/','libexec/','include/','compiler-rt/')):continue
    if member.isfile():
     stream=tar.extractfile(member);digest=hashlib.file_digest(stream,'sha256').hexdigest();stream.close()
     old=OLD/'build'/HOST/root/name
     # rustfmt uses the matching nightly compiler runtime, but bootstrap copies
     # only its rustc runtime libraries; unrelated nightly tools are not needed.
     if root=='rustfmt' and component=='rustc' and not old.is_file():continue
     assert old.resolve(strict=True)==old and old.is_file() and sha(old)==digest,(p,name,old)
     members[name]=dict(kind='file',bytes=member.size,sha256=digest,existing=str(old),current=file(old))
    elif member.issym():
     old=OLD/'build'/HOST/root/name
     assert old.is_symlink() and os.readlink(old)==member.linkname,(p,name)
     members[name]=dict(kind='link',target=member.linkname,existing=str(old),stamp=stamp(old))
    else:raise AssertionError(('unexpected provider archive member',member.name,member.type))
  assert members
  result[str(p)]=dict(sha256=row['sha256'],active=True,component=component,output_root=root,members=members)
 return result

def guard(plan,freeze,full):
 assert loaders.platform_identity()==plan['platform']
 for name,row in freeze['files'].items():
  p=Path(name);assert p.resolve(strict=True)==p and stamp(p)==row['stamp'],name
  if full:assert sha(p)==row['sha256'],name
 for name,row in freeze['links'].items():
  p=Path(name);assert p.is_symlink() and stamp(p)==row['stamp'] and os.readlink(p)==row['target'] and str(p.resolve(strict=True))==row['resolved'],name
 for name,expected in plan['configuration'].items():
  p=Path(name);assert not p.is_symlink() and (sha(p) if p.is_file() else None)==expected,name
 for name,resolved in plan['routes'].items():assert str(Path(name).resolve(strict=True))==resolved,name
 acquired=read(ACQUIRED)
 for prefix,records in [(SOURCE,acquired['source_files']),(SOURCE/'library/backtrace',acquired['backtrace_files'])]:
  for name,row in records.items():
   p=prefix/name
   if row['mode']=='120000':assert p.is_symlink() and os.readlink(p)==row['target']
   else:
    assert p.resolve(strict=True)==p
    if full:assert sha(p)==row['sha256'],p
 if full:
  now=inventory(SDK,True);assert now==plan['sdk_inventory']

class Stage:
 def __init__(self,digest):
  assert sha(HERE/'inputs.json')==digest
  self.freeze=read(HERE/'inputs.json');assert sha(HERE/'plan.json')==self.freeze['plan_sha256']
  self.plan=read(HERE/'plan.json')
  assert Path.cwd()==OWNER and str(Path(sys.executable).resolve(strict=True))==self.freeze['python']
  assert sha(Path(sys.executable).resolve(strict=True))==self.freeze['files'][self.freeze['python']]['sha256']
  expected=self.freeze['launch_environment'];actual=dict(os.environ)
  extra=set(actual)-set(expected)
  assert all(actual.get(k)==v for k,v in expected.items()) and extra<={'__CF_USER_TEXT_ENCODING'}
  if extra:
   cf=actual['__CF_USER_TEXT_ENCODING'].split(':')
   assert len(cf)==3 and all(re.fullmatch(r'(?:0[xX][0-9a-fA-F]{1,8}|[0-9]{1,10})',v) for v in cf)
   assert int(cf[0],16 if cf[0].lower().startswith('0x') else 10)==os.getuid()==501
  self.environment=actual
  for module in list(sys.modules.values()):
   path=getattr(module,'__file__',None)
   if path and path.startswith('/Users/danluu/dev/'):
    assert str(Path(path).resolve(strict=True)) in self.freeze['files'],path
  assert not WORK.exists();WORK.mkdir();(WORK/'commands').mkdir()
  self.receipt=dict(status='waiting',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),commands=[],compiler_builds=0,source=str(SOURCE),candidate_revision=self.plan['candidate_revision'])
  self.save()
 def save(self):owned.write(WORK/'receipt.json',self.receipt)
 def command(self,argv,cwd=OWNER,expected=(0,)):
  row=self.plan['children'][len(self.receipt['commands'])]
  assert argv==row['argv'] and str(cwd)==row['cwd'] and list(expected)==row['expected']
  assert dict(os.environ)==self.environment
  guard(self.plan,self.freeze,False);owned.disk(OWNER,9)
  out=WORK/'commands'/f'{len(self.receipt["commands"]):03}'
  try:owned.run(argv,cwd=cwd,env=row['environment'],out=out,expected=expected,capacity_root=OWNER)
  finally:
   if (out/'receipt.json').is_file():
    child=read(out/'receipt.json');self.receipt['commands'].append(dict(path=str(out/'receipt.json'),sha256=sha(out/'receipt.json'),pid=child.get('pid'),command=argv));self.save()
  raw=(out/'stdout').read_bytes();err=(out/'stderr').read_bytes()
  if 'stdout' in row:assert raw.decode()==row['stdout'],argv
  if 'stderr' in row:assert err.decode()==row['stderr'],argv
  return raw,err
 def run(self):
  try:
   with owned.workload_lock(owned.CANONICAL_LOCK,600):
    self.receipt.update(status='running',admitted_at=time.time(),free_bytes_before=owned.disk(OWNER,24));self.save()
    guard(self.plan,self.freeze,True)
    # Source/seed provenance was fully checked by acquisition and is repeated
    # here, including a fresh archive member versus current provider proof.
    assert seed_members(read(ACQUIRED)['copies'])==self.plan['seeds']
    for row in self.plan['prefix_children']:self.command(row['argv'],Path(row['cwd']),tuple(row['expected']))
    closures={}
    for name,path in self.plan['closure_roots']:
     def inspect(argv,*,text):
      assert text is True
      out,err=self.command(argv);assert not err
      return linker_loads(argv,out.decode()) if name=='ld' else out.decode()
     identity,state=loaders.library_closure(Path(path),HOST,inspect=inspect)
     closures[name]=dict(identity=identity,state=state)
     assert closures[name]==self.plan['closures'][name],name
    for row in self.plan['suffix_children']:
     out,err=self.command(row['argv'],Path(row['cwd']),tuple(row['expected']))
     if row.get('llvm_version_probe'):
      assert not err and out.decode()==self.plan['llvm']['provider_version']+'\n'
      self.llvm_version=self.plan['llvm']['numeric_version']
      self.llvm_provider_version=out.decode().strip()
     if row.get('linker_probe'):
      assert not out
      child=read(self.receipt['commands'][-1]['path'])
      owned.write(WORK/'linker-probe.json',linker_probe(err,child['pid'],self.plan['linker_expected_loaded']))
    assert len(self.receipt['commands'])==len(self.plan['children'])
    guard(self.plan,self.freeze,True)
    owned.write(WORK/'metadata.json',dict(status='metadata-qualified-not-built',candidate_revision=self.plan['candidate_revision'],source_identity=read(ACQUIRED)['source_identity'],closures=closures,seeds=self.plan['seeds'],sdk_inventory_sha256=hashlib.sha256(json.dumps(self.plan['sdk_inventory'],sort_keys=True).encode()).hexdigest(),platform=self.plan['platform'],llvm_version=self.llvm_version,llvm_provider_version=self.llvm_provider_version,network_block=self.plan['network_block'],build_environment=self.plan['build_environment']))
    self.receipt.update(status='passed',metadata_sha256=sha(WORK/'metadata.json'),free_bytes_after=owned.disk(OWNER,9))
  except BaseException as error:self.receipt.update(status='failed',error=repr(error));raise
  finally:self.receipt['finished_at']=time.time();self.save()

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--inputs-sha256',required=True);args=parser.parse_args()
 assert sys.dont_write_bytecode and not sys.flags.optimize
 Stage(args.inputs_sha256).run()
if __name__=='__main__':main()
