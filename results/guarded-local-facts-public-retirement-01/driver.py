from contextlib import ExitStack
from pathlib import Path
import json, os, shutil, stat, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write

NAME='guarded-local-facts-public-retirement-01'
RUNS={'guarded-local-facts-full-01':93278,'guarded-local-facts-screen-continuation-admission-02':15209}

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
    sys.path.insert(0,str(ROOT/'benchmarks/experiments/guarded-local-facts-continuation'))
    from prefix import load_prefix
    prefix_path=ROOT/'results/guarded-local-facts-full-prefix-01/summary.json'
    prefix,evidence,audit=load_prefix(prefix_path)
    roots=set();proofs=dict(evidence);process_checks=[];evidence_roots=set()
    proofs[str(prefix_path.relative_to(ROOT))]=sha(prefix_path)
    cases=[('guarded-local-facts-edit-'+case+'-01',154,case) for case in ['token','folded','pgrust']]
    cases.append(('guarded-local-facts-screen-token-continuation-01',40,'token'))
    for run,count,case in cases:
        path=ROOT/'results'/run/'summary.json';summary=json.loads(path.read_text())
        assert summary['status']=='passed' and summary['commands']==count and summary['case']==case
        assert summary['gate_passed'] and summary['source_restored'] and summary['test_source_unchanged']
        assert summary['native_assertion_outcomes_match'] and summary['candidate_control_bytecode_matches']
        proofs[str(path.relative_to(ROOT))]=sha(path)
        raw=ROOT/summary['raw'];assert raw==ROOT/'.work'/run;evidence_roots.add(raw)
        for name in ['plan','records','transitions','space']:
            path=raw/(name+'.json');assert sha(path)==summary[name+'_sha256'];proofs[str(path.relative_to(ROOT))]=sha(path)
        plan=json.loads((raw/'plan.json').read_text());assert plan['owner']==str(ROOT)
        records=json.loads((raw/'records.json').read_text());assert len(records)==count
        custom=set();native=set()
        for row in records:
            mode=row['mode'];command=row['command']
            assert (row['returncode']==0)==(row['state']!=-1 or mode=='check')
            for kind in ['artifact','catalog','entry_catalog','selection','native_executable']:
                if kind in row:
                    item=row[kind];key=item['path'];assert key not in proofs or proofs[key]==item['sha256'];proofs[key]=item['sha256']
            if mode in ['native','native_lines','check']:
                target=Path(command[command.index('--target-dir')+1])
                expected=ROOT/'.work/guarded-local-facts-screen-token-01/native' if count==40 else raw/mode
                assert target==expected and target.resolve(strict=True)==target;native.add(target)
            else:
                assert mode in ['baseline','duplicate','candidate','anchor']
                assert command[command.index('--cache-namespace')+1]==run+':'+mode
                assert command[command.index('--tool-key')+1]==summary['tool_keys'][mode]
                target=Path(row['launch']['workspace_path'])
                assert target.parent.parent==ROOT/'.work/interpreter-workspaces' and target.parent.name==summary['tool_keys'][mode]
                assert target.resolve(strict=True)==target;custom.add(target)
                suite=raw/(str(row['cycle'])+'-'+str(row['state'])+'-'+mode+'-suite.json')
                assert sha(suite)==row['suite_sha256'];proofs[str(suite.relative_to(ROOT))]=sha(suite)
        assert len(custom)==4 and len(native)==(1 if count==40 else 3)
        roots.update(custom|native)
    assert len(roots)==26;roots=sorted(roots)
    for run,pid in RUNS.items():
        path=ROOT/'.work/experiments'/run/'status.json';terminal=json.loads(path.read_text())
        assert terminal['status']=='finished' and terminal['child_pid']==pid and terminal['owner']==str(ROOT)
        assert terminal['returncode']==(1 if run=='guarded-local-facts-full-01' else 0)
        proofs[str(path.relative_to(ROOT))]=sha(path)
        for old_pid in [terminal['supervisor_pid'],pid]:
            check=subprocess.run(['ps','-p',str(old_pid),'-o','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
            process_checks.append(dict(pid=old_pid,returncode=check.returncode,stdout=check.stdout));assert run not in check.stdout
    for name in ['guarded-local-facts-screen-token-01','guarded-local-facts-prefix-audit-01']:
        evidence_roots.add(ROOT/'.work'/name)
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
        scope='Exactly the completed token/folded/pgrust full histories and completed token screen; private and unstarted Nushell caches are excluded. Prefix ownership, terminal failure before Nushell, all four completed gates and retained artifacts are revalidated first. Nonexecutable incremental files and .o/.rlib/.rmeta in build/deps only. All other namespace files and saved case evidence hashed and preserved. No active, private, installed-tool or unrelated worktree cache. Shared and invocation locks held.'))
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
