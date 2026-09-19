import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'benchmarks/experiments/closed-public-artifact-compression'))
from compress import RUN as ORIGINAL,identity,verify,sha,read,write,acquire_lock,require_space,PRESERVE,capture
from birthtime import birthtime,set_birthtime
RUN='closed-public-artifact-compression-recovery-02'
def prefix():
    raw=ROOT/'.work'/ORIGINAL;outer=ROOT/'.work/experiments'/ORIGINAL
    plan=read(raw/'plan.json');rows=read(raw/'inventory.json');records=read(raw/'records.json');terminal=read(outer/'status.json')
    assert terminal['status']=='finished' and terminal['returncode']==1 and terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT)
    assert sha(outer/'command.log')==terminal['log_sha256'] and sha(outer/'plan.json')==terminal['plan_sha256']
    assert 'birthtime' in (outer/'command.log').read_text() and sha(raw/'inventory.json')==plan['inventory_sha256']
    assert len(rows)==373 and len(records)==133 and all(r['state']=='replaced' for r in records[:-1])
    assert 'state' not in records[-1] and records[-1]['returncode']==0
    for i,row in enumerate(rows):
        p=ROOT/row['path'];current=verify(p,row['sha256'],row['before'])
        if i<132:assert current==records[i]['after']
        else:assert current==row['before']
    pending=Path(records[-1]['command'][-1]);assert pending== (ROOT/rows[132]['path']).with_name('.'+Path(rows[132]['path']).name+'.'+ORIGINAL+'.tmp')
    meta=identity(pending);assert sha(pending)==rows[132]['sha256']
    assert all(meta[k]==rows[132]['before'][k] for k in PRESERVE if k!='birthtime')
    assert meta['birthtime']!=rows[132]['before']['birthtime']
    assert all(sha(ROOT/p)==h for p,h in plan['frozen'].items())
    return dict(original_run=ORIGINAL,files=373,completed_replacements=132,remaining_originals=241,
        all_original_plaintext_hashes_preserved=True,failure_before_replacement=True,
        pending_path=str(pending.relative_to(ROOT)),pending_sha256=sha(pending),pending_identity=meta,
        frozen={**plan['frozen'],**{str(p.relative_to(ROOT)):sha(p) for p in [raw/'plan.json',raw/'inventory.json',raw/'records.json',outer/'status.json',outer/'plan.json',outer/'command.log']}})
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);saved=prefix();write(raw/'prefix.json',saved)
        paths=[*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md')]
        prior=ROOT/'.work/closed-public-artifact-compression-recovery-01'
        prior_outer=ROOT/'.work/experiments/closed-public-artifact-compression-recovery-01'
        failed=read(prior_outer/'status.json');assert failed['status']=='finished' and failed['returncode']==1
        assert failed['owner']==failed['cwd']==str(ROOT) and sha(prior_outer/'command.log')==failed['log_sha256']
        assert sha(prior_outer/'plan.json')==failed['plan_sha256']
        assert read(prior/'copy.json')['returncode']==0
        assert all(sha(ROOT/p)==h for p,h in read(prior/'plan.json')['frozen'].items())
        paths += [p for p in prior.iterdir() if p.is_file()]+[prior_outer/'status.json',prior_outer/'plan.json',prior_outer/'command.log']
        frozen={**saved['frozen'],**{str(p.relative_to(ROOT)):sha(p) for p in paths}}
        header=Path('/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include/sys/attr.h');decl=header.read_text()
        assert '#define ATTR_BIT_MAP_COUNT 5' in decl and '#define ATTR_CMN_CRTIME                         0x00000200' in decl
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,controller_command=[sys.executable,*sys.orig_argv[1:]],header=str(header),header_sha256=sha(header),existing_evidence_modified=0))
        source=raw/'source.fixture';source.write_bytes(b'creation time differs from modification time\n'*65536);source.chmod(0o640)
        os.utime(source,ns=(1700000100987654321,1700000100987654321));set_birthtime(source,(1700000000,123456789))
        old=identity(source);stamp=birthtime(source);assert stamp==(1700000000,123456789) and stamp[0]*10**9+stamp[1]!=old['mtime_ns']
        temp=raw/'copy.tmp';cmd=['/usr/bin/ditto','--hfsCompression','--noclone',str(source),str(temp)]
        env={k:v for k,v in os.environ.items() if not k.startswith('DITTO')};env['DITTOABORT']='1'
        require_space(ROOT,8);child,out,err=capture(cmd,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(label='copy'))
        (raw/'copy.stdout').write_text(out);(raw/'copy.stderr').write_text(err)
        write(raw/'copy.json',dict(command=cmd,pid=child.pid,returncode=child.returncode,stdout_sha256=sha(raw/'copy.stdout'),stderr_sha256=sha(raw/'copy.stderr')))
        assert child.returncode==0;copied_stamp=birthtime(temp);set_birthtime(temp,stamp)
        new=verify(temp,sha(source),old);assert birthtime(temp)==stamp and identity(source)==old
        import stat
        assert new['flags']==stat.UF_COMPRESSED and new['blocks']<old['blocks']
        write(raw/'fixture.json',dict(source=old,copy=new,original_creation_time=stamp,ditto_creation_time=copied_stamp,restored_creation_time=birthtime(temp),sha256=sha(source),full_metadata_preserved=True))
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),original_prefix_replacements=132,
            original_files_verified=373,existing_evidence_modified=0,exact_native_creation_time_preserved=True,compression_preserved=True,prior_failed_probe_retained=True,
            performance_measurement=False,original_project_guest_commands=0,
            **{n+'_sha256':sha(raw/(n+'.json')) for n in ['plan','prefix','copy','fixture']}))
        print('Preserved132 completed replacements and241 originals; distinct creation-time fixture passed')
if __name__=='__main__':main()
