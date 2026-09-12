#!/usr/bin/env python3
"""Build the isolated guarded Call VM with the exact integrated compiler/wrapper."""
import argparse
import fcntl
import hashlib
import io
from pathlib import Path
import os
import re
import shutil
import subprocess
import tarfile
import time

import sys
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT/'benchmarks/experiments/aggregate-byte-writes'))
from build_relocation import read, write, sha, require, installed_tools, environment
from tool_source_index import index
from inject import inject

CONTROL = '9637b0acb1d208524c3c8b446af64cfd5e2d0d3be75e1412a8df76750ce36223'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(re.fullmatch(r'call-slot-build-[0-9]{2}', args.run_id), 'unexpected build ID')
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fs = os.statvfs(ROOT)
        free = fs.f_bavail * fs.f_frsize
        # Prior debug cache was 782 MB unique and release about 95 MB on disk.
        # Four GiB of build allowance above the unchanged eight-GiB floor.
        require(free >= 12*1024**3, 'insufficient isolated host-build headroom')
        work = ROOT/'.work'/args.run_id
        work.mkdir(exist_ok=False)
        status = dict(status='preflight', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time())
        write(work/'status.json', status)
        try:
            parent = index('5b2330c')
            require(parent['tool_key'] == CONTROL and
                    all(sha(ROOT/p) == h for p,h in parent['files'].items()), 'retained VM source changed')
            qualified = ROOT/'results/aggregate-relocation-heldout-recovery-01/summary.json'
            q = read(qualified)
            require(q['heldout_gates_passed'] and len(q['cases']) == 7 and
                    all(sha(ROOT/p) == h for p,h in q['evidence'].items()), 'compiler qualification changed')
            control_report = ROOT/'results/aggregate-integration-root-01/summary.json'
            control = read(control_report)
            tools, key = installed_tools(CONTROL)
            require(key == control['tool_key'] == CONTROL and
                    all(sha(tools/name) == h for name,h in control['actual_binaries'].items()), 'control binary changed')
            recipes = [p for p in HERE.iterdir() if p.is_file()]
            recipes += [ROOT/'benchmarks/experiments/call-slot-census/FAST-PATH-NEXT.md',
                        ROOT/'results/call-slot-census-02/summary.json', qualified, control_report]
            frozen = {**parent['files'], **{str(p.relative_to(ROOT)):sha(p) for p in recipes}}
            source = work/'tool-source'
            source.mkdir()
            payload = subprocess.check_output(['git','archive',parent['commit'],
                'Cargo.toml','Cargo.lock','rust-toolchain.toml','crates','scripts/interpreter.py'], cwd=ROOT)
            with tarfile.open(fileobj=io.BytesIO(payload)) as archive:
                for member in archive:
                    path = Path(member.name)
                    require(not path.is_absolute() and '..' not in path.parts, 'invalid source archive path')
                    if member.isfile():
                        destination = source/path
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        destination.write_bytes(archive.extractfile(member).read())
                    else:
                        require(member.isdir(), 'unexpected source archive entry')
            require(all(sha(source/p) == h for p,h in parent['files'].items()),
                    'archived integrated compiler source differs')
            inject(source)
            inputs = [source/'Cargo.toml', source/'Cargo.lock']
            for crate in ['bytecode','mir-export']:
                inputs += sorted((source/'crates'/crate).rglob('*.rs'))
                inputs.append(source/'crates'/crate/'Cargo.toml')
            fingerprint = hashlib.sha256()
            for path in inputs:
                fingerprint.update(str(path.relative_to(source)).encode()+b'\0'+path.read_bytes())
            key = fingerprint.hexdigest()
            copied = {str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file()}
            provenance = dict(parent_source_commit=parent['commit'], control_tool_key=CONTROL,
                source=str(source.relative_to(ROOT)), source_archive_sha256=hashlib.sha256(payload).hexdigest(),
                root_frozen=frozen, copied_inputs=copied, tool_key=key, observed_free_bytes=free,
                required_free_bytes=12*1024**3, exporter_and_wrapper_copied_from_control=True,
                experimental_call_slot_guards=True, production_change=False)
            write(work/'provenance.json', provenance)

            def verify():
                require(all(sha(ROOT/p)==h for p,h in frozen.items()), 'frozen root input changed')
                require(all(sha(source/p)==h for p,h in copied.items()), 'isolated source changed')
                require(all(sha(tools/n)==h for n,h in control['actual_binaries'].items()), 'immutable control changed')

            records, test_reports = [], {}
            target = ROOT/'.work/diagnostic-builds'/args.run_id
            env = environment()
            for label, action, flags in [('debug','test',['--workspace']),
                    ('release','test',['--workspace','--release']),
                    ('vm','build',['--release','-p','rust-interp-bytecode','--bin','rust-interp-vm'])]:
                verify()
                fs = os.statvfs(ROOT)
                require(fs.f_bavail*fs.f_frsize >= 8*1024**3, 'pre-command eight-GiB floor rejected')
                command = ['cargo','+nightly-2026-09-08',action,'--locked','--offline','--jobs','2',
                    '--manifest-path',str(source/'Cargo.toml'),'--target-dir',str(target),*flags]
                with (work/(label+'.log')).open('x') as log:
                    child = subprocess.Popen(command,cwd=source,env=env,stdin=subprocess.DEVNULL,
                        stdout=log,stderr=subprocess.STDOUT)
                    try:
                        status.update(status='running', child_pid=child.pid, command=command,
                            child_cwd=str(source),child_started_at=time.time())
                        write(work/'status.json',status)
                    finally:
                        code = child.wait()
                records.append(dict(label=label,command=command,pid=child.pid,returncode=code,
                    log_sha256=sha(work/(label+'.log'))))
                write(work/'commands.json',records)
                require(code==0, label+' host qualification failed')
                if action == 'test':
                    text = (work/(label+'.log')).read_text()
                    counts = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',text)
                    names = sorted(re.findall(r'^test (\S*(?:call_slots::tests::|slot_arguments::)\S+) \.\.\. ok$',text,re.M))
                    require(len(names)==len(set(names))==8 and counts and all(f=='0' for _,f,_ in counts), 'focused tests incomplete')
                    test_reports[label] = dict(passed=sum(int(n) for n,_,_ in counts),
                        ignored=sum(int(n) for _,_,n in counts), call_slot_tests=names)
            verify()
            require(test_reports['debug']==test_reports['release'] and test_reports['debug']['passed'] == 297 and test_reports['debug']['ignored'] == 1, 'debug/release coverage differs')
            destination = ROOT/'.work/interpreter-tools'/key
            binaries = dict(control['actual_binaries'])
            binaries['rust-interp-vm'] = sha(target/'release/rust-interp-vm')
            with (ROOT/'.work/interpreter-tools.lock').open('a') as publication:
                fcntl.flock(publication,fcntl.LOCK_EX)
                destination.mkdir(exist_ok=False)
                for name in binaries:
                    shutil.copy2(target/'release'/name if name=='rust-interp-vm' else tools/name, destination/name)
                capability = read(tools/'capabilities.json')
                capability['tool_key'] = key
                write(destination/'capabilities.json',capability)
                write(destination/'source.json',dict(tool_key=key,source=str(source.relative_to(ROOT)),
                    files=copied,provenance_sha256=sha(work/'provenance.json'),experimental_call_slot_guards=True,
                    exporter_and_wrapper_copied_from_control=True,control_tool_key=CONTROL))
                require(all(sha(destination/n)==h for n,h in binaries.items()), 'published binary differs')
                write(destination/'ready.json',binaries)
            result = dict(status='passed',tool_key=key,control_tool_key=CONTROL,binaries=binaries,
                tests=test_reports,source=str(source.relative_to(ROOT)),
                provenance=str((work/'provenance.json').relative_to(ROOT)),provenance_sha256=sha(work/'provenance.json'),
                commands=records,experimental_call_slot_guards=True,production_change=False,performance_measurement=False)
            out = ROOT/'results'/args.run_id
            out.mkdir(exist_ok=False)
            write(out/'summary.json',result)
            status.update(status='finished',returncode=0,finished_at=time.time())
            write(work/'status.json',status)
            print(dict(tool_key=key,tests=test_reports))
        except BaseException as error:
            status.update(status='failed',error=repr(error),finished_at=time.time())
            write(work/'status.json',status)
            raise


if __name__ == '__main__':
    main()
