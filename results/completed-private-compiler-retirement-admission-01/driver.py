from contextlib import ExitStack
from pathlib import Path
import json, os, shutil, stat, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write

NAME='completed-private-compiler-retirement-01'
RUNS=['guarded-local-facts','guarded-ranges','scalar-copy-operands','memory-lookup','toolchain-lookup']
OUTERS={'guarded-local-facts':('guarded-local-facts-full-01',93275,93278,1),'guarded-ranges':('guarded-ranges-admission-resume-01',79844,79847,0),'scalar-copy-operands':('scalar-copy-operands-admission-resume-01',81838,81869,0),'memory-lookup':('memory-lookup-edit-rg-aot-01',38014,38023,0),'toolchain-lookup':('toolchain-lookup-edit-rg-aot-01',85035,85038,0)}

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
    roots=set();proofs={};process_checks=[];evidence_roots=set();pids=set()
    source=ROOT/'.work/sources/rg-aot';marker=source/'.rust-interp-owned.json';owner=json.loads(marker.read_text())
    adapter_path=ROOT/'.work/private/workflow-rg-aot.json';adapter=json.loads(adapter_path.read_text())
    assert owner['owner']==adapter['owner']==str(ROOT) and owner['revision']==adapter['revision']
    assert adapter['case']['private']
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==owner['revision']
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
    proofs[str(marker.relative_to(ROOT))]=sha(marker);proofs[str(adapter_path.relative_to(ROOT))]=sha(adapter_path)
    changed=source/adapter['case']['file'];proofs[str(changed.relative_to(ROOT))]=sha(changed)
    for prefix in RUNS:
        run=prefix+'-edit-rg-aot-01';base=ROOT/'.work'/run;evidence_roots.add(base)
        result_path=ROOT/'results'/run/'summary.json';result=json.loads(result_path.read_text())
        assert result['status']=='passed' and result['commands']==132 and result['source_restored'] and result['test_source_unchanged']
        assert result['native_assertion_outcomes_match'] and result['candidate_control_bytecode_matches']
        assert result['raw']==str(base.relative_to(ROOT))
        proofs[str(result_path.relative_to(ROOT))]=sha(result_path)
        for name,digest in result['evidence'].items():
            path=base/(name+'.json');assert sha(path)==digest;proofs[str(path.relative_to(ROOT))]=sha(path)
        plan=json.loads((base/'plan.json').read_text());assert plan['owner']==str(ROOT) and plan['revision']==owner['revision']
        assert sha(changed)==plan['source_sha256']
        outer,supervisor,pid,code=OUTERS[prefix];terminal_path=ROOT/'.work/experiments'/outer/'status.json';terminal=json.loads(terminal_path.read_text())
        assert terminal['owner']==terminal['cwd']==str(ROOT) and terminal['status']=='finished' and terminal['returncode']==code
        assert terminal['supervisor_pid']==supervisor and terminal['child_pid']==pid;pids.update([supervisor,pid]);proofs[str(terminal_path.relative_to(ROOT))]=sha(terminal_path)
        for name,field in [('plan.json','plan_sha256'),('command.log','log_sha256')]:
            path=terminal_path.with_name(name);assert sha(path)==terminal[field];proofs[str(path.relative_to(ROOT))]=sha(path)
        if outer!=run:
            parent_records=ROOT/'.work'/outer/'records.json';records=json.loads(parent_records.read_text());match,=[r for r in records if r['case']=='rg-aot'];assert match['returncode']==0 and match['summary_sha256']==sha(result_path);proofs[str(parent_records.relative_to(ROOT))]=sha(parent_records)
        rows=json.loads((base/'records.json').read_text());assert len(rows)==132
        selected=set()
        for row in rows:
            mode=row['mode'];cmd=row['command'];pids.add(row['pid'])
            assert (row['returncode']==0)==(row['state']!=-1 or mode=='check')
            assert cmd[cmd.index('--manifest-path')+1]==str(source/'Cargo.toml')
            if mode in ['native','native_lines','check']:
                target=Path(cmd[cmd.index('--target-dir')+1]);assert target==base/mode;selected.add(target)
            else:
                assert mode in ['baseline','duplicate','candidate'] and cmd[cmd.index('--cache-namespace')+1]==run+':'+mode
                assert cmd[cmd.index('--tool-key')+1]==row['launch']['tool_key']==result['tool_keys'][mode]
                target=Path(row['launch']['workspace_path']);assert target.parent==ROOT/'.work/interpreter-workspaces'/result['tool_keys'][mode];selected.add(target)
            for kind in ['artifact','catalog','entry_catalog','selection','native_executable']:
                if kind in row:
                    item=row[kind];assert sha(ROOT/item['path'])==item['sha256'];proofs[item['path']]=item['sha256']
        assert len(selected)==6;roots.update(selected)
    assert len(roots)==30;roots=sorted(roots);assert all(p.resolve(strict=True)==p for p in roots)
    for pid in sorted(pids):
        check=subprocess.run(['ps','-p',str(pid),'-o','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
        assert check.returncode in [0,1] and not check.stderr and not any(OUTERS[p][0] in check.stdout for p in RUNS)
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
        print(json.dumps(dict(root_index=len(sizes)-1,files=sizes[-1]['files'],logical_bytes=sizes[-1]['logical_bytes'])),flush=True)
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
        scope='Thirty exact compiler caches from five completed private132-command histories. Existing private adapter ownership/source pin/restoration, terminal controllers, parent case receipts, every original command and saved artifact verified. Paths, manifests and command details stay local. Nonexecutable compiler intermediates only; every executable, bytecode/catalog snapshot and raw proof preserved. Shared/invocation locks and fresh process/open-file checks. No current command, installed-tool or peer cache; no benchmark repeated.'))
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
        plan_sha256=sha(work/'plan.json'),raw=str(work.relative_to(ROOT)),performance_measurement=False,private_details_redacted=True,completed_histories=5,completed_commands=660)
    write(work/'summary.json',result);print(json.dumps(result),flush=True)
