"""Lossless compression of seven exact closed public artifact snapshot sets."""
import hashlib, os, shutil, stat, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'benchmarks/experiments/closed-public-artifact-compression'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/closed-public-artifact-compression-recovery-02'))
from compress import identity,unopened,attributes,verify,sha,read,write,capture,acquire_lock,require_space,PRESERVE
from birthtime import birthtime,set_birthtime

RUN='closed-remaining-public-artifact-compression-02'
RUNS='compact-switch-adopted-screen-token-01 conditional-demand-parser-screen-incremental-01 scratch-memory-values-parser-edits-incremental-01 scratch-memory-values-parser-edits-repository-01 emitter-register-workspace-parser-screen-incremental-01 indexed-switches-parser-screen-incremental-01 shared-emission-templates-parser-screen-incremental-01'.split()

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
        failed=ROOT/'results/closed-remaining-public-artifact-compression-01'
        fc=bind(failed/'closure.json');assert fc['status']=='closed' and fc['no_mutation_stage_reached']
        fs=bind(failed/'summary.json',fc['summary_sha256']);ft=bind(failed/'terminal.json',fc['terminal_sha256'])
        assert fs['status']=='preflight-failed' and fs['mutations']==0 and not fs['raw_inventory_created']
        assert fs['expected_binding']['kind']=='file' and fs['expected_binding']['sha256']==fs['actual_owner_sha256']
        assert ft['status']=='finished' and ft['returncode']==1
        assert not (ROOT/'.work/closed-remaining-public-artifact-compression-01').exists()
        for name,digest in fs['evidence'].items():
            p=ROOT/name;assert sha(p)==digest;frozen[name]=digest
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
        for name in RUNS:
            out=ROOT/'results'/name;base=ROOT/'.work'/name
            c=bind(out/'closure.json');assert c['status']=='closed' and c['all_hashes_verified']
            summary=bind(out/'summary.json',c['summary_sha256']);terminal=bind(out/'terminal.json',c['terminal_sha256'])
            assert summary['status']=='passed' and terminal['status']=='finished' and terminal['returncode']==0
            assert terminal['owner']==terminal['cwd']==str(ROOT) and summary['raw']==str(base.relative_to(ROOT))
            plan=bind(base/'plan.json',summary['plan_sha256']);rows=bind(base/'records.json',summary['records_sha256'])
            assert plan['owner']==str(ROOT) and len(rows)==summary['commands']
            assert summary['source_restored'] and summary['original_assertions_unchanged']
            project='fre' if name=='compact-switch-adopted-screen-token-01' else 'pgrust'
            package='fre-kernels' if project=='fre' else 'gram_core'
            source=ROOT/'.work/sources'/project;owner_path=source/'.rust-interp-owned.json'
            expected=plan['frozen'][str(owner_path.relative_to(ROOT))]
            if isinstance(expected,dict):
                assert expected['kind']=='file';expected=expected['sha256']
            assert isinstance(expected,str) and len(expected)==64 and all(c in '0123456789abcdef' for c in expected)
            owner=bind(owner_path,expected)
            assert owner['owner']==str(ROOT) and owner['revision']==plan['revision']
            for row in rows:
                command=row['command']
                assert command[command.index('--manifest-path')+1]==str(source/'Cargo.toml')
                assert command[command.index('--package')+1]==package
            authoritative=manifest_hashes(bind(ROOT/c['evidence'],c['evidence_sha256']))
            before=len(selected)
            for p in sorted((base/'artifacts').glob('*.rbc')):
                assert p.stem==authoritative[str(p.relative_to(ROOT))]
                select(p,name,authoritative[str(p.relative_to(ROOT))])
            runs.append(dict(run=name,status=summary['status'],returncode=terminal['returncode'],files=len(selected)-before,project=project))
        assert len(RUNS)==7 and selected and len({r['path'] for r in selected})==len(selected)
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
