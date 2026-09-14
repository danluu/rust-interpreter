"""Retire only the exact compiler intermediates in the reviewed public inventory."""
from contextlib import ExitStack
from pathlib import Path
import hashlib,json,os,shutil,stat,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
NAME='default-public-cache-retirement-20260914-01'
INVENTORY='default-public-cache-inventory-20260914-01'
EXPECTED={'plan.json':'a96174a7cf2a08baf836416e7644ca9ff77cfb80cd5163aadbb79d62144f6b4c',
          'inventory.json':'e576bcee04ac19cd7578338e21636a1a2ca994a399db38fef09aaa17607eb292',
          'protected.json':'4e1a1ff14634a38ba47d69d3c6ef14fae60eb0ca13f9526137fc85848179c3c7'}
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
    lock=stack.enter_context((ROOT/'.work/benchmark.lock').open('a'));acquire_lock(lock,45);require_space(ROOT,8)
    proofs={};raw=ROOT/'.work'/INVENTORY;outer=ROOT/'.work/experiments'/INVENTORY
    for name,digest in EXPECTED.items():bind(raw/name,digest)
    summary=bind(raw/'summary.json');plan=json.loads((raw/'plan.json').read_text())
    rows=json.loads((raw/'inventory.json').read_text());protected=json.loads((raw/'protected.json').read_text())
    terminal=bind(outer/'status.json');assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==terminal['cwd']==str(ROOT)
    bind(outer/'plan.json',terminal['plan_sha256']);assert sha(outer/'command.log')==terminal['log_sha256'];proofs[str((outer/'command.log').relative_to(ROOT))]=terminal['log_sha256']
    assert summary['status']=='passed' and summary['read_only'] and summary['files_removed']==0
    assert plan['owner']==str(ROOT) and plan['no_current_process_references'] and plan['shared_and_invocation_locks_held']
    assert len(rows)==summary['eligible_files']==28664 and len(protected)==summary['protected_files']==39995
    script=terminal['command'][1];historical=subprocess.check_output(['git','show',plan['source_revision']+':'+script],cwd=ROOT)
    assert hashlib.sha256(historical).hexdigest()==plan['script_sha256']
    roots=[ROOT/r['path'] for r in plan['roots']];assert len(set(roots))==13 and {r['path'] for r in plan['identities']}=={r['path'] for r in plan['roots']}
    for item in plan['identities']:
        root=ROOT/item['path'];assert root==ROOT/'.work/interpreter-workspaces'/item['tool_key']/item['namespace'] and root.resolve(strict=True)==root
        assert item['project'] in ['nushell','ruff'] and item['test_body'] is True
        invocation=stack.enter_context((root/'invocation.lock').open('r+'));acquire_lock(invocation,45)
    for project,item in plan['sources'].items():
        source=Path(item['source']);assert source==ROOT/'.work/sources'/project
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==item['pin']
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
    assert all(sha(ROOT/p)==h for p,h in protected.items())
    process=subprocess.run(['ps','-axo','pid,ppid,lstart,tty,command'],capture_output=True,text=True,check=True)
    assert not any(str(root) in line for root in roots for line in process.stdout.splitlines()[1:])
    checks=[check_open(root) for root in roots]
    for row in rows:
        p=ROOT/row['path'];assert any(p.is_relative_to(root/'target') for root in roots)
        now=identity(p);assert all(now[k]==row[k] for k in ['device','inode','size','mtime_ns','mode'])
    work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
    before=shutil.disk_usage(ROOT).free;started=time.time()
    write(work/'plan.json',dict(owner=str(ROOT),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),script_sha256=sha(Path(__file__)),inventory=INVENTORY,inventory_hashes=EXPECTED,proofs=proofs,roots=[str(p.relative_to(ROOT)) for p in roots],open_checks=checks,no_current_process_references=True,files=len(rows),protected_files=len(protected),free_before=before,started_at=started,
        scope='Only the 28,664 reviewed nonexecutable compiler intermediates in 13 explicit idle default public source caches. Revalidated pinned source ownership, immutable installed-tool hashes, exact inventory identities, shared/invocation locks and current process/open-file absence. Preserve all 39,995 other files, including every bytecode, executable and installed tool. No historical timing completion is inferred and no private, peer or fresh measurement namespace is selected.'))
    for root in roots:check_open(root)
    assert all(sha(ROOT/p)==h for p,h in proofs.items())
    removed=0
    for row in rows:
        p=ROOT/row['path'];now=identity(p)
        assert all(now[k]==row[k] for k in ['device','inode','size','mtime_ns','mode'])
        p.unlink();removed+=1
        if removed%2000==0:write(work/'progress.json',dict(files_removed=removed,total=len(rows)))
    assert all(sha(ROOT/p)==h for p,h in protected.items())
    assert all(sha(ROOT/p)==h for p,h in proofs.items())
    result=dict(status='passed',files_removed=removed,logical_bytes_removed=sum(r['size'] for r in rows),free_before=before,free_after=shutil.disk_usage(ROOT).free,started_at=started,finished_at=time.time(),protected_files=len(protected),all_protected_hashes_unchanged=True,raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),inventory=INVENTORY,inventory_hashes=EXPECTED,performance_measurement=False)
    write(work/'summary.json',result);print(json.dumps(result),flush=True)
