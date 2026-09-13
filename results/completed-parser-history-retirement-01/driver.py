from contextlib import ExitStack
from pathlib import Path
import json, os, shutil, stat, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write

NAME='completed-parser-history-retirement-01'
RUNS={'pgrust-parser-edits-repository-continuation-01':(8722,8732),'pgrust-parser-edits-incremental-history-01':(85138,85141)}

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
    key='8c2d64bb756cbfedaaf84820cae1b1705575a7022326e239b04084f6217d06ae'
    def bind(path,expected=None):
        assert path.resolve(strict=True)==path and path.is_relative_to(ROOT)
        digest=sha(path)
        if expected is not None:assert digest==expected,path
        name=str(path.relative_to(ROOT));assert name not in proofs or proofs[name]==digest;proofs[name]=digest
        return json.loads(path.read_text()) if path.suffix=='.json' else None
    for run,(supervisor,pid) in RUNS.items():
        result_path=ROOT/'results'/run/'summary.json';result=bind(result_path)
        assert result['status']=='passed' and result['commands']==66 and result['original_tests']==114
        assert result['source_restored'] and result['original_assertions_unchanged'] and result['exact_native_test_outcomes']
        assert result['tool_key']==key
        base=ROOT/result['raw'];assert base==ROOT/'.work'/run;evidence_roots.add(base)
        plan=bind(base/'plan.json',result['plan_sha256']);rows=bind(base/'records.json',result['records_sha256'])
        assert plan['owner']==str(ROOT) and plan['tool_key']==key and len(rows)==66
        prefix=plan['prefix'];bind(ROOT/prefix['proof'],prefix['proof_sha256'])
        old=ROOT/prefix['old_raw'];bind(old/'plan.json',prefix['old_plan_sha256']);evidence_roots.add(old)
        assert prefix['retained_commands']==(2 if result['profile']=='repository' else 22)
        assert result['new_commands']+prefix['retained_commands']==66
        terminal_path=ROOT/'.work/experiments'/run/'status.json';terminal=bind(terminal_path)
        assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==terminal['cwd']==str(ROOT)
        assert terminal['supervisor_pid']==supervisor and terminal['child_pid']==pid;pids.update([supervisor,pid])
        for name,field in [('plan.json','plan_sha256'),('command.log','log_sha256')]:bind(terminal_path.with_name(name),terminal[field])
        source=ROOT/'.work/sources/pgrust';marker=source/'.rust-interp-owned.json';owner=bind(marker)
        assert owner['owner']==str(ROOT) and owner['revision']==plan['revision']
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==plan['revision']
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
        bind(source/'crates/backend/parser/gram_core/src/parse.rs',plan['original_source_sha256'])
        selected=set()
        for row in rows:
            pids.add(row['pid']);cmd=row['command'];assert (row['returncode']==0)==(row['state']!=-1)
            assert cmd[cmd.index('--manifest-path')+1]==str(source/'Cargo.toml')
            logs=ROOT/row['log_raw'];assert logs in [old,base];evidence_roots.add(logs)
            for stream in ['stdout','stderr']:bind(logs/(str(row['index'])+'.'+stream),row[stream+'_sha256'])
            for kind in ['artifact','entry_catalog','executable']:
                if kind in row:
                    item=row[kind];bind(ROOT/item['path'],item['sha256'])
            if row['mode']=='native':
                target=Path(cmd[cmd.index('--target-dir')+1]);assert target==old/'native';selected.add(target)
            else:
                assert row['mode'] in ['custom-a','custom-b'] and row['launch']['tool_key']==key
                assert cmd[cmd.index('--tool-key')+1]==key and cmd[cmd.index('--cache-namespace')+1]==old.name+':'+row['mode']
                target=Path(row['launch']['workspace_path']);assert target.parent==ROOT/'.work/interpreter-workspaces'/key;selected.add(target)
                bind(logs/(str(row['index'])+'-suite.json'),row['suite_sha256'])
        assert len(selected)==3 and all(p.resolve(strict=True)==p for p in selected);roots.update(selected)
    assert len(roots)==6;roots=sorted(roots)
    for pid in sorted(pids):
        check=subprocess.run(['ps','-p',str(pid),'-o','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
        assert check.returncode in [0,1] and not check.stderr and not any(run in check.stdout for run in RUNS)
        assert 'pgrust-parser-edits-' not in check.stdout
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
        scope='Six exact caches from two completed 66-command original pgrust parser histories. Retained prefixes, final terminal receipts, all source/record hashes, 114-test outcomes, suites, bytecode/catalogs and native executable snapshots verified. Only nonexecutable incremental and .o/.rlib/.rmeta compiler intermediates. All raw old/new evidence and every other selected-target file retained. No current, private, installed-tool or peer cache. Shared and invocation locks with fresh process and open-file checks.'))
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
