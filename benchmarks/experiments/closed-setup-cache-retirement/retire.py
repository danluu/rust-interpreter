from contextlib import ExitStack
from pathlib import Path
import json, os, shutil, stat, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write
from native_suite import test_status
from suite_reports import validate_report

NAME='closed-runtime-setup-cache-retirement-01'
RUNS=['runtime-composition-edit-token-01']

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

def source_pin(project,revision,file,digest):
    source=ROOT/'.work/sources'/project
    marker=bind(source/'.rust-interp-owned.json')
    assert marker['owner']==str(ROOT) and marker['revision']==revision
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==revision
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
    bind(source/file,digest)
    return source

def snapshots(row):
    for kind in ['artifact','catalog','entry_catalog','selection','native_executable','cargo_timing']:
        if kind in row:
            item=row[kind];bind(ROOT/item['path'],item['sha256'])

def workspace(row,run,mode,key):
    cmd=row['command']
    assert cmd[cmd.index('--cache-namespace')+1]==run+':'+mode
    assert cmd[cmd.index('--tool-key')+1]==key
    if 'launch' in row:launch=row['launch']
    else:
        launch,=[json.loads(line.split(': ',1)[1]) for line in row['stderr'].splitlines() if line.startswith('rust-interp-launch: ')]
    assert launch['tool_key']==key
    target=Path(launch['workspace_path'])
    assert target.parent==ROOT/'.work/interpreter-workspaces'/key and target.resolve(strict=True)==target
    roots.add(target)

with ExitStack() as stack:
    lock=stack.enter_context((ROOT/'.work/benchmark.lock').open('a'));acquire_lock(lock,45)
    from workflow_io import require_space
    import hashlib,re
    require_space(ROOT,8)
    assert shutil.disk_usage(ROOT).free<24*1024**3, 'full guard admission already fits; retirement unnecessary'
    roots=set();proofs={};process_checks=[];evidence_roots=set();pids=set();protected_references=set()
    run,=RUNS;base=ROOT/'.work'/run;evidence_roots.add(base);result=ROOT/'results'/run
    closure=bind(result/'closure.json');assert closure['status']=='closed' and closure['all_hashes_verified'] and closure['source_restored']
    summary=bind(result/'summary.json',closure['summary_sha256']);final=bind(result/'terminal.json',closure['terminal_sha256'])
    assert summary['status']=='failed' and summary['phase']=='setup-launcher-option-validation'
    assert summary['commands']==2 and summary['valid_edited_pairs']==0 and summary['source_restored'] and not summary['performance_gate_evaluated']
    assert final['owner']==final['cwd']==str(ROOT) and final['status']=='finished' and final['returncode']==1
    match,=re.findall(r'--supervise (\S+/plan\.json)',final['supervisor_identity']);outer=Path(match).parent
    assert outer==ROOT/'.work/experiments/runtime-composition-full-token-01'
    bind(outer/'status.json',sha(result/'terminal.json'));bind(outer/'plan.json',final['plan_sha256']);bind(outer/'command.log',final['log_sha256'])
    pids.update([final['supervisor_pid'],final['child_pid']])
    bindings=bind(ROOT/closure['bindings'],closure['bindings_sha256'])
    for path,item in bindings['source'].items():
        protected_references.add(path)
        if item['kind']=='retained':bind(ROOT/path,item['sha256'])
        else:
            assert item['kind']=='git'
            data=subprocess.check_output(['git','show',item['revision']+':'+path],cwd=ROOT)
            assert hashlib.sha256(data).hexdigest()==item['sha256'],path
    for path,h in bindings['artifacts'].items():bind(ROOT/path,h)
    plan=bind(base/'plan.json');rows=bind(base/'records.json');assert plan['owner']==str(ROOT)
    assert [row['mode'] for row in rows]==['native_lines','baseline']
    assert all(row['returncode']==0 and row['state']==row['cycle']==0 and row['source_sha256']==plan['original_source_sha256'] for row in rows)
    source=source_pin('fre','e0df0b010b156b030a02f073588d28703f4267f3',plan['case']['file'],plan['original_source_sha256'])
    assert plan['revision']=='e0df0b010b156b030a02f073588d28703f4267f3'
    native,custom=rows
    for row in rows:
        pids.add(row['pid']);cmd=row['command'];assert cmd[cmd.index('--manifest-path')+1]==str(source/'Cargo.toml')
    cmd=native['command'];target=Path(cmd[cmd.index('--target-dir')+1]);assert target==base/'native_lines';roots.add(target)
    found=re.findall(r'^test (.+) \.\.\. (ok|FAILED|ignored)$',native['stdout'],re.M)
    assert len(found)==len(plan['names'])==12 and set(dict(found))==set(plan['names']) and all(v=='ok' for _,v in found)
    assert native['outcomes']==[list(x) for x in sorted((name,'passed') for name,_ in found)]
    snapshots(native);bind(ROOT/native['native_build_executable'],native['native_executable']['sha256'])
    workspace(custom,run,'baseline',plan['tools']['baseline'])
    launch,=[json.loads(line.split(': ',1)[1]) for line in custom['stderr'].splitlines() if line.startswith('rust-interp-launch: ')]
    for kind in ['artifact','entry_catalog','test_selection','suite_report']:
        bind(Path(launch[kind+'_path']),launch[kind+'_sha256'])
    report=json.loads(Path(launch['suite_report_path']).read_text())
    assert native['outcomes']==[list(x) for x in sorted(validate_report(report,plan['names'],'prepared',True))]
    assert len(roots)==2;roots=sorted(roots);assert all(p.resolve(strict=True)==p for p in roots)
    check=subprocess.run(['ps','-p',','.join(map(str,sorted(pids))),'-o','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
    assert check.returncode in [0,1] and not check.stderr and not any(run in line or 'runtime-composition-full' in line for line in check.stdout.splitlines()[1:])
    process_checks.append(dict(pids=sorted(pids),returncode=check.returncode,stdout=check.stdout))
    current=subprocess.run(['ps','-axo','pid,ppid,lstart,tty,command'],capture_output=True,text=True,check=True)
    assert not any(str(root) in line for root in roots for line in current.stdout.splitlines()[1:])
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
            if remove and key not in protected and key not in protected_references: rows.append(dict(path=key,**info))
            else: protected[key]=sha(path)
        sizes.append(dict(path=str(root.relative_to(ROOT)),files=len(rows)-count_before,
                          logical_bytes=sum(r['size'] for r in rows)-bytes_before))
        print(json.dumps(dict(root_index=len(sizes)-1,files=sizes[-1]['files'],logical_bytes=sizes[-1]['logical_bytes'])),flush=True)
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
        scope='Two exact owned compiler caches from the closed runtime-composition-edit-token-01 setup failure. Native and baseline setup commands returned zero; an obsolete harness assertion stopped before edited pairs. Preserve the failure and all sources, results, executables, artifact bytes, historical proof references, shared target and peerwork. No benchmark retry or performance claim. Shared and invocation locks, original closed proof bindings, exact process/open-file checks and file identity revalidation precede removing only nonexecutable compiler intermediates.'))
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
        plan_sha256=sha(work/'plan.json'),raw=str(work.relative_to(ROOT)),performance_measurement=False,closed_failed_histories=1,completed_setup_commands=2,valid_edited_pairs=0)
    write(work/'summary.json',result);print(json.dumps(result),flush=True)
