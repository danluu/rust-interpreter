#!/usr/bin/env python3
"""Qualify a committed runtime candidate while preserving exporter/wrapper bytes."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools
from workflow_io import capture, require_space, write_json as write

CONTROL = '9ae791980111702fbe88b04e5fff74d6816218fba433701ab54b370447f9337b'
TARGET = ROOT / '.work/fixed-frame-clear-combined-build-01/target'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--expected-tests', type=int, required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'jit-remat-build-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        prior = json.loads((ROOT / '.work/experiments/fixed-frame-clear-combined-build-01/status.json').read_text())
        assert prior['status'] == 'finished' and prior['returncode'] == 0
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=ROOT).strip()
        source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        paths = [ROOT / n for n in ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml']]
        paths += [p for p in (ROOT / 'crates').rglob('*') if p.is_file() and (p.suffix == '.rs' or p.name == 'Cargo.toml')]
        paths += [Path(__file__).resolve(), Path(__file__).with_name('PLAN.md').resolve()]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        retained, _ = installed_tools(CONTROL)
        work = ROOT / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(source_commit=source, frozen=frozen, target=str(TARGET), control=CONTROL,
            expected_tests=args.expected_tests, jobs=2, minimum_free_gib=8, performance_measurement=False))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
                             'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET']}
        env.update(CARGO_TERM_COLOR='never', CARGO_INCREMENTAL='0', CARGO_PROFILE_DEV_DEBUG='0',
                   CARGO_PROFILE_TEST_DEBUG='0', CARGO_PROFILE_RELEASE_DEBUG='1')
        records, counts = [], {}
        for label, action, profile in [('test-debug', 'test', []), ('test-release', 'test', ['--release']),
                                       ('build-release', 'build', ['--release'])]:
            require_space(ROOT, 8)
            command = ['cargo', '+nightly-2026-09-08', action, *profile, '--locked', '--offline', '--jobs', '2',
                       '--target-dir', str(TARGET)]
            command += ['--workspace'] if action == 'test' else ['-p', 'rust-interp-bytecode', '--bin', 'rust-interp-vm']
            child, stdout, stderr = capture(command, cwd=ROOT, env=env,
                receipt_path=work / 'active.json', receipt=dict(label=label))
            for suffix, content in [('stdout', stdout), ('stderr', stderr)]:
                (work / f'{label}.{suffix}').write_text(content)
            records.append(dict(label=label, command=command, pid=child.pid, returncode=child.returncode))
            write(work / 'commands.json', records)
            assert child.returncode == 0, f'{label} failed'
            if action == 'test':
                matches = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;', stdout + stderr)
                assert matches and all(int(failed) == 0 for _, failed, _ in matches)
                counts[label] = dict(passed=sum(int(passed) for passed, _, _ in matches),
                                     ignored=sum(int(ignored) for _, _, ignored in matches))
                assert counts[label] == dict(passed=args.expected_tests, ignored=1), counts
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        binaries = json.loads((retained / 'ready.json').read_text())
        binaries['rust-interp-vm'] = sha(TARGET / 'release/rust-interp-vm')
        composition = dict(kind='runtime-candidate', schema_version=1, source_commit=source,
                           exporter_and_wrapper_key=CONTROL, binaries=binaries)
        key = hashlib.sha256(json.dumps(composition, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        with (ROOT / '.work/interpreter-tools.lock').open('a') as publication:
            acquire_lock(publication, 45)
            installed = ROOT / '.work/interpreter-tools' / key
            installed.mkdir(exist_ok=False)
            for name in binaries:
                shutil.copy2(TARGET / 'release' / name if name == 'rust-interp-vm' else retained / name, installed / name)
            caps = json.loads((retained / 'capabilities.json').read_text())
            caps.update(tool_key=key, exporter_sha256=binaries['rust-interp-mir-export'])
            write(installed / 'capabilities.json', caps)
            write(installed / 'source.json', dict(tool_key=key, composition=composition, files=frozen,
                source_commit=source, key_algorithm='SHA256 of canonical composition JSON', source=str(ROOT)))
            write(installed / 'ready.json', binaries)
        result = ROOT / 'results' / args.run_id
        result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', source_commit=source, tool_key=key, binaries=binaries,
            composition=composition, tests=counts, performance_measurement=False,
            source_manifest_sha256=sha(work / 'plan.json'), raw=str(work.relative_to(ROOT))))
        print('PASS', counts, key, flush=True)


if __name__ == '__main__':
    main()
