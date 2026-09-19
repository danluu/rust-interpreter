"""Transparent compression of exact retained public cache bytecode and reservation evidence."""
import hashlib, os, shutil, stat, subprocess, sys
from contextlib import ExitStack
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'benchmarks/experiments/closed-public-artifact-compression'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/closed-public-artifact-compression-recovery-02'))
from compress import identity,unopened,attributes,verify,sha,read,write,capture,acquire_lock,require_space,PRESERVE
from birthtime import birthtime,set_birthtime

RUN='closed-public-cache-bytecode-compression-02'
CACHE_RUNS='branch-budget-native-screen-token-01 compact-switch-adopted-screen-token-01 compact-native-switch-edit-token-01 session-runtime-composition-edit-token-01 session-project-edit-token-01 session-runtime-composition-screen-token-01 compact-native-switch-screen-token-01'.split()
RUNS=CACHE_RUNS+['branch-budget-native-profile-01']

def manifest_hashes(obj):
    found={}
    def visit(value):
        if not isinstance(value,dict):return
        for key,item in value.items():
            if key.startswith('.work/'):
                digest=item.get('sha256') if isinstance(item,dict) else item
                if isinstance(digest,str) and len(digest)==64:
                    assert key not in found or found[key]==digest,key
                    found[key]=digest
            else:visit(item)
    visit(obj)
    return found

def main():
    with ExitStack() as namespaces, (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        frozen={};selected=[];runs=[]
        def bind(p,expected=None):
            assert p.resolve(strict=True)==p and p.is_file(),p
            digest=sha(p)
            if expected is not None:assert digest==expected,p
            frozen[str(p.relative_to(ROOT))]=digest
            return read(p)
        failed=ROOT/'results/closed-public-cache-bytecode-compression-01'
        fc=bind(failed/'closure.json');assert fc['status']=='closed' and fc['no_mutation_stage_reached']
        fs=bind(failed/'summary.json',fc['summary_sha256'])
        ft=bind(failed/'terminal.json',fc['terminal_sha256'])
        assert fs['status']=='admission-failed' and fs['mutations']==0 and not fs['raw_inventory_created']
        assert ft['status']=='finished' and ft['returncode']==1
        assert not (ROOT/'.work/closed-public-cache-bytecode-compression-01').exists()
        for name,digest in fs['evidence'].items():
            p=ROOT/name;assert sha(p)==digest;frozen[name]=digest
        qualification=ROOT/'results/closed-public-artifact-compression-recovery-02'
        qc=bind(qualification/'closure.json');assert qc['status']=='closed'
        qs=bind(qualification/'summary.json',qc['summary_sha256'])
        qt=bind(qualification/'terminal.json',qc['terminal_sha256'])
        assert qs['status']=='passed' and qs['compression_preserved'] and qs['exact_native_creation_time_preserved']
        assert qt['status']=='finished' and qt['returncode']==0 and qt['owner']==qt['cwd']==str(ROOT)
        qp=bind(ROOT/qs['raw']/'plan.json',qs['plan_sha256'])
        # Reuse only the already qualified metadata/helper implementation.
        for name in ['benchmarks/experiments/closed-public-artifact-compression-recovery-02/birthtime.py',
                     'benchmarks/experiments/closed-public-artifact-compression/compress.py']:
            assert sha(ROOT/name)==qp['frozen'][name];frozen[name]=qp['frozen'][name]
        seen=set()
        def select(p,name,expected):
            key=str(p.relative_to(ROOT));assert key not in seen;seen.add(key)
            assert p.suffix in ['.rbc','.json'] and p.stat().st_size>=1024**2
            if p.stat().st_flags!=0:return
            old=identity(p);assert old['size']<=256*1024**2
            attributes(p);assert sha(p)==expected
            selected.append(dict(path=key,run=name,sha256=expected,before=old,native_birthtime=list(birthtime(p))))
        for name in RUNS:
            out=ROOT/'results'/name;base=ROOT/'.work'/name
            c=bind(out/'closure.json');assert c['status']=='closed' and c['all_hashes_verified']
            s=bind(out/'summary.json',c['summary_sha256']);t=bind(out/'terminal.json',c['terminal_sha256'])
            assert s['status']=='passed' and t['status']=='finished' and t['returncode']==0 and t['owner']==t['cwd']==str(ROOT)
            plan=bind(base/'plan.json',s['plan_sha256']);rows=bind(base/'records.json',s['records_sha256'])
            assert plan['owner']==str(ROOT) and len(rows)==s['commands']
            before=len(selected)
            if name in CACHE_RUNS:
                assert plan['project']=='fre' and plan['case']['package']=='fre-kernels'
                assert s['source_restored'] and s['original_assertions_unchanged']
                source=ROOT/'.work/sources/fre';owner=bind(source/'.rust-interp-owned.json')
                assert owner['owner']==str(ROOT) and owner['revision']==plan['revision']
                assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
                assert sha(source/plan['case']['file'])==plan['original_source_sha256']
                last={r['mode']:r for r in rows if 'launch' in r}
                assert len(last) in [4,5]
                for mode,row in last.items():
                    assert row['state']==0 and row['returncode']==0 and row['source_sha256']==plan['original_source_sha256']
                    launch=row['launch'];key=launch['tool_key'];cmd=row['command']
                    assert key==plan['tool_keys'][mode] and cmd[cmd.index('--cache-namespace')+1]==name+':'+mode
                    assert cmd[cmd.index('--tool-key')+1]==key
                    workspace=Path(launch['workspace_path']);p=Path(launch['artifact_path'])
                    assert workspace.parent==ROOT/'.work/interpreter-workspaces'/key
                    assert workspace.resolve(strict=True)==workspace and p.is_relative_to(workspace/'target')
                    assert p.resolve(strict=True)==p and p.suffix=='.rbc'
                    identity_input='shared-entries-v1\0'+str(source/'Cargo.toml')+'\0fre-kernels\0True\0std-mir:'+launch['std_mir']['key']+'\0'+name+':'+mode
                    assert workspace.name==hashlib.sha256(identity_input.encode()).hexdigest()[:24]
                    guard=namespaces.enter_context((workspace/'invocation.lock').open('r+'));acquire_lock(guard,45)
                    select(p,name,launch['artifact_sha256'])
                if name=='branch-budget-native-screen-token-01':
                    authoritative=manifest_hashes(bind(ROOT/c['evidence'],c['evidence_sha256']))
                    for p in sorted((base/'artifacts').glob('*.rbc')):
                        select(p,name,authoritative[str(p.relative_to(ROOT))])
            else:
                assert name=='branch-budget-native-profile-01' and s['commands']==3 and s['exact_per_pc_counts']
                authoritative=manifest_hashes(bind(ROOT/c['evidence'],c['evidence_sha256']))
                for p in sorted(base.rglob('*.json')):
                    if p.stat().st_size>=1024**2:
                        select(p,name,authoritative[str(p.relative_to(ROOT))])
            runs.append(dict(run=name,status=s['status'],returncode=t['returncode'],files=len(selected)-before))
        assert len(RUNS)==8 and selected and len({r['path'] for r in selected})==len(selected)
        for p in [*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md'),
                  ROOT/'scripts/workflow_io.py',ROOT/'scripts/compare_saved_runtime.py',ROOT/'scripts/supervise_experiment.py']:
            frozen[str(p.relative_to(ROOT))]=sha(p)
        tool=Path('/usr/bin/ditto');tool_sha=sha(tool);raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'inventory.json',selected);write(raw/'runs.json',runs)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],tool=str(tool),tool_sha256=tool_sha,
            inventory_sha256=sha(raw/'inventory.json'),runs_sha256=sha(raw/'runs.json'),
            minimum_initial_gib=12,minimum_child_gib=8,free_before=shutil.disk_usage(ROOT).free,
            performance_measurement=False,original_project_guest_commands=0))
        records=[];write(raw/'records.json',records)
        env={k:v for k,v in os.environ.items() if not k.startswith('DITTO')};env['DITTOABORT']='1'
        print('Inventoried',len(selected),'closed public bytecode/JSON files;',sum(r['before']['blocks']*512 for r in selected),'allocated bytes',flush=True)
        for i,row in enumerate(selected):
            require_space(ROOT,8);p=ROOT/row['path'];old=row['before'];assert identity(p)==old
            opening=unopened(p);stamp=tuple(row['native_birthtime'])
            assert birthtime(p)==stamp and sha(p)==row['sha256'] and identity(p)==old
            temp=p.with_name('.'+p.name+'.'+RUN+'.tmp');assert not temp.exists() and sha(tool)==tool_sha
            cmd=[str(tool),'--hfsCompression','--noclone',str(p),str(temp)]
            child,stdout,stderr=capture(cmd,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(index=i,path=row['path']))
            for stream,value in [('stdout',stdout),('stderr',stderr)]:(raw/(str(i)+'.'+stream)).write_text(value)
            record=dict(index=i,path=row['path'],command=cmd,pid=child.pid,returncode=child.returncode,
                first_open_check=opening,state='copied-unverified',
                **{stream+'_sha256':sha(raw/(str(i)+'.'+stream)) for stream in ['stdout','stderr']})
            records.append(record);write(raw/'records.json',records);assert child.returncode==0
            assert sha(temp)==row['sha256'];set_birthtime(temp,stamp)
            replacement=verify(temp,row['sha256'],old)
            assert birthtime(temp)==birthtime(p)==stamp and identity(p)==old and sha(p)==row['sha256']
            record['second_open_check']=unopened(p);assert identity(p)==old;record['replacement_identity']=replacement
            if replacement['blocks']<old['blocks']:
                assert replacement['flags']==stat.UF_COMPRESSED
                record['state']='verified-before-atomic-replacement';write(raw/'records.json',records)
                os.replace(temp,p);record['state']='replaced'
            else:
                assert identity(temp)==replacement;temp.unlink();record['state']='original-retained-no-saving'
            record['after']=verify(p,row['sha256'],old);assert birthtime(p)==stamp
            write(raw/'records.json',records)
            if (i+1)%10==0:print('Verified',i+1,'of',len(selected),flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),files=len(selected),runs=len(runs),
            compressed_files=sum(r['state']=='replaced' for r in records),all_plaintext_hashes_preserved=True,
            preserved_metadata=PRESERVE,exact_native_creation_time_preserved=True,
            intentionally_changed_metadata=['inode','ctime_ns','compression_flag'],
            allocated_bytes_before=sum(r['before']['blocks']*512 for r in selected),
            allocated_bytes_after=sum(r['after']['blocks']*512 for r in records),
            free_before=read(raw/'plan.json')['free_before'],free_after=shutil.disk_usage(ROOT).free,
            performance_measurement=False,original_project_guest_commands=0,
            **{n+'_sha256':sha(raw/(n+'.json')) for n in ['plan','inventory','records','runs']}))
        print('Completed public cache/evidence compression with every plaintext hash preserved',flush=True)

if __name__=='__main__':main()
