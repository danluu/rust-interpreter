#!/usr/bin/env python3
"""Qualify the integrated compiler from the ordinary root workspace."""
import fcntl
import os
from pathlib import Path
import re
import subprocess
import time

from build import ROOT, read, write, sha, require, environment, installed_tools
from tool_source_index import index


def main():
    run = 'aggregate-integration-root-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fs = os.statvfs(ROOT)
        require(fs.f_bavail*fs.f_frsize >= 12*1024**3, 'insufficient workspace-check headroom')
        work = ROOT/'.work'/run
        work.mkdir(exist_ok=False)
        status = dict(status='preflight', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time())
        write(work/'status.json', status)
        try:
            integrated = index('HEAD')
            key = '9637b0acb1d208524c3c8b446af64cfd5e2d0d3be75e1412a8df76750ce36223'
            require(integrated['tool_key'] == key, 'committed compiler source differs')
            component_path = ROOT/'results/aggregate-integration-components-01/summary.json'
            component = read(component_path)
            require(component['component_identity_matches'], 'ordinary component reconstruction incomplete')
            expected = component['expected_binaries']
            installed, _ = installed_tools(key)
            paths = [Path(__file__), component_path, ROOT/'rust-toolchain.toml']
            paths += sorted((ROOT/'crates').rglob('*.rs')) + sorted((ROOT/'crates').rglob('Cargo.toml'))
            frozen = {**integrated['files'], **{str(p.relative_to(ROOT)):sha(p) for p in paths}}

            def verify():
                require(all(sha(ROOT/p) == h for p,h in frozen.items()), 'workspace source changed')
                require(all(sha(installed/n) == h for n,h in expected.items()), 'qualified installed component changed')

            verify()
            target = ROOT/'.work/diagnostic-builds'/run
            require(not target.exists(), 'fresh workspace target already exists')
            write(work/'plan.json', dict(source_commit=integrated['commit'], tool_key=key, frozen=frozen,
                expected_binaries=expected, normal_root_workspace=True, installed_tools_unchanged=True))
            records, tests = [], {}
            for label, action, flags in [('debug','test',['--workspace']),
                    ('release','test',['--workspace','--release']),
                    ('components','build',['--release','-p','rust-interp-bytecode','-p','rust-interp-mir-export'])]:
                verify()
                fs = os.statvfs(ROOT)
                require(fs.f_bavail*fs.f_frsize >= 8*1024**3, 'pre-command eight-GiB floor rejected')
                command = ['cargo','+nightly-2026-09-08',action,'--locked','--offline','--jobs','2',
                    '--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target),*flags]
                with (work/(label+'.log')).open('x') as log:
                    child = subprocess.Popen(command,cwd=ROOT,env=environment(),stdin=subprocess.DEVNULL,
                        stdout=log,stderr=subprocess.STDOUT)
                    try:
                        status.update(status='running',child_pid=child.pid,command=command,child_started_at=time.time())
                        write(work/'status.json',status)
                    finally:
                        code = child.wait()
                records.append(dict(label=label,command=command,pid=child.pid,returncode=code,
                    log_sha256=sha(work/(label+'.log'))))
                write(work/'commands.json',records)
                require(code == 0, 'root workspace '+label+' failed')
                if action == 'test':
                    counts = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',
                                        (work/(label+'.log')).read_text())
                    require(counts and all(f == '0' for _,f,_ in counts), 'test result missing')
                    tests[label] = dict(passed=sum(int(n) for n,_,_ in counts), ignored=sum(int(n) for _,_,n in counts))
                    require(tests[label] == dict(passed=289,ignored=1), 'integrated workspace coverage differs')
            verify()
            actual = {name:sha(target/'release'/name) for name in expected}
            result = dict(status='passed', component_identity_matches=actual == expected, tests=tests,
                expected_binaries=expected, actual_binaries=actual, tool_key=key,
                source_commit=integrated['commit'], frozen=frozen, commands=records,
                normal_root_workspace=True, installed_tools_unchanged=True, performance_measurement=False,
                note='Source integration is qualified only if all three root-built components match the measured tool.')
            out = ROOT/'results'/run
            out.mkdir(exist_ok=False)
            write(out/'summary.json',result)
            status.update(status='finished',returncode=0,component_identity_matches=actual == expected,finished_at=time.time())
            write(work/'status.json',status)
            print(dict(component_identity_matches=actual == expected,tests=tests),flush=True)
        except BaseException as error:
            status.update(status='failed',error=repr(error),finished_at=time.time())
            write(work/'status.json',status)
            raise


if __name__ == '__main__':
    main()
