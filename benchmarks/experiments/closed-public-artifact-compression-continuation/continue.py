import os,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'benchmarks/experiments/closed-public-artifact-compression-recovery-02'))
from qualify import prefix,RUN as RECOVERY,ORIGINAL,read,write,sha,identity,verify,acquire_lock,require_space,capture
from birthtime import birthtime,set_birthtime
from compress import unopened
RUN='closed-public-artifact-compression-02'
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();frozen={}
        def bind(p,h=None):
            digest=sha(p)
            if h is not None:assert digest==h,p
            frozen[str(p.relative_to(ROOT))]=digest;return read(p)
        for name in [ORIGINAL,RECOVERY]:
            out=ROOT/'results'/name;c=bind(out/'closure.json');assert c['status']=='closed'
            s=bind(out/'summary.json',c['summary_sha256']);t=bind(out/'terminal.json',c['terminal_sha256'])
            assert t['status']=='finished' and t['owner']==t['cwd']==str(ROOT)
            if name==RECOVERY:
                assert s['status']=='passed' and s['compression_preserved'] and s['exact_native_creation_time_preserved'] and t['returncode']==0
                rp=bind(ROOT/s['raw']/'plan.json',s['plan_sha256'])
                for p,h in rp['frozen'].items():assert sha(ROOT/p)==h;frozen[p]=h
                saved=bind(ROOT/s['raw']/'prefix.json',s['prefix_sha256'])
            else:assert s['status']=='partial-stopped' and t['returncode']==1
        assert prefix()==saved
        oldraw=ROOT/'.work'/ORIGINAL;rows=bind(oldraw/'inventory.json');oldrecords=bind(oldraw/'records.json')
        assert len(rows)==373 and len(oldrecords)==133
        for p in [*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md')]:frozen[str(p.relative_to(ROOT))]=sha(p)
        tool=Path('/usr/bin/ditto');tool_sha=sha(tool);raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,controller_command=[sys.executable,*sys.orig_argv[1:]],
            original_run=ORIGINAL,recovery_run=RECOVERY,original_inventory_sha256=sha(oldraw/'inventory.json'),
            completed_prefix=132,remaining_files=241,tool=str(tool),tool_sha256=tool_sha,minimum_initial_gib=12,minimum_child_gib=8,
            free_before=shutil.disk_usage(ROOT).free,performance_measurement=False,original_project_guest_commands=0))
        records=[];write(raw/'records.json',records);env={k:v for k,v in os.environ.items() if not k.startswith('DITTO')};env['DITTOABORT']='1'
        for i in range(132,len(rows)):
            require_space(ROOT,8);row=rows[i];p=ROOT/row['path'];old=row['before'];assert identity(p)==old
            opening=unopened(p);stamp=birthtime(p);assert sha(p)==row['sha256'] and identity(p)==old
            if i==132:
                temp=ROOT/saved['pending_path'];assert identity(temp)==saved['pending_identity'] and sha(temp)==saved['pending_sha256']
                record=dict(index=i,path=row['path'],reused_pending_copy=True,prior_copy_index=132,returncode=0,first_open_check=opening)
            else:
                temp=p.with_name('.'+p.name+'.'+RUN+'.tmp');assert not temp.exists() and sha(tool)==tool_sha
                cmd=[str(tool),'--hfsCompression','--noclone',str(p),str(temp)];start=time.time()
                child,out,err=capture(cmd,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(index=i,path=row['path']))
                for stream,value in [('stdout',out),('stderr',err)]:(raw/(str(i)+'.'+stream)).write_text(value)
                record=dict(index=i,path=row['path'],reused_pending_copy=False,command=cmd,pid=child.pid,returncode=child.returncode,
                    seconds=time.time()-start,first_open_check=opening,
                    **{stream+'_sha256':sha(raw/(str(i)+'.'+stream)) for stream in ['stdout','stderr']})
            records.append(record);write(raw/'records.json',records);assert record['returncode']==0
            assert sha(temp)==row['sha256'];record['native_creation_time_before']=list(stamp)
            set_birthtime(temp,stamp);replacement=verify(temp,row['sha256'],old)
            assert birthtime(temp)==birthtime(p)==stamp and identity(p)==old and sha(p)==row['sha256']
            record['second_open_check']=unopened(p);assert identity(p)==old;record['replacement_identity']=replacement
            if replacement['blocks']<old['blocks']:
                record['state']='verified-before-atomic-replacement';write(raw/'records.json',records)
                os.replace(temp,p);record['state']='replaced'
            else:
                assert identity(temp)==replacement;temp.unlink();record['state']='original-retained-no-saving'
            record['after']=verify(p,row['sha256'],old);assert birthtime(p)==stamp
            write(raw/'records.json',records)
            if len(records)%25==0:print('Verified',len(records),'of241 remaining copies',flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        final=[verify(ROOT/r['path'],r['sha256'],r['before']) for r in rows]
        write(raw/'final-identities.json',final);out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            completed_prefix=132,remaining_files=241,all_files=373,reused_pending_copies=1,new_copy_commands=240,
            compressed_files_in_continuation=sum(r['state']=='replaced' for r in records),all_plaintext_hashes_preserved=True,
            exact_native_creation_time_preserved=True,allocated_bytes_before=sum(r['before']['blocks']*512 for r in rows),
            allocated_bytes_after=sum(r['blocks']*512 for r in final),free_before=read(raw/'plan.json')['free_before'],free_after=shutil.disk_usage(ROOT).free,
            performance_measurement=False,original_project_guest_commands=0,
            **{n.replace('-','_')+'_sha256':sha(raw/(n+'.json')) for n in ['plan','records','final-identities']}))
        print('All373 original hashes preserved; remaining241 entries completed',flush=True)
if __name__=='__main__':main()
