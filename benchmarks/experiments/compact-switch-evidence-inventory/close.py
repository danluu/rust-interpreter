"""Close the bounded inventory without altering any inventoried file."""
import hashlib,json,stat,subprocess,zlib
from pathlib import Path
from inventory import ROOT,RUN,RUNS,SUFFIXES,FORBIDDEN,acquire_lock,sha,require_space,write,read

with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,8)
    raw=ROOT/'.work'/RUN;out=ROOT/'results'/RUN;outer=ROOT/'.work/experiments'/RUN
    plan=read(raw/'plan.json');summary=read(out/'summary.json');terminal=read(outer/'status.json')
    rows=read(raw/'inventory.json');runs=read(raw/'runs.json')
    assert terminal['status']=='finished' and terminal['returncode']==0
    assert terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT)
    assert terminal['command'][1:]==plan['controller_command'][1:]
    assert sha(outer/'plan.json')==terminal['plan_sha256'] and sha(outer/'command.log')==terminal['log_sha256']
    assert plan['runs']==RUNS and len(runs)==len(RUNS)
    for name in ['plan','inventory','runs']:assert sha(raw/(name+'.json'))==summary[name+'_sha256']
    assert summary['eligible_files']==len(rows) and summary['allocated_bytes']==sum(r['allocated_bytes'] for r in rows)
    assert summary['logical_bytes']==sum(r['size'] for r in rows)
    assert summary['existing_files_modified']==0 and summary['full_payload_hashes_rechecked'] is False
    manifests={r['run']:read(ROOT/r['evidence_manifest']) for r in runs}
    assert len({r['path'] for r in rows})==len(rows)
    for r in rows:
        p=ROOT/r['path'];stage=ROOT/'.work'/r['run'];s=p.lstat()
        assert p.is_relative_to(stage) and p.suffix in SUFFIXES
        assert not set(p.relative_to(stage).parts)&FORBIDDEN
        assert p.resolve(strict=True)==p and stat.S_ISREG(s.st_mode) and s.st_nlink==1
        assert not s.st_mode&0o111 and not s.st_flags&stat.UF_COMPRESSED
        assert (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_mode,s.st_flags,s.st_blocks*512)==tuple(r[k] for k in ['device','inode','size','mtime_ns','mode','flags','allocated_bytes'])
        assert manifests[r['run']][r['path']]==r['expected_plaintext_sha256']
        with p.open('rb') as f:sample=f.read(65536)
        assert len(sample)==r['sample_bytes'] and len(zlib.compress(sample))==r['sample_zlib_bytes']
    bindings={}
    for path,h in plan['frozen'].items():
        assert sha(ROOT/path)==h
        if not path.startswith(('.work/','results/')):
            assert hashlib.sha256(subprocess.check_output(['git','show',plan['source_revision']+':'+path],cwd=ROOT)).hexdigest()==h
        bindings[path]=dict(sha256=h,revision=plan['source_revision'])
    evidence={str(p.relative_to(ROOT)):sha(p) for p in [*raw.glob('*.json'),outer/'plan.json',outer/'status.json',outer/'command.log']}
    assert not (out/'closure.json').exists()
    write(raw/'closed-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',all_hashes_verified=True,full_payload_hashes_rechecked=False,
        existing_files_modified=0,real_evidence_compression_admitted=False,
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
        bindings=str((raw/'closed-bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'closed-bindings.json'),
        evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json')))
    print('Closed read-only inventory:',len(rows),'files; no payload changed')
