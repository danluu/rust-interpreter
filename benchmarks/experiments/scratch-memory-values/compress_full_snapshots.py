"""Losslessly preserve retained public bytecode snapshots from the closed passing scratch-memory full token history."""
from pathlib import Path
import hashlib,json,os,stat,subprocess,sys,shutil
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/heap-address-bias'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from compression_probe import metadata
NAME='closed-runtime-full-artifact-compression-02'
RUNS=['scratch-memory-values-edit-token-01']

def no_open_file(path):
    r=subprocess.run(['lsof','-Fpn','--',str(path)],text=True,capture_output=True)
    assert r.returncode==1 and not r.stdout and not r.stderr,(path,r.stdout,r.stderr)

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,10)
        sources={};proofs={};completion=[]
        def bind(p,digest=None):
            actual=sha(p)
            if digest is not None:assert actual==digest,p
            proofs[str(p.relative_to(ROOT))]=actual
            return json.loads(p.read_text())
        proofs['results/RETENTION.md']=sha(ROOT/'results/RETENTION.md')
        proofs['benchmarks/experiments/heap-address-bias/compression_probe.py']=sha(ROOT/'benchmarks/experiments/heap-address-bias/compression_probe.py')
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        for run in RUNS:
            out=ROOT/'results'/run;raw=ROOT/'.work'/run;outer=ROOT/'.work/experiments/scratch-memory-values-full-01'
            summary=bind(out/'summary.json');closure=bind(out/'closure.json');terminal=bind(out/'terminal.json')
            for name in ['summary.json','closure.json','terminal.json']:
                assert hashlib.sha256(subprocess.check_output(['git','show',revision+':results/'+run+'/'+name])).hexdigest()==sha(out/name)
            assert summary['status']=='passed' and summary['commands']==154 and summary['gate_passed'] is True
            assert summary['source_restored'] and summary['test_source_unchanged'] and summary['native_assertion_outcomes_match'] and summary['candidate_control_bytecode_matches']
            assert closure['status']=='closed' and closure['performance_gate_passed'] is True
            assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['cwd']==terminal['owner']==str(ROOT)
            bind(outer/'status.json',sha(out/'terminal.json'));bind(outer/'plan.json',terminal['plan_sha256'])
            proofs[str((outer/'command.log').relative_to(ROOT))]=sha(outer/'command.log');assert sha(outer/'command.log')==terminal['log_sha256']
            plan=bind(raw/'plan.json',summary['plan_sha256']);rows=bind(raw/'records.json',summary['records_sha256'])
            assert plan['owner']==str(ROOT) and len(rows)==154
            checks=subprocess.run(['ps','-p',','.join(str(terminal[k]) for k in ['supervisor_pid','child_pid']),'-o','pid,ppid,lstart,tty,command'],text=True,capture_output=True)
            assert checks.returncode in [0,1] and not checks.stderr and not any(run in line for line in checks.stdout.splitlines()[1:])
            selected=set()
            for row in rows:
                if row['mode'] in ['native','native_lines','check']:continue
                artifact=row['artifact'];p=ROOT/artifact['path']
                assert p.parent==raw/'artifacts' and p.suffix=='.rbc' and p.stem==artifact['sha256']
                # This is the retained post-command snapshot. The launcher reads
                # its separate workspace artifact; never modify that cache.
                assert Path(row['launch']['artifact_path'])!=p
                assert sha(p)==artifact['sha256'];selected.add(artifact['path']);sources[artifact['path']]=artifact['sha256']
            assert len(selected)==26
            completion.append(dict(run=run,retained_snapshots=sorted(selected),process_inspection=checks.stdout))
        assert len(sources)==26
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
            scope='Byte-preserving APFS compression of 26 retained public RBC snapshots in the closed passing scratch-memory full token history. Preserve every linked path, readable byte, SHA, mode, owner and mtime. Do not remove or reserialize any evidence. Executed workspace artifacts, executables, installed tools, source snapshots, private caches, shared targets and peer worktrees are untouched. This is storage representation only, outside performance timers.',completed_scopes=completion))
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
