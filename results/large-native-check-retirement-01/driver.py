from contextlib import ExitStack
from pathlib import Path
import json, os, shutil, stat, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write

NAME='large-native-check-retirement-01'
RUNS={'large-native-nushell-02':58986}

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
    assert not fields and check.returncode==1, (root,fields)
    return dict(path=str(root.relative_to(ROOT)),returncode=check.returncode,
                no_open_files=True,owner_pid=os.getpid())

with ExitStack() as stack:
    lock=stack.enter_context((ROOT/'.work/benchmark.lock').open('a'));acquire_lock(lock,45)
    from workflow_io import require_space
    require_space(ROOT,8)
    run='large-native-nushell-02';base=ROOT/'.work'/run
    proofs={};process_checks=[];evidence_roots=set()
    result_path=ROOT/'results'/run/'summary.json';result=json.loads(result_path.read_text())
    assert result['status']=='passed' and result['commands']==88 and result['raw']==str(base.relative_to(ROOT))
    assert result['source_restored'] and result['test_source_unchanged'] and result['original_assertions_match']
    proofs[str(result_path.relative_to(ROOT))]=sha(result_path)
    for name,digest in result['evidence'].items():
        path=base/(name+'.json');assert sha(path)==digest;proofs[str(path.relative_to(ROOT))]=sha(path)
    plan=json.loads((base/'plan.json').read_text());assert plan['owner']==str(ROOT)
    terminal_path=ROOT/'.work/experiments'/run/'status.json';terminal=json.loads(terminal_path.read_text())
    assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==terminal['cwd']==str(ROOT) and terminal['child_pid']==58986
    assert terminal['command']==['python3','benchmarks/experiments/large-native-calibration/run.py','--run-id',run]
    proofs[str(terminal_path.relative_to(ROOT))]=sha(terminal_path)
    for name,field in [('plan.json','plan_sha256'),('command.log','log_sha256')]:
        path=terminal_path.with_name(name);assert sha(path)==terminal[field];proofs[str(path.relative_to(ROOT))]=sha(path)
    rows=json.loads((base/'records.json').read_text());assert len(rows)==88
    pids={terminal['supervisor_pid'],terminal['child_pid']};target=base/'check';checks=[]
    for row in rows:
        assert (row['returncode']==0)==(row['state']!=-1 or row['mode']=='check');pids.add(row['pid'])
        if row['mode']=='check':
            cmd=row['command'];assert cmd[:3]==['cargo','+nightly-2026-09-08','check']
            assert cmd[cmd.index('--target-dir')+1]==str(target)
            assert cmd[cmd.index('--manifest-path')+1]==str(ROOT/'.work/sources/nushell/Cargo.toml')
            checks.append(row)
    assert len(checks)==22;roots=[target];assert target.resolve(strict=True)==target
    source=ROOT/'.work/sources/nushell';marker=source/'.rust-interp-owned.json';owner=json.loads(marker.read_text())
    assert owner['owner']==str(ROOT) and owner['revision']==plan['source_revision']
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==plan['source_revision']
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
    changed=source/'crates/nu-protocol/src/ty.rs';assert sha(changed)==plan['source_sha256']
    proofs[str(changed.relative_to(ROOT))]=sha(changed);proofs[str(marker.relative_to(ROOT))]=sha(marker)
    for pid in sorted(pids):
        check=subprocess.run(['ps','-p',str(pid),'-o','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
        assert check.returncode in [0,1] and not check.stderr and run not in check.stdout
        process_checks.append(dict(pid=pid,returncode=check.returncode,stdout=check.stdout))
    # The other three native profiles and their raw artifacts are outside this single check-cache deletion scope.
    for path in base.iterdir():
        if path.is_file():assert not path.is_symlink();proofs[str(path.relative_to(ROOT))]=sha(path)
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
            for prefix in [('debug',)]:
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
    for base in evidence_roots:
        for path in base.rglob('*'):
            if not path.is_file() or path.relative_to(base).parts[0] in ['native','native_lines','check']:continue
            assert not path.is_symlink();protected[str(path.relative_to(ROOT))]=sha(path)
    write(work/'inventory.json',rows);write(work/'protected.json',protected)
    before=shutil.disk_usage(ROOT).free;started=time.time()
    write(work/'plan.json',dict(owner=str(ROOT),script_sha256=sha(Path(__file__)),completed_runs=RUNS,
        roots=sizes,process_checks=process_checks,open_checks=open_checks,files=len(rows),
        logical_bytes=sum(r['size'] for r in rows),free_before=before,started_at=started,
        scope='One exact completed Cargo-check cache from the 88-command public Nushell native calibration. Completed controller, source restoration/pin, all record hashes and 22 exact check targets revalidated. Other native profiles untouched. Nonexecutable compiler intermediates only; all other selected-target files and raw evidence preserved. Shared lock and exact process/open-file checks; no private, current or peer cache.'))
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
