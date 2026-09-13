from contextlib import ExitStack
from pathlib import Path
import json, os, shutil, stat, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write

NAME='legacy-public-compiler-retirement-01'
RUNS=['dev-profiles-03','pilot-02','native-repository-04']

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
    from legacy_native_cache_evidence import cache,CATALOG
    catalog=json.loads((ROOT/CATALOG).read_text());assert catalog['owner']==str(ROOT)
    roots=set();proofs={CATALOG:sha(ROOT/CATALOG)};process_checks=[];evidence_roots=set();qualified=[]
    for group in catalog['groups']:
        assert group['run'] in RUNS and group['project'] in ['nushell','ruff','pgrust']
        for variant in group['variants']:
            run=group['run']+'-'+group['project']+'-'+variant
            target,evidence,verified=cache(ROOT,run,group['run'],'native',sha)
            assert target==ROOT/'.work/targets'/group['run']/group['project']/variant
            assert verified['source_restored'] and verified['completed_commands']>0
            roots.add(target);qualified.append(verified)
            for p,h in evidence.items():assert p not in proofs or proofs[p]==h;proofs[p]=h
        evidence_roots.add(ROOT/'.work/runs'/group['run']/group['project'])
        evidence_roots.add(ROOT/'.work/runs'/group['run']/'source-record')
    assert len(roots)==20;roots=sorted(roots)
    assert all(sha(ROOT/p)==h for p,h in proofs.items())
    process_checks.append(dict(existing_catalog_verifier_checked_all_current_processes=True,qualified_groups=len(catalog['groups']),qualified_targets=len(qualified),no_old_backend_invoked=True))
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
            for prefix in [('debug',),('aarch64-apple-darwin','debug')]:
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
        scope='Twenty exact completed public Cargo baseline caches from the existing legacy-native-cache catalog. The catalog verifier validates all final command/runtime outcomes, archived harness hashes, source ownership/pins/restoration and absence of current exact-target/controller users. No old backend is invoked. Nonexecutable incremental and .o/.rlib/.rmeta compiler intermediates only. Every executable, other target file and archived benchmark evidence preserved. Shared lock and open-file checks; no private, installed-tool, active or other-worktree cache.'))
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
