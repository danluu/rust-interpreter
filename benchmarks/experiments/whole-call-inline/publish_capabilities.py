#!/usr/bin/env python3
"""Probe and bind capabilities after the historical isolated component builder."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import time
from build import ROOT, CONTROL, read, write, sha, require, installed_tools


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--build-run',required=True)
    args=parser.parse_args()
    require(re.fullmatch(r'whole-call-capabilities-[0-9]{2}',args.run_id) and
        re.fullmatch(r'whole-call-build-[0-9]{2}',args.build_run),'unexpected publication ID')
    with (ROOT/'.work/benchmark.lock').open('a') as lock, (ROOT/'.work/interpreter-tools.lock').open('a') as publication:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        fcntl.flock(publication,fcntl.LOCK_EX|fcntl.LOCK_NB)
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
        out=ROOT/'results'/args.run_id;out.mkdir(exist_ok=False)
        status=dict(status='preflight',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time())
        write(work/'status.json',status)
        try:
            build_path=ROOT/'results'/args.build_run/'summary.json';build=read(build_path)
            require(build['status']=='passed' and build['control_tool_key']==CONTROL and
                build['tests']['debug']==build['tests']['release'] and build['tests']['debug']['passed']==300,
                'unqualified build')
            require(read(ROOT/'.work/experiments'/args.build_run/'status.json')['returncode']==0,'build still active')
            directory,key=installed_tools(build['tool_key'])
            require(all(sha(directory/n)==h for n,h in build['binaries'].items()),'binary changed')
            stable=[directory/n for n in build['binaries']]+[directory/'ready.json',directory/'source.json',build_path]
            frozen={str(p.relative_to(ROOT)):sha(p) for p in stable+[Path(__file__)]}
            before=(directory/'capabilities.json').read_bytes()
            (out/'before.json').write_bytes(before)
            command=[str(directory/'rust-interp-mir-export'),'--rust-interp-capabilities']
            with (work/'probe.json').open('x') as stdout,(work/'probe.stderr').open('x') as stderr:
                child=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
                try:
                    status.update(status='probing',child_pid=child.pid,command=command,child_started_at=time.time())
                    write(work/'status.json',status)
                finally: code=child.wait()
            require(code==0,'capability probe failed')
            capability=read(work/'probe.json')
            require(capability=={k:v for k,v in read(out/'before.json').items() if k not in ['tool_key','exporter_sha256']},
                'capability semantics changed unexpectedly')
            capability.update(tool_key=key,exporter_sha256=build['binaries']['rust-interp-mir-export'])
            require(all(sha(ROOT/p)==h for p,h in frozen.items()),'publication inputs changed')
            require((directory/'capabilities.json').read_bytes()==before,'capability changed concurrently')
            write(directory/'capabilities.json',capability)
            write(out/'after.json',capability)
            # Exercise the same exact-hash guard used by the ordinary launcher.
            from interpreter import require_export_option
            for option in capability['export_options']: require_export_option(directory,key,option)
            require(all(sha(ROOT/p)==h for p,h in frozen.items()),'publication changed stable files')
            result=dict(status='passed',tool_key=key,build_report=str(build_path.relative_to(ROOT)),
                frozen=frozen,command=command,probe_pid=child.pid,probe_returncode=code,
                probe_sha256=sha(work/'probe.json'),probe_stderr_sha256=sha(work/'probe.stderr'),
                before_sha256=sha(out/'before.json'),after_sha256=sha(out/'after.json'),
                installed_capabilities=str((directory/'capabilities.json').relative_to(ROOT)),
                installed_capabilities_sha256=sha(directory/'capabilities.json'),binaries_unchanged=True,
                export_options_verified=capability['export_options'])
            write(out/'summary.json',result)
            status.update(status='finished',returncode=0,finished_at=time.time());write(work/'status.json',status)
            print(json.dumps(result),flush=True)
        except BaseException as error:
            status.update(status='failed',error=repr(error),finished_at=time.time());write(work/'status.json',status)
            raise


if __name__=='__main__':main()
