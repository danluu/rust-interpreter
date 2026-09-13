#!/usr/bin/env python3
"""Build current main compiler integration while retaining the qualified VM."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools
from workflow_io import capture, require_space, write_json as write

TARGET = ROOT / '.work/fixed-frame-clear-combined-build-01/target'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--control-build', type=Path, required=True)
    args = parser.parse_args()
    control_path = args.control_build.resolve(strict=True)
    control = json.loads(control_path.read_text())
    assert control['status'] == 'passed'
    CONTROL = control['tool_key']
    assert CONTROL == '8c2d64bb756cbfedaaf84820cae1b1705575a7022326e239b04084f6217d06ae'
    run = args.run_id
    assert re.fullmatch(r'environment-main-build-\d{2}', run)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        from workflow_io import require_space
        require_space(ROOT, 12)
        prior = json.loads((ROOT / '.work/experiments/fixed-frame-clear-combined-build-01/status.json').read_text())
        assert prior['status'] == 'finished' and prior['returncode'] == 0
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=ROOT, text=True).strip()
        source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        files = [ROOT / name for name in ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml', 'scripts/compare_saved_runtime.py', 'scripts/workflow_io.py', 'scripts/interpreter.py']]
        files += [Path(__file__).resolve(), Path(__file__).with_name('PLAN.md'), control_path]
        files += [p for p in (ROOT / 'crates').rglob('*') if p.is_file() and (p.suffix == '.rs' or p.name == 'Cargo.toml')]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in files}
        retained, _ = installed_tools(CONTROL)
        assert json.loads((retained/'ready.json').read_text()) == control['binaries']
        assert all(sha(retained/name) == digest for name,digest in control['binaries'].items())
        inherited = json.loads((retained / 'source.json').read_text())['files']
        publication = ROOT / '.work/publication-main'
        for name in frozen:
            if not name.startswith('crates/'):
                continue
            if name == 'crates/bytecode/src/jit/local_memory_tests.rs':
                # Only the explicit ignored offline observer differs. The
                # publication source preserves the qualified test file exactly.
                assert sha(publication / name) == inherited[name]
                current = (ROOT / name).read_text()
                start = current.index('#[test]\n#[ignore = "Offline emission diagnosis;')
                end = current.index('#[test]\nfn forwarded_copy_fault', start)
                assert current[:start] + current[end:] == (publication / name).read_text()
            else:
                assert (ROOT / name).read_bytes() == (publication / name).read_bytes(), name
            if name.startswith('crates/bytecode/') and name != 'crates/bytecode/src/jit/local_memory_tests.rs':
                if name == 'crates/bytecode/src/prepared.rs':
                    current = (ROOT / name).read_text()
                    current = current.replace('/// preceding invocation failed. Code, immutable analyses and any environment\n/// input snapshot are retained. Environment values are copied into fresh\n/// readonly guest storage on each invocation; later host changes are not seen.',
                        '/// preceding invocation failed. Only code and immutable analyses are retained.')
                    import hashlib
                    assert hashlib.sha256(current.encode()).hexdigest() == inherited[name]
                else:
                    assert frozen[name] == inherited[name], name
        work = ROOT / '.work' / run
        work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), source_commit=source, frozen=frozen,
              source=str(ROOT), target=str(TARGET), control=CONTROL, controller_sha256=sha(Path(__file__))))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
                             'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never', CARGO_INCREMENTAL='0', CARGO_PROFILE_DEV_DEBUG='0',
                   CARGO_PROFILE_TEST_DEBUG='0', CARGO_PROFILE_RELEASE_DEBUG='1')
        records, counts = [], {}
        for label, action, profile in [('test-debug', 'test', []), ('test-release', 'test', ['--release']),
                                       ('build-release', 'build', ['--release'])]:
            require_space(ROOT, 8)
            command = ['cargo', '+nightly-2026-09-08', action, *profile, '--locked', '--offline', '--jobs', '2',
                       '--target-dir', str(TARGET), '-p', 'rust-interp-mir-export']
            if action == 'build':
                command += ['--bins']
            started = time.time()
            child, stdout, stderr = capture(command, cwd=ROOT, env=env,
                receipt_path=work / 'active.json', receipt=dict(label=label))
            for suffix, text in [('stdout', stdout), ('stderr', stderr)]:
                (work / f'{label}.{suffix}').write_text(text)
            records.append(dict(label=label, command=command, pid=child.pid, returncode=child.returncode,
                                started_at=started, finished_at=time.time()))
            write(work / 'commands.json', records)
            assert child.returncode == 0, f'{label} failed'
            if action == 'test':
                matches = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed;', stdout + stderr)
                assert matches and all(int(failed) == 0 for _, failed in matches)
                counts[label] = sum(int(passed) for passed, _ in matches)
                assert counts[label] >= 89, counts
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        assert counts['test-debug'] == counts['test-release']
        binaries = json.loads((retained / 'ready.json').read_text())
        for name in ['rust-interp-mir-export', 'rust-interp-rustc-wrapper']:
            binaries[name] = sha(TARGET / 'release' / name)
        composition = dict(kind='environment-main-compiler', schema_version=1, source_commit=source,
                           vm_source_key=CONTROL, binaries=binaries)
        import hashlib
        key = hashlib.sha256(json.dumps(composition, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        with (ROOT / '.work/interpreter-tools.lock').open('a') as publication:
            acquire_lock(publication, 45)
            installed = ROOT / '.work/interpreter-tools' / key
            installed.mkdir(exist_ok=False)
            for name in binaries:
                shutil.copy2(TARGET / 'release' / name if name != 'rust-interp-vm' else retained / name, installed / name)
            caps = json.loads(subprocess.check_output([str(installed / 'rust-interp-mir-export'), '--rust-interp-capabilities'], env=env, text=True))
            caps.update(tool_key=key, exporter_sha256=binaries['rust-interp-mir-export'])
            write(installed / 'capabilities.json', caps)
            write(installed / 'source.json', dict(tool_key=key, composition=composition, files=frozen,
                  source_commit=source, key_algorithm='SHA256 of canonical composition JSON', source=str(ROOT)))
            write(installed / 'ready.json', binaries)
        out = ROOT / 'results' / run
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', dict(status='passed', source_commit=source, tool_key=key, binaries=binaries,
              composition=composition, tests=counts, commands=records, source_manifest=str((work / 'plan.json').relative_to(ROOT)),
              source_manifest_sha256=sha(work / 'plan.json'), raw=str(work.relative_to(ROOT)), performance_measurement=False))
        print('PASS', counts, key, flush=True)


if __name__ == '__main__':
    main()
