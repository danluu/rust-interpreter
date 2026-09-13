from contextlib import ExitStack
from pathlib import Path
import json, os, shutil, stat, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write

NAME='completed-recovered-corpus-retirement-01'
RUNS=['pgrust','nushell','forward-anchored-tls','pgrust-sha1-inline8','ruff']

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
    from reclaim_workflow_objects import workflow
    from workflow_cache_evidence import derive
    corpus='resumable-bulk-heldout-01'
    roots=set();proofs={};process_checks=[];evidence_roots=set()
    for case in RUNS:
        run=corpus+'-'+case
        native,case_proofs,verified=workflow(run,corpus,recovered=True)
        assert native==ROOT/'.work/runs'/run/'native'
        for p,h in case_proofs.items():assert p not in proofs or proofs[p]==h;proofs[p]=h
        report_path=ROOT/'results'/run/'summary.json';report=json.loads(report_path.read_text())
        assert report['project'] in ['pgrust','nushell','fre','ruff']
        raw=ROOT/report['raw'];assert raw==native.parent;evidence_roots.add(raw)
        rows=json.loads((raw/'records.json').read_text());checks=json.loads((raw/'check-records.json').read_text())
        assert len(rows)==63 and len(checks)==21 and report['cycles']==3
        roots.add(native)
        for mode in ['check','baseline','candidate']:
            target,selection,snapshots=derive(ROOT,run,report,rows,checks,mode)
            if mode in ['baseline','candidate']:
                assert target.name=='target' and target.parent.parent.parent==ROOT/'.work/interpreter-workspaces'
                roots.add(target.parent)
            else:roots.add(target)
            for path in snapshots:proofs[str(path.relative_to(ROOT))]=sha(path)
        source=ROOT/'.work/sources'/report['project'];marker=source/'.rust-interp-owned.json';owner=json.loads(marker.read_text())
        assert owner['owner']==str(ROOT) and owner['revision']==report['revision']
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==report['revision']
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
        proofs[str(marker.relative_to(ROOT))]=sha(marker)
        pids={call['pid'] for row in rows for call in row['calls']}
        for pid in sorted(pids):
            check=subprocess.run(['ps','-p',str(pid),'-o','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
            assert check.returncode in [0,1] and not check.stderr and corpus not in check.stdout
            process_checks.append(dict(pid=pid,returncode=check.returncode,stdout=check.stdout))
    assert len(roots)==20;roots=sorted(roots);assert all(p.resolve(strict=True)==p for p in roots)
    for root in roots:
        if root.parent.parent==ROOT/'.work/interpreter-workspaces':
            invocation=stack.enter_context((root/'invocation.lock').open('r+'));acquire_lock(invocation,45)
    assert all(sha(ROOT/path)==digest for path,digest in proofs.items())
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
        scope='Twenty exact cache roots from five fully completed public cases in the recovered corpus. Existing recovery-evidence and workflow verifiers revalidate the completed63-command/21-check ledgers and paired artifacts, source pins, native commands and derived custom namespace identities. Private and incomplete cases excluded. Only nonexecutable compiler intermediates; all raw evidence, executable snapshots, bytecode and noncompiler files preserved. Shared/invocation locks and fresh process/open-file checks. No current or peer cache.'))
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
