#!/usr/bin/env python3
"""Prepare one private synthetic std CLI fixture; never import or execute project code.
Draft requires separately bound controller admission; outputs are always retained.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

PACKET=Path('/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-mir-lazy-selection-probe')
OUT=PACKET/'fixture-preparation-01'
FIXTURES=OUT/'fixtures'
BASELINE=Path('/Users/danluu/dev/rust-interp-std-readmission-publication-20260918')
CANDIDATE=Path('/Users/danluu/dev/rust-interp-std-mir-lazy-selection-20260918')
PLAN=PACKET/'decision-plan.json'
PLAN_SHA='c432cb2dc3cb182e038a936c898e7d6a76c1270d6425629a4239ef1136838826'
INPUTS=PACKET/'fixture-prep-bindings.json'
INPUTS_SHA='383bc6585f95cdbe8dc3adaf13af1f09c8315a7c9dab42c504ecf4277f0c881f'
SHAPE=PACKET.parent/'std-readmission-stat-probe/fixture-shape-draft.json'
SHAPE_SHA='e6869d97e57f9814858ef9013b9d1c83835bc88174474cb451fbd5191bda0731'
PYTHON=Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
MIB=1024**2
FLOOR=16*1024**3
MAX_ENTRIES,MAX_TOTAL,MAX_FILE=256,MIB,64*1024

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

def main():
    require(sys.argv[1:]==['--prepare-std-cli-fixture'], 'explicit preparation flag required')
    require(sys.implementation.name=='cpython' and sys.version_info[:3]==(3,14,7)
            and Path(sys.executable).resolve()==PYTHON and sys.flags.isolated and sys.flags.no_site
            and sys.flags.no_user_site and sys.dont_write_bytecode, 'pinned Python -I -S -B required')
    require(re.fullmatch(r'[0-9a-f]{64}',INPUTS_SHA) is not None, 'fixture inputs UNBOUND')
    binding_proof,binding_raw=file_proof(INPUTS,4*MIB)
    require(binding_proof['sha256']==INPUTS_SHA, 'fixture inputs changed')
    bindings=json.loads(binding_raw)
    require(bindings['state']=='frozen', 'fixture descriptor unreviewed')
    plan_proof,plan_raw=file_proof(PLAN)
    require(plan_proof['sha256']==PLAN_SHA and json.loads(plan_raw)['case']=='stock_standalone_ready_reuse',
            'wrong numerical decision')
    source_proofs={}
    constants=None
    for root,expected in ((BASELINE,'88ba5afe07c1d5bdce65368162c9954ac6c17683aa7cffb78657370fa821e49c'),
                          (CANDIDATE,'b1e1009f8e6ac04a4270137d964cd0784043b738c16c81980e1ce04364080a72')):
        row,raw=file_proof(root/'scripts/std_mir.py')
        require(row['sha256']==expected,'std source changed')
        source_proofs[str(root/'scripts/std_mir.py')]=row
        declarations={n.targets[0].id:ast.literal_eval(n.value) for n in ast.parse(raw).body
            if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)
            and n.targets[0].id in ('FLAGS','POLICY')}
        if constants is None:constants=declarations
        require(declarations==constants and len(constants)==2,'std identity constants differ')
    corpus_proof,corpus=file_proof(BASELINE/'benchmarks/corpus.json')
    require(corpus_proof['sha256']=='c7b768daa34f4f388d43852fe6290654f5bfdb7fef0abc6f77a16679dae97989'
            and file_proof(CANDIDATE/'benchmarks/corpus.json')[1]==corpus,'corpus differs')
    toolchain=json.loads(corpus)['toolchain']
    require(toolchain=='nightly-2026-09-08','wrong fixture toolchain')
    shape_proof,shape_raw=file_proof(SHAPE)
    require(shape_proof['sha256']==SHAPE_SHA,'historical path-only shape changed')
    shape=json.loads(shape_raw)
    paths=shape['artifact_paths_in_original_order']
    require(shape['artifact_count']==len(paths)==len(set(paths))==26,'wrong artifact count')
    for relative in paths:
        q=Path(relative)
        require(not q.is_absolute() and '..' not in q.parts and str(q)==relative
                and relative.startswith('sysroot/lib/rustlib/aarch64-apple-darwin/lib/')
                and len(q.parts)==6 and q.suffix=='.rmeta','invalid synthetic artifact name')
    disk()
    require(OUT.resolve()==OUT and OUT.is_dir() and not FIXTURES.exists() and not FIXTURES.is_symlink(),
            'fresh parent-controlled fixture output required')
    sys.addaudithook(audit)
    FIXTURES.mkdir(mode=0o700)
    owner=FIXTURES/'owner'
    compiler=FIXTURES/'compiler'
    corpus_path=owner/'benchmarks/corpus.json'
    corpus_path.parent.mkdir(parents=True)
    corpus_path.write_bytes(corpus);corpus_path.chmod(0o444)
    source_lock=compiler/'lib/rustlib/src/rust/library/Cargo.lock'
    source_lock.parent.mkdir(parents=True)
    lock_bytes=b'# Synthetic source identity for std CLI ready-reuse qualification.\n'
    source_lock.write_bytes(lock_bytes);source_lock.chmod(0o444)
    compiler_text='rustc synthetic-std-cli-fixture\nhost: aarch64-apple-darwin\n'
    identity=dict(policy=constants['POLICY'],compiler=compiler_text,target='aarch64-apple-darwin',
                  flags=constants['FLAGS'],lock_sha256=hashlib.sha256(lock_bytes).hexdigest())
    key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    work=owner/'.work/std-mir'/key
    work.mkdir(parents=True)
    std_lock=owner/'.work/std-mir.lock'
    std_lock.touch(mode=0o600,exist_ok=False)
    artifacts={}
    for relative in paths:
        disk()
        target=work/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        payload=hashlib.sha256(('std-cli-selection-v1\0'+relative).encode()).digest()*32
        target.write_bytes(payload);target.chmod(0o444)
        info=target.stat()
        artifacts[relative]=dict(sha256=hashlib.sha256(payload).hexdigest(),
                                stamp=[info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns])
    result=dict(owner=str(owner),identity=identity,artifacts=artifacts,
                source_sha256=hashlib.sha256(b'explicitly synthetic source').hexdigest(),
                setup_seconds=1.0,build_seconds=0.5,fetch_seconds=0.0,metadata_bytes=26*1024)
    ready=work/'ready.json'
    ready.write_text(json.dumps(result,indent=2)+'\n');ready.chmod(0o444)
    expected_report=dict(sysroot=str(work/'sysroot'),target=identity['target'],key=key,
                         setup_seconds=1.0,build_seconds=0.5,metadata_bytes=26*1024)
    frozen=inventory(FIXTURES)
    descriptor=dict(schema_version=1,fixture_owner=str(owner),compiler_sysroot=str(compiler),
        fixture_output_root=str(FIXTURES),toolchain=toolchain,compiler_text=compiler_text,
        artifact_count=26,expected_report=expected_report,fixture_inventory=frozen,
        std_lock=str(std_lock),std_lock_mode='precreated writable empty file, bytes/stamps frozen',
        actual_payload_scope='26 deterministic synthetic1024-byte regular files; never valid Rust metadata',
        source_proofs=source_proofs,corpus_proof=corpus_proof,shape_proof=shape_proof,
        plan=plan_proof,bindings=binding_proof,project_imports_or_calls=0,
        execution_scope='File preparation only; actual main parity is the first fixed screen pair.')
    save(OUT/'fixture-descriptor.json',descriptor)
    print(json.dumps(dict(status='prepared',descriptor=str(OUT/'fixture-descriptor.json'),
                          entry_count=frozen['entry_count'],total_file_bytes=frozen['total_file_bytes'])))


if __name__=='__main__':
    main()
