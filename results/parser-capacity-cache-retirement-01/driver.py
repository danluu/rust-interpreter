from contextlib import ExitStack
from pathlib import Path
import json, os, shutil, stat, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write

NAME='parser-capacity-cache-retirement-01'
RUNS={'parser-jit-capacity-screen-01':22756,'parser-jit-capacity-screen-continuation-01':64252,'parser-jit-capacity-prefix-audit-01':45774}
PIN='38d2517d3e09168a8fe222837730d435238ff358'

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
    from workflow_io import require_space
    require_space(ROOT,8)
    roots=[];proofs={};process_checks=[]
    result_path=ROOT/'results/parser-jit-capacity-screen-continuation-01/summary.json'
    result=json.loads(result_path.read_text());base=ROOT/result['raw']
    assert result['status']=='passed' and result['commands']==32 and result['retained_commands']==5 and result['new_commands']==27
    assert result['source_restored'] and result['original_assertions_unchanged'] and result['exact_native_test_outcomes'] and result['within_state_artifact_identity']
    assert result['original_tests']==114
    proofs[str(result_path.relative_to(ROOT))]=sha(result_path)
    for name in ['plan','records']:
        path=base/(name+'.json');assert sha(path)==result[name+'_sha256'];proofs[str(path.relative_to(ROOT))]=sha(path)
    plan=json.loads((base/'plan.json').read_text());assert plan['owner']==str(ROOT) and plan['revision']==PIN
    assert plan['cache_scope']=='parser-jit-capacity-screen-01'
    assert plan['tool_key']=='c0378f22956270c76f4ef8ab6237612f3f68715cdcf9a9a9b7ff24b8accd860b'
    audit_path=ROOT/'results/parser-jit-capacity-screen-analysis-01/summary.json'
    audit=json.loads(audit_path.read_text());assert audit['status']=='passed' and audit['screen_commands_audited']==32 and audit['repeated_commands']==0
    proofs[str(audit_path.relative_to(ROOT))]=sha(audit_path)
    for path in [result_path,base/'plan.json',base/'records.json']:
        assert sha(path)==audit['evidence'][str(path.relative_to(ROOT))]
    for run,pid in RUNS.items():
        terminal_path=ROOT/'.work/experiments'/run/'status.json'
        terminal=json.loads(terminal_path.read_text())
        assert terminal['owner']==str(ROOT) and terminal['status']=='finished' and terminal['child_pid']==pid
        assert terminal['returncode']==(1 if run=='parser-jit-capacity-screen-01' else 0)
        proofs[str(terminal_path.relative_to(ROOT))]=sha(terminal_path)
        if run=='parser-jit-capacity-screen-continuation-01':
            assert sha(terminal_path)==audit['evidence'][str(terminal_path.relative_to(ROOT))]
        for old_pid in [terminal['supervisor_pid'],terminal['child_pid']]:
            check=subprocess.run(['ps','-p',str(old_pid),'-o','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
            process_checks.append(dict(pid=old_pid,returncode=check.returncode,stdout=check.stdout))
            assert run not in check.stdout
    records=json.loads((base/'records.json').read_text());assert [r['index'] for r in records]==list(range(32))
    namespaces=set();native_paths=set()
    for row in records:
        assert (row['returncode']==0)==(row['state']!=-1)
        log=ROOT/row['log_raw']
        assert row['log_raw'] in ['.work/parser-jit-capacity-screen-01','.work/parser-jit-capacity-screen-continuation-01']
        for stream in ['stdout','stderr']:
            path=log/(str(row['index'])+'.'+stream);assert sha(path)==row[stream+'_sha256'];proofs[str(path.relative_to(ROOT))]=sha(path)
        for kind in ['artifact','entry_catalog','executable']:
            if kind in row:
                item=row[kind];path=ROOT/item['path'];assert sha(path)==item['sha256'];proofs[str(path.relative_to(ROOT))]=sha(path)
        command=row['command']
        if row['mode']=='native':
            assert command.count('--target-dir')==1
            path=Path(command[command.index('--target-dir')+1]);assert path==ROOT/'.work/parser-jit-capacity-screen-01/native'
            native_paths.add(path)
        else:
            assert command.count('--cache-namespace')==1
            namespace=command[command.index('--cache-namespace')+1]
            assert namespace in ['parser-jit-capacity-screen-01:custom-a','parser-jit-capacity-screen-01:custom-b','parser-jit-capacity-screen-01:custom-32']
            namespaces.add(Path(row['launch']['workspace_path']))
            suite=log/(str(row['index'])+'-suite.json');assert sha(suite)==row['suite_sha256'];proofs[str(suite.relative_to(ROOT))]=sha(suite)
    assert len(native_paths)==1 and len(namespaces)==3
    assert {p.name for p in namespaces}=={'6a68b3749237257fc4ed782c','76113caf1661ca496b3a62b2','7a257566c39f510d9794f152'}
    for path in namespaces:
        assert path.parent.parent==ROOT/'.work/interpreter-workspaces' and path.parent.name==plan['tool_key']
    roots=sorted(namespaces|native_paths)
    assert all(path.resolve(strict=True)==path for path in roots)
    marker=ROOT/'.work/sources/pgrust/.rust-interp-owned.json'
    owner=json.loads(marker.read_text());assert owner['owner']==str(ROOT) and owner['revision']==PIN
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=marker.parent,text=True).strip()==PIN
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=marker.parent).strip()
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
    # Protect all original, retained-prefix and continuation evidence outside the selected compiler cache.
    for run in RUNS:
        base=ROOT/'.work'/run
        for path in base.rglob('*'):
            if not path.is_file() or path.relative_to(base).parts[0] in ['native','native_lines','check']:continue
            assert not path.is_symlink();protected[str(path.relative_to(ROOT))]=sha(path)
    write(work/'inventory.json',rows);write(work/'protected.json',protected)
    assert rows, 'no eligible compiler intermediates remain; no deletion attempted'
    before=shutil.disk_usage(ROOT).free;started=time.time()
    write(work/'plan.json',dict(owner=str(ROOT),script_sha256=sha(Path(__file__)),completed_runs=RUNS,
        roots=sizes,process_checks=process_checks,open_checks=open_checks,files=len(rows),
        logical_bytes=sum(r['size'] for r in rows),free_before=before,started_at=started,
        scope='Three exact custom namespaces and one native cache from the complete32-command parser capacity screen, including its five audited retained controls. The failed performance gate remains parked. Nonexecutable incremental files and .o/.rlib/.rmeta in build/deps only. All other namespace files and saved case evidence hashed and preserved. No active, private, installed-tool or unrelated worktree cache. Shared and invocation locks held.'))
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
