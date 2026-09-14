"""Preserve exact closed diagnostic JSON bytes using APFS file compression."""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import shutil

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/heap-address-bias'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from compression_probe import metadata

NAME='closed-diagnostic-json-compression-16'
SCOPES=['scalar-width-aliases-profile-01']

def no_open_file(path):
    result=subprocess.run(['lsof','-Fpn','--',str(path)],text=True,capture_output=True)
    assert result.returncode==1 and not result.stdout and not result.stderr,(path,result.stdout,result.stderr)

def main():
    import hashlib
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,10)
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        sources={};proofs={};skips=[];completion=[]
        for name in SCOPES:
            raw=ROOT/'.work'/name
            terminal=ROOT/'.work/experiments'/name/'status.json'
            if not terminal.exists():
                terminal=raw/'active-command.json'
            if not terminal.is_file():terminal=raw/'active.json'
            assert terminal.is_file(),name
            status=json.loads(terminal.read_text())
            assert status['status']=='finished' and isinstance(status['returncode'],int),(name,status)
            allowed_cwd=ROOT/'.work/sources/fre/crates/fre-kernels' if name=='token-phrase-profile-01' else ROOT
            assert status['cwd']==str(allowed_cwd),name
            if terminal.parent.parent==ROOT/'.work/experiments':assert status['owner']==str(ROOT)
            pids=[status[k] for k in ['pid','parent_pid','supervisor_pid','child_pid'] if k in status]
            inspection=subprocess.run(['ps','-p',','.join(map(str,pids)),'-o','pid,ppid,lstart,tty,command'],text=True,capture_output=True)
            assert inspection.returncode in [0,1] and not inspection.stderr
            assert not any(name in row for row in inspection.stdout.splitlines()[1:]),inspection.stdout
            opened=subprocess.run(['lsof','-Fpn','+D',str(raw)],text=True,capture_output=True)
            assert opened.returncode==1 and not opened.stdout and not opened.stderr,(name,opened.stdout,opened.stderr)
            local={str(terminal.relative_to(ROOT)):sha(terminal)}
            if 'plan_sha256' in status:
                assert sha(terminal.with_name('plan.json'))==status['plan_sha256']
                local[str(terminal.with_name('plan.json').relative_to(ROOT))]=status['plan_sha256']
            if 'log_sha256' in status:
                assert sha(terminal.with_name('command.log'))==status['log_sha256']
                local[str(terminal.with_name('command.log').relative_to(ROOT))]=status['log_sha256']
            for file in ['plan.json','summary.json','records.json','record.json','frozen.json','status.json','active.json','active-command.json']:
                p=raw/file
                if p.exists():local[str(p.relative_to(ROOT))]=sha(p)
            committed=ROOT/'results'/name/'summary.json'
            if committed.exists():
                assert hashlib.sha256(subprocess.check_output(['git','show',revision+':'+str(committed.relative_to(ROOT))])).hexdigest()==sha(committed)
                local[str(committed.relative_to(ROOT))]=sha(committed)
            # Old runtime observers used direct captures and sometimes closed
            # with an observer failure. Compression requires completed ownership,
            # not a passing performance result. Record today's exact byte hashes;
            # do not imply these newly recorded hashes were historically bound.
            completion.append(dict(run=name,terminal=str(terminal.relative_to(ROOT)),returncode=status['returncode'],process_inspection=inspection.stdout,open_file_check=opened.returncode))
            candidates=list(raw.glob('*.json'))
            for child in raw.iterdir():
                if child.is_dir() and (child.name.endswith('-code') or child.name=='code'):candidates+=list(child.glob('*.json'))+list(child.glob('code.bin'))
            for candidate in candidates:
                if candidate.name!='code.bin' and not any(word in candidate.name for word in ['profile','map','operations']):continue
                info=candidate.lstat()
                if info.st_flags&32 or info.st_size<1024**2:continue
                assert stat.S_ISREG(info.st_mode) and not info.st_mode&0o111 and candidate.resolve(strict=True)==candidate
                sources[str(candidate.relative_to(ROOT))]=sha(candidate)
            proofs.update(local)
        assert sources,'no eligible evidence'
        if '--inspect' in sys.argv:
            print(json.dumps(dict(files=len(sources),allocated_bytes=sum((ROOT/p).stat().st_blocks*512 for p in sources),paths=list(sources),completion=completion)));return
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
            scope='Exact unopened profile JSON, code maps and non-executable code.bin diagnostic copies from the explicitly listed completed scalar width-alias profile. Readable hashes are recorded immediately before compression; historical benchmark qualifications are neither changed nor inferred. Legacy direct captures and failed terminal observers are eligible only after exact completion and open-file checks. Preserve bytes and file metadata using verified atomic APFS compression; no executables, bytecode, source, active or private-workload caches.',selection_skips=skips,completed_scopes=completion))
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
