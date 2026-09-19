from contextlib import ExitStack
from pathlib import Path
import json, os, shutil, stat, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write
from native_suite import test_status
from suite_reports import validate_report

NAME='closed-template-primary-parser-cache-retirement-01'
RUNS=['emitter-register-workspace-parser-screen-incremental-01','shared-emission-templates-parser-screen-incremental-01']

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

def terminal(run):
    import re
    saved=ROOT/'results'/run/'terminal.json';final=bind(saved)
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
    for kind in ['artifact','catalog','entry_catalog','selection','native_executable','executable','cargo_timing']:
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
    sys.path.insert(0,str(ROOT/'benchmarks/experiments/emitter-register-workspace-screen'))
    from benchmark import ratios,schedule,screen_states
    from probe import fingerprint,native_inventory
    from states import source_states,native_outcomes
    require_space(ROOT,8)
    roots=set();proofs={};process_checks=[];evidence_roots=set();pids=set();retained_frozen={}
    for run in RUNS:
        base=ROOT/'.work'/run;out=ROOT/'results'/run;evidence_roots.add(base)
        closure=bind(out/'closure.json');assert closure['status']=='closed' and closure['all_hashes_verified']
        result=bind(out/'summary.json',closure['summary_sha256']);bind(out/'terminal.json',closure['terminal_sha256'])
        assert result['status']=='passed' and result['commands']==32 and result['original_tests']==114
        assert result['source_restored'] and result['candidate_control_artifacts_match'] and result['exact_native_test_outcomes']
        terminal(run)
        plan=bind(base/'plan.json',result['plan_sha256']);rows=bind(base/'records.json',result['records_sha256'])
        assert plan['owner']==str(ROOT) and plan['profile']=='incremental' and plan['commands']==32
        assert ratios(rows)==result['measurement'] and result['measurement']['verdict'] in ['failed','unmeasurable'] and not result['measurement']['gate_passed']
        bindings=bind(ROOT/closure['bindings'],closure['bindings_sha256'])
        evidence=bind(ROOT/closure['evidence'],closure['evidence_sha256'])
        for path,digest in evidence.items():bind(ROOT/path,digest)
        import hashlib
        for path,digest in plan['frozen'].items():
            if path.startswith(('.work/','results/')):
                assert fingerprint(ROOT/path)==digest,path;retained_frozen[path]=digest
                if digest['kind']=='file':bind(ROOT/path,digest['sha256'])
            else:
                data=subprocess.check_output(['git','show',plan['source_commit']+':'+path],cwd=ROOT)
                assert hashlib.sha256(data).hexdigest()==digest['sha256'],path
        source=source_pin('pgrust',plan['revision'],'crates/backend/parser/gram_core/src/parse.rs',plan['original_source_sha256'])
        assert plan['revision']=='38d2517d3e09168a8fe222837730d435238ff358'
        assert schedule(screen_states((source/'crates/backend/parser/gram_core/src/parse.rs').read_bytes()))==plan['schedule']
        names=native_inventory((ROOT/'.work/pgrust-parser-support-01/native.stdout').read_text());assert len(names)==114
        previous=dict.fromkeys(['native','baseline','duplicate','candidate'])
        for row,planned in zip(rows,plan['schedule']):
            assert {k:row[k] for k in planned}==planned
            cmd=row['command'];mode=row['mode'];pids.add(row['pid']);success=row['state']!=-1
            assert row['previous_source_sha256']==previous[mode] and row['source_sha256']!=previous[mode]
            previous[mode]=row['source_sha256'];assert (row['returncode']==0)==success
            assert cmd[cmd.index('--manifest-path')+1]==str(source/'Cargo.toml')
            for stream in ['stdout','stderr']:bind(base/f"{row['index']}.{stream}",row[stream+'_sha256'])
            if mode=='native':
                target=Path(cmd[cmd.index('--target-dir')+1]);assert target==base/'native';roots.add(target)
                assert row['outcomes']==[list(x) for x in native_outcomes((base/f"{row['index']}.stdout").read_text(),names,success)]
            else:
                workspace(row,run,mode,plan['tool_keys'][mode])
                report=bind(base/f"{row['index']}-suite.json",row['suite_sha256'])
                assert row['outcomes']==[list(x) for x in validate_report(report,names,'prepared',success)]
            snapshots(row)
        assert all(h==plan['original_source_sha256'] for h in previous.values())
        assert len(rows)==len(plan['schedule'])==32
    assert len(roots)==8;roots=sorted(roots);assert all(p.resolve(strict=True)==p for p in roots)
    check=subprocess.run(['ps','-p',','.join(map(str,sorted(pids))),'-o','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
    assert check.returncode in [0,1] and not check.stderr and not any(run in line for run in RUNS for line in check.stdout.splitlines()[1:])
    process_checks.append(dict(pids=sorted(pids),returncode=check.returncode,stdout=check.stdout))
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
            if remove and key not in protected: rows.append(dict(path=key,**info))
            else: protected[key]=sha(path)
        sizes.append(dict(path=str(root.relative_to(ROOT)),files=len(rows)-count_before,
                          logical_bytes=sum(r['size'] for r in rows)-bytes_before))
        print(json.dumps(dict(root_index=len(sizes)-1,files=sizes[-1]['files'],logical_bytes=sizes[-1]['logical_bytes'])),flush=True)
    # Protect all original, retained-prefix and continuation evidence outside the selected compiler cache.
    for base in sorted(evidence_roots):
        for path in base.rglob('*'):
            if not path.is_file() or path.relative_to(base).parts[0] in ['native']:continue
            assert not path.is_symlink();protected[str(path.relative_to(ROOT))]=sha(path)
    write(work/'inventory.json',rows);write(work/'protected.json',protected)
    assert rows, 'no eligible compiler intermediates remain; no deletion attempted'
    before=shutil.disk_usage(ROOT).free;started=time.time()
    write(work/'plan.json',dict(owner=str(ROOT),script_sha256=sha(Path(__file__)),completed_runs=RUNS,
        roots=sizes,process_checks=process_checks,open_checks=open_checks,files=len(rows),
        logical_bytes=sum(r['size'] for r in rows),free_before=before,started_at=started,
        scope='Eight exact completed public compiler caches from the closed failed emitter-workspace and shared-template incremental parser primaries. Successful supervisors, source pins/restoration, original assertions and snapshots are verified. Only nonexecutable compiler intermediates are eligible. Preserve every executable, bytecode/catalog snapshot and raw proof under shared/invocation locks and fresh process/open-file checks. No private cache, shared target, installed tool, unstarted later-case cache or peer cache.'))
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
        plan_sha256=sha(work/'plan.json'),raw=str(work.relative_to(ROOT)),performance_measurement=False,completed_histories=2,completed_commands=64)
    write(work/'summary.json',result);print(json.dumps(result),flush=True)
