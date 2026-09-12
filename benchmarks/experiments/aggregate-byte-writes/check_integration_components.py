#!/usr/bin/env python3
"""Test normal source rebuilding of every qualified aggregate-layout component."""
import fcntl
import os
from pathlib import Path
import subprocess
import time

from build import ROOT, HERE, read, write, sha, require, installed_tools, environment


def main():
    run = 'aggregate-integration-components-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fs = os.statvfs(ROOT)
        free = fs.f_bavail*fs.f_frsize
        require(free >= 12*1024**3, 'insufficient fresh host-build headroom')
        work = ROOT/'.work'/run
        work.mkdir(exist_ok=False)
        status = dict(status='preflight', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time())
        write(work/'status.json', status)
        try:
            decision_path = ROOT/'results/budget-register-primary-01/summary.json'
            decision = read(decision_path)
            require(decision['status'] == 'passed' and decision['primary_gates_passed'] is False,
                    'budget-register decision incomplete or changed')
            qualified_path = ROOT/'results/aggregate-relocation-heldout-recovery-01/summary.json'
            qualified = read(qualified_path)
            require(qualified['heldout_gates_passed'] and len(qualified['cases']) == 7,
                    'aggregate compiler held-outs incomplete')
            build_path = ROOT/'results/aggregate-relocation-build-01/summary.json'
            build = read(build_path)
            proof = read(ROOT/build['provenance'])
            source = ROOT/proof['source']
            installed, key = installed_tools(build['tool_key'])
            require(key == '9637b0acb1d208524c3c8b446af64cfd5e2d0d3be75e1412a8df76750ce36223', 'qualified source key differs')
            frozen = dict(proof['copied_inputs'])
            evidence = {str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__), HERE/'INTEGRATION-NEXT.md',
                decision_path, qualified_path, build_path, ROOT/build['provenance'],
                source/'rust-toolchain.toml']}

            def verify():
                require(all(sha(source/p) == h for p,h in frozen.items()), 'qualified source changed')
                require(all(sha(installed/n) == h for n,h in build['binaries'].items()), 'installed component changed')
                require(all(sha(ROOT/p) == h for p,h in evidence.items()), 'integration inputs changed')

            verify()
            target = ROOT/'.work/diagnostic-builds'/run
            require(not target.exists(), 'fresh build target already exists')
            command = ['cargo','+nightly-2026-09-08','build','--release','--locked','--offline','--jobs','2',
                '--manifest-path',str(source/'Cargo.toml'),'--target-dir',str(target),
                '-p','rust-interp-bytecode','-p','rust-interp-mir-export']
            write(work/'plan.json', dict(command=command, source=str(source.relative_to(ROOT)),
                source_files=frozen, evidence=evidence, expected_binaries=build['binaries'],
                observed_free_bytes=free, required_free_bytes=12*1024**3,
                production_change=False, installed_tools_unchanged=True))
            with (work/'build.log').open('x') as log:
                child = subprocess.Popen(command, cwd=source, env=environment(), stdin=subprocess.DEVNULL,
                    stdout=log, stderr=subprocess.STDOUT)
                try:
                    status.update(status='running', child_pid=child.pid, command=command,
                        child_cwd=str(source), child_started_at=time.time())
                    write(work/'status.json', status)
                finally:
                    code = child.wait()
            require(code == 0, 'normal source build failed; log preserved')
            verify()
            actual = {name:sha(target/'release'/name) for name in build['binaries']}
            differences = {name:dict(expected=digest, actual=actual[name])
                for name,digest in build['binaries'].items() if actual[name] != digest}
            result = dict(status='passed', component_identity_matches=not differences,
                expected_binaries=build['binaries'], actual_binaries=actual, differences=differences,
                command=command, pid=child.pid, build_log_sha256=sha(work/'build.log'),
                source=str(source.relative_to(ROOT)), source_files=frozen, evidence=evidence,
                production_change=False, installed_tools_unchanged=True, performance_measurement=False,
                next_action='integrate exact source and verify the normal root build' if not differences else
                    'inspect differing components before source integration; do not overwrite qualified binaries')
            out = ROOT/'results'/run
            out.mkdir(exist_ok=False)
            write(out/'summary.json', result)
            status.update(status='finished', returncode=0, component_identity_matches=not differences,
                finished_at=time.time())
            write(work/'status.json', status)
            print(dict(component_identity_matches=not differences, differences=differences), flush=True)
        except BaseException as error:
            status.update(status='failed', error=repr(error), finished_at=time.time())
            write(work/'status.json', status)
            raise


if __name__ == '__main__':
    main()
