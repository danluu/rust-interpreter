from contextlib import ExitStack
from pathlib import Path
import json, os, shutil, stat, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write

NAME='early-public-native-retirement-01'
RUNS=['e2e-tests-ruff-heap-01','e2e-tests-ruff-01','e2e-tests-nushell-heap-01','e2e-tests-nushell-mir-01','e2e-tests-nushell-01','e2e-tests-fre-mir-01','e2e-tests-fre-heap-01','e2e-tests-fre-01','composed-development-edit-anchor-01']

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
    roots=[];proofs={};process_checks=[];evidence_roots=set();pids=set()
    from bench_e2e_tests import CASES
    for run in RUNS:
        result_path=ROOT/'results'/run/'summary.json';result=json.loads(result_path.read_text())
        proofs[str(result_path.relative_to(ROOT))]=sha(result_path)
        base=ROOT/result['raw'];rows=json.loads((base/'records.json').read_text())
        proofs[str((base/'records.json').relative_to(ROOT))]=sha(base/'records.json');evidence_roots.add(base)
        if run.startswith('e2e-tests-'):
            project=result['project'];assert project in ['ruff','nushell','fre'] and base==ROOT/'.work/runs'/run
            assert result['wrong_assertion_rejected'] and result['includes_launcher'] and len(rows)==len(result['samples'])==21
            assert {(r['state'],r['mode']) for r in rows}=={(state,mode) for state in [-1,0,1,2,3,4,5] for mode in ['native','interpreter','jit']}
            assert result['samples']==[{k:v for k,v in row.items() if k not in ['pid','command','stdout','stderr']} for row in rows]
            source=ROOT/'.work/sources'/project;case=CASES[project];revision=result['revision']
            target=base/'native'
            for row in rows:
                pids.add(row['pid']);cmd=row['command']
                assert cmd[cmd.index('--manifest-path')+1]==str(source/'Cargo.toml') and cmd[cmd.index('--package')+1]==case['package']
                assert (row['returncode']==0)==(row['state']!=-1)
                if row['mode']=='native':
                    assert cmd[:3]==['cargo','+nightly-2026-09-08','test']
                    assert cmd[cmd.index('--target-dir')+1]==str(target) and case['test'] in cmd and '--exact' in cmd
                    if row['state']!=-1:assert 'test result: ok. 1 passed; 0 failed' in row['stdout']
                else:assert Path(cmd[1])==ROOT/'scripts/interpreter.py'
            roots.append(target)
        else:
            assert run=='composed-development-edit-anchor-01' and base==ROOT/'.work'/run
            assert result['status']=='passed' and result['commands']==132 and len(rows)==132
            assert result['source_restored'] and result['test_source_unchanged'] and result['native_assertion_outcomes_match']
            for name in ['plan','records','transitions','space']:
                path=base/(name+'.json');assert sha(path)==result[name+'_sha256'];proofs[str(path.relative_to(ROOT))]=sha(path)
            plan=json.loads((base/'plan.json').read_text());assert plan['owner']==str(ROOT)
            source=ROOT/'.work/sources/fre';case=plan['case'];revision=plan['revision']
            assert sha(source/case['file'])==plan['original_source_sha256']
            terminal_path=ROOT/'.work/experiments'/run/'status.json';terminal=json.loads(terminal_path.read_text())
            assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==str(ROOT) and terminal['child_pid']==4836
            proofs[str(terminal_path.relative_to(ROOT))]=sha(terminal_path)
            pids.update([terminal['supervisor_pid'],terminal['child_pid']])
            for name,field in [('plan.json','plan_sha256'),('command.log','log_sha256')]:
                path=terminal_path.with_name(name);assert sha(path)==terminal[field];proofs[str(path.relative_to(ROOT))]=sha(path)
            native=set()
            for row in rows:
                pids.add(row['pid']);assert (row['returncode']==0)==(row['state']!=-1 or row['mode']=='check')
                if row['mode'] in ['native','native_lines','check']:
                    cmd=row['command'];target=Path(cmd[cmd.index('--target-dir')+1]);assert target==base/row['mode'];native.add(target)
                for kind in ['artifact','catalog','entry_catalog','selection','native_executable']:
                    if kind in row:
                        item=row[kind];assert sha(ROOT/item['path'])==item['sha256'];proofs[item['path']]=item['sha256']
            assert len(native)==3;roots.extend(sorted(native))
        marker=source/'.rust-interp-owned.json';owner=json.loads(marker.read_text())
        assert owner['owner']==str(ROOT) and owner['revision']==revision
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==revision
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
        proofs[str(marker.relative_to(ROOT))]=sha(marker)
        proofs[str((source/case['file']).relative_to(ROOT))]=sha(source/case['file'])
    assert len(roots)==len(set(roots))==11 and all(p.resolve(strict=True)==p for p in roots)
    for pid in sorted(pids):
        check=subprocess.run(['ps','-p',str(pid),'-o','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
        assert check.returncode in [0,1] and not check.stderr and not any(run in check.stdout for run in RUNS)
        process_checks.append(dict(pid=pid,returncode=check.returncode,stdout=check.stdout))
    proofs['scripts/bench_e2e_tests.py']=sha(ROOT/'scripts/bench_e2e_tests.py')
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
        scope='Eleven exact public native/check cache roots: eight original completed 21-command single-test histories and one completed 132-command composed-development anchor. Earlier histories predate supervisor receipts; ownership is bound to recorded absolute source/cache commands, current owned source markers/pins, exact published samples and all 21 completed original/wrong/five-edit outcomes. No native test is executed now. Fresh exact-PID and open-file checks precede removal. Nonexecutable incremental and .o/.rlib/.rmeta compiler intermediates only; every executable, metadata outside these compiler categories and all raw logs/artifacts preserved. No private, current or other-worktree cache.'))
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
