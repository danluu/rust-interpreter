#!/usr/bin/env python3
"""Apply transparent filesystem compression to an exact completed evidence list."""
import hashlib,json,os,shutil,stat,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write

def properties(path):
    s=path.lstat();assert stat.S_ISREG(s.st_mode) and s.st_nlink==1
    return dict(size=s.st_size,mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid,mtime_ns=s.st_mtime_ns,
        flags=s.st_flags & ~stat.UF_COMPRESSED,allocated=s.st_blocks*512)

def main():
    run='completed-evidence-compression-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,3)
        work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
        inputs=[];proofs=[Path(__file__),Path(__file__).with_name('TRANSPARENT-STORAGE.md')]
        profile=ROOT/'results/suite-profiling-real-01/summary.json';report=json.loads(profile.read_text());assert report['status']=='passed';proofs.append(profile)
        for item in report['profiles']:
            inputs.append((ROOT/'.work/suite-profiling-real-01'/(str(item['index'])+'-profile.json'),item['profile_sha256'],'suite-profiling-real-01'))
        for number in ['01','02','03']:
            report_path=ROOT/'results'/('constant-specialize-saved-'+number)/'summary.json';report=json.loads(report_path.read_text());assert report['status']=='passed';proofs.append(report_path)
            item=next(c for c in report['cases'] if c['case']=='token')
            inputs.append((ROOT/report['raw']/'0.rbc',item['candidate_artifact_sha256'],Path(report['raw']).name))
        for run_name in sorted({run_name for _,_,run_name in inputs}):
            path=ROOT/'.work/experiments'/run_name/'status.json';s=json.loads(path.read_text())
            assert s['owner']==s['cwd']==str(ROOT) and s['status']=='finished' and s['returncode']==0
            assert sha(path.with_name('plan.json'))==s['plan_sha256'] and sha(path.with_name('command.log'))==s['log_sha256'];proofs.append(path)
        frozen={str(p.relative_to(ROOT)):sha(p) for p in proofs}
        prepared=[]
        for path,digest,run_name in inputs:
            assert path.resolve(strict=True)==path and sha(path)==digest
            prepared.append(dict(path=str(path.relative_to(ROOT)),sha256=digest,before=properties(path)))
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,inputs=prepared,method='ditto --hfsCompression --noclone; verify bytes and metadata, then atomic replacement',minimum_free_gib=3))
        records=[]
        env={k:v for k,v in os.environ.items() if not k.startswith('DITTO')};env['DITTOABORT']='1'
        for item in prepared:
            path=ROOT/item['path'];stage=path.with_name(path.name+'.completed-evidence-compression-01')
            assert not stage.exists() and not stage.is_symlink();require_space(ROOT,3)
            assert sha(path)==item['sha256'] and properties(path)==item['before']
            command=['/usr/bin/ditto','--hfsCompression','--noclone',str(path),str(stage)]
            child,stdout,stderr=capture(command,cwd=ROOT,env=env,receipt_path=work/'active.json',receipt=dict(path=item['path']))
            row=dict(**item,command=command,pid=child.pid,returncode=child.returncode,stdout=stdout,stderr=stderr,replaced=False)
            records.append(row);write(work/'records.json',records);assert child.returncode==0,stderr
            assert sha(stage)==item['sha256'];after=properties(stage)
            assert {k:v for k,v in after.items() if k!='allocated'}=={k:v for k,v in item['before'].items() if k!='allocated'}
            assert after['allocated']<item['before']['allocated'],'no space benefit; original retained'
            assert sha(path)==item['sha256'] and properties(path)==item['before']
            os.replace(stage,path)
            assert sha(path)==item['sha256'] and properties(path)==after
            row.update(replaced=True,after=after,allocated_bytes_saved=item['before']['allocated']-after['allocated']);write(work/'records.json',records)
            print(item['path'],row['allocated_bytes_saved'],'allocated bytes saved; contents unchanged',flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        assert all(sha(ROOT/i['path'])==i['sha256'] for i in prepared)
        out=ROOT/'results'/run;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',files=len(records),allocated_bytes_saved=sum(r['allocated_bytes_saved'] for r in records),
            original_paths_and_contents_preserved=True,logical_metadata_preserved=True,archives_created=0,performance_measurement=False,
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),free_after=shutil.disk_usage(ROOT).free))

if __name__=='__main__':main()
