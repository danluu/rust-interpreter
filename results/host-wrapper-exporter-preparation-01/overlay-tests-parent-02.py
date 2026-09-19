import ast,hashlib,json,os,resource,subprocess,sys,time
from pathlib import Path
Q=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913');R=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918');H=Q/'experiments/host-wrapper-exporter-01';OUT=Q/'results/host-wrapper-exporter-overlay-tests-02'
OUT.mkdir(exist_ok=False);(OUT/'tmp').mkdir()
def row(p):
 b=p.read_bytes();s=p.lstat();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),identity=[s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns])
def write(n,d):(OUT/n).write_text(json.dumps(d,sort_keys=True,indent=2)+'\n')
paths={H/'common.py',H/'test_source_overlay.py',Path(__file__).resolve()}
before={str(p):row(p) for p in sorted(paths)};write('source-before.json',before)
assert sum(v['bytes'] for v in before.values())<8*1024*1024
child=r'''
import atexit,hashlib,json,os,resource,runpy,sys
from pathlib import Path
out=Path(sys.argv[1]);test=Path(sys.argv[2]);sources=json.loads((out/'source-before.json').read_text())
resource.setrlimit(resource.RLIMIT_CPU,(30,30));resource.setrlimit(resource.RLIMIT_FSIZE,(4*1024*1024,4*1024*1024))
def deny(event,args):
 if event in ('subprocess.Popen','os.system','os.posix_spawn','os.kill','os.killpg'):raise RuntimeError('pure test denied '+event)
sys.addaudithook(deny)
def finish():
 rows={}
 for name,m in list(sys.modules.items()):
  p=getattr(m,'__file__',None)
  if not p:continue
  p=Path(p).resolve()
  if p.suffix=='.py' and str(p).startswith('/Users/danluu/dev/'):
   if str(p) not in sources:raise RuntimeError('undeclared pure source '+str(p))
   b=p.read_bytes();h=hashlib.sha256(b).hexdigest()
   if h!=sources[str(p)]['sha256']:raise RuntimeError('pure source changed')
   rows[str(p)]=h
 (out/'loaded-sources.json').write_text(json.dumps(rows,sort_keys=True,indent=2)+'\n')
atexit.register(finish)
sys.argv=[str(test)];runpy.run_path(str(test),run_name='__main__')
'''
cmd=[sys.executable,'-B','-c',child,str(OUT),str(H/'test_source_overlay.py')]
env={'PATH':'/opt/homebrew/bin:/usr/bin:/bin','HOME':os.environ['HOME'],'TMPDIR':str(OUT/'tmp'),'PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0'}
record=dict(status='running',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),cwd=str(H),command=cmd,environment=env,source_files=len(before),limits=dict(cpu_seconds=30,raw_file_bytes=4*1024*1024,total_owned_bytes=64*1024*1024,child_processes='denied by audit hook'))
with (OUT/'stdout').open('wb') as stdout,(OUT/'stderr').open('wb') as stderr:
 p=subprocess.Popen(cmd,cwd=H,env=env,stdout=stdout,stderr=stderr);record['child_pid']=p.pid;write('record.json',record);rc=p.wait()
record.update(status='closed',returncode=rc,finished_at=time.time(),normal_wait_completed=True,child_maxrss=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
after={str(p):row(p) for p in sorted(paths)};write('source-after.json',after);record['sources_unchanged']=before==after
record['owned_bytes']=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file());write('record.json',record)
assert rc==0,(rc,(OUT/'stderr').read_text());assert before==after;assert (OUT/'loaded-sources.json').is_file();assert record['owned_bytes']<64*1024*1024
raw=(OUT/'stderr').read_text();assert 'Ran 8 tests' in raw and raw.rstrip().endswith('OK');assert not any((OUT/'tmp').iterdir())
print(json.dumps(dict(status='passed',record=row(OUT/'record.json'),pid=record['pid'],child_pid=p.pid,sources=len(before),loaded=len(json.loads((OUT/'loaded-sources.json').read_text()))),sort_keys=True))
