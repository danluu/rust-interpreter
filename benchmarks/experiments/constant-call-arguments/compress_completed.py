#!/usr/bin/env python3
"""Apply transparent filesystem compression to an exact completed evidence list."""
import argparse,hashlib,json,os,shutil,stat,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write

def properties(path):
    s=path.lstat();assert stat.S_ISREG(s.st_mode) and s.st_nlink==1
    return dict(size=s.st_size,mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid,mtime_ns=s.st_mtime_ns,
        flags=s.st_flags & ~stat.UF_COMPRESSED,allocated=s.st_blocks*512)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',choices=['completed-evidence-compression-01','completed-evidence-compression-02','completed-evidence-compression-03'],default='completed-evidence-compression-01')
    run=parser.parse_args().run_id
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,3)
        work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
        inputs=[];proofs=[Path(__file__),Path(__file__).with_name('TRANSPARENT-STORAGE.md')]
        if run.endswith('01'):
            profile=ROOT/'results/suite-profiling-real-01/summary.json';report=json.loads(profile.read_text());assert report['status']=='passed';proofs.append(profile)
            for item in report['profiles']:
                inputs.append((ROOT/'.work/suite-profiling-real-01'/(str(item['index'])+'-profile.json'),item['profile_sha256'],'suite-profiling-real-01'))
            for number in ['01','02','03']:
                report_path=ROOT/'results'/('constant-specialize-saved-'+number)/'summary.json';report=json.loads(report_path.read_text());assert report['status']=='passed';proofs.append(report_path)
                item=next(c for c in report['cases'] if c['case']=='token')
                inputs.append((ROOT/report['raw']/'0.rbc',item['candidate_artifact_sha256'],Path(report['raw']).name))
        elif run.endswith('02'):
            report_path=ROOT/'results/fixed-frame-clear-entropy-aa-01/summary.json';report=json.loads(report_path.read_text());assert report['status']=='passed';proofs.append(report_path)
            for index in [0,1]:
                path=Path('.work/fixed-frame-clear-entropy-aa-01')/(str(index)+'.profile.json')
                inputs.append((ROOT/path,report['evidence'][str(path)],'fixed-frame-clear-entropy-aa-01'))
            commands_path=ROOT/'.work/budget-register-smoke-05/commands.json';commands=json.loads(commands_path.read_text());proofs.append(commands_path)
            for index in [1,3,11,13]:
                path=Path('.work/budget-register-smoke-05')/(str(index)+'-profile.json')
                rows=[row for row in commands if str(path) in row['files']];assert len(rows)==1 and rows[0]['returncode']==0
                inputs.append((ROOT/path,rows[0]['files'][str(path)],'budget-register-smoke-05'))
            for sample_run in ['selected-native-block-sample-01','selected-native-exhaustive-sample-01']:
                report_path=ROOT/'results'/sample_run/'summary.json';report=json.loads(report_path.read_text());proofs.append(report_path)
                assert report['performance_measurement'] is False and len(report['samples'])==3
                for sample in report['samples']:
                    record_path=ROOT/'.work'/sample_run/str(sample['index'])/'record.json'
                    assert sha(record_path)==sample['evidence'][str(record_path.relative_to(ROOT))]
                    record=json.loads(record_path.read_text());proofs.append(record_path)
                    assert record['identity']['status']=='finished' and record['identity']['returncode']==0
                    for name in ['jit-code/code.bin','jit-code/map.json']:
                        inputs.append((record_path.parent/name,record['files'][name],sample_run))
        else:
            for run_name,field in [('budget-register-randomness-01','executions'),('resumable-bulk-token-transitions-01','evidence')]:
                rp=ROOT/'results'/run_name/'summary.json';r=json.loads(rp.read_text());assert r['status']=='passed';proofs.append(rp)
                path=Path('.work')/run_name/'profile.json'
                digest=r[field][str(path)] if field=='evidence' else next(e['files'][str(path)] for e in r[field] if str(path) in e['files'])
                inputs.append((ROOT/path,digest,run_name))
            run_name='aggregate-reuse-collection-01';rp=ROOT/'results'/run_name/'summary.json';r=json.loads(rp.read_text())
            assert r['status']=='passed';proofs.append(rp)
            for case in r['cases']:inputs.append((ROOT/case['profile'],case['profile_sha256'],run_name))
            for run_name in ['call-slot-smoke-01','whole-call-runtime-smoke-01','budget-register-smoke-04']:
                rp=ROOT/'results'/run_name/'summary.json';r=json.loads(rp.read_text());proofs.append(rp)
                cp=ROOT/'.work'/run_name/'commands.json';commands=json.loads(cp.read_text());proofs.append(cp)
                if run_name=='budget-register-smoke-04':
                    assert r['status']=='failed' and r['commands_completed']==14 and r['token_original_success_executions']==4
                    assert sha(cp)==r['evidence'][str(cp.relative_to(ROOT))]
                    assert r['cause']=='Token cross-process counters differ; original assertions pass. Original randomness is being investigated with an unchanged-VM repetition.'
                else:assert r['status']=='passed' and r['commands']==commands
                for index in [1,3,11,13]:
                    path=Path('.work')/run_name/(str(index)+'-profile.json')
                    rows=[row for row in commands if str(path) in row['files']];assert len(rows)==1 and rows[0]['returncode']==0
                    inputs.append((ROOT/path,rows[0]['files'][str(path)],run_name))
        for run_name in sorted({run_name for _,_,run_name in inputs}):
            path=ROOT/'.work/experiments'/run_name/'status.json';s=json.loads(path.read_text())
            expected_returncode=1 if run.endswith('03') and run_name=='budget-register-smoke-04' else 0
            assert s['owner']==s['cwd']==str(ROOT) and s['status']=='finished' and s['returncode']==expected_returncode
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
            path=ROOT/item['path'];stage=path.with_name(path.name+'.'+run)
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
