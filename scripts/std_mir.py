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


def checked_std_mir(toolchain,fetch=False,lookup='fresh',lookup_stats=None,custom=None,namespace='',cargo=None,policy='v1',prepared_key=None):
    """Install a frozen source snapshot once; validate metadata stamps on reuse."""
    if policy!='v1' or prepared_key is not None:
        from std_mir_source_paths import SELECTION, load
        if policy!=SELECTION or custom is None or cargo is not None or fetch or prepared_key is None:
            raise RuntimeError('std source-paths-v2 requires an explicit custom compiler and prepared key, without fetch/custom Cargo')
        if toolchain!='nightly-2026-09-08':raise RuntimeError('std source-paths-v2 requires the pinned toolchain')
        if lookup not in ['fresh','cached']:raise ValueError('unknown toolchain lookup mode')
        result=load(ROOT,prepared_key,custom,namespace)
        if lookup_stats is not None:lookup_stats.update(mode=lookup,outcome='owned-manifest')
        return result
    if custom is not None:custom.environment(os.environ)
    if cargo is not None:cargo.environment(os.environ,toolchain,custom)
    (ROOT/'.work').mkdir(exist_ok=True)
    with (ROOT/'.work/std-mir.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        return _checked_std_mir_locked(toolchain,fetch,lookup,lookup_stats,custom,namespace,cargo)


def _checked_std_mir_locked(toolchain,fetch,lookup,lookup_stats,custom,namespace,cargo):
    started=time.perf_counter()
    from toolchain_lookup import compiler_identity
    if lookup not in ['fresh','cached']:raise ValueError('unknown toolchain lookup mode')
    if custom is None:
        compiler,original,outcome=compiler_identity(toolchain,ROOT/'.work/toolchain-lookup' if lookup=='cached' else None)
    else:
        # The caller validates the immutable installation before entering here;
        # standalone std setup loads it through the same manifest validator.
        compiler,original,outcome=custom.identity['compiler'],custom.sysroot,'owned-manifest'
    if cargo is not None and custom is None:
        binding=cargo.identity['pinned_compiler']
        if compiler!=binding['compiler'] or original!=Path(binding['sysroot']):
            raise RuntimeError('std MIR compiler differs from selected Cargo compiler')
    if lookup_stats is not None:lookup_stats.update(mode=lookup,outcome=outcome)
    target=next(line.removeprefix('host: ') for line in compiler.splitlines() if line.startswith('host: '))
    source=original/'lib/rustlib/src/rust/library'
    identity=dict(policy=POLICY,compiler=compiler,target=target,flags=FLAGS,
                  lock_sha256=hashlib.sha256((source/'Cargo.lock').read_bytes()).hexdigest())
    if custom is not None:
        identity.update(compiler_key=custom.key,source_sha256=custom.identity['source_sha256'],namespace=namespace)
    if cargo is not None:identity['cargo']=cargo.receipt(custom)
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
    if custom is not None and cargo is None:env=custom.environment(env)
    if cargo is not None:env=cargo.environment(env,toolchain,custom)
    cargo_command=[str(cargo.executable)] if cargo is not None else ['cargo','+'+toolchain]
    fetch_seconds=0
    if fetch:
        before=time.perf_counter()
        command=cargo_command+['fetch','--manifest-path',str(snapshot/'Cargo.toml'),'--locked','--target',target]
        with (work/'fetch.log').open('w') as log:
            subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        fetch_seconds=time.perf_counter()-before
    command=cargo_command+['check','--manifest-path',str(snapshot/'Cargo.toml'),
             '-p','sysroot','--release','--target',target,'--features','backtrace',
             '--locked','--offline','--jobs','4','--target-dir',str(work/'target')]
    before=time.perf_counter()
    with (work/'build.log').open('w') as log:
        process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            receipt=dict(pid=process.pid,command=command,flags=FLAGS)
            if cargo is not None:receipt['cargo']=cargo.receipt(custom)
            (work/'command.json').write_text(json.dumps(receipt,indent=2)+'\n')
        finally:
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
    parser.add_argument('--compiler-key',help='use an owned complete stage2 compiler')
    parser.add_argument('--cargo-key',help='use an owned qualified Cargo executable')
    parser.add_argument('--stable-cgu-partitioning',choices=['off','on'],default='off')
    parser.add_argument('--std-mir-policy',choices=['v1','source-paths-v2'],default='v1')
    parser.add_argument('--std-mir-key',help='preinstalled source-paths-v2 key; prepare separately')
    args=parser.parse_args()
    toolchain=json.loads((ROOT/'benchmarks/corpus.json').read_text())['toolchain']
    if args.stable_cgu_partitioning!='off' and args.compiler_key is None:
        parser.error('--stable-cgu-partitioning=on requires --compiler-key')
    from custom_compiler import load_compiler
    from custom_cargo import load_cargo
    custom=load_compiler(ROOT,args.compiler_key) if args.compiler_key is not None else None
    options={} if custom is None else dict(custom=custom,namespace='stable-cgu:'+args.stable_cgu_partitioning)
    if args.std_mir_policy!='v1' or args.std_mir_key is not None:
        options.update(policy=args.std_mir_policy,prepared_key=args.std_mir_key)
    if args.cargo_key is not None:options['cargo']=load_cargo(ROOT,args.cargo_key)
    sysroot,target,key,result=checked_std_mir(toolchain,fetch=args.fetch,**options)
    print(json.dumps(dict(sysroot=str(sysroot),target=target,key=key,setup_seconds=result['setup_seconds'],
                         build_seconds=result['build_seconds'],metadata_bytes=result['metadata_bytes']),indent=2))


if __name__=='__main__':main()
