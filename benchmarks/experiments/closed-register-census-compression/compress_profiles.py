"""Lossless compression of nine exact closed public register census reports."""
import hashlib, os, shutil, stat, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'benchmarks/experiments/closed-public-artifact-compression'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/closed-public-artifact-compression-recovery-02'))
from compress import identity,unopened,attributes,verify,sha,read,write,capture,acquire_lock,require_space,PRESERVE
from birthtime import birthtime,set_birthtime

RUN='closed-register-census-compression-01'
SELECTED={
    'emitter-register-workspace-reconstruction-01':['block.json','exhaustive.json'],
    'ordinary-register-census-04':['details.json'],
    'ordinary-register-census-03':['details.json'],
    'ordinary-register-census-02':['details.json'],
    'ordinary-register-census-01':['details.json'],
    'narrow-register-storage-census-01':['typed.json','block-sites.json','exhaustive-sites.json'],
}
RUNS=list(SELECTED)

def manifest_hashes(obj):
    found={}
    def visit(value):
        if not isinstance(value,dict):return
        for key,item in value.items():
            if key.startswith('.work/'):
                digest=item.get('sha256') if isinstance(item,dict) else item
                if isinstance(digest,str) and len(digest)==64:
                    assert key not in found or found[key]==digest,key
                    found[key]=digest
            else:visit(item)
    visit(obj)
    return found

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        frozen={};selected=[];runs=[]
        def bind(p,expected=None):
            assert p.resolve(strict=True)==p and p.is_file(),p
            digest=sha(p)
            if expected is not None:assert digest==expected,p
            frozen[str(p.relative_to(ROOT))]=digest
            return read(p)
        qualification=ROOT/'results/closed-public-artifact-compression-recovery-02'
        qc=bind(qualification/'closure.json');assert qc['status']=='closed'
        qs=bind(qualification/'summary.json',qc['summary_sha256'])
        qt=bind(qualification/'terminal.json',qc['terminal_sha256'])
        assert qs['status']=='passed' and qs['compression_preserved'] and qs['exact_native_creation_time_preserved']
        assert qt['status']=='finished' and qt['returncode']==0 and qt['owner']==qt['cwd']==str(ROOT)
        qp=bind(ROOT/qs['raw']/'plan.json',qs['plan_sha256'])
        # Reuse only the already qualified metadata/helper implementation.
        for name in ['benchmarks/experiments/closed-public-artifact-compression-recovery-02/birthtime.py',
                     'benchmarks/experiments/closed-public-artifact-compression/compress.py']:
            assert sha(ROOT/name)==qp['frozen'][name];frozen[name]=qp['frozen'][name]
        seen=set()
        def select(p,name,expected):
            key=str(p.relative_to(ROOT));assert key not in seen;seen.add(key)
            assert p.suffix in ['.rbc','.json'] and p.stat().st_size>=1024**2
            if p.stat().st_flags!=0:return
            old=identity(p);assert old['size']<=256*1024**2
            attributes(p);assert sha(p)==expected
            selected.append(dict(path=key,run=name,sha256=expected,before=old,native_birthtime=list(birthtime(p))))
        for name,filenames in SELECTED.items():
            out=ROOT/'results'/name;base=ROOT/'.work'/name
            c=bind(out/'closure.json');assert c['status']=='closed' and c['all_hashes_verified']
            summary=bind(out/'summary.json',c['summary_sha256']);terminal=bind(out/'terminal.json',c['terminal_sha256'])
            assert summary['status']=='passed' and terminal['status']=='finished' and terminal['returncode']==0
            assert terminal['owner']==terminal['cwd']==str(ROOT) and summary['raw']==str(base.relative_to(ROOT))
            plan=bind(base/'plan.json',summary['plan_sha256']);bind(base/'records.json',summary['records_sha256'])
            assert plan['owner']==str(ROOT)
            # These are exactly the two public fre cases, not mixed-project reports.
            assert {case['case'] for case in summary['cases']}=={'block','exhaustive'}
            assert summary.get('guest_commands',0)==0 and summary['performance_measurement'] is False
            before=len(selected)
            for filename in filenames:
                p=base/filename
                expected=summary['details_sha256'] if name.startswith('ordinary-register-census-') else summary['outputs'][str(p.relative_to(ROOT))]
                select(p,name,expected)
            runs.append(dict(run=name,status=summary['status'],returncode=terminal['returncode'],files=len(selected)-before,project='fre'))
        assert len(RUNS)==6 and len(selected)==9 and len({r['path'] for r in selected})==len(selected)
        for p in [*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md'),
                  ROOT/'scripts/workflow_io.py',ROOT/'scripts/compare_saved_runtime.py',ROOT/'scripts/supervise_experiment.py']:
            frozen[str(p.relative_to(ROOT))]=sha(p)
        tool=Path('/usr/bin/ditto');tool_sha=sha(tool);raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'inventory.json',selected);write(raw/'runs.json',runs)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],tool=str(tool),tool_sha256=tool_sha,
            inventory_sha256=sha(raw/'inventory.json'),runs_sha256=sha(raw/'runs.json'),
            minimum_initial_gib=12,minimum_child_gib=8,free_before=shutil.disk_usage(ROOT).free,
            performance_measurement=False,original_project_guest_commands=0))
        records=[];write(raw/'records.json',records)
        env={k:v for k,v in os.environ.items() if not k.startswith('DITTO')};env['DITTOABORT']='1'
        print('Inventoried',len(selected),'closed public bytecode/JSON files;',sum(r['before']['blocks']*512 for r in selected),'allocated bytes',flush=True)
        for i,row in enumerate(selected):
            require_space(ROOT,8);p=ROOT/row['path'];old=row['before'];assert identity(p)==old
            opening=unopened(p);stamp=tuple(row['native_birthtime'])
            assert birthtime(p)==stamp and sha(p)==row['sha256'] and identity(p)==old
            temp=p.with_name('.'+p.name+'.'+RUN+'.tmp');assert not temp.exists() and sha(tool)==tool_sha
            cmd=[str(tool),'--hfsCompression','--noclone',str(p),str(temp)]
            child,stdout,stderr=capture(cmd,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(index=i,path=row['path']))
            for stream,value in [('stdout',stdout),('stderr',stderr)]:(raw/(str(i)+'.'+stream)).write_text(value)
            record=dict(index=i,path=row['path'],command=cmd,pid=child.pid,returncode=child.returncode,
                first_open_check=opening,state='copied-unverified',
                **{stream+'_sha256':sha(raw/(str(i)+'.'+stream)) for stream in ['stdout','stderr']})
            records.append(record);write(raw/'records.json',records);assert child.returncode==0
            assert sha(temp)==row['sha256'];set_birthtime(temp,stamp)
            replacement=verify(temp,row['sha256'],old)
            assert birthtime(temp)==birthtime(p)==stamp and identity(p)==old and sha(p)==row['sha256']
            record['second_open_check']=unopened(p);assert identity(p)==old;record['replacement_identity']=replacement
            if replacement['blocks']<old['blocks']:
                assert replacement['flags']==stat.UF_COMPRESSED
                record['state']='verified-before-atomic-replacement';write(raw/'records.json',records)
                os.replace(temp,p);record['state']='replaced'
            else:
                assert identity(temp)==replacement;temp.unlink();record['state']='original-retained-no-saving'
            record['after']=verify(p,row['sha256'],old);assert birthtime(p)==stamp
            write(raw/'records.json',records)
            if (i+1)%10==0:print('Verified',i+1,'of',len(selected),flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),files=len(selected),runs=len(runs),
            compressed_files=sum(r['state']=='replaced' for r in records),all_plaintext_hashes_preserved=True,
            preserved_metadata=PRESERVE,exact_native_creation_time_preserved=True,
            intentionally_changed_metadata=['inode','ctime_ns','compression_flag'],
            allocated_bytes_before=sum(r['before']['blocks']*512 for r in selected),
            allocated_bytes_after=sum(r['after']['blocks']*512 for r in records),
            free_before=read(raw/'plan.json')['free_before'],free_after=shutil.disk_usage(ROOT).free,
            performance_measurement=False,original_project_guest_commands=0,
            **{n+'_sha256':sha(raw/(n+'.json')) for n in ['plan','inventory','records','runs']}))
        print('Completed public cache/evidence compression with every plaintext hash preserved',flush=True)

if __name__=='__main__':main()
