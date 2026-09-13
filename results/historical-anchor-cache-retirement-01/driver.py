from contextlib import ExitStack
from pathlib import Path
import json, os, shutil, stat, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write

NAME='historical-anchor-cache-retirement-01'
RUNS={'composed-development-edit-anchor-01':4836}

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
    import hashlib
    run='composed-development-edit-anchor-01';base=ROOT/'.work'/run
    roots=set();proofs={};process_checks=[];evidence_roots={base};pids=set()
    result_path=ROOT/'results'/run/'summary.json';result=json.loads(result_path.read_text())
    assert result['status']=='passed' and result['case']=='anchor' and result['commands']==132
    assert result['source_restored'] and result['test_source_unchanged']
    assert result['native_assertion_outcomes_match'] is False and result['batch_success_and_assertion_failure_match'] is True
    proofs[str(result_path.relative_to(ROOT))]=sha(result_path)
    for name in ['plan','records','transitions','space']:
        path=base/(name+'.json');assert sha(path)==result[name+'_sha256'];proofs[str(path.relative_to(ROOT))]=sha(path)
    plan=json.loads((base/'plan.json').read_text());assert plan['owner']==str(ROOT)
    original_driver=subprocess.check_output(['git','show','5c64d038a07e99adac8ce2082ca650168f8ef951:benchmarks/experiments/composed-development/workflows.py'])
    assert hashlib.sha256(original_driver).hexdigest()==plan['frozen']['benchmarks/experiments/composed-development/workflows.py']=='2672155b3c3e828d79534ade7aea538408aef7d58f018d6a4b4d6d3f3dc9c4a1'
    assert b'native_assertion_outcomes_match=not historical, batch_success_and_assertion_failure_match=historical' in original_driver
    terminal_path=ROOT/'.work/experiments'/run/'status.json';terminal=json.loads(terminal_path.read_text())
    assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==terminal['cwd']==str(ROOT) and terminal['child_pid']==4836
    assert terminal['command'][terminal['command'].index('--run-id')+1]==run
    proofs[str(terminal_path.relative_to(ROOT))]=sha(terminal_path);pids.update([terminal['supervisor_pid'],terminal['child_pid']])
    for name,field in [('plan.json','plan_sha256'),('command.log','log_sha256')]:
        path=terminal_path.with_name(name);assert sha(path)==terminal[field];proofs[str(path.relative_to(ROOT))]=sha(path)
    rows=json.loads((base/'records.json').read_text());assert len(rows)==132
    for row in rows:
        mode=row['mode'];cmd=row['command'];pids.add(row['pid'])
        assert (row['returncode']==0)==(row['state']!=-1 or mode=='check')
        assert cmd[cmd.index('--manifest-path')+1]==str(ROOT/'.work/sources/fre/Cargo.toml')
        if mode in ['native','native_lines','check']:
            target=Path(cmd[cmd.index('--target-dir')+1]);assert target==base/mode;roots.add(target)
        else:
            assert mode in ['baseline','duplicate','candidate'] and row['batch_passed']==(row['state']!=-1)
            assert cmd[cmd.index('--tool-key')+1]==row['launch']['tool_key']==result['tool_keys'][mode]
            assert cmd[cmd.index('--cache-namespace')+1]==run+':'+mode
            target=Path(row['launch']['workspace_path']);assert target.parent==ROOT/'.work/interpreter-workspaces'/result['tool_keys'][mode];roots.add(target)
        if 'artifact' in row:
            item=row['artifact'];assert sha(ROOT/item['path'])==item['sha256'];proofs[item['path']]=item['sha256']
    assert len(roots)==6;roots=sorted(roots);assert all(p.resolve(strict=True)==p for p in roots)
    source=ROOT/'.work/sources/fre';marker=source/'.rust-interp-owned.json';owner=json.loads(marker.read_text())
    assert owner['owner']==str(ROOT) and owner['revision']==plan['revision']
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==plan['revision']
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
    changed=source/plan['case']['file'];assert sha(changed)==plan['original_source_sha256'];proofs[str(changed.relative_to(ROOT))]=sha(changed);proofs[str(marker.relative_to(ROOT))]=sha(marker)
    for pid in sorted(pids):
        check=subprocess.run(['ps','-p',str(pid),'-o','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
        assert check.returncode in [0,1] and not check.stderr and run not in check.stdout
        process_checks.append(dict(pid=pid,returncode=check.returncode,stdout=check.stdout))
    for root in roots:
        if root.parent.parent==ROOT/'.work/interpreter-workspaces':
            invocation=stack.enter_context((root/'invocation.lock').open('r+'));acquire_lock(invocation,45)
    assert all(sha(ROOT/path)==digest for path,digest in proofs.items())
    work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
    (work/'original-workflows.py').write_bytes(original_driver)
    proofs[str((work/'original-workflows.py').relative_to(ROOT))]=sha(work/'original-workflows.py')
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
    for base in sorted(evidence_roots):
        for path in base.rglob('*'):
            if not path.is_file() or path.relative_to(base).parts[0] in ['native','native_lines','check']:continue
            assert not path.is_symlink();protected[str(path.relative_to(ROOT))]=sha(path)
    write(work/'inventory.json',rows);write(work/'protected.json',protected)
    assert rows, 'no eligible compiler intermediates remain; no deletion attempted'
    before=shutil.disk_usage(ROOT).free;started=time.time()
    write(work/'plan.json',dict(owner=str(ROOT),script_sha256=sha(Path(__file__)),completed_runs=RUNS,
        roots=sizes,process_checks=process_checks,open_checks=open_checks,files=len(rows),
        logical_bytes=sum(r['size'] for r in rows),free_before=before,started_at=started,
        scope='Six exact completed historical-anchor caches. The earlier proposed retirement refused a modern per-test-outcome field. Exact archived driver SHA proves that field is deliberately false for the older batch runner; its batch success/wrong-assertion field is true and all132 actual outcomes, source restoration, terminal and artifact hashes are revalidated. Historical granularity is preserved, not upgraded. Nonexecutable compiler intermediates only; every executable and saved source/log/artifact retained. Shared/invocation locks and fresh process/open-file checks. No private, incomplete, current or peer cache.'))
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
