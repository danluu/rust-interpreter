from contextlib import ExitStack
from pathlib import Path
import json, os, shutil, stat, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write

NAME='completed-legacy-private-native-retirement-01'
CATALOG=ROOT/'.work/completed-legacy-private-native-candidates.json'
CATALOG_SHA='92de8d80d22f44bc5e73aa285e827e46040364cc9a62986326e800ce98b9cf2c'
RUNS=[r['run'] for r in json.loads(CATALOG.read_text())]

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
    from native_suite import test_status
    assert sha(CATALOG)==CATALOG_SHA and len(RUNS)==24
    roots=set();proofs={str(CATALOG.relative_to(ROOT)):CATALOG_SHA};process_checks=[];evidence_roots=set();pids=set()
    source=ROOT/'.work/sources/rg-aot';marker=source/'.rust-interp-owned.json';adapter_path=ROOT/'.work/private/workflow-rg-aot.json'
    owner=json.loads(marker.read_text());adapter=json.loads(adapter_path.read_text());case=adapter['case']
    assert owner['owner']==adapter['owner']==str(ROOT) and owner['revision']==adapter['revision'] and case['private']
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==owner['revision']
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
    changed=source/case['file'];assert len(case['tests'])==1
    for path in [marker,adapter_path,changed]:proofs[str(path.relative_to(ROOT))]=sha(path)
    process=subprocess.run(['ps','-axo','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
    assert process.returncode==0 and not process.stderr
    for run in RUNS:
        base=ROOT/'.work/runs'/run;target=base/'native';result_path=ROOT/'results'/run/'summary.json'
        result=json.loads(result_path.read_text());rows=json.loads((base/'records.json').read_text())
        assert result['project']=='rg-aot' and result['revision']==owner['revision'] and result['raw']==str(base.relative_to(ROOT))
        assert 'schema_version' not in result and result['test_source_unchanged'] and result['wrong_production_edit_rejected']
        assert result['samples']==[{k:v for k,v in row.items() if k not in ['calls','tests']} for row in rows]
        assert len(rows)==21 and sorted({r['state'] for r in rows})==[-1,0,1,2,3,4,5]
        modes={r['mode'] for r in rows};assert modes in [{'native','interpreter','jit'},{'native','baseline','candidate'}]
        assert len({(r['mode'],r['state']) for r in rows})==21
        assert sha(changed)==rows[0]['source_sha256']
        for state in [0,-1,1,2,3,4,5]:
            selected=[r for r in rows if r['state']==state]
            assert len(selected)==3 and len({r['source_sha256'] for r in selected})==1
        assert len({r['source_sha256'] for r in rows})==7
        for row in rows:
            assert row['tests']==case['tests'] and len(row['calls'])==1
            call,=row['calls'];pids.add(call['pid']);assert (call['returncode']==0)==(row['state']!=-1)
            cmd=call['command'];assert cmd[cmd.index('--manifest-path')+1]==str(source/'Cargo.toml')
            if row['mode']=='native':
                assert cmd[cmd.index('--target-dir')+1]==str(target)
                assert test_status(case['tests'][0],call['returncode'],call['stdout'])==('failed' if row['state']==-1 else 'passed')
            for artifact in row.get('artifacts',[]):
                path=ROOT/artifact['path'];assert path.is_relative_to(base) and sha(path)==artifact['sha256']
                proofs[str(path.relative_to(ROOT))]=sha(path)
        assert not any(str(target) in line or ('--run-id '+run in line and 'bench_e2e_workflow.py' in line) for line in process.stdout.splitlines()[1:])
        proofs[str(result_path.relative_to(ROOT))]=sha(result_path)
        roots.add(target);evidence_roots.add(base)
    for pid in sorted(pids):
        check=subprocess.run(['ps','-p',str(pid),'-o','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
        assert check.returncode in [0,1] and not check.stderr and not any(run in check.stdout for run in RUNS)
        process_checks.append(dict(pid=pid,returncode=check.returncode,stdout=check.stdout))
    assert len(roots)==24;roots=sorted(roots);assert all(p.resolve(strict=True)==p for p in roots)
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
        print(json.dumps(dict(root_index=len(sizes)-1,files=sizes[-1]['files'],logical_bytes=sizes[-1]['logical_bytes'])),flush=True)
    # Protect all original, retained-prefix and continuation evidence outside the selected compiler cache.
    for base in sorted(evidence_roots):
        for path in base.rglob('*'):
            if not path.is_file() or path.relative_to(base).parts[0] in ['native','native_lines','check']:continue
            assert not path.is_symlink();protected[str(path.relative_to(ROOT))]=sha(path)
    write(work/'inventory.json',rows);write(work/'protected.json',protected)
    before=shutil.disk_usage(ROOT).free;started=time.time()
    write(work/'plan.json',dict(owner=str(ROOT),script_sha256=sha(Path(__file__)),completed_runs=RUNS,
        roots=sizes,process_checks=process_checks,open_checks=open_checks,files=len(rows),
        logical_bytes=sum(r['size'] for r in rows),free_before=before,started_at=started,
        scope='Twenty-four exact native compiler caches from completed private21-command histories predating the current supervisor format. Bind the full published/raw sample equality, seven distinct source states, all expected custom results and exact single-test native outcomes, current owned source/adapter revision and restoration, and recorded native target paths. No assertion of unavailable historical executable snapshots; every remaining executable and all raw evidence preserved. Only nonexecutable compiler intermediates. Shared lock and fresh process/open-file checks. Private paths and detailed evidence remain local. No custom, active or peer cache.'))
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
        plan_sha256=sha(work/'plan.json'),raw=str(work.relative_to(ROOT)),performance_measurement=False,private_details_redacted=True,completed_histories=24,completed_commands=504)
    write(work/'summary.json',result);print(json.dumps(result),flush=True)
