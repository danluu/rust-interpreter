"""Run the two retained compiler controls against the exact stock composition."""
import json
import os
from pathlib import Path
import re
import sys

from component import ROOT, require_build
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools, TOOLCHAIN
from std_mir import checked_std_mir
from workflow_io import capture, require_space, write_json as write


def main():
    run = 'guarded-local-facts-main-remapping-01'
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 10)
        build_path = ROOT / 'results/guarded-local-facts-main-build-01/summary.json'
        build = json.loads(build_path.read_text())
        require_build(build)
        tools, key = installed_tools(build['tool_key'])
        assert json.loads((tools / 'ready.json').read_text()) == build['binaries']
        raw = ROOT / build['raw']
        log = (raw / 'test-debug.stderr').read_text()
        executable, = re.findall(r'Running tests/trap_span_remap.rs \(([^\n)]+)\)', log)
        executable = Path(executable).resolve(strict=True)
        target = ROOT / '.work/fixed-frame-clear-combined-build-01/target/debug'
        relative = executable.relative_to(target).as_posix()
        # This pinned Cargo puts integration test executables in the unit's
        # build/hash/out directory. Bind both hash occurrences and the package,
        # using the exact successful test command recorded by our build.
        assert re.fullmatch(r'build/rust-interp-bytecode/([0-9a-f]{16})/out/trap_span_remap-\1', relative)
        caps = json.loads((tools / 'capabilities.json').read_text())
        rustc = Path(caps['compiler_sysroot']) / 'bin/rustc'
        sysroot, _, std_key, _ = checked_std_mir(TOOLCHAIN)
        assert std_key == 'bd27cc0f910e0c93a9a6cf088789ef526d36a8697a7717e08d7585f5d19467ef'
        work = ROOT / '.work' / run
        work.mkdir(exist_ok=False)
        paths = [Path(__file__), Path(__file__).with_name('component.py'),
                 Path(__file__).with_name('PLAN.md'), build_path, executable,
                 raw / 'test-debug.stderr', tools / 'capabilities.json']
        paths += [tools / name for name in build['binaries']]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        command = [str(executable), '--ignored', '--test-threads=1', '--nocapture']
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_'))
               and k not in ['RUSTFLAGS', 'RUSTC', 'RUSTDOC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(RUST_INTERP_TEST_ARTIFACT_DIR=str(work),
                   RUST_INTERP_TEST_EXPORTER=str(tools / 'rust-interp-mir-export'),
                   RUST_INTERP_TEST_VM=str(tools / 'rust-interp-vm'), RUST_INTERP_TEST_RUSTC=str(rustc),
                   RUST_INTERP_TEST_STD_SYSROOT=str(sysroot),
                   RUST_INTERP_TEST_BACKEND_JOBS_FLAG='-Ccodegen-units=2')
        write(work / 'plan.json', dict(owner=str(ROOT), tool_key=key, frozen=frozen,
            command=command, std_key=std_key, rustc=str(rustc), rustc_sha256=sha(rustc),
            expected_tests=2, expected_internal_commands=130, performance_measurement=False,
            backend_jobs_flag=env['RUST_INTERP_TEST_BACKEND_JOBS_FLAG']))
        require_space(ROOT, 8)
        child, out, err = capture(command, cwd=ROOT, env=env,
            receipt_path=work / 'active.json', receipt=dict(stage='ignored remapping controls'))
        (work / 'stdout').write_text(out); (work / 'stderr').write_text(err)
        write(work / 'record.json', dict(command=command, pid=child.pid, returncode=child.returncode,
            stdout_sha256=sha(work / 'stdout'), stderr_sha256=sha(work / 'stderr')))
        assert child.returncode == 0, (out + err)[-4000:]
        assert 'test result: ok. 2 passed; 0 failed; 0 ignored;' in out
        receipts = sorted(work.glob('trap-*/command-*/receipt.json'))
        assert len(receipts) == 130
        assert all('finished_at' in json.loads(p.read_text()) for p in receipts)
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        require_build(build)
        inventory = {str(p.relative_to(work)): sha(p) for p in work.rglob('*') if p.is_file()}
        write(work / 'artifacts.json', inventory)
        destination = ROOT / 'results' / run
        destination.mkdir(exist_ok=False)
        write(destination / 'summary.json', dict(status='passed', tool_key=key, tests=2,
            internal_commands=130, harness_commands=1, performance_measurement=False,
            raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'),
            record_sha256=sha(work / 'record.json'), artifacts_sha256=sha(work / 'artifacts.json')))
        print('PASS: two remapping controls and130 retained child commands', flush=True)


if __name__ == '__main__': main()
