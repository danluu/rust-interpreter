"""Lossless preservation of closed legacy runtime fixture command logs."""
from pathlib import Path
import hashlib,json,os,stat,subprocess,sys,shutil
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/heap-address-bias'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from compression_probe import metadata
NAME='closed-legacy-runtime-log-compression-01'
QUALIFICATIONS=['jit-region-linking-validation-01','native-exit-dispatch-default-validation-01',
'jit-temporary-reuse-validation-01','native-medium-copy-default-validation-01','jit-popcount-validation-01',
'native-wide-default-validation-01','native-medium-leaf-frame-guard-default-validation-01',
'native-medium-leaf-default-validation-01','jit-region-budget-register-validation-01',
'native-popcount-default-validation-01','jit-region-budget-leaf-validation-01','jit-local-fill-validation-01']

def no_open_file(path):
    r=subprocess.run(['lsof','-Fpn','--',str(path)],text=True,capture_output=True)
    assert r.returncode==1 and not r.stdout and not r.stderr,(path,r.stdout,r.stderr)

def raw_paths(value):
    if isinstance(value,dict):
        raw=value.get('raw')
        if isinstance(raw,str) and raw.startswith('.work/interpreter-validation-'):yield raw
        for v in value.values():yield from raw_paths(v)
    elif isinstance(value,list):
        for v in value:yield from raw_paths(v)

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,10)
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        helper='benchmarks/experiments/heap-address-bias/compression_probe.py'
        sources={};proofs={helper:sha(ROOT/helper)};completion=[];seen=set()
        for name in QUALIFICATIONS:
            result=ROOT/'results'/(name+'.json');terminal=ROOT/'.work'/name/'active-command.json'
            assert sha(result)==hashlib.sha256(subprocess.check_output(['git','show',revision+':'+str(result.relative_to(ROOT))])).hexdigest()
            summary=json.loads(result.read_text());status=json.loads(terminal.read_text())
            assert status['status']=='finished' and status['returncode']==0 and status['cwd']==str(ROOT)
            pids=[status[k] for k in ['pid','parent_pid'] if k in status];assert pids
            process=subprocess.run(['ps','-p',','.join(map(str,pids)),'-o','pid,ppid,lstart,tty,command'],text=True,capture_output=True)
            assert process.returncode in [0,1] and not process.stderr
            assert not any(name in line for line in process.stdout.splitlines()[1:])
            proofs[str(result.relative_to(ROOT))]=sha(result);proofs[str(terminal.relative_to(ROOT))]=sha(terminal)
            bound=[]
            for relative in sorted(set(raw_paths(summary))):
                raw=ROOT/relative;assert raw.parent==ROOT/'.work' and raw.name.startswith('interpreter-validation-')
                pair=[raw/'commands.jsonl',raw/'records.json']
                if not all(p.is_file() for p in pair) or relative in seen:continue
                seen.add(relative)
                if all(p.stat().st_flags&32 for p in pair):continue
                commands=[json.loads(line) for line in pair[0].read_text().splitlines()]
                records=json.loads(pair[1].read_text())
                assert commands==records and len(records)>100
                assert all(isinstance(r,dict) and type(r.get('returncode'))==int for r in records)
                for p in pair:
                    info=p.lstat();assert stat.S_ISREG(info.st_mode) and not p.is_symlink() and not info.st_mode&0o111
                    no_open_file(p)
                    if not info.st_flags&32:sources[str(p.relative_to(ROOT))]=sha(p)
                bound.append(dict(raw=relative,commands=len(records),exact_jsonl_record_equality=True))
            completion.append(dict(run=name,committed_report=str(result.relative_to(ROOT)),process_inspection=process.stdout,fixtures=bound))
        assert sources
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
            scope='Only command JSONL and its matching records JSON for completed legacy runtime fixture qualifications. Committed parent reports, terminal direct captures and exact structural equality are checked; current byte hashes are preserved. No fixture source, executable, bytecode or cache is changed, and no historical performance result is reinterpreted.',completed_scopes=completion))
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
