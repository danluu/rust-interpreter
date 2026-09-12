#!/usr/bin/env python3
"""Build reusable standard-library metadata retaining MIR, without guest codegen."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
FLAGS='-Zalways-encode-mir=yes -Zforce-unstable-if-unmarked'
POLICY='metadata-sysroot-v1-release-backtrace'


def stamp(path):
    s=path.stat()
    return [s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns]


def source_digest(directory):
    h=hashlib.sha256()
    for p in sorted(directory.rglob('*')):
        if p.is_symlink():data=os.readlink(p).encode()
        elif p.is_file():data=p.read_bytes()
        else:continue
        h.update(str(p.relative_to(directory)).encode()+b'\0'+data)
    return h.hexdigest()


def checked_std_mir(toolchain,fetch=False):
    """Install a frozen source snapshot once; validate metadata stamps on reuse."""
    (ROOT/'.work').mkdir(exist_ok=True)
    lock=(ROOT/'.work/std-mir.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX)
    started=time.perf_counter()
    compiler=subprocess.check_output(['rustc','+'+toolchain,'-vV'],text=True)
    target=next(line.removeprefix('host: ') for line in compiler.splitlines() if line.startswith('host: '))
    original=Path(subprocess.check_output(['rustc','+'+toolchain,'--print','sysroot'],text=True).strip())
    source=original/'lib/rustlib/src/rust/library'
    identity=dict(policy=POLICY,compiler=compiler,target=target,flags=FLAGS,
                  lock_sha256=hashlib.sha256((source/'Cargo.lock').read_bytes()).hexdigest())
    key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    work=ROOT/'.work/std-mir'/key
    ready=work/'ready.json'
    if ready.exists():
        result=json.loads(ready.read_text())
        if result['owner']!=str(ROOT) or result['identity']!=identity:
            raise RuntimeError('standard-library MIR ownership or identity mismatch')
        for name,metadata in result['artifacts'].items():
            path=work/name
            if not path.is_file() or stamp(path)!=metadata['stamp']:
                raise RuntimeError('standard-library MIR artifact changed: '+str(path))
        return work/'sysroot',target,key,result
    work.mkdir(parents=True,exist_ok=True)
    marker=work/'owner.json'
    if marker.exists():
        if json.loads(marker.read_text())!={'owner':str(ROOT),'identity':identity}:
            raise RuntimeError('standard-library build ownership mismatch')
    else:
        if any(work.iterdir()):raise RuntimeError('unmarked standard-library build directory')
        marker.write_text(json.dumps(dict(owner=str(ROOT),identity=identity),indent=2)+'\n')
    snapshot=work/'library'
    digest_file=work/'source.json'
    if not snapshot.exists():
        temporary=work/'library-copy'
        if temporary.exists():raise RuntimeError('incomplete standard-library source copy: '+str(temporary))
        shutil.copytree(source,temporary,symlinks=True)
        digest=source_digest(temporary)
        temporary.rename(snapshot)
        digest_file.write_text(json.dumps({'sha256':digest},indent=2)+'\n')
    if not digest_file.exists():raise RuntimeError('standard-library source copy lacks its manifest')
    env=os.environ.copy()
    for name in list(env):
        if name.startswith(('RUST_INTERP_','CARGO_PROFILE_')) or name in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET']:
            env.pop(name,None)
    env['RUSTFLAGS']=FLAGS
    env['CARGO_TERM_COLOR']='never'
    fetch_seconds=0
    if fetch:
        before=time.perf_counter()
        command=['cargo','+'+toolchain,'fetch','--manifest-path',str(snapshot/'Cargo.toml'),'--locked','--target',target]
        with (work/'fetch.log').open('w') as log:
            subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        fetch_seconds=time.perf_counter()-before
    command=['cargo','+'+toolchain,'check','--manifest-path',str(snapshot/'Cargo.toml'),
             '-p','sysroot','--release','--target',target,'--features','backtrace',
             '--locked','--offline','--jobs','4','--target-dir',str(work/'target')]
    before=time.perf_counter()
    with (work/'build.log').open('w') as log:
        process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        (work/'command.json').write_text(json.dumps(dict(pid=process.pid,command=command,flags=FLAGS),indent=2)+'\n')
        code=process.wait()
    if code:
        tail='\n'.join((work/'build.log').read_text().splitlines()[-25:])
        raise RuntimeError('standard-library metadata build failed; log: '+str(work/'build.log')+'\n'+tail)
    build_seconds=time.perf_counter()-before
    lib=work/'sysroot/lib/rustlib'/target/'lib';lib.mkdir(parents=True,exist_ok=True)
    artifacts={}
    for p in sorted((work/'target'/target/'release').rglob('*.rmeta')):
        destination=lib/p.name
        if destination.exists():raise RuntimeError('incomplete metadata publication: '+str(destination))
        shutil.copy2(p,destination)
        destination.chmod(0o444)
        artifacts[str(destination.relative_to(work))]=dict(sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),stamp=stamp(destination))
    for crate in ['core','alloc','std','test','proc_macro']:
        if len(list(lib.glob('lib'+crate+'-*.rmeta')))!=1:
            raise RuntimeError('missing or ambiguous standard-library metadata for '+crate)
    result=dict(owner=str(ROOT),identity=identity,source_sha256=json.loads(digest_file.read_text())['sha256'],
                artifacts=artifacts,setup_seconds=time.perf_counter()-started,
                build_seconds=build_seconds,fetch_seconds=fetch_seconds,
                metadata_bytes=sum((work/p).stat().st_size for p in artifacts))
    temporary=ready.with_suffix('.tmp');temporary.write_text(json.dumps(result,indent=2)+'\n');temporary.rename(ready)
    return work/'sysroot',target,key,result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch',action='store_true',help='download missing pinned dependencies before building')
    args=parser.parse_args()
    toolchain=json.loads((ROOT/'benchmarks/corpus.json').read_text())['toolchain']
    sysroot,target,key,result=checked_std_mir(toolchain,fetch=args.fetch)
    print(json.dumps(dict(sysroot=str(sysroot),target=target,key=key,setup_seconds=result['setup_seconds'],
                         build_seconds=result['build_seconds'],metadata_bytes=result['metadata_bytes']),indent=2))


if __name__=='__main__':main()
