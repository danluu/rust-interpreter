"""Qualify the explicit capacity option and retain the exact known compiler pair."""
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


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 16)
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=ROOT).strip()
        source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        proof_path = ROOT / 'results/environment-main-build-01/summary.json'
        proof = json.loads(proof_path.read_text())
        assert proof['status'] == 'passed' and proof['tool_key'] == 'b08f39e282ece70b125d23cf1a9b3a22cef5cfd4c03bf5b8cae023701f9b21ff'
        retained, _ = installed_tools(proof['tool_key'])
        assert all(sha(retained / n) == h for n, h in proof['binaries'].items())
        target = ROOT / '.work/fixed-frame-clear-combined-build-01/target'
        work = ROOT / '.work/parser-jit-capacity-build-01'; work.mkdir(exist_ok=False)
        paths = [ROOT / name for name in ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml']]
        paths += [Path(__file__), Path(__file__).with_name('PLAN.md'), proof_path]
        paths += list((ROOT / 'scripts').glob('*.py')) + list((ROOT / 'tests').glob('test_*.py'))
        paths += [p for p in (ROOT / 'crates').rglob('*') if p.is_file() and (p.suffix == '.rs' or p.name == 'Cargo.toml')]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        commands = [('python', ['/opt/homebrew/bin/python3', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'])]
        for label, profile in [('debug', []), ('release', ['--release'])]:
            commands.append((label, ['cargo', '+nightly-2026-09-08', 'test', *profile, '--workspace',
                '--locked', '--offline', '--jobs', '2', '--target-dir', str(target)]))
        commands.append(('build', ['cargo', '+nightly-2026-09-08', 'build', '--release', '--locked', '--offline',
            '--jobs', '2', '--target-dir', str(target), '-p', 'rust-interp-bytecode', '--bin', 'rust-interp-vm']))
        commands.append(('capabilities', [str(target / 'release/rust-interp-vm'), '--rust-interp-capabilities']))
        write(work / 'plan.json', dict(owner=str(ROOT), source_commit=source, frozen=frozen,
            commands=commands, target=str(target), retained_compiler_key=proof['tool_key'],
            minimum_free_gib=8, performance_measurement=False))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                             'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never', CARGO_INCREMENTAL='0', CARGO_PROFILE_DEV_DEBUG='0',
                   CARGO_PROFILE_TEST_DEBUG='0', CARGO_PROFILE_RELEASE_DEBUG='1', PYTHONDONTWRITEBYTECODE='1')
        records, totals = [], {}
        for label, command in commands:
            require_space(ROOT, 8)
            child, out, err = capture(command, cwd=ROOT, env=env,
                                     receipt_path=work / 'active.json', receipt=dict(label=label))
            (work / (label + '.stdout')).write_text(out); (work / (label + '.stderr')).write_text(err)
            records.append(dict(label=label, command=command, pid=child.pid, returncode=child.returncode,
                stdout_sha256=sha(work / (label + '.stdout')), stderr_sha256=sha(work / (label + '.stderr'))))
            write(work / 'records.json', records)
            assert child.returncode == 0, (label, err[-3000:])
            if label == 'python':
                count, = re.findall(r'Ran (\d+) tests? in ', err)
                assert int(count) == 256 and err.rstrip().endswith('OK (skipped=13)')
                totals[label] = dict(tests=256, skipped=13)
            elif label in ['debug', 'release']:
                groups = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;', out + err)
                assert groups and all(int(f) == 0 for _, f, _ in groups)
                totals[label] = dict(passed=sum(int(n) for n, _, _ in groups), ignored=sum(int(i) for _, _, i in groups))
                assert totals[label] == dict(passed=497, ignored=2), totals
            elif label == 'capabilities':
                assert json.loads(out) == dict(schema_version=1, bytecode_version=5,
                    jit_code_limit=dict(default=16777216, maximum=33554432))
            assert all(sha(ROOT / p) == h for p, h in frozen.items())
            print(label, totals.get(label, 'passed'), flush=True)
        binaries = dict(proof['binaries'])
        binaries['rust-interp-vm'] = sha(target / 'release/rust-interp-vm')
        composition = dict(kind='explicit-jit-code-capacity', schema_version=1, source_commit=source,
            compiler_source_key=proof['tool_key'], binaries=binaries)
        key = hashlib.sha256(json.dumps(composition, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        with (ROOT / '.work/interpreter-tools.lock').open('a') as publication:
            acquire_lock(publication, 45)
            destination = ROOT / '.work/interpreter-tools' / key; destination.mkdir(exist_ok=False)
            for name in binaries:
                shutil.copy2(target / 'release' / name if name == 'rust-interp-vm' else retained / name, destination / name)
                assert sha(destination / name) == binaries[name]
            caps = json.loads((retained / 'capabilities.json').read_text())
            caps.update(tool_key=key, exporter_sha256=binaries['rust-interp-mir-export'])
            write(destination / 'capabilities.json', caps)
            write(destination / 'vm-capabilities.json', json.loads((work / 'capabilities.stdout').read_text()))
            write(destination / 'source.json', dict(tool_key=key, composition=composition, files=frozen,
                source_commit=source, source=str(ROOT), key_algorithm='SHA256 canonical composition JSON'))
            write(destination / 'ready.json', binaries)
        result = ROOT / 'results/parser-jit-capacity-build-01'; result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', commands=len(records), tests=totals,
            tool_key=key, binaries=binaries, composition=composition, source_commit=source,
            source_manifest=str((work / 'plan.json').relative_to(ROOT)), source_manifest_sha256=sha(work / 'plan.json'),
            records_sha256=sha(work / 'records.json'), raw=str(work.relative_to(ROOT)), performance_measurement=False))
        print('PASS', key, flush=True)


if __name__ == '__main__':
    main()
