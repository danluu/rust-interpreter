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

NAME='closed-diagnostic-json-compression-08'
# Exact completed experiments from this runtime workstream. No recursive cache,
# executable, bytecode, source, private-workload or peer-workspace selection.
PROFILE_SCOPES=[]
MAP_SCOPES=[]
SCALAR_SCOPE='scalar-local-registers-profile-01'
SCOPES=[SCALAR_SCOPE]

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
            assert summary['status']=='passed' and summary['exact_logical_counts_memory_and_entropy']
            expected=6 if name==SCALAR_SCOPE else 3
            assert summary['raw']=='.work/'+name and len(summary['comparisons'])==expected
            import hashlib
            assert hashlib.sha256(subprocess.check_output(['git','show',revision+':'+str(summary_path.relative_to(ROOT))])).hexdigest()==sha(summary_path)
            plan_path=ROOT/summary['raw']/'plan.json';records_path=ROOT/summary['raw']/'records.json'
            assert sha(plan_path)==summary['plan_sha256'] and sha(records_path)==summary['records_sha256']
            plan=json.loads(plan_path.read_text());assert plan['owner']==str(ROOT)
            records=json.loads(records_path.read_text());assert len(records)==expected and all(r['returncode']==0 for r in records)
            for p in [summary_path,plan_path,records_path]:proofs[str(p.relative_to(ROOT))]=sha(p)
            terminal=ROOT/'.work/experiments'/name/'status.json'
            if terminal.exists():
                status=json.loads(terminal.read_text());assert status['status']=='finished' and status['owner']==str(ROOT)
                # A terminal observer-audit failure may have a later, recorded
                # offline correction; the qualified summary binds all guest rc=0.
                proofs[str(terminal.relative_to(ROOT))]=sha(terminal)
            if name==SCALAR_SCOPE:
                closure_path=summary_path.with_name('closure.json');closure=json.loads(closure_path.read_text())
                assert closure['all_hashes_verified'] and closure['summary_sha256']==sha(summary_path)
                proofs[str(closure_path.relative_to(ROOT))]=sha(closure_path)
            for row in summary['comparisons']:
                index=row['index'];assert index in [0,1,2]
                if name==SCALAR_SCOPE:
                    selected=[(row[k+'_path'],row[k+'_sha256']) for k in ['profile','operations']]
                elif name in PROFILE_SCOPES:
                    selected=[(summary['raw']+'/'+str(index)+'-profile.json',row['profile_sha256'])]
                else:
                    selected=[(summary['raw']+'/'+str(index)+'-code/operations.json',row['operation_map_sha256'])]
                for relative,digest in selected:
                    assert relative not in sources;sources[relative]=digest
        for name in ['current-runtime-boundaries-02','guarded-local-facts-static-census-01','guarded-local-facts-composed-census-01']:
            result=ROOT/'results'/name;summary_path=result/'summary.json';summary=json.loads(summary_path.read_text())
            assert summary['status']=='passed' and summary['raw']=='.work/'+name
            raw=ROOT/summary['raw'];plan_path=raw/'plan.json';records_path=raw/'records.json'
            assert sha(plan_path)==summary['plan_sha256'] and sha(records_path)==summary['records_sha256']
            assert json.loads(plan_path.read_text())['owner']==str(ROOT)
            records=json.loads(records_path.read_text());assert len(records)==summary['commands'] and all(r['returncode']==0 for r in records)
            terminal_path=ROOT/'.work/experiments'/name/'status.json';terminal=json.loads(terminal_path.read_text())
            assert terminal['owner']==str(ROOT) and terminal['status']=='finished' and terminal['returncode']==0
            assert hashlib.sha256(subprocess.check_output(['git','show',revision+':'+str(summary_path.relative_to(ROOT))])).hexdigest()==sha(summary_path)
            for item in [summary_path,plan_path,records_path,terminal_path]:proofs[str(item.relative_to(ROOT))]=sha(item)
            if name=='current-runtime-boundaries-02':
                assert summary['exact_logical_counts_memory_and_entropy'] and len(summary['profiles'])==3
                for row in summary['profiles']:sources[summary['raw']+'/'+str(row['index'])+'-profile.json']=row['profile_sha256']
            else:
                assert summary['frozen_inputs_verified'] and len(summary['cases'])==3
                for row in summary['cases']:sources[summary['raw']+'/'+str(row['index'])+'-census.json']=row['census_sha256']
        assert len(sources)==21
        inventory=[]
        for relative,digest in sorted(sources.items()):
            source=ROOT/relative;before=metadata(source)
            assert stat.S_ISREG(before['mode']) and before['uid']==os.getuid() and before['links']==1
            assert not before['mode'] & 0o111 and sha(source)==digest
            no_open_file(source)
            inventory.append(dict(path=relative,sha256=digest,before=before))
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            script_sha256=sha(Path(__file__)),proofs=proofs,files=inventory,
            scope='Only 21 exact closed runtime profile, operation-map and census JSON files. Every logical hash is bound by a committed passed summary, an owned raw plan and three or six completed command records. The scalar run also has a closed full artifact/hash audit. Preserve readable bytes, length, mode, ownership and mtime; verify staged copies before atomic replacement. No executable, RBC, source, active cache or peer file. Global lock and exact open-file checks.'))
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
