"""Transparent compression of an explicit, hash-bound closed public profile set."""
import hashlib, os, shutil, stat, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'benchmarks/experiments/closed-public-artifact-compression'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/closed-public-artifact-compression-recovery-02'))
from compress import identity,unopened,attributes,verify,sha,read,write,capture,acquire_lock,require_space,PRESERVE
from birthtime import birthtime,set_birthtime

RUN='closed-public-profile-compression-01'
RUNS='''conditional-demand-parser-profile-01 conditional-demand-profile-01
demand-large-function-profile-01 demand-region-profile-01 implicit-zero-storage-profile-01
indexed-switches-parser-profile-01 indexed-switches-profile-01 indexed-switches-profile-02
native-continuation-snapshot-profile-01 retained-region-values-profile-01
runtime-composition-profile-01 runtime-composition-profile-02 scalar-aggregate-profile-01
scalar-byte-phis-profile-01 scalar-indirect-profile-01 scalar-path-profile-01
scalar-readonly-native-profile-01 scalar-store-log-profile-01 scalar-transaction-native-profile-01
selective-narrow-repair-profile-01 selective-narrow-repair-profile-02 shared-cold-tail-profile-01
compact-switch-current-host-01'''.split()

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
        for name in RUNS:
            out=ROOT/'results'/name;base=ROOT/'.work'/name
            c=bind(out/'closure.json');assert c['status']=='closed' and c['all_hashes_verified']
            s=bind(out/'summary.json',c['summary_sha256']);t=bind(out/'terminal.json',c['terminal_sha256'])
            assert t['status']=='finished' and t['owner']==t['cwd']==str(ROOT)
            assert (s['status']=='passed' and t['returncode']==0) or (s['status'] in ['failed','observer-failed'] and t['returncode']==1)
            authoritative=manifest_hashes(bind(ROOT/c['bindings'],c['bindings_sha256']))
            if 'evidence' in c:
                for path,digest in manifest_hashes(bind(ROOT/c['evidence'],c['evidence_sha256'])).items():
                    assert path not in authoritative or authoritative[path]==digest
                    authoritative[path]=digest
            before=len(selected)
            for p in sorted(base.rglob('*.json')):
                st=p.lstat()
                if st.st_size<1024**2 or st.st_flags!=0:continue
                key=str(p.relative_to(ROOT));assert key in authoritative,key
                old=identity(p);assert old['size']<=256*1024**2
                attributes(p);assert sha(p)==authoritative[key]
                selected.append(dict(path=key,run=name,sha256=authoritative[key],before=old,
                                     native_birthtime=list(birthtime(p))))
            runs.append(dict(run=name,status=s['status'],returncode=t['returncode'],files=len(selected)-before))
        assert len(RUNS)==23 and selected and len({r['path'] for r in selected})==len(selected)
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
        print('Inventoried',len(selected),'closed public JSON files;',sum(r['before']['blocks']*512 for r in selected),'allocated bytes',flush=True)
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
        print('Completed public profile compression with every plaintext hash preserved',flush=True)

if __name__=='__main__':main()
