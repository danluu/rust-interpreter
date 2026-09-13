from contextlib import ExitStack
from pathlib import Path
import json, os, shutil, stat, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write

NAME='completed-public-native-retirement-01'
RUNS={'guarded-ranges-admission-resume-01':(79844,79847),'scalar-copy-operands-admission-resume-01':(81838,81869)}

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
    roots=[];proofs={};process_checks=[];evidence_roots=set()
    for campaign,(supervisor,pid) in RUNS.items():
        final_path=ROOT/'results'/campaign/'summary.json';final=json.loads(final_path.read_text())
        assert final['status'] in ['passed','rejected'] and final['commands']==726
        assert final['no_completed_case_repeated'] and final['final_source_and_input_audit_passed']
        assert final['completed_cases']==['token','folded','pgrust','rg-aot','nushell'] and final['unstarted_cases']==[]
        raw=ROOT/final['raw'];assert raw==ROOT/'.work'/campaign
        proofs[str(final_path.relative_to(ROOT))]=sha(final_path)
        for field,name in [('plan','plan'),('records','records'),('final_audit','final-audit')]:
            path=raw/(name+'.json');assert sha(path)==final[field+'_sha256'];proofs[str(path.relative_to(ROOT))]=sha(path)
        terminal_path=ROOT/'.work/experiments'/campaign/'status.json';terminal=json.loads(terminal_path.read_text())
        assert terminal['owner']==terminal['cwd']==str(ROOT) and terminal['status']=='finished' and terminal['returncode']==0
        assert terminal['supervisor_pid']==supervisor and terminal['child_pid']==pid
        assert terminal['command'][-2:]==['--run-id',campaign]
        proofs[str(terminal_path.relative_to(ROOT))]=sha(terminal_path)
        for name in ['plan','command']:
            path=terminal_path.with_name(name+('.json' if name=='plan' else '.log'))
            assert sha(path)==terminal['plan_sha256' if name=='plan' else 'log_sha256'];proofs[str(path.relative_to(ROOT))]=sha(path)
        for old_pid in [supervisor,pid]:
            check=subprocess.run(['ps','-p',str(old_pid),'-o','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
            assert check.returncode in [0,1] and not check.stderr and campaign not in check.stdout
            process_checks.append(dict(pid=old_pid,returncode=check.returncode,stdout=check.stdout))
        campaign_records=json.loads((raw/'records.json').read_text());assert len(campaign_records)==5
        prefix=campaign.removesuffix('-admission-resume-01') if hasattr(str,'removesuffix') else campaign[:-len('-admission-resume-01')]
        for case in ['token','folded','pgrust']:
            run=prefix+'-edit-'+case+'-01';base=ROOT/'.work'/run;evidence_roots.add(base)
            result_path=ROOT/'results'/run/'summary.json';result=json.loads(result_path.read_text())
            matched=[r for r in campaign_records if r['case']==case];assert len(matched)==1 and matched[0]['returncode']==0 and matched[0]['summary_sha256']==sha(result_path)
            assert result['status']=='passed' and result['commands']==154 and result['source_restored'] and result['test_source_unchanged']
            assert result['native_assertion_outcomes_match'] and result['candidate_control_bytecode_matches']
            assert result['case']==case and result['raw']==str(base.relative_to(ROOT))
            proofs[str(result_path.relative_to(ROOT))]=sha(result_path)
            for name in ['plan','records','transitions','space']:
                path=base/(name+'.json');assert sha(path)==result[name+'_sha256'];proofs[str(path.relative_to(ROOT))]=sha(path)
            plan=json.loads((base/'plan.json').read_text());assert plan['owner']==str(ROOT)
            source=ROOT/'.work/sources'/('pgrust' if case=='pgrust' else 'fre')
            marker=source/'.rust-interp-owned.json';owner=json.loads(marker.read_text())
            assert owner['owner']==str(ROOT) and owner['revision']==plan['revision']
            assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==plan['revision']
            assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
            changed=source/plan['case']['file'];assert sha(changed)==plan['original_source_sha256']
            proofs[str(marker.relative_to(ROOT))]=sha(marker);proofs[str(changed.relative_to(ROOT))]=sha(changed)
            records=json.loads((base/'records.json').read_text());assert len(records)==154
            native_paths=set()
            for row in records:
                assert (row['returncode']==0)==(row['state']!=-1 or row['mode']=='check')
                for kind in ['artifact','catalog','entry_catalog','selection','native_executable']:
                    if kind in row:
                        item=row[kind];assert sha(ROOT/item['path'])==item['sha256'];proofs[item['path']]=item['sha256']
                if row['mode'] in ['native','native_lines','check']:
                    command=row['command'];assert command.count('--target-dir')==1
                    target=Path(command[command.index('--target-dir')+1]);assert target==base/row['mode'] and target.resolve(strict=True)==target
                    native_paths.add(target)
            assert len(native_paths)==3;roots.extend(sorted(native_paths))
    assert len(roots)==len(set(roots))==18
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
        scope='Eighteen exact native/check cache roots from the completed token, folded and pgrust histories of guarded-ranges and scalar-copy-operands. Final 726-command receipts, per-case source restoration, original commands, current source pins and artifact hashes verified. Only nonexecutable incremental and .o/.rlib/.rmeta compiler intermediates; executables and all raw evidence preserved. No private, incomplete, installed-tool or other-worktree caches. Shared lock held; all selected roots checked for open files.'))
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
