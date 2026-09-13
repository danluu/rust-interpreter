"""After all five gates pass, qualify the main frontend with the measured VM."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from inputs import CASES, VM_KEY, VM_SHA, require_complete, require_vm_sources, rust_input

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / '.work/publication-main'
TARGET = ROOT / '.work/fixed-frame-clear-combined-build-01/target'
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools
from workflow_io import capture, require_space, write_json as write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--comparison', required=True, type=Path)
    parser.add_argument('--terminal', required=True, type=Path)
    args = parser.parse_args()
    assert re.fullmatch(r'guarded-local-facts-main-build-\d{2}', args.run_id)
    assert sys.version_info >= (3, 11), 'current main Python contracts require tomllib'
    comparison_path = args.comparison.resolve(strict=True)
    terminal_path = args.terminal.resolve(strict=True)
    assert comparison_path.parent.parent == ROOT / 'results'
    assert terminal_path.parent.parent == ROOT / '.work/experiments'
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 16)
        proof = json.loads(comparison_path.read_text())
        case_paths = [ROOT / 'results' / ('guarded-local-facts-edit-' + case + '-01') / 'summary.json' for case in CASES]
        cases = [json.loads(p.read_text()) for p in case_paths]
        require_complete(proof, cases)
        raw = ROOT / proof['raw']
        assert raw.parent == ROOT / '.work'
        terminal = json.loads(terminal_path.read_text())
        assert terminal['status'] == 'finished' and terminal['returncode'] == 0
        assert terminal['owner'] == terminal['cwd'] == str(ROOT)
        assert terminal['command'][1:] == [
            'benchmarks/experiments/guarded-local-facts-continuation/resume.py', '--run-id', raw.name]
        evidence = [comparison_path, terminal_path, *case_paths]
        for name, field in [('plan.json', 'plan_sha256'), ('command.log', 'log_sha256')]:
            path = terminal_path.with_name(name)
            assert sha(path) == terminal[field]
            evidence.append(path)
        for name, field in [('plan', 'plan_sha256'), ('records', 'records_sha256'), ('final-audit', 'final_audit_sha256')]:
            path = raw / (name + '.json')
            assert sha(path) == proof[field]
            evidence.append(path)
        audit = json.loads((raw / 'final-audit.json').read_text())
        assert audit['all_frozen_inputs_verified'] and [r['case'] for r in audit['cases']] == CASES
        assert [r['summary_sha256'] for r in audit['cases']] == [sha(p) for p in case_paths]
        vm_proof_path = ROOT / 'results/guarded-local-facts-build-03/summary.json'
        vm_proof = json.loads(vm_proof_path.read_text())
        assert vm_proof['status'] == 'passed' and vm_proof['tool_key'] == VM_KEY
        assert vm_proof['tests'] == {'test-debug': 504, 'test-release': 504}
        vm_plan_path = ROOT / vm_proof['source_manifest']
        assert sha(vm_plan_path) == vm_proof['source_manifest_sha256']
        qualified = json.loads(vm_plan_path.read_text())['frozen']
        retained, _ = installed_tools(VM_KEY)
        assert json.loads((retained / 'ready.json').read_text()) == vm_proof['binaries']
        assert sha(retained / 'rust-interp-vm') == VM_SHA
        evidence += [vm_proof_path, vm_plan_path, retained / 'source.json', retained / 'ready.json', retained / 'rust-interp-vm']
        assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=SOURCE).strip()
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE, text=True).strip()
        compiler_command = ['rustc', '+nightly-2026-09-08', '-vV']
        compiler = subprocess.run(compiler_command, capture_output=True, text=True, check=True)
        assert 'commit-hash: cea272fa356e94bd2ee2cadf376630aa0683867a' in compiler.stdout.splitlines()
        assert 'host: aarch64-apple-darwin' in compiler.stdout.splitlines()
        tracked = [p for p in subprocess.check_output(['git', 'ls-files', '-z'], cwd=SOURCE).decode().split('\0') if p]
        current = {p: sha(SOURCE / p) for p in tracked if rust_input(p)}
        actual_rust = {str(p.relative_to(SOURCE)): sha(p) for p in (SOURCE / 'crates').rglob('*')
                       if p.is_file() and rust_input(str(p.relative_to(SOURCE)))}
        assert actual_rust == {p: h for p, h in current.items() if p.startswith('crates/')}, 'untracked Rust build input'
        require_vm_sources(current, qualified)
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in evidence}
        for name in tracked:
            if (rust_input(name) or name.endswith('.rs') or name.startswith(('scripts/', 'tests/', '.cargo/'))
                    or name == 'benchmarks/corpus.json'):
                path = SOURCE / name
                frozen[str(path.relative_to(ROOT))] = sha(path)
        for path in Path(__file__).parent.iterdir():
            if path.suffix in ['.py', '.md']: frozen[str(path.relative_to(ROOT))] = sha(path)
        work = ROOT / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        commands = [('controller-tests', [sys.executable, '-m', 'unittest', 'discover', '-s', str(Path(__file__).parent), '-p', 'test_*.py', '-v'], ROOT),
                    ('python', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'], SOURCE)]
        for label, action, profile in [('test-debug', 'test', []), ('test-release', 'test', ['--release']), ('build-release', 'build', ['--release'])]:
            commands.append((label, ['cargo', '+nightly-2026-09-08', action, *profile, '--locked', '--offline',
                '--jobs', '2', '--target-dir', str(TARGET), '-p', 'rust-interp-mir-export'], SOURCE))
        write(work / 'plan.json', dict(owner=str(ROOT), source=str(SOURCE), source_commit=revision,
            frozen=frozen, rust_inputs=current, target=str(TARGET), vm_source_key=VM_KEY,
            compiler_identity_command=compiler_command, compiler_identity_stdout=compiler.stdout,
            previous_workspace_tests_per_profile=504, commands=[dict(label=l, command=c, cwd=str(d)) for l, c, d in commands],
            admitted_free_bytes=shutil.disk_usage(ROOT).free, minimum_initial_free_gib=16,
            scope='Compiler and launcher compatibility qualification; measured VM binary reused only with exact component/shared input inventory. The prior504 tests are a whole-workspace result, not504 VM-only tests. No timing repetition or claim about newer optional compiler routes.'))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
                             'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET', 'CARGO_BUILD_BUILD_DIR',
                             'CARGO_BUILD_RUSTC', 'CARGO_BUILD_RUSTC_WRAPPER', 'CARGO_BUILD_RUSTC_WORKSPACE_WRAPPER', 'RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never', CARGO_INCREMENTAL='0', CARGO_PROFILE_DEV_DEBUG='0',
                   CARGO_PROFILE_TEST_DEBUG='0', CARGO_PROFILE_RELEASE_DEBUG='1', PYTHONDONTWRITEBYTECODE='1')
        records, counts = [], {}
        for label, command, cwd in commands:
            require_space(ROOT, 8)
            child, out, err = capture(command, cwd=cwd, env=env, receipt_path=work / 'active.json', receipt=dict(label=label))
            (work / (label + '.stdout')).write_text(out)
            (work / (label + '.stderr')).write_text(err)
            records.append(dict(label=label, command=command, cwd=str(cwd), pid=child.pid, returncode=child.returncode,
                stdout_sha256=sha(work / (label + '.stdout')), stderr_sha256=sha(work / (label + '.stderr'))))
            write(work / 'records.json', records)
            assert child.returncode == 0, label + ' failed'
            if label in ['controller-tests', 'python']:
                total, = re.findall(r'Ran (\d+) tests? in ', err)
                skips = re.findall(r'OK \(skipped=(\d+)\)', err)
                assert err.rstrip().endswith('OK') or skips
                counts[label] = dict(tests=int(total), skipped=int(skips[0]) if skips else 0)
                if label == 'controller-tests': assert counts[label] == dict(tests=5, skipped=0)
            elif label.startswith('test-'):
                groups = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed;', out + err)
                assert groups and all(int(f) == 0 for _, f in groups)
                counts[label] = sum(int(n) for n, _ in groups)
                assert counts[label] >= 98
            assert all(sha(ROOT / p) == h for p, h in frozen.items())
            print(label, counts.get(label, 'completed'), flush=True)
        assert counts['test-debug'] == counts['test-release']
        assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE, text=True).strip() == revision
        binaries = dict(vm_proof['binaries'])
        for name in ['rust-interp-mir-export', 'rust-interp-rustc-wrapper']: binaries[name] = sha(TARGET / 'release' / name)
        composition = dict(kind='guarded-local-facts-main-compiler', schema_version=1, source_commit=revision,
                           vm_source_key=VM_KEY, binaries=binaries)
        key = hashlib.sha256(json.dumps(composition, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        with (ROOT / '.work/interpreter-tools.lock').open('a') as publication:
            acquire_lock(publication, 45)
            installed = ROOT / '.work/interpreter-tools' / key
            installed.mkdir(exist_ok=False)
            for name in binaries:
                shutil.copy2(retained / name if name == 'rust-interp-vm' else TARGET / 'release' / name, installed / name)
                assert sha(installed / name) == binaries[name]
            cap = subprocess.run([str(installed / 'rust-interp-mir-export'), '--rust-interp-capabilities'], env=env, capture_output=True, text=True, timeout=10, check=True)
            capabilities = json.loads(cap.stdout)
            assert capabilities['schema_version'] == 1
            capabilities.update(tool_key=key, exporter_sha256=binaries['rust-interp-mir-export'])
            write(installed / 'capabilities.json', capabilities)
            write(installed / 'source.json', dict(tool_key=key, composition=composition, files=current,
                source_commit=revision, source=str(SOURCE), key_algorithm='SHA256 of canonical composition JSON'))
            write(installed / 'ready.json', binaries)
        destination = ROOT / 'results' / args.run_id
        destination.mkdir(exist_ok=False)
        write(destination / 'summary.json', dict(status='passed', source_commit=revision, tool_key=key,
            binaries=binaries, composition=composition, tests=counts, reused_vm_source_manifest_matches=True,
            commands=len(records), raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'),
            records_sha256=sha(work / 'records.json'), performance_measurement=False,
            real_project_qualification_pending=True))
        print('PASS: main compiler and measured runtime composed', key, flush=True)


if __name__ == '__main__': main()
