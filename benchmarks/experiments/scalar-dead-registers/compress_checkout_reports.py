"""Losslessly preserve committed report bytes in the two owned worktrees."""
from pathlib import Path
import hashlib,json,os,stat,subprocess,sys,shutil
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/heap-address-bias'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from compression_probe import metadata
NAME='closed-checkout-report-compression-01'

def no_open_file(path):
    r=subprocess.run(['lsof','-Fpn','--',str(path)],text=True,capture_output=True)
    assert r.returncode==1 and not r.stdout and not r.stderr,(path,r.stdout,r.stderr)

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,10)
        helper='benchmarks/experiments/heap-address-bias/compression_probe.py'
        sources={};proofs={helper:sha(ROOT/helper)};completion=[]
        for base in [ROOT,ROOT/'.work/publication-main']:
            assert not subprocess.check_output(['git','diff','--name-only','HEAD','--','results'],cwd=base).strip()
            revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=base,text=True).strip()
            selected=[]
            for name in subprocess.check_output(['git','ls-files','results'],cwd=base,text=True).splitlines():
                p=base/name
                if p.suffix not in ['.json','.jsonl']:continue
                info=p.lstat()
                if info.st_size<128*1024 or info.st_flags&32:continue
                assert stat.S_ISREG(info.st_mode) and not info.st_mode&0o111 and not p.is_symlink()
                digest=sha(p)
                assert digest==hashlib.sha256(subprocess.check_output(['git','show',revision+':'+name],cwd=base)).hexdigest()
                key=str(p.relative_to(ROOT));sources[key]=digest;selected.append(name)
            completion.append(dict(worktree=str(base),source_revision=revision,committed_files=selected))
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
            scope='Only already committed JSON/JSONL reports in the owned root and publication worktrees. Every current file must match its recorded Git commit, be unopened, regular and singly linked. Preserve exact readable bytes and metadata. No raw payload, source, executable, bytecode, tool or cache is changed.',completed_scopes=completion))
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
