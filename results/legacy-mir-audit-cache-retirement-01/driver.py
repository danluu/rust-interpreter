from contextlib import ExitStack
from pathlib import Path
import json, os, shutil, stat, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write

NAME='legacy-mir-audit-cache-retirement-01'
RUNS=['lowering-audit-fre-01','lowering-audit-ruff-02','lowering-audit-ruff-03','lowering-audit-fre-02','lowering-audit-fre-03','lowering-audit-ruff-01']

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
    catalog_path=ROOT/'.work/legacy-audit-cache-candidates.json'
    assert sha(catalog_path)=='18f6727a70501f90aab5fe7bf980dc2a0d58ef2609d604419d1df90d629f95b8'
    catalog=json.loads(catalog_path.read_text());assert [r['run'] for r in catalog]==RUNS
    roots=set();proofs={str(catalog_path.relative_to(ROOT)):sha(catalog_path)};process_checks=[];evidence_roots=set()
    process=subprocess.run(['ps','-axo','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
    assert process.returncode==0 and not process.stderr
    for item in catalog:
        run=item['run'];base=ROOT/'.work/runs'/run;target=ROOT/item['root'];audit=ROOT/item['audit']
        assert set(p.name for p in base.iterdir())=={'invocation.json','report.json','compiler.log','entries.json'}
        invocation=json.loads((base/'invocation.json').read_text());report=json.loads((base/'report.json').read_text())
        result_path=ROOT/'results'/run/'summary.json';result=json.loads(result_path.read_text())
        assert invocation['returncode']==0 and invocation['revision']==result['revision']
        assert invocation['source_project']==result['project'] and result['project'] in ['fre','ruff']
        assert result['raw']==str(base.relative_to(ROOT)) and invocation['tool_key']==report['tool_key']==result['tool_key']
        assert sha(base/'entries.json')==invocation['entries_sha256']
        entries=json.loads((base/'entries.json').read_text())
        assert report['kind']=='lowering-audit' and report['strict_frontend'] and not report['executed']
        assert result['strict_frontend'] and not result['executed']
        assert len(entries)==len(report['entries'])==report['requested']==result['sampled']
        assert [r['entry'] for r in report['entries']]==entries
        assert result['lowered']==report['lowered'] and result['blocked']==report['blocked']
        source=ROOT/'.work/sources'/result['project'];marker=source/'.rust-interp-owned.json';owner=json.loads(marker.read_text())
        assert owner['owner']==str(ROOT) and owner['revision']==result['revision']
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==owner['revision']
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
        cmd=invocation['command'];assert cmd[1]==str(ROOT/'scripts/interpreter.py')
        assert cmd[cmd.index('--manifest-path')+1]==str(source/'Cargo.toml')
        assert cmd[cmd.index('--cache-namespace')+1]==run and cmd[cmd.index('--audit-entries')+1]==str(base/'entries.json')
        assert '--test-body' in cmd and '--std-mir' in cmd
        assert target.parent==ROOT/'.work/interpreter-workspaces'/result['tool_key'] and audit.is_relative_to(target/'target')
        underlying={k:v for k,v in report.items() if k!='tool_key'}
        # Exact content binding; do not infer an obsolete namespace hash formula.
        matches=[p for p in target.parent.glob('*/target/aarch64-apple-darwin/debug/build/*/*/out/*.rmeta.audit.json') if json.loads(p.read_text())==underlying]
        assert matches==[audit]
        assert not any(str(target) in line or ('--cache-namespace '+run in line and 'interpreter.py' in line) for line in process.stdout.splitlines()[1:])
        check=subprocess.run(['ps','-p',str(invocation['pid']),'-o','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
        assert check.returncode in [0,1] and not check.stderr and run not in check.stdout
        process_checks.append(dict(run=run,pid=invocation['pid'],returncode=check.returncode,stdout=check.stdout,no_current_exact_namespace_or_target=True))
        for path in [*base.iterdir(),result_path,marker,audit]:proofs[str(path.relative_to(ROOT))]=sha(path)
        roots.add(target);evidence_roots.add(base)
    assert len(roots)==6;roots=sorted(roots);assert all(p.resolve(strict=True)==p for p in roots)
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
    before=shutil.disk_usage(ROOT).free;started=time.time()
    write(work/'plan.json',dict(owner=str(ROOT),script_sha256=sha(Path(__file__)),completed_runs=RUNS,
        roots=sizes,process_checks=process_checks,open_checks=open_checks,files=len(rows),
        logical_bytes=sum(r['size'] for r in rows),free_before=before,started_at=started,
        scope='Six exact completed public MIR audit namespaces. Bind each terminal invocation, entries digest, published coverage summary, current owned source pin and unique content-matched target audit report. These early formats preserve diagnostics, not individual body shards, and execute no guest. Remove only nonexecutable compiler intermediates while retaining every existing audit report, executable and noncompiler file. Shared/invocation locks and fresh process/open-file checks. No unknown, active or peer cache.'))
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
        plan_sha256=sha(work/'plan.json'),raw=str(work.relative_to(ROOT)),performance_measurement=False,completed_lowering_audits=6,guest_commands_repeated=0)
    write(work/'summary.json',result);print(json.dumps(result),flush=True)
