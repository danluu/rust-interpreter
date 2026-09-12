#!/usr/bin/env python3
"""Build an isolated scalar-boundary observer while retaining all current VM/wrapper bytes."""
import argparse
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from interpreter import installed_tools
from tool_source_index import index
from verify_repeated_workflow import require

PARENT = '9637b0acb1d208524c3c8b446af64cfd5e2d0d3be75e1412a8df76750ce36223'
CONTROL = PARENT


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text())
def write(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n'); temp.replace(path)
def environment():
    env = os.environ.copy()
    for name in list(env):
        if name.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_')) or name in [
            'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
            'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET']:
            env.pop(name)
    env['CARGO_TERM_COLOR'] = 'never'
    return env
def replace(path, old, new):
    text = path.read_text(); require(text.count(old) == 1, 'injection anchor changed: ' + old[:100])
    path.write_text(text.replace(old, new))


from inject import inject


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(re.fullmatch(r'scalar-boundary-build-[0-9]{2}', args.run_id), 'invalid run ID')
    work = ROOT / '.work' / args.run_id; work.mkdir(exist_ok=False)
    status = dict(status='preflight', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time())
    write(work / 'status.json', status)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            parent = index('5b2330c'); require(parent['tool_key'] == PARENT, 'parent source key differs')
            compiler = subprocess.check_output(['rustc','+nightly-2026-09-08','-vV'],text=True)
            require('commit-hash: cea272fa356e94bd2ee2cadf376630aa0683867a' in compiler, 'compiler pin differs')
            installed, _ = installed_tools(PARENT)
            require(all(sha(ROOT / p) == h for p,h in parent['files'].items()), 'production compiler changed')
            fs = os.statvfs(ROOT); free = fs.f_bavail * fs.f_frsize
            require(free >= 12 * 1024**3, 'insufficient build/export headroom')
            paths = [HERE / n for n in ['build.py', 'inject.py', 'observe.rs', 'tests.rs', 'PLAN.md']]
            paths += [ROOT/'scripts/tool_source_index.py', ROOT/'scripts/interpreter.py',
                      ROOT/'scripts/verify_repeated_workflow.py', ROOT/'rust-toolchain.toml']
            frozen = {**parent['files'], **{str(p.relative_to(ROOT)):sha(p) for p in paths}}
            source = work / 'tool-source'; source.mkdir()
            data = subprocess.check_output(['git','archive',parent['commit'],'Cargo.toml','Cargo.lock','rust-toolchain.toml','crates','scripts/interpreter.py'],cwd=ROOT)
            with tarfile.open(fileobj=io.BytesIO(data)) as archive:
                for member in archive:
                    path=Path(member.name); require(not path.is_absolute() and '..' not in path.parts,'invalid archive path')
                    if member.isfile():
                        out=source/path;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(archive.extractfile(member).read())
                    else: require(member.isdir(),'unexpected archive entry')
            inject(source)
            inputs=[source/'Cargo.toml',source/'Cargo.lock']
            for crate in ['bytecode','mir-export']:
                inputs += sorted((source/'crates'/crate).rglob('*.rs'))
                inputs.append(source/'crates'/crate/'Cargo.toml')
            digest=hashlib.sha256()
            for path in inputs: digest.update(str(path.relative_to(source)).encode()+b'\0'+path.read_bytes())
            key=digest.hexdigest(); copied={str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file()}
            write(work/'provenance.json',dict(parent_source_commit=parent['commit'],parent_tool_key=PARENT,
                source=str(source.relative_to(ROOT)),copied_inputs=copied,root_frozen=frozen,tool_key=key,
                compiler=compiler,source_archive_sha256=hashlib.sha256(data).hexdigest(),
                observed_free_bytes=free,required_free_bytes=12*1024**3,diagnostic_only=True,vm_and_wrapper_copied_from_parent=True))
            def verify():
                require(all(sha(ROOT/p)==h for p,h in frozen.items()),'root input changed')
                require(all(sha(source/p)==h for p,h in copied.items()),'diagnostic input changed')
                require(all(sha(installed/p)==h for p,h in parent['binaries'].items()),'parent binaries changed')
            target=ROOT/'.work/diagnostic-builds'/args.run_id
            records=[];env=environment()
            for action in ['test','build']:
                verify()
                fs=os.statvfs(ROOT);require(fs.f_bavail*fs.f_frsize >= 8*1024**3,'host build space floor')
                command=['cargo','+nightly-2026-09-08',action,'--release','--locked','--offline','--jobs','2',
                    '--manifest-path',str(source/'Cargo.toml'),'--target-dir',str(target),'-p','rust-interp-mir-export']
                with (work/(action+'.log')).open('x') as log:
                    child=subprocess.Popen(command,cwd=source,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
                    status.update(status='running',child_pid=child.pid,command=command,child_cwd=str(source),child_started_at=time.time(),child_identity=subprocess.check_output(['ps','-p',str(child.pid),'-o','pid,ppid,lstart,tty,command'],text=True))
                    write(work/'status.json',status);code=child.wait()
                records.append(dict(command=command,pid=child.pid,returncode=code,log_sha256=sha(work/(action+'.log'))))
                write(work/'commands.json',records);require(code==0,'diagnostic '+action+' failed')
            tests=(work/'test.log').read_text()
            names=re.findall(r'^test (\S*boundary::tests::\S+) \.\.\. ok$',tests,re.M)
            require(len(names)==6 and len(set(names))==6,'missing observer tests')
            counts=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed;',tests)
            require(counts and all(f=='0' for _,f in counts),'exporter tests incomplete')
            verify()
            destination=ROOT/'.work/interpreter-tools'/key
            binaries=dict(parent['binaries']);binaries['rust-interp-mir-export']=sha(target/'release/rust-interp-mir-export')
            with (ROOT/'.work/interpreter-tools.lock').open('a') as publication:
                fcntl.flock(publication,fcntl.LOCK_EX);destination.mkdir(exist_ok=False)
                for name in binaries:
                    shutil.copy2(target/'release'/name if name=='rust-interp-mir-export' else installed/name,destination/name)
                capability=json.loads(subprocess.check_output([str(destination/'rust-interp-mir-export'),'--rust-interp-capabilities'],env=env,text=True))
                capability.update(tool_key=key,exporter_sha256=binaries['rust-interp-mir-export'])
                write(destination/'capabilities.json',capability)
                write(destination/'source.json',dict(tool_key=key,parent_tool_key=PARENT,source=str(source.relative_to(ROOT)),
                    files=copied,provenance_sha256=sha(work/'provenance.json'),diagnostic_only=True))
                require(all(sha(destination/n)==h for n,h in binaries.items()),'published binary differs')
                write(destination/'ready.json',binaries)
            result=dict(status='passed',tool_key=key,parent_tool_key=PARENT,binaries=binaries,observer_tests=names,
                exporter_test_count=sum(int(n) for n,_ in counts),source=str(source.relative_to(ROOT)),
                provenance=str((work/'provenance.json').relative_to(ROOT)),provenance_sha256=sha(work/'provenance.json'),
                production_change=False,performance_measurement=False,commands=records)
            write(work/'summary.json',result)
            out=ROOT/'results'/args.run_id;out.mkdir(exist_ok=False);write(out/'summary.json',result)
            status.update(status='finished',finished_at=time.time(),returncode=0);write(work/'status.json',status)
            print(json.dumps(dict(tool_key=key,observer_tests=len(names),exporter_tests=result['exporter_test_count'])))
        except BaseException as error:
            status.update(status='failed',error=repr(error),finished_at=time.time());write(work/'status.json',status);raise


if __name__=='__main__':main()
