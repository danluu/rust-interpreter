"""Preserve exact completed public artifact bytes with transparent compression."""
import hashlib,json,mmap,os,shutil,stat,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='closed-compact-switch-evidence-compression-01'
METADATA_PROOF='closed-public-artifact-compression-recovery-02'
HELPER=ROOT/'benchmarks/experiments/closed-public-artifact-compression-recovery-02/birthtime.py'
sys.path.insert(0,str(HELPER.parent))
from birthtime import birthtime,set_birthtime
INVENTORIES=['closed-compact-switch-evidence-inventory-01']
PRESERVE=['size','mode','uid','gid','mtime_ns','birthtime']
def read(p):return json.loads(p.read_text())
def identity(p):
    s=p.lstat()
    assert p.resolve(strict=True)==p and stat.S_ISREG(s.st_mode) and s.st_nlink==1 and not s.st_mode&0o111,p
    return dict(device=s.st_dev,inode=s.st_ino,size=s.st_size,blocks=s.st_blocks,mode=s.st_mode,
        uid=s.st_uid,gid=s.st_gid,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns,
        birthtime=s.st_birthtime,flags=s.st_flags)
def unopened(p):
    r=subprocess.run(['/usr/sbin/lsof','-Fpn','--',str(p)],capture_output=True,text=True)
    assert r.returncode==1 and not r.stdout and not r.stderr,(p,r.returncode,r.stdout,r.stderr)
    return dict(path=str(p.relative_to(ROOT)),returncode=r.returncode,checked_at=time.time())
def attributes(p,compressed=False):
    names=subprocess.check_output(['/usr/bin/xattr',str(p)],text=True).splitlines()
    assert not names or (compressed and set(names)<= {'com.apple.decmpfs','com.apple.ResourceFork'}),(p,names)
    listing=subprocess.check_output(['/bin/ls','-lde',str(p)],text=True).splitlines()
    assert len(listing)==1 and '+' not in listing[0].split()[0],p
    return names
def verify(p,expected,old):
    current=identity(p);assert all(current[k]==old[k] for k in PRESERVE),(p,old,current)
    assert sha(p)==expected,p
    with p.open('rb') as f:
        with mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as m:assert hashlib.sha256(m).hexdigest()==expected,p
    attributes(p,compressed=bool(current['flags']&stat.UF_COMPRESSED))
    assert current['flags'] in [0,stat.UF_COMPRESSED]
    return current
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);frozen={};selected=[]
        def bind(p,h=None):
            digest=sha(p)
            if h is not None:assert digest==h,p
            frozen[str(p.relative_to(ROOT))]=digest
            return read(p)
        proof=ROOT/'results'/METADATA_PROOF;closure=bind(proof/'closure.json')
        assert closure['status']=='closed' and closure['all_hashes_verified']
        qualified=bind(proof/'summary.json',closure['summary_sha256'])
        terminal=bind(proof/'terminal.json',closure['terminal_sha256'])
        assert qualified['status']=='passed' and qualified['exact_native_creation_time_preserved'] and qualified['compression_preserved']
        assert qualified['existing_evidence_modified']==0 and terminal['status']=='finished' and terminal['returncode']==0
        assert terminal['owner']==terminal['cwd']==str(ROOT)
        qualified_plan=bind(ROOT/qualified['raw']/'plan.json',qualified['plan_sha256'])
        helper_path=str(HELPER.relative_to(ROOT));assert sha(HELPER)==qualified_plan['frozen'][helper_path]
        frozen[helper_path]=sha(HELPER)
        for name in INVENTORIES:
            out=ROOT/'results'/name;c=bind(out/'closure.json')
            assert c['status']=='closed' and c['all_hashes_verified'] and c['existing_files_modified']==0
            s=bind(out/'summary.json',c['summary_sha256']);t=bind(out/'terminal.json',c['terminal_sha256'])
            assert s['status']=='passed' and t['returncode']==0 and t['owner']==t['cwd']==str(ROOT)
            source=ROOT/s['raw'];plan=bind(source/'plan.json',s['plan_sha256'])
            rows=bind(source/'inventory.json',s['inventory_sha256']);bind(source/'runs.json',s['runs_sha256'])
            for path,h in plan['frozen'].items():assert sha(ROOT/path)==h;frozen[path]=h
            for r in rows:
                p=ROOT/r['path']
                if p.suffix!='.rbc' or p.parent!=ROOT/'.work'/r['run']/'artifacts':continue
                old=identity(p)
                assert old['size']>=256*1024 and old['size']<=128*1024**2 and old['flags']==0
                assert all(old[k]==r[k] for k in ['device','inode','size','mtime_ns','mode'])
                assert old['blocks']*512==r['allocated_bytes']
                attributes(p);assert sha(p)==r['expected_plaintext_sha256']
                selected.append(dict(path=r['path'],sha256=r['expected_plaintext_sha256'],before=old,native_birthtime=birthtime(p),inventory=name))
        assert selected and len({r['path'] for r in selected})==len(selected)
        for p in [*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md'),ROOT/'scripts/workflow_io.py',ROOT/'scripts/compare_saved_runtime.py']:
            frozen[str(p.relative_to(ROOT))]=sha(p)
        tool=Path('/usr/bin/ditto');tool_sha=sha(tool)
        write(raw/'inventory.json',selected)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,tool=str(tool),tool_sha256=tool_sha,
            controller_command=[sys.executable,*sys.orig_argv[1:]],inventory_sha256=sha(raw/'inventory.json'),
            minimum_initial_gib=12,minimum_child_gib=8,free_before=shutil.disk_usage(ROOT).free,
            original_project_guest_commands=0,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith('DITTO')};env['DITTOABORT']='1';records=[]
        write(raw/'records.json',records)
        for i,row in enumerate(selected):
            require_space(ROOT,8);p=ROOT/row['path'];old=row['before'];assert identity(p)==old
            opening=unopened(p);tmp=p.with_name('.'+p.name+'.'+RUN+'.tmp');assert not tmp.exists()
            assert sha(tool)==tool_sha
            cmd=[str(tool),'--hfsCompression','--noclone',str(p),str(tmp)]
            start=time.time();child,out,err=capture(cmd,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(index=i,path=row['path']))
            for stream,value in [('stdout',out),('stderr',err)]:(raw/(str(i)+'.'+stream)).write_text(value)
            record=dict(index=i,path=row['path'],command=cmd,pid=child.pid,returncode=child.returncode,
                seconds=time.time()-start,first_open_check=opening,
                **{stream+'_sha256':sha(raw/(str(i)+'.'+stream)) for stream in ['stdout','stderr']})
            records.append(record);write(raw/'records.json',records)
            assert child.returncode==0,(out+err)[-2000:]
            assert list(birthtime(p))==list(row['native_birthtime'])
            if list(birthtime(tmp))!=list(row['native_birthtime']):set_birthtime(tmp,tuple(row['native_birthtime']))
            assert list(birthtime(tmp))==list(row['native_birthtime'])
            replacement=verify(tmp,row['sha256'],old);assert identity(p)==old and sha(p)==row['sha256']
            record['second_open_check']=unopened(p);assert identity(p)==old
            record['replacement_identity']=replacement
            if replacement['blocks']<old['blocks']:
                assert replacement['flags']==stat.UF_COMPRESSED
                record['state']='verified-before-atomic-replacement';write(raw/'records.json',records)
                os.replace(tmp,p);record['state']='replaced'
            else:
                assert identity(tmp)==replacement;tmp.unlink();record['state']='original-retained-no-saving'
            record['after']=verify(p,row['sha256'],old)
            assert list(birthtime(p))==list(row['native_birthtime'])
            write(raw/'records.json',records)
            if i%25==0:print('Verified',i+1,'of',len(selected),'public artifact copies',flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),files=len(selected),
            compressed_files=sum(r['state']=='replaced' for r in records),all_plaintext_hashes_preserved=True,exact_native_creation_time_preserved=True,qualified_metadata_proof=METADATA_PROOF,
            preserved_metadata=PRESERVE,intentionally_changed_metadata=['inode','ctime_ns','compression_flag'],
            allocated_bytes_before=sum(r['before']['blocks']*512 for r in selected),
            allocated_bytes_after=sum(r['after']['blocks']*512 for r in records),
            free_before=read(raw/'plan.json')['free_before'],free_after=shutil.disk_usage(ROOT).free,
            performance_measurement=False,original_project_guest_commands=0,
            **{name+'_sha256':sha(raw/(name+'.json')) for name in ['plan','inventory','records']}))
        print('Completed',len(selected),'exact artifact copies; all plaintext hashes preserved',flush=True)
if __name__=='__main__':main()
