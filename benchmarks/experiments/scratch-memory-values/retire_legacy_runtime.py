from contextlib import ExitStack
from pathlib import Path
import json, os, shutil, stat, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write
from native_suite import test_status
from suite_reports import validate_report

NAME='closed-legacy-runtime-compiler-retirement-02'
RUNS=[
    'paired-repeated-token-01','aggregate-relocation-e2e-01-token-phrase',
    'resumable-copy-e2e-01-token-phrase','native-controls-corpus-01-token-phrase',
    'whole-call-e2e-02-token-phrase','mir-call-policy-01-token-phrase',
    'paired-call-results-local-token-phrase-01','paired-native-memory-parts-token-phrase-01',
    'paired-native-compare-bytes-token-phrase-01','paired-packed-native-cache-token-phrase-01',
    'paired-constant-dynamic-copy-token-phrase-01','paired-native-cast-width-token-phrase-01',
    'paired-scalar-packed-cache-token-phrase-01','paired-scalar-promotion-moves-token-phrase-01',
    'paired-virtual-register-compaction-token-phrase-01','paired-local-memory-forwarding-token-phrase-01',
    'paired-native-paired-spills-token-phrase-01','fixed-frame-clear-library-token-02',
    'resumable-copy-original-e2e-01-token-phrase','resumable-bulk-e2e-01-token-phrase',
    'resumable-e2e-01-token-phrase','resumable-bulk-e2e-02-token-phrase',
    'persistent-e2e-01-token-phrase','native-region-e2e-01-token-phrase',
    'bounded-native-e2e-01-token-phrase',
]

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

with ExitStack() as stack:
    lock=stack.enter_context((ROOT/'.work/benchmark.lock').open('a'));acquire_lock(lock,45)
    from workflow_io import require_space
    from workflow_cases import WORKFLOW_VARIANTS
    import hashlib
    require_space(ROOT,8)
    roots=set();proofs={};process_checks=[];evidence_roots=set();pids=set();completed=[]
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    source=ROOT/'.work/sources/fre';pin='e0df0b010b156b030a02f073588d28703f4267f3'
    marker=bind(source/'.rust-interp-owned.json');assert marker['owner']==str(ROOT) and marker['revision']==pin
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==pin
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
    for run in RUNS:
        raw=ROOT/'.work/runs'/run;out=ROOT/'results'/run;evidence_roots.add(raw)
        summary=bind(out/'summary.json');rows=bind(raw/'records.json');active=bind(raw/'active-command.json')
        data=subprocess.check_output(['git','show',revision+':'+str((out/'summary.json').relative_to(ROOT))],cwd=ROOT)
        assert hashlib.sha256(data).hexdigest()==sha(out/'summary.json')
        assert summary['project']=='fre' and summary['revision']==pin and summary['raw']==str(raw.relative_to(ROOT))
        assert summary['test_source_unchanged'] and summary['wrong_production_edit_rejected']
        assert summary['samples']==[{k:v for k,v in row.items() if k!='calls'} for row in rows]
        assert len(rows) in [21,63] and len(summary['tests'])==3
        changed=source/WORKFLOW_VARIANTS['fre',summary['workflow']]['file']
        bind(changed,rows[0]['source_sha256'])
        assert active['status']=='finished' and active['returncode']==0 and active['cwd']==str(source)
        pids.update([active['pid'],active['parent_pid']])
        cycles=len(rows)//21
        expected={(c,s,m) for c in range(cycles) for s in [0,-1,1,2,3,4,5] for m in ['native','baseline','candidate']}
        assert {(r.get('cycle',0),r['state'],r['mode']) for r in rows}==expected
        assert len({r['source_sha256'] for r in rows if r['state']==0})==1
        selected=set()
        for row in rows:
            assert row['tests']==summary['tests'] and row['calls']
            assert (all(c['returncode']==0 for c in row['calls']))==(row['state']!=-1)
            for artifact in row['artifacts']:
                p=ROOT/artifact['path'];assert p.is_relative_to(raw/'artifacts') and p.suffix=='.rbc'
                bind(p,artifact['sha256'])
            for call in row['calls']:
                pids.add(call['pid']);cmd=call['command'];mode=row['mode']
                assert cmd[cmd.index('--manifest-path')+1]==str(source/'Cargo.toml')
                if mode=='native':
                    target=Path(cmd[cmd.index('--target-dir')+1]);assert target==raw/'native'
                else:
                    assert cmd[cmd.index('--cache-namespace')+1]==run+':'+mode
                    key=cmd[cmd.index('--tool-key')+1];assert key==row['tool_key']
                    launch=call['launch'];assert launch['tool_key']==key
                    artifact=Path(launch['artifact_path']);parent=ROOT/'.work/interpreter-workspaces'/key
                    relative=artifact.relative_to(parent);assert relative.parts[1]=='target' and len(relative.parts[0])==24
                    target=parent/relative.parts[0]
                    assert all(artifact!=ROOT/a['path'] for a in row['artifacts'])
                # A previously retired cache may be absent; it contributes no new removal.
                if target.exists():
                    assert target.resolve(strict=True)==target;roots.add(target);selected.add(str(target.relative_to(ROOT)))
        # Any separately recorded native check floor uses the same completed run namespace.
        if (raw/'check-records.json').exists():
            checks=bind(raw/'check-records.json')
            assert len(checks)==cycles*7
            for row in checks:
                # Historical check-floor records are flat and do not retain
                # per-command PIDs; their final child is in active-command.json.
                cmd=row['command'];assert row['returncode']==0 and 'check' in cmd
                target=Path(cmd[cmd.index('--target-dir')+1]);assert target==raw/'check'
                assert cmd[cmd.index('--manifest-path')+1]==str(source/'Cargo.toml')
                if target.exists():roots.add(target);selected.add(str(target.relative_to(ROOT)))
        completed.append(dict(run=run,commands=len(rows),roots=sorted(selected),summary_sha256=sha(out/'summary.json'),records_sha256=sha(raw/'records.json')))
        print('verified completed history',len(completed),len(RUNS),run,flush=True)
    roots=sorted(roots);assert roots and all(p.resolve(strict=True)==p for p in roots)
    check=subprocess.run(['ps','-p',','.join(map(str,sorted(pids))),'-o','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
    assert check.returncode in [0,1] and not check.stderr
    assert not any(run in line for run in RUNS for line in check.stdout.splitlines()[1:])
    process_checks.append(dict(pids=sorted(pids),returncode=check.returncode,stdout=check.stdout))
    for root in roots:
        if root.parent.parent==ROOT/'.work/interpreter-workspaces':
            invocation=stack.enter_context((root/'invocation.lock').open('r+'));acquire_lock(invocation,45)
    assert all(sha(ROOT/p)==h for p,h in proofs.items())
    work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
    write(work/'completed-histories.json',completed)
    proofs[str((work/'completed-histories.json').relative_to(ROOT))]=sha(work/'completed-histories.json')
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
            if not path.is_file() or path.relative_to(base).parts[0] in ['native','check']:continue
            assert not path.is_symlink();protected[str(path.relative_to(ROOT))]=sha(path)
    write(work/'inventory.json',rows);write(work/'protected.json',protected)
    assert rows, 'no eligible compiler intermediates remain; no deletion attempted'
    before=shutil.disk_usage(ROOT).free;started=time.time()
    write(work/'plan.json',dict(owner=str(ROOT),source_revision=revision,script_sha256=sha(Path(__file__)),completed_runs=RUNS,
        roots=sizes,process_checks=process_checks,open_checks=open_checks,files=len(rows),
        logical_bytes=sum(r['size'] for r in rows),free_before=before,started_at=started,
        scope='Exact completed public compiler caches from the 25 explicitly listed historical runtime token comparisons. Published summaries, complete recorded command outcomes, terminal final children, original source pin/restoration, snapshots and per-run custom cache namespaces are verified. Only nonexecutable compiler intermediates are eligible. Preserve every executable, bytecode/catalog snapshot and raw proof under shared/invocation locks and fresh process/open-file checks. No private cache, shared target, installed tool, unstarted later-case cache or peer cache.'))
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
        plan_sha256=sha(work/'plan.json'),raw=str(work.relative_to(ROOT)),performance_measurement=False,completed_histories=len(completed),completed_commands=sum(r['commands'] for r in completed))
    write(work/'summary.json',result);print(json.dumps(result),flush=True)
