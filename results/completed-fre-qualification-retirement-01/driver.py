from contextlib import ExitStack
from pathlib import Path
import json, os, shutil, stat, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write

NAME='completed-fre-qualification-retirement-01'
RUNS={'aggregate-relocation-fre-01':13296,'budget-register-fre-01':1978,'resumable-bulk-fre-01':57121,'resumable-copy-fre-01':43203}
OUTERS={'aggregate-relocation-fre-01':'aggregate-relocation-fre-01','budget-register-fre-01':'budget-register-fre-01','resumable-bulk-fre-01':'resumable-bulk-fre-remaining-01','resumable-copy-fre-01':'resumable-copy-fre-remaining-01'}
KEYS={'aggregate-relocation-fre-01':'9637b0acb1d208524c3c8b446af64cfd5e2d0d3be75e1412a8df76750ce36223','budget-register-fre-01':'366567663f043d4a2370d72ae7eeade60bb91cda07ac19e12831491b4f606504','resumable-bulk-fre-01':'78e60cdd76195c55583651bac6a7f7d349314dd1ea582b6a86335adbee48049d','resumable-copy-fre-01':'0e94d6d82b4b734e281e5b8c95a55866e5c7b0a8be53be2dafadd410708467ee'}
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
    from workflow_io import require_space
    require_space(ROOT,8)
    roots=[];proofs={};process_checks=[];evidence_roots=set()
    def bind(path,expected=None):
        path=path.resolve(strict=True);assert path.is_relative_to(ROOT)
        digest=sha(path)
        if expected is not None:assert digest==expected,path
        key=str(path.relative_to(ROOT));assert key not in proofs or proofs[key]==digest
        proofs[key]=digest
        return json.loads(path.read_text()) if path.suffix=='.json' else None
    for run,pid in RUNS.items():
        result_path=ROOT/'results'/run/'summary.json';result=bind(result_path)
        assert result['status']=='passed' and result['batches']==25 and len(result['records'])==25
        assert result['tool_key']==KEYS[run] and result['project']=='fre' and result['revision']==PIN
        assert result['counts']==dict(passed=382,ignored=7) and not result['failures'] and not result['outcome_changes']
        assert result['original_sources_and_tests_unchanged'] and result['strict_frontend']
        base=ROOT/result['raw'];assert base==ROOT/'.work'/run;evidence_roots.add(base)
        plan=bind(base/'plan.json');assert plan['config']['tool_key']==KEYS[run]
        assert plan['config']['project']=='fre' and plan['config']['revision']==PIN
        terminal=bind(base/'status.json')
        assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['completed_batches']==25
        assert terminal['pid']==pid and terminal['cwd']==str(ROOT)
        outer=bind(ROOT/'.work/experiments'/OUTERS[run]/'status.json')
        assert outer['status']=='finished' and outer['returncode']==0 and outer['child_pid']==pid
        assert outer['owner']==str(ROOT) and outer['supervisor_pid']==terminal['parent_pid']
        for old_pid in [outer['supervisor_pid'],pid]:
            check=subprocess.run(['ps','-p',str(old_pid),'-o','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
            process_checks.append(dict(pid=old_pid,returncode=check.returncode,stdout=check.stdout));assert run not in check.stdout and OUTERS[run] not in check.stdout
        case_roots=set()
        for record in result['records']:
            index=record['index'];assert 0<=index<25
            for path,digest in record['evidence'].items():bind(ROOT/path,digest)
            collection_path=ROOT/record['collection'];collection=json.loads(collection_path.read_text())
            assert collection['tool_key']==KEYS[run] and collection['project']=='fre' and collection['revision']==PIN
            expected_name=run+'-collect-'+str(index).zfill(3)
            collect_root=ROOT/collection['raw'];assert collect_root==ROOT/'.work/runs'/expected_name
            evidence_roots.add(collect_root)
            replay=json.loads((ROOT/record['replay']).read_text());evidence_roots.add(ROOT/replay['raw'])
            item=collection['compilation_invocation'];invocation=bind(ROOT/item['path'],item['sha256'])
            assert invocation['returncode']==0 and invocation['tool_key']==KEYS[run] and invocation['source_project']=='fre'
            assert invocation['revision']==PIN
            command=invocation['command'];assert command.count('--cache-namespace')==1
            assert command[command.index('--cache-namespace')+1]==expected_name
            assert command[command.index('--manifest-path')+1]==str(ROOT/'.work/sources/fre/Cargo.toml')
            bind(collect_root/'entries.json',invocation['entries_sha256'])
            report=json.loads((collect_root/'report.json').read_text())
            provenance=report['artifact_provenance'];assert provenance==collection['artifact_provenance']
            audit_path=Path(provenance['audit_path']);bind(audit_path,provenance['audit_sha256'])
            parts=audit_path.relative_to(ROOT/'.work/interpreter-workspaces'/KEYS[run]).parts
            assert len(parts)>2 and parts[1]=='target'
            namespace=ROOT/'.work/interpreter-workspaces'/KEYS[run]/parts[0]
            assert namespace.resolve(strict=True)==namespace;case_roots.add(namespace)
            artifacts=report['artifacts'];pack=Path(artifacts['directory'])
            assert pack.parent==namespace and pack.name.startswith('audit-bodies-')
            retained=[e['artifact'] for e in report['entries'] if 'artifact' in e]
            assert len(retained)==artifacts['files'] and retained
            for item in retained:
                path=pack/item['file'];assert path.parent==pack and path.stat().st_size==item['bytes'];bind(path,item['sha256'])
        assert len(case_roots)==25;roots+=sorted(case_roots)
        assert result['native_builds']==1 and result['fresh_native_controls']==382
        native=bind(ROOT/result['native_control'])
        assert native['project']=='fre' and native['revision']==PIN and native['package']=='fre-kernels' and native['reused_from'] is None
        assert native['sha256']==result['native_binary_sha256']
        executable=Path(native['binary']);bind(executable,native['sha256'])
        native_root=ROOT/'.work/runs'/(run+'-replay-000')/'native'
        assert executable.is_relative_to(native_root) and native_root.resolve(strict=True)==native_root
        native_commands=ROOT/'.work/runs'/(run+'-replay-000')/'commands.jsonl'
        builds=[json.loads(line) for line in native_commands.read_text().splitlines() if '--no-run' in json.loads(line)['command']]
        build,=builds;assert build['returncode']==0
        assert build['command'][build['command'].index('--target-dir')+1]==str(native_root)
        roots.append(native_root)
    assert len(roots)==len(set(roots))==104
    marker=ROOT/'.work/sources/fre/.rust-interp-owned.json';owner=bind(marker)
    assert owner['owner']==str(ROOT) and owner['revision']==PIN
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=marker.parent,text=True).strip()==PIN
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=marker.parent).strip()
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
        scope='Exactly one hundred collection namespaces and four original native build caches from four completed public fre runtime qualifications, each bound to its25-batch terminal, compilation invocations, artifact provenance, native executable and retained bodies. Nonexecutable incremental files and .o/.rlib/.rmeta in build/deps only. All other namespace files and saved case evidence hashed and preserved. No active, private, installed-tool or unrelated worktree cache. Shared and invocation locks held.'))
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
