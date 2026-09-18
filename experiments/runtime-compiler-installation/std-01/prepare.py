#!/usr/bin/env python3
"""Run the reviewed ordinary std CLI with owned process/capacity supervision."""
import argparse,hashlib,importlib.util,json,os
from pathlib import Path
import sys,time

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
PLAN=HERE/'plan.json'
FROZEN=HERE/'inputs.json'
WORK=ROOT/'.work/runtime-std-preparation-supervision-01'


def require(ok,message):
    if not ok:raise RuntimeError(message)


def sha(path):
    path=Path(path)
    require(path.resolve(strict=True)==path and path.is_file() and not path.is_symlink(),'indirect source/proof input')
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def read(path):return json.loads(Path(path).read_bytes())


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--frozen-sha',required=True);args=parser.parse_args()
    require(Path.cwd()==ROOT and sys.dont_write_bytecode and sys.flags.optimize==0,'fixed owner and unoptimized Python -B required')
    require(sha(FROZEN)==args.frozen_sha,'std source freeze differs');frozen=read(FROZEN);plan=read(PLAN)
    require(plan['owner']==str(ROOT) and plan['work']==str(WORK) and dict(os.environ)==plan['environment'],'std launch owner/environment differs')
    def sources():
        require(sha(FROZEN)==args.frozen_sha,'std source freeze changed')
        for path,digest in frozen['files'].items():require(sha(path)==digest,'std source/proof changed: '+path)
        require(str(Path(sys.executable).resolve())==frozen['python']['resolved']
                and sha(Path(sys.executable).resolve())==frozen['python']['sha256'],'std Python differs')
    sources()
    owned_path=ROOT/'experiments/stable-cgu/owned_stage.py'
    spec=importlib.util.spec_from_file_location('runtime_std_owned',owned_path);owned=importlib.util.module_from_spec(spec);sys.modules[spec.name]=owned;spec.loader.exec_module(owned)
    sys.path.insert(0,str(ROOT/'scripts'))
    import runtime_compiler as runtime
    import std_mir_source_paths as std
    from custom_cargo_libraries import platform_identity
    from toolchain_lookup import _stamp
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename and filename.startswith('/Users/danluu/dev/rust-interp'):
            require(str(Path(filename).resolve()) in frozen['files'],'unfrozen std import: '+filename)
    compiler=runtime.load_runtime_compiler(ROOT,plan['runtime_key'])
    def state():
        require(platform_identity()==plan['platform'],'std host platform changed')
        require(Path(plan['environment']['DEVELOPER_DIR']).resolve(strict=True)==Path(plan['environment']['DEVELOPER_DIR']),'indirect selected developer directory')
        require(std.configuration(ROOT,os.environ)==plan['configuration'],'std Cargo configuration changed')
        for path,row in plan['executors'].items():
            require(_stamp(Path(path))==row['stamp'] and sha(Path(path).resolve())==row['sha256'],'std executor changed: '+path)
            require((os.readlink(path) if Path(path).is_symlink() else None)==row['link_text'],'std executor route changed: '+path)
        compiler.revalidate(ROOT)
    state();require(not Path(plan['run_work']).exists() and not Path(plan['run_work']).is_symlink(),'std CLI output must be fresh')
    WORK.mkdir(parents=True,exist_ok=False)
    record=dict(schema_version=1,status='starting',owner=str(ROOT),pid=os.getpid(),parent_pid=os.getppid(),
        started_at=time.time(),frozen_sha256=args.frozen_sha,plan_sha256=sha(PLAN),runtime_key=compiler.key,
        command=plan['command'],environment=plan['environment'],application_qualified=False,benchmark=False)
    def save():owned.write(WORK/'receipt.json',record)
    save()
    try:
        # The CLI itself acquires canonical + std locks. Do not hold another
        # canonical descriptor while waiting for that child: it would deadlock.
        record.update(status='running',free_bytes_before=owned.disk(ROOT,16));save()
        inputs=WORK/'inputs';inputs.mkdir()
        total=0
        for path,digest in frozen['files'].items():
            owned.disk(ROOT,8);require(Path(path).stat().st_size<=32*2**20,'oversized retained std input')
            payload=Path(path).read_bytes();total+=len(payload)
            require(total<=64*2**20 and hashlib.sha256(payload).hexdigest()==digest,'std retained input differs')
            target=inputs/path.lstrip('/');target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as output:output.write(payload)
            require(target.stat().st_nlink==1 and sha(target)==digest,'std retained input readback differs')
        sources();state();owned.disk(ROOT,16)
        try:
            child=owned.run(plan['command'],cwd=ROOT,env=plan['environment'],out=WORK/'command',capacity_root=ROOT)
        finally:
            if (WORK/'command/receipt.json').exists():
                record['child']=dict(path=str(WORK/'command/receipt.json'),sha256=sha(WORK/'command/receipt.json'));save()
        sources();state()
        result=read(Path(plan['run_work'])/'result.json')
        require(result['status']=='passed' and result['commands']==7,'ordinary std preparation did not pass all seven children')
        rows=read(Path(plan['run_work'])/'commands.json')
        require([row['label'] for row in rows]==['cargo-location','cargo-version','cargo-library-1','cargo-library-2','probe-native','metadata','probe-prepared'],'std child recipe differs')
        require([row['returncode'] for row in rows]==[0,0,0,0,1,0,1],'std child return codes differ')
        sysroot,host,key,ready=std.load(ROOT,result['key'],compiler,plan['namespace'],rehash=True)
        require(ready['identity']['cargo']['libraries']['libraries']==[]
                and ready['identity']['cargo']['executable']==plan['cargo_executable']
                and ready['identity']['cargo']['sha256']==plan['executors'][plan['cargo_executable']]['sha256']
                and ready['identity']['cargo']['libraries']['platform']==plan['platform'],'std Cargo closure differs')
        record.update(status='passed',finished_at=time.time(),std_key=key,sysroot=str(sysroot),target=host,
            result=dict(path=str(Path(plan['run_work'])/'result.json'),sha256=sha(Path(plan['run_work'])/'result.json')),
            ready=dict(path=str(sysroot.parent/'ready.json'),sha256=sha(sysroot.parent/'ready.json')),
            inner_children=7,retained_input_bytes=total,free_bytes_after=owned.disk(ROOT,8),full_presentation_qualified=False)
        save()
    except BaseException as error:
        record.update(status='failed',finished_at=time.time(),error=repr(error));save();raise


if __name__=='__main__':main()
