from contextlib import ExitStack
from pathlib import Path
import json, os, shutil, stat, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write

NAME='scalar-copy-fre-cache-retirement-01'
RUNS={'direct-operands-edit-token-01':74372,
      'direct-operands-screen-token-01':86773,'immediate-shifts-screen-token-01':93631}
PIN='e0df0b010b156b030a02f073588d28703f4267f3'

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

with ExitStack() as stack:
    lock=stack.enter_context((ROOT/'.work/benchmark.lock').open('a'));acquire_lock(lock,45)
    active=json.loads((ROOT/'.work/experiments/scalar-copy-operands-full-01/status.json').read_text())
    assert active['status']=='finished' and active['returncode']==1
    assert not (ROOT/'.work/scalar-copy-operands-edit-nushell-01').exists()
    roots=[];proofs={};process_checks=[]
    for run,pid in RUNS.items():
        base=ROOT/'.work'/run
        status_name='direct-operands-full-01' if run=='direct-operands-edit-token-01' else run
        status_path=ROOT/'.work/experiments'/status_name/'status.json'
        result_path=ROOT/'results'/run/'summary.json'
        status=json.loads(status_path.read_text());result=json.loads(result_path.read_text())
        plan=json.loads((base/'plan.json').read_text())
        assert status['status']=='finished' and status['returncode']==0 and status['child_pid']==pid
        assert status['owner']==plan['owner']==str(ROOT) and plan['case']['package']=='fre-kernels' and plan['revision']==PIN
        assert result['status']=='passed' and result['commands']==(154 if run=='direct-operands-edit-token-01' else 40) and result['source_restored'] and not result.get('private',False)
        for name in ['plan','records','transitions','space']:
            digest=result[name+'_sha256']
            path=base/(name+'.json');assert sha(path)==digest;proofs[str(path.relative_to(ROOT))]=digest
        proofs[str(status_path.relative_to(ROOT))]=sha(status_path)
        proofs[str(result_path.relative_to(ROOT))]=sha(result_path)
        for old_pid in [status['supervisor_pid'],pid]:
            check=subprocess.run(['ps','-p',str(old_pid),'-o','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
            # A recycled unrelated PID is retained as read-only evidence, never controlled.
            process_checks.append(dict(pid=old_pid,returncode=check.returncode,stdout=check.stdout))
            assert str(base) not in check.stdout and run not in check.stdout
        if run=='direct-operands-edit-token-01':
            parent_records_path=ROOT/'.work/direct-operands-full-01/records.json'
            parent_records=json.loads(parent_records_path.read_text())
            assert len(parent_records)==1 and parent_records[0]['pid']==74395 and parent_records[0]['returncode']==0
            assert parent_records[0]['summary_sha256']==sha(result_path)
            proofs[str(parent_records_path.relative_to(ROOT))]=sha(parent_records_path)
        records=json.loads((base/'records.json').read_text());assert len(records)==result['commands']
        namespaces=sorted({x['launch']['workspace_path'] for x in records if 'launch' in x})
        assert len(namespaces)==4
        for namespace in namespaces:
            path=Path(namespace)
            assert path.resolve(strict=True)==path and path.parent.parent==ROOT/'.work/interpreter-workspaces'
            assert path.parent.name in plan['tools'].values()
            roots.append(path)
        native_paths=set()
        for row in records:
            if row['mode'] in ['native','native_lines','check']:
                command=row['command'];assert command.count('--target-dir')==1
                path=Path(command[command.index('--target-dir')+1])
                assert path==base/row['mode'] and path.resolve(strict=True)==path
                native_paths.add(path)
        assert len(native_paths)==(3 if run=='direct-operands-edit-token-01' else 1)
        roots.extend(sorted(native_paths))
    assert len(set(roots))==17
    marker=ROOT/'.work/sources/fre/.rust-interp-owned.json'
    owner=json.loads(marker.read_text());assert owner['owner']==str(ROOT) and owner['revision']==PIN
    proofs[str(marker.relative_to(ROOT))]=sha(marker)
    for root in roots:
        if root.parent.parent==ROOT/'.work/interpreter-workspaces':
            invocation=stack.enter_context((root/'invocation.lock').open('r+'));acquire_lock(invocation,45)
    work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
    rows=[];protected=dict(proofs);open_checks=[];sizes=[]
    for root in roots:
        open_checks.append(check_open(root))
        count_before=len(rows);bytes_before=sum(r['size'] for r in rows)
        for path in root.rglob('*'):
            assert not path.is_symlink(),path
            if not path.is_file():continue
            info=identity(path);relative=path.relative_to(root);parts=relative.parts
            compiler=False;incremental=False
            for prefix in [('debug',),('target','debug'),('target','aarch64-apple-darwin','debug')]:
                if parts[:len(prefix)]==prefix and len(parts)>len(prefix):
                    section=parts[len(prefix)]
                    compiler=section in ['incremental','build','deps'];incremental=section=='incremental'
            remove=compiler and (incremental or path.suffix in ['.o','.rlib','.rmeta'])
            remove=remove and not info['mode'] & 0o111
            remove=remove and path.suffix not in ['.rbc','.dylib','.a','.rs','.toml','.lock'] and '.rbc.' not in path.name
            key=str(path.relative_to(ROOT))
            if remove: rows.append(dict(path=key,**info))
            else: protected[key]=sha(path)
        sizes.append(dict(path=str(root.relative_to(ROOT)),files=len(rows)-count_before,
                          logical_bytes=sum(r['size'] for r in rows)-bytes_before))
        print(json.dumps(sizes[-1]),flush=True)
    # Protect saved evidence outside the three previously retired native cache trees.
    for run in RUNS:
        base=ROOT/'.work'/run
        for path in base.rglob('*'):
            if not path.is_file() or path.relative_to(base).parts[0] in ['native','native_lines','check']:continue
            assert not path.is_symlink();protected[str(path.relative_to(ROOT))]=sha(path)
    write(work/'inventory.json',rows);write(work/'protected.json',protected)
    before=shutil.disk_usage(ROOT).free;started=time.time()
    write(work/'plan.json',dict(owner=str(ROOT),script_sha256=sha(Path(__file__)),completed_runs=RUNS,
        roots=sizes,process_checks=process_checks,open_checks=open_checks,files=len(rows),
        logical_bytes=sum(r['size'] for r in rows),free_before=before,started_at=started,
        scope='Twelve exact custom and five native cache roots from three completed fre comparisons of parked candidates. Nonexecutable incremental files and .o/.rlib/.rmeta in build/deps only. All other namespace files and saved case evidence hashed and preserved. No active, private, installed-tool or unrelated worktree cache. Shared and invocation locks held.'))
    assert all(sha(ROOT/p)==h for p,h in proofs.items())
    for root in roots:
        check_open(root)
    for row in rows:
        path=ROOT/row['path'];current=identity(path)
        assert all(current[k]==row[k] for k in ['device','inode','size','mtime_ns','mode']), (path,current,row)
        # Unlinking an earlier hard link changes st_nlink, not this file's identity or bytes.
        path.unlink()
    assert all(sha(ROOT/p)==h for p,h in protected.items())
    result=dict(status='passed',files_removed=len(rows),logical_bytes_removed=sum(r['size'] for r in rows),
        free_before=before,free_after=shutil.disk_usage(ROOT).free,started_at=started,finished_at=time.time(),
        protected_files=len(protected),all_protected_hashes_unchanged=True,
        inventory_sha256=sha(work/'inventory.json'),protected_manifest_sha256=sha(work/'protected.json'),
        plan_sha256=sha(work/'plan.json'),raw=str(work.relative_to(ROOT)),performance_measurement=False)
    write(work/'summary.json',result);print(json.dumps(result),flush=True)
