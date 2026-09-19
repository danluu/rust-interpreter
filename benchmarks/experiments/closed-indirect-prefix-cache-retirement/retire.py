from contextlib import ExitStack
from pathlib import Path
import json, os, shutil, stat, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write
from native_suite import test_status
from suite_reports import validate_report

NAME='closed-indirect-prefix-cache-retirement-01'
RUNS=['guarded-indirect-edit-token-01']

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

def completed_case(run):
    summary=bind(ROOT/'results'/run/'summary.json')
    assert summary['status']=='incomplete' and summary['commands']==52 and summary['expected_commands']==154
    assert summary['all_completed_returncodes_expected'] and summary['no_performance_assessment'] and summary['source_restored']
    assert summary['reason']=='8 GiB before-child storage floor reached; no next child was started'
    for path,digest in summary['evidence'].items():bind(ROOT/path,digest)
    outer=ROOT/'.work/experiments'/run;final=bind(outer/'status.json')
    assert final['status']=='finished' and final['returncode']==1 and final['owner']==final['cwd']==str(ROOT)
    assert final['command'][final['command'].index('--run-id')+1]==run
    bind(outer/'plan.json',final['plan_sha256']);bind(outer/'command.log',final['log_sha256'])
    assert 'insufficient free disk: 8485933056 bytes; no child started' in (outer/'command.log').read_text()
    active=bind(ROOT/'.work'/run/'active.json')
    assert active['status']=='finished' and active['returncode']==0 and active['mode']=='anchor' and active['cycle']==1 and active['state']==0
    pids.update([final['supervisor_pid'],final['child_pid'],active['pid']])
    successor=bind(ROOT/'results/guarded-indirect-edit-token-02/summary.json')
    assert successor['status']=='passed' and successor['commands']==154 and successor['source_restored']
    return summary

def source_pin(project,revision,file,digest):
    source=ROOT/'.work/sources'/project
    marker=bind(source/'.rust-interp-owned.json')
    assert marker['owner']==str(ROOT) and marker['revision']==revision
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==revision
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
    bind(source/file,digest)
    return source

def snapshots(row):
    for kind in ['artifact','catalog','entry_catalog','selection','native_executable','cargo_timing']:
        if kind in row:
            item=row[kind];bind(ROOT/item['path'],item['sha256'])

def workspace(row,run,mode,key):
    cmd=row['command']
    assert cmd[cmd.index('--cache-namespace')+1]==run+':'+mode
    assert cmd[cmd.index('--tool-key')+1]==key
    if 'launch' in row:launch=row['launch']
    else:
        launch,=[json.loads(line.split(': ',1)[1]) for line in row['stderr'].splitlines() if line.startswith('rust-interp-launch: ')]
    assert launch['tool_key']==key
    target=Path(launch['workspace_path'])
    assert target.parent==ROOT/'.work/interpreter-workspaces'/key and target.resolve(strict=True)==target
    roots.add(target)

with ExitStack() as stack:
    lock=stack.enter_context((ROOT/'.work/benchmark.lock').open('a'));acquire_lock(lock,45)
    from workflow_io import require_space
    from workflow_cases import WORKFLOW_VARIANTS
    require_space(ROOT,8)
    target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
    allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
    assert shutil.disk_usage(ROOT).free<max(14*1024**3,8*1024**3+2*allocated),'build headroom sufficient; leave caches'
    roots=set();proofs={};process_checks=[];evidence_roots=set();pids=set();protected_references=set()
    sys.path.insert(0,str(ROOT/'benchmarks/experiments/cross-program-template-screen'))
    for run in RUNS:
        base=ROOT/'.work'/run;evidence_roots.add(base)
        result=completed_case(run)
        base=ROOT/'.work'/run
        for name in ['plan','records','transitions','space']:
            bind(base/(name+'.json'),result['evidence'][str((base/(name+'.json')).relative_to(ROOT))])
        plan=json.loads((base/'plan.json').read_text());rows=json.loads((base/'records.json').read_text())
        assert plan['owner']==str(ROOT) and result['raw']==str(base.relative_to(ROOT))
        # Historical launcher sources have evolved. This audit binds the
        # committed result and original plan rather than claiming to requalify
        # that historical runtime. Actual retained data still matches its hash.
        for path,digest in plan['frozen'].items():
            protected_references.add(path)
            if path.startswith(('.work/','results/')):
                if isinstance(digest,str):bind(ROOT/path,digest)
                else:
                    from probe import fingerprint
                    assert fingerprint(ROOT/path)==digest,path
                    if digest.get('kind')=='file':bind(ROOT/path,digest['sha256'])
        source=source_pin('fre','e0df0b010b156b030a02f073588d28703f4267f3',plan['case']['file'],plan['original_source_sha256'])
        assert plan['revision']=='e0df0b010b156b030a02f073588d28703f4267f3'
        schedule=[(cycle,state) for cycle in range(3) for state in [0,-1,1,2,3,4,5]]+[(3,0)]
        previous=dict.fromkeys(['baseline','duplicate','candidate','anchor','native','native_lines','check'])
        assert len(rows)==52
        for i,(cycle,state) in enumerate(schedule[:8]):
            group=rows[i*7:(i+1)*7];modes={r['mode']:r for r in group}
            assert list(modes)==['native','candidate','anchor'] if i==7 else set(modes)==set(previous)
            assert all((r['cycle'],r['state'])==(cycle,state) for r in group)
            assert len({r['source_sha256'] for r in group})==1
            assert len({json.dumps(r['outcomes']) for r in group if r['mode']!='check'})==1
            if i<7:
                for kind in ['artifact','catalog']:assert len({modes[m][kind]['sha256'] for m in ['baseline','duplicate','candidate']})==1
            for row in group:
                mode=row['mode'];cmd=row['command'];pids.add(row['pid'])
                assert row['previous_source_sha256']==previous[mode] and row['source_sha256']!=previous[mode]
                previous[mode]=row['source_sha256'];assert (row['returncode']==0)==(state!=-1 or mode=='check')
                assert cmd[cmd.index('--manifest-path')+1]==str(source/'Cargo.toml')
                if mode in ['native','native_lines','check']:
                    if mode!='check':
                        import re
                        found=re.findall(r'^test (.+) \.\.\. (ok|FAILED|ignored)$',row['stdout'],re.M)
                        assert len(found)==len(plan['names']) and set(dict(found))==set(plan['names']) and all(v!='ignored' for _,v in found)
                        assert row['outcomes']==[list(x) for x in sorted((n,'passed' if v=='ok' else 'failed') for n,v in found)]
                    else:assert '--lib' in cmd and 'check' in cmd and 'outcomes' not in row
                    target=Path(cmd[cmd.index('--target-dir')+1]);assert target==base/mode
                    roots.add(target)
                else:
                    workspace(row,run,mode,plan['tools'][mode])
                    suite=Path(cmd[cmd.index('--suite-report')+1]);assert suite.parent==base
                    report=bind(suite,row['suite_sha256'])
                    assert row['outcomes']==[list(x) for x in sorted(validate_report(report,plan['names'],'prepared',state!=-1))]
                snapshots(row)
        assert all(previous[m]==plan['original_source_sha256'] for m in ['native','candidate','anchor'])
        # Other arms stopped after edit5; the source itself was restored in finally.
        assert all(previous[m]==rows[42]['source_sha256'] for m in ['baseline','duplicate','native_lines','check'])
    assert len(roots)==7;roots=sorted(roots);assert all(p.resolve(strict=True)==p for p in roots)
    check=subprocess.run(['ps','-p',','.join(map(str,sorted(pids))),'-o','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
    assert check.returncode in [0,1] and not check.stderr and not any(run in line for run in RUNS for line in check.stdout.splitlines()[1:])
    process_checks.append(dict(pids=sorted(pids),returncode=check.returncode,stdout=check.stdout))
    current=subprocess.run(['ps','-axo','pid,ppid,lstart,tty,command'],capture_output=True,text=True,check=True)
    assert not any(str(root) in line for root in roots for line in current.stdout.splitlines()[1:])
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
            if remove and key not in protected and key not in protected_references: rows.append(dict(path=key,**info))
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
        scope='Seven exact compiler namespaces from an incomplete but terminal52-command guarded-indirect token prefix. Independent stopped-run receipt proves no next child started and source restored; complete successor uses other namespaces. No ratios or completed-history claim. Verify every retained outcome/snapshot and original evidence before removing only nonexecutable compiler intermediates. Preserve executables, artifacts, sources, all proofs, installed tools, shared target and peer data with exact locks, ownership/process/open-file and inode checks.'))
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
        plan_sha256=sha(work/'plan.json'),raw=str(work.relative_to(ROOT)),performance_measurement=False,completed_histories=0,completed_commands=52)
    write(work/'summary.json',result);print(json.dumps(result),flush=True)
