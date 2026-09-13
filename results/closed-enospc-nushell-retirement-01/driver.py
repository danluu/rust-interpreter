from contextlib import ExitStack
from pathlib import Path
import json, os, shutil, stat, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write

NAME='closed-enospc-nushell-retirement-01'
RUNS={'resumable-bulk-heldout-01':(79695,79698,45748)}

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
    original='resumable-bulk-heldout-01';run=original+'-nushell-type-relations'
    base=ROOT/'.work/runs'/run
    assert not (ROOT/'results'/run/'summary.json').exists(), 'partial run acquired a new result'
    roots=set();proofs={};process_checks=[];evidence_roots={base}
    def bind(path,expected=None):
        assert path.resolve(strict=True)==path and path.is_relative_to(ROOT)
        digest=sha(path)
        if expected is not None:assert digest==expected,path
        key=str(path.relative_to(ROOT));assert key not in proofs or proofs[key]==digest
        proofs[key]=digest
        return json.loads(path.read_text()) if path.suffix=='.json' else None
    failure_path=ROOT/'results/resumable-bulk-heldout-failure-01/summary.json'
    recovery=bind(ROOT/'results/resumable-bulk-heldout-recovery-01/summary.json')
    failure=bind(failure_path,recovery['failure_sha256'])
    assert failure['status']=='incomplete: ENOSPC' and failure['run_id']==original
    assert failure['source_restored'] and failure['no_matching_processes'] and failure['stale_original_status_receipts_preserved']
    assert failure['incomplete_workflow']=='nushell-type-relations' and failure['incomplete_primary_records']==12 and failure['incomplete_check_records']==3
    assert failure['partial_final_check_outcome']=='unknown: no completed receipt'
    assert recovery['status']=='seven complete cases verified across two run histories' and recovery['original_run_status']=='incomplete: ENOSPC; unchanged'
    assert recovery['original_primary_gates_unchanged'] and recovery['retained'] is False
    replacement,=[r for r in recovery['workflows'] if r['workflow']=='nushell-type-relations']
    replacement_path=ROOT/replacement['report'];replacement_report=bind(replacement_path,replacement['report_sha256'])
    assert replacement_path==ROOT/'results/resumable-bulk-heldout-retry-02-nushell-type-relations/summary.json'
    assert len(replacement_report['samples'])==63 and replacement_report['project']=='nushell'
    for source,item in failure['evidence'].items():
        bind(ROOT/source,item['sha256']);bind(failure_path.parent/item['snapshot'],item['sha256'])
    outer=bind(ROOT/'.work/experiments'/original/'status.json')
    ledger=bind(ROOT/'.work/corpus-runs'/original/'status.json')
    corpus_plan=bind(ROOT/'.work/corpus-runs'/original/'plan.json')
    assert outer['owner']==outer['cwd']==ledger['cwd']==str(ROOT)
    assert outer['supervisor_pid']==79695 and outer['child_pid']==ledger['pid']==79698 and ledger['child_pid']==45748
    assert ledger['command'][ledger['command'].index('--run-id')+1]==run
    assessor=bind(ROOT/'.work/experiments/resumable-heldout-recovery-assessment-01/status.json')
    assert assessor['status']=='finished' and assessor['returncode']==0 and assessor['owner']==str(ROOT)
    assert assessor['supervisor_pid']==46359 and assessor['child_pid']==46369
    bind(ROOT/'benchmarks/experiments/resumable-native-calls/assess_heldout_recovery.py',recovery['assessor_sha256'])
    for name,field in [('plan.json','plan_sha256'),('command.log','log_sha256')]:
        bind(ROOT/'.work/experiments/resumable-heldout-recovery-assessment-01'/name,assessor[field])
    rows=json.loads((base/'records.json').read_text());checks=json.loads((base/'check-records.json').read_text())
    assert len(rows)==12 and len(checks)==3
    assert {(r['cycle'],r['state'],r['mode']) for r in rows}=={(0,state,mode) for state in [0,-1,1,2] for mode in ['native','baseline','candidate']}
    keys={mode:corpus_plan['options'][mode+'_tool_key'] for mode in ['baseline','candidate']}
    assert all(keys[m]==recovery[m+'_tool_key'] for m in keys)
    active=json.loads((base/'active-command.json').read_text());pids={79695,79698,45748,46359,46369,active['pid']}
    manifest=ROOT/'.work/sources/nushell/Cargo.toml'
    for row in rows:
        call,=row['calls'];cmd=call['command'];pids.add(call['pid'])
        assert cmd[cmd.index('--manifest-path')+1]==str(manifest)
        assert (call['returncode']==0)==(row['state']!=-1)
        if row['mode']=='native':
            target=Path(cmd[cmd.index('--target-dir')+1]);assert target==base/'native';roots.add(target)
        else:
            mode=row['mode'];key=keys[mode]
            assert cmd[cmd.index('--tool-key')+1]==row['tool_key']==key
            assert cmd[cmd.index('--cache-namespace')+1]==run+':'+mode
            launch=call['launch'];assert launch['tool_key']==key
            artifact=Path(launch['artifact_path']);parts=artifact.relative_to(ROOT/'.work/interpreter-workspaces'/key).parts
            assert len(parts)>2 and parts[1]=='target';target=ROOT/'.work/interpreter-workspaces'/key/parts[0];roots.add(target)
            snapshot,=row['artifacts'];assert snapshot['sha256']==launch['artifact_sha256'] and snapshot['bytes']==launch['artifact_bytes']
            bind(ROOT/snapshot['path'],snapshot['sha256'])
    for row in checks:
        cmd=row['command'];assert row['returncode']==0 and cmd[cmd.index('--manifest-path')+1]==str(manifest)
        target=Path(cmd[cmd.index('--target-dir')+1]);assert target==base/'check';roots.add(target)
    assert len(roots)==4;roots=sorted(roots)
    expected={base/'native',base/'check',ROOT/'.work/interpreter-workspaces'/keys['candidate']/'6e922a0a7ff56576aadf1b6e',ROOT/'.work/interpreter-workspaces'/keys['baseline']/'b8472363fad4eb09420e029d'}
    assert set(roots)==expected and all(p.resolve(strict=True)==p for p in roots)
    marker=manifest.parent/'.rust-interp-owned.json';owner=bind(marker)
    assert owner['owner']==str(ROOT) and owner['revision']==failure['source_revision']
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=manifest.parent,text=True).strip()==failure['source_revision']
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=manifest.parent).strip()
    bind(manifest.parent/failure['source_file'],failure['restored_source_sha256'])
    for pid in sorted(pids):
        check=subprocess.run(['ps','-p',str(pid),'-o','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
        assert check.returncode in [0,1] and not check.stderr and original not in check.stdout and 'assess_heldout_recovery.py' not in check.stdout
        process_checks.append(dict(pid=pid,returncode=check.returncode,stdout=check.stdout))
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
        scope='Four exact compiler caches from the closed ENOSPC Nushell attempt. It remains an incomplete 12-command/3-check history with unknown final check. A separately completed 63-command replacement and terminal recovery audit already exist; no partial timing is adopted or resumed. Original stale receipts, failed-run snapshots, saved bytecode, current executables, sources and all noncompiler files retained. Only nonexecutable incremental and .o/.rlib/.rmeta compiler files. No private, current benchmark, installed-tool or peer cache. Shared/invocation locks and fresh exact-PID/open-file checks.'))
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
