#!/usr/bin/env python3
"""Qualify a committed runtime candidate while preserving exporter/wrapper bytes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools
from workflow_io import capture, require_space, write_json as write

CONTROL = '9ae791980111702fbe88b04e5fff74d6816218fba433701ab54b370447f9337b'
TARGET = ROOT / '.work/fixed-frame-clear-combined-build-01/target'


def test_counts(output):
    matches = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;', output)
    assert matches and all(int(failed) == 0 for _, failed, _ in matches)
    return dict(passed=sum(int(passed) for passed, _, _ in matches),
                ignored=sum(int(ignored) for _, _, ignored in matches))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--expected-tests', type=int, required=True)
    parser.add_argument('--minimum-free-gib', type=int, choices=[7, 8], default=8,
        help='host-only qualification admission; 7 requires an explicit justification in the frozen plan, default 8')
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--build-exporter', action='store_true', help='also qualify and install the current exporter/wrapper')
    parser.add_argument('--exporter-key', default=CONTROL, help='immutable exporter/wrapper composition retained by a runtime-only build')
    parser.add_argument('--reuse-tests', type=Path, help='reuse both passed profiles from a build stopped before binary publication; Rust inputs must be identical')
    args = parser.parse_args()
    if args.minimum_free_gib == 7:
        assert 'Host qualification floor: 7 GiB' in args.plan.read_text(), 'lower host floor must be explicit in the frozen plan'
    control = args.exporter_key
    assert re.fullmatch(r'[a-z][a-z0-9-]*-build-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        prior = json.loads((ROOT / '.work/experiments/fixed-frame-clear-combined-build-01/status.json').read_text())
        assert prior['status'] == 'finished' and prior['returncode'] == 0
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=ROOT).strip()
        source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        paths = [ROOT / n for n in ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml']]
        paths += [p for p in (ROOT / 'crates').rglob('*') if p.is_file() and (p.suffix == '.rs' or p.name == 'Cargo.toml')]
        paths += [Path(__file__).resolve(), args.plan.resolve()]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        reused_counts = {}
        if args.reuse_tests is not None:
            old = args.reuse_tests.resolve(strict=True)
            assert old.parent == ROOT / '.work' and old.name != args.run_id
            old_plan = json.loads((old / 'plan.json').read_text())
            old_status_path = ROOT / '.work/experiments' / old.name / 'status.json'
            old_status = json.loads(old_status_path.read_text())
            assert old_status['owner'] == old_status['cwd'] == str(ROOT) and old_status['status'] == 'finished'
            assert sha(old_status_path.with_name('plan.json')) == old_status['plan_sha256']
            assert sha(old_status_path.with_name('command.log')) == old_status['log_sha256']
            assert old_plan['target'] == str(TARGET) and old_plan['expected_tests'] == args.expected_tests
            assert old_plan.get('build_exporter', False) == args.build_exporter and old_plan['control'] == control
            for name, digest in old_plan['frozen'].items():
                if name == str(Path(__file__).resolve().relative_to(ROOT)):
                    content = subprocess.check_output(['git', 'show', old_plan['source_commit'] + ':' + name], cwd=ROOT)
                    assert hashlib.sha256(content).hexdigest() == digest
                else:
                    assert sha(ROOT / name) == digest, 'tested input changed: ' + name
            commands = json.loads((old / 'commands.json').read_text())
            assert [c['label'] for c in commands] == ['test-debug', 'test-release']
            assert all(c['returncode'] == 0 for c in commands)
            proof_paths = [old / 'plan.json', old / 'commands.json', old_status_path,
                           old_status_path.with_name('plan.json'), old_status_path.with_name('command.log')]
            for label in ['test-debug', 'test-release']:
                logs = [old / (label + '.' + suffix) for suffix in ['stdout', 'stderr']]
                reused_counts[label] = test_counts(''.join(p.read_text() for p in logs))
                assert reused_counts[label] == dict(passed=args.expected_tests, ignored=1)
                proof_paths += logs
            frozen.update({str(p.relative_to(ROOT)): sha(p) for p in proof_paths})
        retained, _ = installed_tools(control)
        work = ROOT / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(source_commit=source, frozen=frozen, target=str(TARGET), control=control,
            expected_tests=args.expected_tests, build_exporter=args.build_exporter,
            tests_reused_from=str(args.reuse_tests) if args.reuse_tests is not None else None,
            jobs=2, minimum_free_gib=args.minimum_free_gib, performance_measurement=False))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
                             'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET']}
        env.update(CARGO_TERM_COLOR='never', CARGO_INCREMENTAL='0', CARGO_PROFILE_DEV_DEBUG='0',
                   CARGO_PROFILE_TEST_DEBUG='0', CARGO_PROFILE_RELEASE_DEBUG='1')
        records, counts = [], dict(reused_counts)
        for label, action, profile in [('test-debug', 'test', []), ('test-release', 'test', ['--release']),
                                       ('build-release', 'build', ['--release'])]:
            if label in reused_counts: continue
            require_space(ROOT, args.minimum_free_gib)
            command = ['cargo', '+nightly-2026-09-08', action, *profile, '--locked', '--offline', '--jobs', '2',
                       '--target-dir', str(TARGET)]
            command += (['--workspace'] if action == 'test' else
                ['-p', 'rust-interp-bytecode', '-p', 'rust-interp-mir-export', '--bins'] if args.build_exporter else
                ['-p', 'rust-interp-bytecode', '--bin', 'rust-interp-vm'])
            child, stdout, stderr = capture(command, cwd=ROOT, env=env,
                receipt_path=work / 'active.json', receipt=dict(label=label))
            for suffix, content in [('stdout', stdout), ('stderr', stderr)]:
                (work / f'{label}.{suffix}').write_text(content)
            records.append(dict(label=label, command=command, pid=child.pid, returncode=child.returncode))
            write(work / 'commands.json', records)
            assert child.returncode == 0, f'{label} failed'
            if action == 'test':
                counts[label] = test_counts(stdout + stderr)
                assert counts[label] == dict(passed=args.expected_tests, ignored=1), counts
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        binaries = json.loads((retained / 'ready.json').read_text())
        binaries['rust-interp-vm'] = sha(TARGET / 'release/rust-interp-vm')
        if args.build_exporter:
            for name in ['rust-interp-mir-export', 'rust-interp-rustc-wrapper']:
                binaries[name] = sha(TARGET / 'release' / name)
        composition = dict(kind='tool-candidate' if args.build_exporter else 'runtime-candidate', schema_version=1, source_commit=source,
                           exporter_and_wrapper_key=None if args.build_exporter else control, binaries=binaries)
        key = hashlib.sha256(json.dumps(composition, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        with (ROOT / '.work/interpreter-tools.lock').open('a') as publication:
            acquire_lock(publication, 45)
            installed = ROOT / '.work/interpreter-tools' / key
            installed.mkdir(exist_ok=False)
            for name in binaries:
                shutil.copy2(TARGET / 'release' / name if name == 'rust-interp-vm' or args.build_exporter else retained / name, installed / name)
            if args.build_exporter:
                caps = json.loads(subprocess.check_output([str(installed / 'rust-interp-mir-export'), '--rust-interp-capabilities'], text=True))
                assert caps['schema_version'] == 1
            else:
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
            tests_reused_from=str(args.reuse_tests) if args.reuse_tests is not None else None,
            source_manifest_sha256=sha(work / 'plan.json'), raw=str(work.relative_to(ROOT))))
        print('PASS', counts, key, flush=True)


if __name__ == '__main__':
    main()
