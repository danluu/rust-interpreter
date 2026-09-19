"""Disposable compatibility test; existing evidence and workspaces are untouched."""
import hashlib,json,mmap,os,stat,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='closed-evidence-compression-probe-02'
ATTRIBUTE='com.rust_interp.compression_fixture'
def read(p):return json.loads(p.read_text())
def metadata(p):
    s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_nlink==1
    return dict(size=s.st_size,blocks=s.st_blocks,mode=s.st_mode,mtime_ns=s.st_mtime_ns,uid=s.st_uid,gid=s.st_gid,
        flags=s.st_flags,compressed=bool(s.st_flags & stat.UF_COMPRESSED),attribute=''.join(subprocess.check_output(['/usr/bin/xattr','-px',ATTRIBUTE,str(p)],text=True).split()).lower())
def verify(source,destination):
    a=metadata(source);b=metadata(destination)
    assert sha(source)==sha(destination)
    for key in ['size','mode','mtime_ns','uid','gid','attribute']:assert a[key]==b[key],(key,a[key],b[key])
    with source.open('rb') as left,destination.open('rb') as right:
        for offset in [0,7,4095,65535,a['size']-17]:
            left.seek(offset);right.seek(offset);assert left.read(17)==right.read(17)
        with mmap.mmap(right.fileno(),0,access=mmap.ACCESS_READ) as mapped:
            assert hashlib.sha256(mapped).hexdigest()==sha(source)
    return dict(source=a,destination=b,sha256=sha(source),ordinary_seek_and_mmap_equal=True)
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        assert sys.platform=='darwin' and hasattr(stat,'UF_COMPRESSED')
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        paths=[*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md'),ROOT/'scripts/workflow_io.py',ROOT/'scripts/compare_saved_runtime.py']
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        tool=Path('/usr/bin/ditto');tool_sha=sha(tool);attribute_tool=Path('/usr/bin/xattr');attribute_tool_sha=sha(attribute_tool)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,tool=str(tool),tool_sha256=tool_sha,attribute_tool=str(attribute_tool),attribute_tool_sha256=attribute_tool_sha,
            controller_command=[sys.executable,*sys.orig_argv[1:]],minimum_initial_gib=12,minimum_child_gib=8,
            existing_files_modified=0,original_project_guest_commands=0,performance_measurement=False))
        line=b'{"function":42,"operation":"load","frame":512,"counter":12345678,"source":"synthetic"}\n'
        data={'repetitive':line*32768,'incompressible':b''.join(hashlib.sha256(i.to_bytes(8,'little')).digest() for i in range(65536))}
        records=[];observations=[];write(raw/'records.json',records)
        env={k:v for k,v in os.environ.items() if not k.startswith('DITTO')};env['DITTOABORT']='1'
        for label,payload in data.items():
            source=raw/(label+'.original');source.write_bytes(payload);source.chmod(0o640)
            require_space(ROOT,8);assert sha(attribute_tool)==attribute_tool_sha
            tag=label+'-attribute';command=[str(attribute_tool),'-w',ATTRIBUTE,'owned disposable fixture',str(source)]
            start=time.time();child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(label=tag))
            for stream,value in [('stdout',out),('stderr',err)]:(raw/(tag+'.'+stream)).write_text(value)
            records.append(dict(label=tag,command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-start,
                stdout_sha256=sha(raw/(tag+'.stdout')),stderr_sha256=sha(raw/(tag+'.stderr'))));write(raw/'records.json',records)
            assert child.returncode==0,(out+err)[-2000:]
            os.utime(source,ns=(1700000000123456789,1700000000123456789))
            original=metadata(source);assert not original['compressed'];digest=sha(source)
            compressed=raw/(label+'.compressed');restored=raw/(label+'.restored')
            for phase,src,dest,options in [('compress',source,compressed,['--hfsCompression']),
                    ('restore',compressed,restored,['--nohfsCompression','--nopreserveHFSCompression'])]:
                require_space(ROOT,8);assert sha(tool)==tool_sha
                command=[str(tool),*options,'--noclone',str(src),str(dest)];tag=label+'-'+phase
                start=time.time();child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(label=tag))
                for stream,value in [('stdout',out),('stderr',err)]:(raw/(tag+'.'+stream)).write_text(value)
                records.append(dict(label=tag,command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-start,
                    stdout_sha256=sha(raw/(tag+'.stdout')),stderr_sha256=sha(raw/(tag+'.stderr'))));write(raw/'records.json',records)
                assert child.returncode==0,(out+err)[-2000:]
                observations.append(dict(label=tag,**verify(source,dest)));write(raw/'observations.json',observations)
                assert metadata(source)==original and sha(source)==digest
            assert not metadata(restored)['compressed']
            if label=='repetitive':assert metadata(compressed)['compressed'] and metadata(compressed)['blocks']<original['blocks']
        assert all(sha(ROOT/p)==h for p,h in frozen.items()) and sha(tool)==tool_sha
        out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),commands=6,copy_commands=4,attribute_setup_commands=2,fixtures=2,
            ordinary_seek_and_mmap_equal=True,metadata_preserved=True,original_fixtures_unchanged=True,existing_files_modified=0,
            original_project_guest_commands=0,performance_measurement=False,real_evidence_compression_admitted=False,
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),observations_sha256=sha(raw/'observations.json'),
            repetitive_allocated_bytes_before=observations[0]['source']['blocks']*512,
            repetitive_allocated_bytes_after=observations[0]['destination']['blocks']*512))
        print('Two disposable fixtures preserve bytes, seek/mmap reads and metadata; no existing file modified')
def close():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        raw=ROOT/'.work'/RUN;out=ROOT/'results'/RUN;outer=ROOT/'.work/experiments'/RUN
        plan=read(raw/'plan.json');summary=read(out/'summary.json');terminal=read(outer/'status.json');records=read(raw/'records.json')
        assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT)
        assert terminal['command'][1:]==plan['controller_command'][1:]
        assert sha(outer/'plan.json')==terminal['plan_sha256'] and sha(outer/'command.log')==terminal['log_sha256']
        for key in ['plan','records','observations']:assert sha(raw/(key+'.json'))==summary[key+'_sha256']
        assert summary['status']=='passed' and len(records)==6 and all(r['returncode']==0 for r in records)
        assert sha(Path(plan['tool']))==plan['tool_sha256'] and sha(Path(plan['attribute_tool']))==plan['attribute_tool_sha256']
        for label in ['repetitive','incompressible']:
            for suffix in ['compressed','restored']:verify(raw/(label+'.original'),raw/(label+'.'+suffix))
        bindings={};evidence={}
        for p,h in plan['frozen'].items():
            assert sha(ROOT/p)==h
            assert hashlib.sha256(subprocess.check_output(['git','show',plan['source_revision']+':'+p],cwd=ROOT)).hexdigest()==h
            bindings[p]=dict(revision=plan['source_revision'],sha256=h)
        for row in records:
            for stream in ['stdout','stderr']:assert sha(raw/(row['label']+'.'+stream))==row[stream+'_sha256']
        for p in raw.rglob('*'):
            if p.is_file():evidence[str(p.relative_to(ROOT))]=sha(p)
        for p in [outer/'plan.json',outer/'status.json',outer/'command.log']:evidence[str(p.relative_to(ROOT))]=sha(p)
        assert not (out/'closure.json').exists();write(raw/'closed-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
        (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
        write(out/'closure.json',dict(status='closed',all_hashes_verified=True,existing_files_modified=0,
            summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
            bindings=str((raw/'closed-bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'closed-bindings.json'),
            evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json')))
        print('Closed disposable compression compatibility; no existing evidence changed')
if __name__=='__main__':
    if sys.argv[1:]==['--close']:close()
    else:assert len(sys.argv)==1;main()
