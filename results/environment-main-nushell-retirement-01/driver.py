from contextlib import ExitStack
from pathlib import Path
import json, os, shutil, stat, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write

NAME='environment-main-nushell-retirement-01'
RUNS={'environment-main-projects-01':24232}
PIN='9d3157963241cf89447119d34d6e887859f5e7e8'

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
    roots=[];proofs={};process_checks=[]
    result_path=ROOT/'results/environment-main-projects-01/summary.json'
    result=json.loads(result_path.read_text());base=ROOT/result['raw']
    assert result['status']=='passed' and result['commands']==40
    audit_path=ROOT/'results/environment-main-final-audit-01/summary.json';audit=json.loads(audit_path.read_text())
    assert audit['status']=='passed' and audit['project_commands']==40 and audit['exact_existing_and_parser_artifacts']
    assert audit['tool_key']==result['tool_key']=='b08f39e282ece70b125d23cf1a9b3a22cef5cfd4c03bf5b8cae023701f9b21ff'
    assert sha(result_path)==audit['evidence'][str(result_path.relative_to(ROOT))]
    proofs[str(audit_path.relative_to(ROOT))]=sha(audit_path)
    proofs[str(result_path.relative_to(ROOT))]=sha(result_path)
    status_path=ROOT/'.work/experiments/environment-main-projects-01/status.json'
    status=json.loads(status_path.read_text())
    assert status['status']=='finished' and status['returncode']==0 and status['child_pid']==24232 and status['owner']==str(ROOT)
    assert sha(status_path)==audit['evidence'][str(status_path.relative_to(ROOT))]
    proofs[str(status_path.relative_to(ROOT))]=sha(status_path)
    case,=[r for r in result['cases'] if r['case']=='nushell']
    assert case==dict(case='nushell',commands=8,source_restored=True,exact_reference_artifacts=True,original_assertion_outcomes=True,private=False)
    for name in ['plan','records']:
        path=base/(name+'.json');assert sha(path)==result[name+'_sha256'];proofs[str(path.relative_to(ROOT))]=sha(path)
    plan=json.loads((base/'plan.json').read_text());assert plan['owner']==str(ROOT) and plan['tool_key']==result['tool_key']
    rows=json.loads((base/'records.json').read_text());assert len(rows)==40
    public=[r for r in rows if r['case']=='nushell'];assert [r['state'] for r in public]==list(range(8))
    namespaces=set()
    for row in public:
        assert row['returncode']==(1 if row['state']==1 else 0)
        command=row['command'];assert command.count('--cache-namespace')==1
        assert command[command.index('--cache-namespace')+1]=='environment-main-projects-01:nushell'
        launch,=[json.loads(l.split(': ',1)[1]) for l in row['stderr'].splitlines() if l.startswith('rust-interp-launch: ')]
        assert launch['tool_key']==result['tool_key'] and launch['borrowck_cache']=='off'
        namespaces.add(launch['workspace_path'])
        for kind in ['artifact','entry_catalog']:
            path=ROOT/row[kind]['path'];assert sha(path)==row[kind]['sha256'];proofs[str(path.relative_to(ROOT))]=sha(path)
    assert len(namespaces)==1
    root=Path(namespaces.pop());assert root.resolve(strict=True)==root
    assert root.parent.parent==ROOT/'.work/interpreter-workspaces' and root.parent.name==result['tool_key']
    assert root.name=='8e3174d1fcbffcbc29ab822c';roots=[root]
    for old_pid in [status['supervisor_pid'],status['child_pid']]:
        check=subprocess.run(['ps','-p',str(old_pid),'-o','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
        process_checks.append(dict(pid=old_pid,returncode=check.returncode,stdout=check.stdout))
        assert str(base) not in check.stdout and 'environment-main-projects-01' not in check.stdout
    marker=ROOT/'.work/sources/nushell/.rust-interp-owned.json'
    owner=json.loads(marker.read_text());assert owner['owner']==str(ROOT) and owner['revision']==PIN
    proofs[str(marker.relative_to(ROOT))]=sha(marker)
    invocation=stack.enter_context((root/'invocation.lock').open('r+'));acquire_lock(invocation,45)
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
    # Protect all saved public/private case evidence; retire only the exact public namespace.
    for run in RUNS:
        base=ROOT/'.work'/run
        for path in base.rglob('*'):
            if not path.is_file() or path.relative_to(base).parts[0] in ['native','native_lines','check']:continue
            assert not path.is_symlink();protected[str(path.relative_to(ROOT))]=sha(path)
    write(work/'inventory.json',rows);write(work/'protected.json',protected)
    assert rows, 'no eligible compiler intermediates remain; no deletion attempted'
    before=shutil.disk_usage(ROOT).free;started=time.time()
    write(work/'plan.json',dict(owner=str(ROOT),script_sha256=sha(Path(__file__)),completed_runs=RUNS,
        roots=sizes,process_checks=process_checks,open_checks=open_checks,files=len(rows),
        logical_bytes=sum(r['size'] for r in rows),free_before=before,started_at=started,
        scope='One exact public Nushell custom namespace from the eight completed Nushell commands in the qualified40-command integration history, bound to its completed terminal and final component/source audit. Nonexecutable incremental files and .o/.rlib/.rmeta in build/deps only. All other namespace files and saved case evidence hashed and preserved. No active, private, installed-tool or unrelated worktree cache. Shared and invocation locks held.'))
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
