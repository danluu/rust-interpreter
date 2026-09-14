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
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from compression_probe import metadata

NAME='closed-diagnostic-json-compression-11'
SCOPES=['resumable-copy-native-02','fixed-frame-clear-combined-native-01','budget-register-native-01',
        'aggregate-relocation-native-01','resumable-bulk-native-01','fixed-frame-clear-native-01']

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
            result=ROOT/'results'/name/'summary.json';summary=json.loads(result.read_text())
            assert summary['status']=='passed' and set(summary['runs'])=={'default','inline'}
            assert hashlib.sha256(subprocess.check_output(['git','show',revision+':'+str(result.relative_to(ROOT))])).hexdigest()==sha(result)
            terminal=ROOT/'.work/experiments'/name/'status.json';status=json.loads(terminal.read_text())
            assert status['status']=='finished' and status['returncode']==0 and status['owner']==status['cwd']==str(ROOT)
            assert sha(terminal.with_name('plan.json'))==status['plan_sha256']
            assert sha(terminal.with_name('command.log'))==status['log_sha256']
            pids=[status[k] for k in ['supervisor_pid','child_pid']]
            inspection=subprocess.run(['ps','-p',','.join(map(str,pids)),'-o','pid,ppid,lstart,tty,command'],text=True,capture_output=True)
            assert inspection.returncode in [0,1] and not inspection.stderr
            assert not any(name in row for row in inspection.stdout.splitlines()[1:]),inspection.stdout
            for path in [result,terminal,terminal.with_name('plan.json'),terminal.with_name('command.log')]:proofs[str(path.relative_to(ROOT))]=sha(path)
            completion.append(dict(run=name,terminal=str(terminal.relative_to(ROOT)),returncode=0,process_inspection=inspection.stdout))
            for mode,row in summary['runs'].items():
                raw=ROOT/row['detail']['raw'];assert raw.parent==ROOT/'.work' and raw.name.startswith('interpreter-validation-')
                commands=raw/'commands.jsonl';digest=row['commands_sha256'];assert sha(commands)==digest
                records=raw/'records.json';logged=[json.loads(line) for line in commands.read_text().splitlines()]
                assert json.loads(records.read_text())==logged
                assert len(logged)==row['classification']['commands']
                detail=raw/'summary.json';assert json.loads(detail.read_text())==row['detail']
                proofs[str(detail.relative_to(ROOT))]=sha(detail)
                for path in [commands,records]:
                    no_open_file(path);assert not path.stat().st_flags&32
                    sources[str(path.relative_to(ROOT))]=sha(path)
        assert len(sources)==24
        if '--inspect' in sys.argv:
            print(json.dumps(dict(files=len(sources),allocated_bytes=sum((ROOT/p).stat().st_blocks*512 for p in sources))));return
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
            scope='Twelve command JSONL files bound by six committed completed runtime native/interpreter differential qualifications, plus twelve JSON copies verified structurally equal. Includes existing expected negative outcomes. Preserve readable hashes, metadata and historical conclusions; no executable, source, guest artifact or cache changes.',selection_skips=skips,completed_scopes=completion))
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
