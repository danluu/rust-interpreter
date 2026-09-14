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

NAME='closed-diagnostic-json-compression-03'
# Exact completed experiments from this runtime workstream. No recursive cache,
# executable, bytecode, source, private-workload or peer-workspace selection.
SCOPES=['guarded-ranges-profile-01','guarded-indirect-profile-01','scalar-copy-budget-profile-01',
        'paired-registers-profile-01','scalar-copy-operands-profile-01','successor-only-flush-profile-01']

def no_open_file(path):
    result=subprocess.run(['lsof','-Fpn','--',str(path)],text=True,capture_output=True)
    assert result.returncode==1 and not result.stdout and not result.stderr,(path,result.stdout,result.stderr)

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,10)
        probe_path=ROOT/'results/closed-profile-compression-probe-01/summary.json'
        probe=json.loads(probe_path.read_text())
        assert probe['status']=='passed' and probe['source_unchanged'] and probe['allocation_ratio']<0.2
        assert probe['source_sha256']==probe['copy_sha256'] and probe['copy_metadata']['flags'] & 32
        work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
        sources={};proofs={str(probe_path.relative_to(ROOT)):sha(probe_path)}
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        for name in SCOPES:
            summary_path=ROOT/'results'/name/'summary.json';summary=json.loads(summary_path.read_text())
            assert summary['status']=='passed' and summary['exact_per_pc_counts'] and summary['exact_logical_counts_memory_and_entropy']
            assert summary['raw']=='.work/'+name and len(summary['comparisons'])==3
            import hashlib
            assert hashlib.sha256(subprocess.check_output(['git','show',revision+':'+str(summary_path.relative_to(ROOT))])).hexdigest()==sha(summary_path)
            plan_path=ROOT/summary['raw']/'plan.json';records_path=ROOT/summary['raw']/'records.json'
            assert sha(plan_path)==summary['plan_sha256'] and sha(records_path)==summary['records_sha256']
            plan=json.loads(plan_path.read_text());assert plan['owner']==str(ROOT)
            records=json.loads(records_path.read_text());assert len(records)==3 and all(r['returncode']==0 for r in records)
            for p in [summary_path,plan_path,records_path]:proofs[str(p.relative_to(ROOT))]=sha(p)
            terminal=ROOT/'.work/experiments'/name/'status.json'
            if terminal.exists():
                status=json.loads(terminal.read_text());assert status['status']=='finished' and status['owner']==str(ROOT)
                # A terminal observer-audit failure may have a later, recorded
                # offline correction; the qualified summary binds all guest rc=0.
                proofs[str(terminal.relative_to(ROOT))]=sha(terminal)
            for row in summary['comparisons']:
                index=row['index'];assert index in [0,1,2]
                relative=summary['raw']+'/'+str(index)+'-profile.json';digest=row['profile_sha256']
                assert relative not in sources;sources[relative]=digest
        assert sources
        inventory=[]
        for relative,digest in sorted(sources.items()):
            source=ROOT/relative;before=metadata(source)
            assert stat.S_ISREG(before['mode']) and before['uid']==os.getuid() and before['links']==1
            assert not before['mode'] & 0o111 and sha(source)==digest
            no_open_file(source)
            inventory.append(dict(path=relative,sha256=digest,before=before))
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            script_sha256=sha(Path(__file__)),proofs=proofs,files=inventory,
            scope='Only 18 exact completed runtime profile JSON files bound by committed successful profile qualification, owned plans and three completed guest records per experiment. Preserve every logical byte, length, mode, ownership and modification time; verify each staged copy before atomic replacement. No executable, RBC, source, active cache or peer file. Global workload lock and exact open-file checks.'))
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
