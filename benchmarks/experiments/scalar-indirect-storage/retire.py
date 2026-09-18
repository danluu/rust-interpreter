from contextlib import ExitStack
from pathlib import Path
import json, os, shutil, stat, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write
from native_suite import test_status
from suite_reports import validate_report

NAME='closed-scratch-memory-values-nushell-native-retirement-01'
RUNS=['scratch-memory-values-edit-nushell-01']

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

def bind(path, expected=None, *, parse=True):
    assert path.resolve(strict=True)==path and path.is_file(),path
    digest=sha(path)
    if expected is not None: assert digest==expected,path
    key=str(path.relative_to(ROOT))
    assert key not in proofs or proofs[key]==digest,path
    proofs[key]=digest
    return json.loads(path.read_text()) if parse and path.suffix=='.json' else digest

def terminal(run):
    import re
    saved=ROOT/'results/scratch-memory-values-edit-token-01/terminal.json';final=bind(saved)
    assert final['owner']==final['cwd']==str(ROOT) and final['status']=='finished' and final['returncode']==0
    match,=re.findall(r'--supervise (\S+/plan\.json)',final['supervisor_identity'])
    outer=Path(match).parent;assert outer.parent==ROOT/'.work/experiments'
    assert outer.name==run
    bind(outer/'status.json',sha(saved));bind(outer/'plan.json',final['plan_sha256'])
    bind(outer/'command.log',final['log_sha256'])
    pids.update([final['supervisor_pid'],final['child_pid']])

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
    from workflow_cases import WORKFLOW_VARIANTS
    sys.path.insert(0,str(ROOT/'benchmarks/experiments/pgrust-parser-probe'))
    from probe import fingerprint
    require_space(ROOT,8)
    roots=set();proofs={};process_checks=[];evidence_roots=set();pids=set();bindings={};retained_frozen={}
    run,=RUNS;raw=ROOT/'.work'/run;out=ROOT/'results'/run
    closed=bind(out/'closure.json');assert closed['status']=='closed' and closed['commands']==132
    assert closed['all_retained_artifacts_and_sources_verified']
    full=bind(ROOT/closed['full_closure'],closed['full_closure_sha256'])
    assert full['status']=='closed' and full['full_campaign_complete'] and full['commands']==726
    result=bind(out/'summary.json',closed['summary_sha256'])
    assert result['status']=='passed' and result['commands']==132 and result['source_restored'] and result['test_source_unchanged']
    for name,digest in result['evidence'].items():bind(raw/(name+'.json'),digest)
    final=bind(out/'terminal.json',closed['terminal_sha256'])
    assert final['owner']==final['cwd']==str(ROOT) and final['status']=='finished' and final['returncode']==0
    import re
    matched,=re.findall(r'--supervise (\S+/plan\.json)',final['supervisor_identity'])
    outer=Path(matched).parent;assert outer.parent==ROOT/'.work/experiments'
    bind(outer/'status.json',sha(out/'terminal.json'));bind(outer/'command.log',final['log_sha256']);bind(outer/'plan.json',final['plan_sha256'])
    pids.update([final['supervisor_pid'],final['child_pid']])
    plan=json.loads((raw/'plan.json').read_text());records=json.loads((raw/'records.json').read_text())
    assert plan['owner']==str(ROOT) and plan['commands']==132 and plan['case']=='nushell' and plan['cargo_workers']==2
    assert plan['revision']=='9d3157963241cf89447119d34d6e887859f5e7e8'
    source=source_pin('nushell',plan['revision'],WORKFLOW_VARIANTS['nushell','type-relations']['file'],plan['source_sha256'])
    for path,digest in plan['frozen'].items():
        if path.startswith(('.work/','results/')):
            assert fingerprint(ROOT/path)==digest,path;retained_frozen[path]=digest
            if digest['kind']=='file':bind(ROOT/path,digest['sha256'],parse=False)
        else:
            import hashlib
            payload=subprocess.check_output(['git','show',plan['source_commit']+':'+path],cwd=ROOT)
            assert hashlib.sha256(payload).hexdigest()==digest['sha256'],path
            bindings[path]=dict(revision=plan['source_commit'],fingerprint=digest)
    assert len(records)==132
    checks=[r for r in records if r['mode']=='native']
    assert [(r['cycle'],r['state']) for r in checks]==[(c,s) for c in range(3) for s in [0,-1,1,2,3,4,5]]+[(3,0)]
    previous=None
    for row in records:
        pids.add(row['pid']);snapshots(row)
    for row in checks:
        cmd=row['command'];assert (row['returncode']==0)==(row['state']!=-1) and 'test' in cmd and '--lib' in cmd
        sys.path.insert(0,str(ROOT/'benchmarks/experiments/scratch-memory-values'))
        from screen import native_outcomes
        assert row['outcomes']==[list(x) for x in native_outcomes(row['stdout'],plan['tests'],row['state']!=-1)]
        assert cmd[cmd.index('--package')+1]=='nu-protocol' and cmd[cmd.index('--manifest-path')+1]==str(source/'Cargo.toml')
        target=Path(cmd[cmd.index('--target-dir')+1]);assert target==raw/'native';roots.add(target)
        assert row['previous_source_sha256']==previous and row['source_sha256']!=previous;previous=row['source_sha256']
    assert previous==plan['source_sha256'] and roots=={raw/'native'}
    roots=sorted(roots);assert all(p.resolve(strict=True)==p for p in roots)
    check=subprocess.run(['ps','-p',','.join(map(str,sorted(pids))),'-o','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
    assert check.returncode in [0,1] and not check.stderr and not any(run in line for line in check.stdout.splitlines()[1:])
    process_checks.append(dict(pids=sorted(pids),returncode=check.returncode,stdout=check.stdout))
    for path in raw.iterdir():
        if path.is_file():bind(path)
    evidence_roots.add(raw)
    work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
    write(work/'historical-source-bindings.json',bindings);write(work/'retained-frozen.json',retained_frozen)
    proofs[str((work/'historical-source-bindings.json').relative_to(ROOT))]=sha(work/'historical-source-bindings.json')
    proofs[str((work/'retained-frozen.json').relative_to(ROOT))]=sha(work/'retained-frozen.json')
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
            if remove and key not in protected: rows.append(dict(path=key,**info))
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
        scope='One exact completed ordinary native Cargo cache from scratch-memory-values-edit-nushell-01. Verify the closed 132-command history, 22 ordinary native test commands, terminal supervisor, source pin/restoration and historical frozen inputs. Preserve every executable, source, artifact/catalog, timing trace and raw proof under the shared lock and fresh process/open-file checks. Only nonexecutable compiler intermediates are eligible. No other native test cache, private cache, shared target, installed tool or peer cache.'))
    assert all(sha(ROOT/p)==h for p,h in proofs.items())
    for root in roots:
        check_open(root)
    for row in rows:
        path=ROOT/row['path'];current=identity(path)
        assert all(current[k]==row[k] for k in ['device','inode','size','mtime_ns','mode']), (path,current,row)
        # Unlinking an earlier hard link changes st_nlink, not this file's identity or bytes.
        path.unlink()
    assert all(sha(ROOT/p)==h for p,h in protected.items())
    assert all(fingerprint(ROOT/p)==h for p,h in retained_frozen.items())
    result=dict(status='passed',files_removed=len(rows),logical_bytes_removed=sum(r['size'] for r in rows),
        free_before=before,free_after=shutil.disk_usage(ROOT).free,started_at=started,finished_at=time.time(),
        protected_files=len(protected),all_protected_hashes_unchanged=True,
        inventory_sha256=sha(work/'inventory.json'),protected_manifest_sha256=sha(work/'protected.json'),
        plan_sha256=sha(work/'plan.json'),raw=str(work.relative_to(ROOT)),performance_measurement=False,completed_histories=1,completed_commands=132)
    write(work/'summary.json',result);print(json.dumps(result),flush=True)
