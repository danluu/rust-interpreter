#!/usr/bin/env python3
"""Prepare only two owned synthetic metadata trees using actual baseline validation."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import sys

PACKET = Path('/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-readmission-stat-probe')
OUT = PACKET / 'fixture-qualification-01'
FIXTURES = OUT / 'fixtures'
CACHE = OUT / 'qualification-pycache'
PYTHON = Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
BASELINE = Path('/Users/danluu/dev/rust-interp-allocation-decoder-publication-20260918/scripts/std_mir_readmission.py')
BASELINE_SHA = '930fa9788b6f41a8f11d51b9b28f2590b2cd146d6ab9cf91b4e32dd89f5dc426'
PLAN_SHA = 'a10f461883b1b3d68416b23c863d304a3c7f3b65edba2fc35fe8f5beb630c76b'
SHAPE_SHA = 'e6869d97e57f9814858ef9013b9d1c83835bc88174474cb451fbd5191bda0731'
MIB = 1024**2
FLOOR = 16*1024**3
MAX_ENTRIES, MAX_TOTAL, MAX_FILE = 256, MIB, 64*1024
CALLS = []


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def disk():
    s = os.statvfs(PACKET)
    require(s.f_bavail*s.f_frsize > FLOOR, 'fixture preparation requires16GiB')


def stamp(s):
    return [s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_nlink]


def file_proof(path, cap=MAX_FILE):
    before = path.lstat()
    require(path.resolve(strict=True) == path and stat.S_ISREG(before.st_mode)
            and before.st_size <= cap, 'unsafe input: '+str(path))
    fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        require(stamp(os.fstat(fd)) == stamp(before), 'opening input changed')
        data = b''
        while len(data) <= before.st_size:
            part = os.read(fd, min(64*1024, before.st_size+1-len(data)))
            if not part:
                break
            data += part
            require(len(data) <= before.st_size, 'input grew')
        require(len(data) == before.st_size and stamp(os.fstat(fd)) == stamp(before)
                and stamp(path.lstat()) == stamp(before), 'input changed')
    finally:
        os.close(fd)
    return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),stamp=stamp(before)), data


def save(path, value):
    disk()
    require(path.is_absolute() and path.resolve() == path and path.is_relative_to(OUT)
            and not path.exists() and not path.is_symlink(), 'unsafe output destination')
    data=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    require(len(data) <= MIB, 'report exceeds bound')
    with path.open('xb') as out:
        out.write(data)


def inventory(root):
    require(root.resolve(strict=True) == root and stat.S_ISDIR(root.lstat().st_mode),
            'unsafe fixture root')
    rows = {}
    pending = [root]
    total = 0
    while pending:
        path = pending.pop()
        s = path.lstat()
        require(path.resolve(strict=True) == path, 'fixture symlink/indirection')
        relative = str(path.relative_to(root))
        if stat.S_ISDIR(s.st_mode):
            rows[relative] = dict(kind='directory',stamp=stamp(s))
            children = []
            for child in path.iterdir():
                children.append(child)
                require(len(children)+len(pending)+len(rows) <= MAX_ENTRIES,
                        'fixture entries exceed bound')
            pending.extend(sorted(children,reverse=True))
        else:
            require(stat.S_ISREG(s.st_mode), 'nonregular fixture entry')
            row, _ = file_proof(path)
            rows[relative] = dict(kind='file',**row)
            total += row['bytes']
            require(total <= MAX_TOTAL, 'fixture byte budget exceeded')
        require(len(rows) <= MAX_ENTRIES, 'fixture entries exceed bound')
    return dict(entries=rows,total_file_bytes=total,entry_count=len(rows))



def loaded_inputs():
    root=PYTHON.parent.parent/'lib/python3.14'
    modules={}
    files={}
    total=0
    for name,module in list(sys.modules.items()):
        value=getattr(module,'__file__',None)
        if not value:
            continue
        path=Path(value)
        if path.suffix=='.pyc':
            path=Path(importlib.util.source_from_cache(str(path)))
        path=path.resolve()
        require(path==BASELINE or path==Path(__file__).resolve() or path.is_relative_to(root),
                'unexpected imported file: '+str(path))
        modules[name]=str(path)
        if str(path) not in files:
            row,_=file_proof(path,16*MIB)
            files[str(path)]=row
            total+=row['bytes']
            require(total<=64*MIB and len(files)<=384,'loaded dependency bound')
    return dict(modules=modules,files=files,total_bytes=total)


def audit(event,args):
    if event.startswith(('subprocess.', 'socket.')) or event in (
            'os.system','os.fork','os.forkpty','os.posix_spawn','os.posix_spawnp','os.exec'):
        raise RuntimeError('fixture child cannot launch processes or network: '+event)
    paths = []
    if event == 'open':
        path,mode,flags = args
        if (isinstance(mode,str) and any(c in mode for c in 'wax+')) or (
                isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)):
            paths=[path]
    elif event in ('os.mkdir','os.chmod','os.remove','os.rmdir','os.utime'):
        paths=[args[0]]
    elif event in ('os.rename','os.link','os.symlink'):
        paths=[args[0],args[1]]
    for name in paths:
        require(not isinstance(name,int),'descriptor mutation forbidden')
        path=Path(name)
        require(path.is_absolute() and path.resolve()==path and path.is_relative_to(OUT),
                'mutation outside owned output: '+str(path))


def validate_once(module,case,phase,work,ready,result):
    disk()
    output,error=io.StringIO(),io.StringIO()
    row=dict(case=case,phase=phase,work=str(work),ready=str(ready),outcome=None,error=None)
    try:
        with contextlib.redirect_stdout(output),contextlib.redirect_stderr(error):
            outcome=module.validate(work,ready,result)
        row.update(outcome=outcome,stdout=output.getvalue(),stderr=error.getvalue())
        require(outcome is None and not row['stdout'] and not row['stderr'],'unexpected validation outcome')
    except BaseException as caught:
        row.update(error=repr(caught),stdout=output.getvalue(),stderr=error.getvalue())
        raise
    finally:
        CALLS.append(row)
        save(OUT/('baseline-call-'+str(len(CALLS))+'.json'),row)


def main():
    require(len(sys.argv)==3 and Path(sys.argv[1])==OUT/'prep-config.json','fixed config required')
    require(sys.platform=='darwin' and sys.version_info[:2]==(3,14)
            and Path(sys.executable).resolve()==PYTHON and sys.flags.isolated and sys.flags.no_site
            and sys.dont_write_bytecode and sys.pycache_prefix==str(CACHE),'pinned isolated no-bytecode runtime required')
    require(Path.cwd()==PACKET and PACKET.resolve(strict=True)==PACKET
            and OUT.resolve(strict=True)==OUT and not OUT.is_symlink(),'owned paths changed')
    config_proof,raw=file_proof(Path(sys.argv[1]),MIB)
    require(config_proof['sha256']==sys.argv[2],'config changed')
    config=json.loads(raw)
    require(config['output']==str(OUT) and config['fixtures']==str(FIXTURES)
            and config['cache']==str(CACHE) and config['baseline']==str(BASELINE)
            and config['plan_sha256']==PLAN_SHA and config['shape_sha256']==SHAPE_SHA,
            'config scope differs')
    require([OUT.stat().st_dev,OUT.stat().st_ino]==config['output_identity'],'output replaced')
    require(not FIXTURES.exists() and not FIXTURES.is_symlink() and CACHE.is_dir()
            and CACHE.resolve(strict=True)==CACHE and not list(CACHE.iterdir()),'fresh empty owned paths required')
    planproof,raw=file_proof(PACKET/'decision-plan.json',MIB)
    require(planproof['sha256']==PLAN_SHA,'decision changed')
    plan=json.loads(raw)
    shapeproof,raw=file_proof(PACKET/'fixture-shape-draft.json',MIB)
    require(shapeproof['sha256']==SHAPE_SHA,'shape changed')
    shape=json.loads(raw)
    names=shape['artifact_paths_in_original_order']
    require(len(names)==len(set(names))==26 and shape['synthetic_bytes_per_artifact']==1024,
            'incorrect fixture shape')
    require(plan['preparation']['actual_baseline_validate_calls']==3 and
            plan['preparation']['limits']==dict(max_entries=MAX_ENTRIES,max_total_bytes=MAX_TOTAL,max_file_bytes=MAX_FILE),
            'preparation scope changed')
    for name in names:
        require(isinstance(name,str) and not Path(name).is_absolute()
                and all(part not in ('','.','..') for part in name.split('/'))
                and name.endswith('.rmeta'),'unsafe relative artifact')
    baseline_proof,raw=file_proof(BASELINE,MIB)
    require(baseline_proof['sha256']==BASELINE_SHA,'baseline source changed')
    require('std_mir_readmission' not in sys.modules,'baseline module preloaded')
    sys.addaudithook(audit)
    spec=importlib.util.spec_from_file_location('std_mir_readmission',BASELINE)
    module=importlib.util.module_from_spec(spec)
    sys.modules['std_mir_readmission']=module
    spec.loader.exec_module(module)
    require(Path(module.__file__).resolve()==BASELINE,'incorrect baseline module')
    loaded_before=loaded_inputs()
    disk()
    FIXTURES.mkdir(mode=0o700)
    cases=[]
    for case in ('matching_saved_stamps','matching_device_readmission_receipt'):
        work=FIXTURES/case
        disk();work.mkdir(mode=0o700)
        artifacts={}
        for name in names:
            disk()
            target=work/name
            target.parent.mkdir(parents=True,exist_ok=True)
            require(target.resolve()==target and target.is_relative_to(work) and not target.exists(),
                    'unsafe fixture destination')
            payload=hashlib.sha256(b'std-readmission-stat-v1\0'+name.encode()).digest()*32
            require(len(payload)==1024,'payload recipe mismatch')
            with target.open('xb') as out:
                out.write(payload)
            target.chmod(0o444)
            s=target.stat()
            recorded=[s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns]
            if case=='matching_device_readmission_receipt':
                recorded[0]+=1
            artifacts[name]=dict(stamp=recorded,sha256=hashlib.sha256(payload).hexdigest())
        result=dict(owner=str(work),artifacts=artifacts,synthetic_fixture=dict(
            schema_version=1,kind='C9 synthetic1KiB payloads with retained26-path shape',
            fixture_shape_sha256=SHAPE_SHA,not_real_rust_metadata=True))
        ready=work/'ready.json'
        # Preserve the original artifact insertion order, as actual validation does.
        disk()
        with ready.open('x') as out:
            json.dump(result,out,indent=2)
            out.write('\n')
        ready.chmod(0o444)
        ready_before,ready_bytes=file_proof(ready)
        require(json.loads(ready_bytes)==result,'manifest readback differs')
        validate_once(module,case,'saved-stamps' if case=='matching_saved_stamps' else 'create-receipt',
                      work,ready,result)
        receipt_paths=sorted(work.glob('readmission-*.json'))
        receipt=None
        if case=='matching_saved_stamps':
            require(not receipt_paths,'matching stamps unexpectedly created receipt')
        else:
            require(len(receipt_paths)==1,'expected exactly one actual readmission receipt')
            receipt_path=receipt_paths[0]
            before,text=file_proof(receipt_path)
            validate_once(module,case,'reuse-receipt',work,ready,result)
            after,text_after=file_proof(receipt_path)
            require(before==after and text==text_after,'receipt changed during reuse')
            receipt_path.chmod(0o444)
            receipt_proof,receipt_bytes=file_proof(receipt_path)
            receipt=dict(path=str(receipt_path),proof=receipt_proof,text=receipt_bytes.decode(),
                         parsed=json.loads(receipt_bytes))
        ready_after,after_bytes=file_proof(ready)
        require(ready_before==ready_after and ready_bytes==after_bytes,'ready changed during preparation')
        # Seal directories after the real baseline is finished publishing.
        unsealed=inventory(work)
        dirs=[work/name for name,row in unsealed['entries'].items()
              if row['kind']=='directory']
        for directory in sorted(dirs,key=lambda path:len(path.parts),reverse=True):
            disk();directory.chmod(0o555)
        snapshot=inventory(work)
        require(all((row['stamp'][2]&0o222)==0 for row in snapshot['entries'].values()),
                'fixture not immutable')
        cases.append(dict(name=case,work=str(work),ready=str(ready),result=result,
                          ready_proof=ready_after,ready_text=ready_bytes.decode(),receipt=receipt,
                          inventory=snapshot,artifact_count=26,synthetic_payload_bytes=26*1024))
    disk();FIXTURES.chmod(0o555)
    aggregate=inventory(FIXTURES)
    require(len(CALLS)==3 and all(row['outcome'] is None and row['error'] is None for row in CALLS),
            'baseline call count/outcome differs')
    require(not list(CACHE.iterdir()),'preparation wrote bytecode cache')
    require(file_proof(BASELINE,MIB)[0]==baseline_proof,'baseline changed')
    for case in cases:
        require(inventory(Path(case['work']))==case['inventory'],'fixture changed before publication')
    loaded_after=loaded_inputs()
    require(loaded_before==loaded_after,'loaded inputs changed during preparation')
    descriptor=dict(schema_version=1,status='passed',decision_sha256=PLAN_SHA,
        fixture_shape_sha256=SHAPE_SHA,baseline_source=baseline_proof,
        baseline_source_path=str(BASELINE),loaded_inputs=loaded_before,root=str(FIXTURES),root_inventory=aggregate,
        cases=cases,actual_baseline_calls=CALLS,expected_baseline_calls=3,
        fixture_label=shape['fixture_label'],source_payloads_read_or_copied=False,
        qualification_cache=dict(path=str(CACHE),empty=True,scope='qualification only; timing creates a new prefix'),
        outcome='All calls returned None with no output; all fixture bytes and identities are frozen')
    save(OUT/'fixtures.json',descriptor)
    return descriptor


if __name__=='__main__':
    failure=None
    try:
        descriptor=main()
    except BaseException as caught:
        failure=repr(caught)
    report=dict(status='passed' if failure is None else 'failed',error=failure,
                actual_baseline_calls=CALLS,expected_baseline_calls=3,
                descriptor=str(OUT/'fixtures.json') if failure is None else None)
    # Retain preparation failures without cleanup or retry.
    if OUT.is_dir() and OUT.resolve()==OUT:
        save(OUT/'prep-result.json',report)
    print(json.dumps(dict(status=report['status'],error=failure,calls=len(CALLS))),flush=True)
    raise SystemExit(0 if failure is None else 1)
