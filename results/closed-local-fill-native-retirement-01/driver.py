from contextlib import ExitStack
from pathlib import Path
import json, os, shutil, stat, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write

NAME='closed-local-fill-native-retirement-01'
RUNS={'e2e-paired-nushell-type-relations-jit-local-fill-broad-02':('nushell',10,19495,77207,101),'e2e-paired-ruff-jit-local-fill-broad-01':('ruff',3,9958,236,0)}

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
    report_path=ROOT/'results/paired-jit-local-fill-corpus-02/summary.json';report=json.loads(report_path.read_text())
    assert report['correctness_qualified'] and report['workflows']==11
    assert report['interrupted_nushell_comparison']=='.work/runs/e2e-paired-nushell-type-relations-jit-local-fill-broad-02'
    assert report['failed_ruff_comparison']=='.work/runs/e2e-paired-ruff-jit-local-fill-broad-01'
    proofs[str(report_path.relative_to(ROOT))]=sha(report_path)
    narrative=report_path.with_name('summary.md');proofs[str(narrative.relative_to(ROOT))]=sha(narrative)
    from workflow_cases import WORKFLOWS,WORKFLOW_VARIANTS
    for run,(project,count,child,parent,returncode) in RUNS.items():
        assert not (ROOT/'results'/run/'summary.json').exists()
        base=ROOT/'.work/runs'/run;evidence_roots.add(base)
        active_path=base/'active-command.json';active=json.loads(active_path.read_text())
        assert active['status']=='finished' and active['pid']==child and active['parent_pid']==parent and active['returncode']==returncode
        source=ROOT/'.work/sources'/project;assert active['cwd']==str(source)
        pids.update([child,parent]);proofs[str(active_path.relative_to(ROOT))]=sha(active_path)
        rows_path=base/'records.json';rows=json.loads(rows_path.read_text());assert len(rows)==count
        proofs[str(rows_path.relative_to(ROOT))]=sha(rows_path)
        native=base/'native';assert native.resolve(strict=True)==native;roots.append(native)
        for row in rows:
            assert row['mode'] in ['native','baseline','candidate']
            for call in row['calls']:
                cmd=call['command'];pids.add(call['pid']);assert cmd[cmd.index('--manifest-path')+1]==str(source/'Cargo.toml')
                if row['mode']=='native':
                    assert cmd[:3]==['cargo','+nightly-2026-09-08','test'] and cmd[cmd.index('--target-dir')+1]==str(native)
                else:assert Path(cmd[1])==ROOT/'scripts/interpreter.py'
            for item in row.get('artifacts',[]):
                path=ROOT/item['path'];assert path.is_relative_to(base/'artifacts') and sha(path)==item['sha256'];proofs[item['path']]=item['sha256']
        case_name='nushell-type-relations' if project=='nushell' else 'ruff'
        replacement=ROOT/report['cases'][case_name]['report'];replacement_summary=json.loads(replacement.read_text())
        expected='e2e-paired-'+case_name+'-jit-local-fill-broad-'+('03' if project=='nushell' else '02')
        assert replacement.parent.name==expected and replacement.name=='summary.json'
        assert replacement_summary['project']==project and len(replacement_summary['samples'])==21
        proofs[str(replacement.relative_to(ROOT))]=sha(replacement)
        marker=source/'.rust-interp-owned.json';owner=json.loads(marker.read_text());assert owner['owner']==str(ROOT) and owner['revision']==replacement_summary['revision']
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==owner['revision']
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
        case=WORKFLOW_VARIANTS['nushell','type-relations'] if project=='nushell' else WORKFLOWS['ruff']
        changed=source/case['file'];first=next(r for r in rows if r['mode']=='native' and r['state']==0)
        assert sha(changed)==first['source_sha256'];proofs[str(changed.relative_to(ROOT))]=sha(changed);proofs[str(marker.relative_to(ROOT))]=sha(marker)
    assert len(roots)==len(set(roots))==2
    for pid in sorted(pids):
        check=subprocess.run(['ps','-p',str(pid),'-o','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
        assert check.returncode in [0,1] and not check.stderr and not any(run in check.stdout for run in RUNS)
        process_checks.append(dict(pid=pid,returncode=check.returncode,stdout=check.stdout))
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
        scope='Two exact native caches of closed local-fill comparison attempts explicitly excluded by their final corpus report: Nushell10 partial records and Ruff3 cold records. Completed last-child receipts, later full21-command replacement reports, all original commands/artifacts and restored public source pins verified. Original failures remain failures; no partial timings adopted or resumed. Only nonexecutable compiler intermediates. Executables, raw logs, bytecode and all other cache files preserved. Shared lock and fresh exact-process/open-file checks; no private, current, installed-tool or peer cache.'))
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
