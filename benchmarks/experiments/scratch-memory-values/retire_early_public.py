from contextlib import ExitStack
from pathlib import Path
import json, os, shutil, stat, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write
from native_suite import test_status
from suite_reports import validate_report

NAME='closed-early-public-compiler-retirement-02'
RUNS=['e2e-workflow-nushell-std-mir-01','e2e-workflow-ruff-hostopt1-01']

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
    from workflow_cases import WORKFLOWS
    import hashlib
    require_space(ROOT,8)
    roots=set();proofs={};process_checks=[];evidence_roots=set();pids=set();completed=[]
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    for run in RUNS:
        raw=ROOT/'.work/runs'/run;out=ROOT/'results'/run;evidence_roots.add(raw)
        summary=bind(out/'summary.json');rows=bind(raw/'records.json')
        data=subprocess.check_output(['git','show',revision+':'+str((out/'summary.json').relative_to(ROOT))],cwd=ROOT)
        assert hashlib.sha256(data).hexdigest()==sha(out/'summary.json')
        assert summary['project'] in ['nushell','ruff'] and summary['raw']==str(raw.relative_to(ROOT))
        assert summary['test_source_unchanged'] and summary['wrong_production_edit_rejected']
        assert summary['samples']==[{k:v for k,v in row.items() if k!='calls'} for row in rows]
        assert len(rows)==21 and {r['mode'] for r in rows}=={'native','interpreter','jit'}
        source=ROOT/'.work/sources'/summary['project'];marker=bind(source/'.rust-interp-owned.json')
        assert marker['owner']==str(ROOT) and marker['revision']==summary['revision']
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==summary['revision']
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
        bind(source/WORKFLOWS[summary['project']]['file'],rows[0]['source_sha256']);bind(source/'Cargo.toml');bind(source/'Cargo.lock')
        key=summary['tool_key'];tool=ROOT/'.work/interpreter-tools'/key
        ready=bind(tool/'ready.json');assert ready=={'rust-interp-vm':summary['vm_sha256'],'rust-interp-mir-export':summary['exporter_sha256']}
        for file,h in ready.items():bind(tool/file,h)
        selected=set()
        assert {(r['state'],r['mode']) for r in rows}=={(s,m) for s in [0,-1,1,2,3,4,5] for m in ['native','interpreter','jit']}
        for row in rows:
            # Early published histories vary test selection by state. The
            # full row, including this exact selection, already matches its
            # immutable published sample above; do not invent full-suite runs.
            assert row['tests'] and set(row['tests'])<=set(summary['tests']) and row['calls']
            assert all(c['returncode']==0 for c in row['calls'])==(row['state']!=-1)
            for call in row['calls']:
                pids.add(call['pid']);cmd=call['command'];mode=row['mode']
                assert cmd[cmd.index('--manifest-path')+1]==str(source/'Cargo.toml')
                if mode=='native':
                    target=Path(cmd[cmd.index('--target-dir')+1]);assert target==raw/'native'
                else:
                    assert cmd[1]==str(ROOT/'scripts/interpreter.py') and '--test-body' in cmd and '--std-mir' in cmd
                    namespace=cmd[cmd.index('--cache-namespace')+1];assert namespace==run+':'+mode
                    value='shared-entries-v1\0'+str(source/'Cargo.toml')+'\0'+cmd[cmd.index('--package')+1]+'\0True\0std-mir:'+summary['std_mir']['key']+'\0'+namespace
                    identity_key=hashlib.sha256(value.encode()).hexdigest()[:24]
                    target=ROOT/'.work/interpreter-workspaces'/key/identity_key
                assert target.resolve(strict=True)==target and target.is_dir();roots.add(target);selected.add(str(target.relative_to(ROOT)))
        completed.append(dict(run=run,commands=len(rows),roots=sorted(selected),summary_sha256=sha(out/'summary.json'),records_sha256=sha(raw/'records.json')))
    roots=sorted(roots);assert len(roots)==6
    check=subprocess.run(['ps','-p',','.join(map(str,sorted(pids))),'-o','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
    assert check.returncode in [0,1] and not check.stderr and not any(run in line for run in RUNS for line in check.stdout.splitlines()[1:])
    process_checks.append(dict(pids=sorted(pids),returncode=check.returncode,stdout=check.stdout))
    current=subprocess.run(['ps','-axo','pid,ppid,lstart,tty,command'],capture_output=True,text=True,check=True)
    assert not any(str(root) in line for root in roots for line in current.stdout.splitlines()[1:])
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
        scope='Six explicit caches from two completed early public Nushell/Ruff comparisons. Published summaries and all 42 captured commands, return codes and PIDs are retained and verified, with restored pinned sources, exact installed tool hashes, named custom namespace reconstruction and fresh process/open-file checks. These early receipts predate executed-artifact path reporting; ownership uses the exact unique public source namespace. Every existing bytecode, executable and other cache file is preserved. No new performance qualification is claimed. Only nonexecutable compiler intermediates are eligible. Preserve every executable, bytecode/catalog snapshot and raw proof under shared/invocation locks and fresh process/open-file checks. No private cache, shared target, installed tool, unstarted later-case cache or peer cache.'))
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
