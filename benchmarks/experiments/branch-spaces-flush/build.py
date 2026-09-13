#!/usr/bin/env python3
"""Build and qualify the branch-selected fixed addresses and successor-only register flushing with retained compiler tools."""
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
    parser.add_argument('--expected-tests', type=int, default=532)
    args = parser.parse_args()
    control_path = args.control_build.resolve(strict=True)
    control = json.loads(control_path.read_text())
    assert control['status'] == 'passed'
    CONTROL = control['tool_key']
    assert CONTROL == '35df4077b5cfb466cf1a7155374abb867fb8fadeb4f5dbedffe766d5b3621bc1'
    run = args.run_id
    assert args.expected_tests == 532
    assert re.fullmatch(r'branch-spaces-flush-build-\d{2}', run)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        from workflow_io import require_space
        require_space(ROOT, 16)
        prior = json.loads((ROOT / '.work/experiments/fixed-frame-clear-combined-build-01/status.json').read_text())
        assert prior['status'] == 'finished' and prior['returncode'] == 0
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=ROOT, text=True).strip()
        source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        files = [ROOT / name for name in ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml', 'scripts/compare_saved_runtime.py', 'scripts/workflow_io.py', 'scripts/interpreter.py']]
        files += [Path(__file__).with_name('selector.s'), Path(__file__).resolve(), Path(__file__).with_name('PLAN.md'), Path(__file__).with_name('QUALIFICATION.md'), control_path]
        files += [p for p in (ROOT / 'crates').rglob('*') if p.is_file() and (p.suffix == '.rs' or p.name == 'Cargo.toml')]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in files}
        retained, _ = installed_tools(CONTROL)
        assert json.loads((retained/'ready.json').read_text()) == control['binaries']
        assert all(sha(retained/name) == digest for name,digest in control['binaries'].items())
        work = ROOT / '.work' / run
        work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), source_commit=source, frozen=frozen,
              source=str(ROOT), target=str(TARGET), control=CONTROL, controller_sha256=sha(Path(__file__))))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
                             'RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never', CARGO_INCREMENTAL='0', CARGO_PROFILE_DEV_DEBUG='0',
                   CARGO_PROFILE_TEST_DEBUG='0', CARGO_PROFILE_RELEASE_DEBUG='1')
        records, counts = [], {}
        for label, command in [
            ('assemble-control', ['/usr/bin/clang', '-target', 'arm64-apple-macos11', '-c',
                str(Path(__file__).with_name('selector.s')), '-o', str(work/'selector.o')]),
            ('inspect-control', ['/usr/bin/otool', '-s', '__TEXT', '__text', str(work/'selector.o')])]:
            child, stdout, stderr = capture(command,cwd=ROOT,env=env,
                receipt_path=work/'active.json',receipt=dict(label=label))
            (work/(label+'.stdout')).write_text(stdout);(work/(label+'.stderr')).write_text(stderr)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode))
            write(work/'commands.json',records);assert child.returncode==0,(stdout+stderr)[-3000:]
            if label=='inspect-control':
                words=[int(word,16) for line in stdout.splitlines() if re.match(r'^[0-9a-f]{16}\s',line)
                    for word in line.split()[1:]]
                assert words==[0xd37efd6d,0xb40000cd,0xd2e8000e,0xcb0e016b,0xaa0703f1,0xaa0803ef,
                    0x14000003,0xaa0203f1,0xaa0303ef,0xd37efd6d,0xb40000ed,0xd2e8000e,0xcb0e016b,
                    0xaa0703f1,0xaa0803ef,0xaa1f03ee,0x14000004,0xaa0203f1,0xaa0303ef,0xaa0403ee,0xd65f03c0],words
        for label, action, profile in [('test-debug', 'test', []), ('test-release', 'test', ['--release']),
                                       ('build-release', 'build', ['--release'])]:
            require_space(ROOT, 8)
            command = ['cargo', '+nightly-2026-09-08', action, *profile, '--locked', '--offline', '--jobs', '2',
                       '--target-dir', str(TARGET)]
            if action == 'build':
                command += ['-p', 'rust-interp-bytecode', '--bin', 'rust-interp-vm']
            else:
                command += ['--workspace']
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
                assert counts[label] == args.expected_tests, counts
                for name in ['branch_arena_selector_matches_unsigned_reference_and_preserves_live_inputs',
                             'branch_arena_scalar_accesses_preserve_bytes_faults_and_address_truncation',
                             'branch_selector_matches_complete_copy_ranges_at_tag_and_immediate_boundaries',
                             'successor_flush_omits_dead_wide_branch_spills_and_preserves_selection',
                             'successor_flush_preserves_wide_values_live_through_both_join_edges',
                             'successor_flush_keeps_frame_arguments_before_native_and_vm_calls']:
                    assert '::' + name + ' ... ok' in stdout
                ignored = sum(int(n) for n in re.findall(r'test result: ok\. \d+ passed; \d+ failed; (\d+) ignored;', stdout+stderr))
                assert ignored == 10, ignored
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        binaries = json.loads((retained / 'ready.json').read_text())
        for name in ['rust-interp-vm']:
            binaries[name] = sha(TARGET / 'release' / name)
        composition = dict(kind='branch-spaces-flush-composition', schema_version=1, source_commit=source,
                           compiler_source_key=CONTROL, binaries=binaries)
        import hashlib
        key = hashlib.sha256(json.dumps(composition, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        with (ROOT / '.work/interpreter-tools.lock').open('a') as publication:
            acquire_lock(publication, 45)
            installed = ROOT / '.work/interpreter-tools' / key
            installed.mkdir(exist_ok=False)
            for name in binaries:
                shutil.copy2(TARGET / 'release' / name if name == 'rust-interp-vm' else retained / name, installed / name)
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
