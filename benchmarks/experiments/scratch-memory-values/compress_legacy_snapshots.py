"""Preserve byte-identical public snapshots from two fully ended runtime campaigns."""
from pathlib import Path
import hashlib,json,os,stat,subprocess,sys,shutil
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/heap-address-bias'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from compression_probe import metadata
NAME='closed-legacy-runtime-artifact-compression-01'
def no_open_file(path):
    r=subprocess.run(['lsof','-Fpn','--',str(path)],text=True,capture_output=True)
    assert r.returncode==1 and not r.stdout and not r.stderr,(path,r.stdout,r.stderr)

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,10)
        sources={};proofs={};completion=[];pids=set()
        def bind(p,digest=None):
            actual=sha(p)
            if digest is not None:assert actual==digest,p
            proofs[str(p.relative_to(ROOT))]=actual
            return json.loads(p.read_text())
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        audit=bind(ROOT/'results/closed-legacy-runtime-compiler-retirement-02/summary.json')
        assert audit['status']=='no-eligible-files' and audit['files_removed']==0 and audit['completed_histories']==25
        for p,h in audit['evidence'].items():
            assert sha(ROOT/p)==h;proofs[p]=h
        histories=json.loads((ROOT/'.work/closed-legacy-runtime-compiler-retirement-02/completed-histories.json').read_text())
        assert len(histories)==25
        for history in histories:
            run=history['run'];raw=ROOT/'.work/runs'/run;out=ROOT/'results'/run
            summary=bind(out/'summary.json',history['summary_sha256']);rows=bind(raw/'records.json',history['records_sha256'])
            active=bind(raw/'active-command.json');assert active['status']=='finished' and active['returncode']==0
            assert active['cwd']==str(ROOT/'.work/sources/fre');pids.update([active['pid'],active['parent_pid']])
            assert summary['project']=='fre' and summary['samples']==[{k:v for k,v in r.items() if k!='calls'} for r in rows]
            assert len(rows)==history['commands'] and summary['test_source_unchanged'] and summary['wrong_production_edit_rejected']
            assert hashlib.sha256(subprocess.check_output(['git','show',revision+':'+str((out/'summary.json').relative_to(ROOT))])).hexdigest()==sha(out/'summary.json')
            selected=set()
            for row in rows:
                pids.update(c['pid'] for c in row['calls'])
                assert all(c['returncode']==0 for c in row['calls'])==(row['state']!=-1)
                executed={c['launch']['artifact_path'] for c in row['calls'] if 'launch' in c}
                for artifact in row['artifacts']:
                    p=ROOT/artifact['path'];assert p.is_relative_to(raw/'artifacts') and p.suffix=='.rbc'
                    assert str(p) not in executed and sha(p)==artifact['sha256']
                    if not metadata(p)['flags'] & 32:
                        sources[artifact['path']]=artifact['sha256'];selected.add(artifact['path'])
            completion.append(dict(run=run,retained_snapshots=sorted(selected)))
        assert len(sources)==448
        checks=subprocess.run(['ps','-p',','.join(map(str,sorted(pids))),'-o','pid,ppid,lstart,tty,command'],text=True,capture_output=True)
        assert checks.returncode in [0,1] and not checks.stderr
        assert not any(h['run'] in line for h in histories for line in checks.stdout.splitlines()[1:])
        completion.append(dict(process_inspection=checks.stdout,pids=sorted(pids)))
        work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
        inventory=[]
        for relative,digest in sorted(sources.items()):
            source=ROOT/relative;before=metadata(source)
            assert stat.S_ISREG(before['mode']) and before['uid']==os.getuid() and before['links']==1
            assert not before['mode'] & 0o111 and sha(source)==digest
            no_open_file(source)
            inventory.append(dict(path=relative,sha256=digest,before=before))
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            script_sha256=sha(Path(__file__)),proofs=proofs,files=inventory,
            scope='Byte-preserving APFS compression of 448 retained public RBC snapshots from 25 explicitly bound completed historical runtime comparisons. Preserve every linked path, readable byte, SHA, mode, owner and mtime. Do not remove or reserialize any evidence. Executed workspace artifacts, executables, installed tools, source snapshots, private caches, shared targets and peer worktrees are untouched. This is storage representation only, outside performance timers.',completed_scopes=completion))
        before_free=shutil.disk_usage(ROOT).free;rows=[]
        for item in inventory:
            require_space(ROOT,10);source=ROOT/item['path'];before=item['before'];digest=item['sha256']
            assert metadata(source)==before and sha(source)==digest;no_open_file(source)
            if before['flags'] & 32:
                rows.append(dict(path=item['path'],status='already compressed'));write(work/'records.json',rows);continue
            temp=source.with_name('.'+source.name+'.'+NAME);assert not temp.exists()
            command=['/usr/bin/ditto','--hfsCompression',str(source),str(temp)]
            child,out,err=capture(command,cwd=ROOT,env=os.environ.copy(),receipt_path=work/'active.json',receipt=dict(source=item['path'],temporary=str(temp.relative_to(ROOT))))
            row=dict(path=item['path'],command=command,pid=child.pid,returncode=child.returncode,stdout=out,stderr=err,source_sha256=digest)
            rows.append(row);write(work/'records.json',rows);assert child.returncode==0,err
            assert sha(temp)==digest;staged=metadata(temp)
            for field in ['size','mode','uid','gid','mtime_ns']:assert staged[field]==before[field],(source,field)
            assert staged['flags'] & 32 and staged['blocks']<before['blocks'],source
            assert metadata(source)==before and sha(source)==digest;no_open_file(source)
            # Replacing an unopened owned diagnostic file preserves its exact
            # readable bytes and timestamp. The receipt retains both identities.
            os.replace(temp,source)
            after=metadata(source);assert sha(source)==digest and after==staged
            row.update(status='compressed',before=before,after=after);write(work/'records.json',rows)
            print(len(rows),len(inventory),item['path'],before['blocks']*512,'->',after['blocks']*512,flush=True)
        assert all(sha(ROOT/p)==h for p,h in sources.items())
        assert all(sha(ROOT/p)==h for p,h in proofs.items())
        changed=[r for r in rows if r['status']=='compressed']
        result=dict(status='passed',files=len(rows),compressed_files=len(changed),all_original_sha256_unchanged=True,
            logical_bytes=sum(r['before']['size'] for r in changed),
            allocated_bytes_before=sum(r['before']['blocks']*512 for r in changed),
            allocated_bytes_after=sum(r['after']['blocks']*512 for r in changed),
            free_before=before_free,free_after=shutil.disk_usage(ROOT).free,
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),
            performance_measurement=False)
        out=ROOT/'results'/NAME;out.mkdir(exist_ok=False);write(out/'summary.json',result);print(json.dumps(result),flush=True)

if __name__=='__main__':main()
