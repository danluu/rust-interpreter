"""Qualify the bounded native store prototype against the bytecode controls."""
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
from workflow_io import capture, require_space, write_json as write
NAME = 'scalar-transaction-native-controls-02'


def read(p):
    return json.loads(p.read_text())


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        target = ROOT / '.work/fixed-frame-clear-combined-build-01/target'
        allocated = int(subprocess.check_output(['du', '-sk', str(target)], text=True).split()[0]) * 1024
        needed = max(14 * 1024**3, 8 * 1024**3 + 2 * allocated)
        assert shutil.disk_usage(ROOT).free >= needed, 'insufficient conservative build admission'
        closed_path = ROOT / 'results/scratch-scalar-runtime-sampling-01/closure.json'
        summary_path = closed_path.with_name('summary.json')
        closed, summary = read(closed_path), read(summary_path)
        assert closed['status'] == 'closed' and closed['all_hashes_verified']
        assert summary['status'] == 'passed' and sha(summary_path) == closed['summary_sha256']
        bindings_path = ROOT / closed['artifact_bindings']
        assert sha(bindings_path) == closed['artifact_bindings_sha256']
        paths = [closed_path, summary_path, bindings_path]
        for p, h in read(bindings_path).items():
            assert sha(ROOT / p) == h
            paths.append(ROOT / p)
        protocol = ROOT / 'results/scalar-protocol-census-03'
        closed_protocol = read(protocol / 'closure.json')
        assert closed_protocol['status']=='closed' and closed_protocol['all_hashes_verified']
        assert sha(protocol / 'summary.json')==closed_protocol['summary_sha256']
        binding = ROOT / closed_protocol['bindings']
        assert sha(binding)==closed_protocol['bindings_sha256']
        paths += [protocol / n for n in ['summary.json','attribution.json','closure.json','terminal.json']] + [binding]
        for name,digest in read(binding)['artifacts'].items():
            assert sha(ROOT/name)==digest;paths.append(ROOT/name)
        paths += [ROOT/'benchmarks/experiments/scalar-protocol-census/attribute.py']
        paths += [ROOT/'benchmarks/experiments/native-call-cost-census/analyze.py']
        shapes=ROOT/'results/current-call-shapes-01'
        shape_closure=read(shapes/'closure.json')
        assert shape_closure['all_hashes_verified'] and shape_closure['status']=='closed'
        assert sha(shapes/'summary.json')==shape_closure['summary_sha256']
        shape_binding=ROOT/shape_closure['bindings'];assert sha(shape_binding)==shape_closure['bindings_sha256']
        paths += [shape_binding, shapes/'closure.json', shapes/'summary.json']
        for name,digest in read(shape_binding)['artifacts'].items():
            assert sha(ROOT/name)==digest;paths.append(ROOT/name)
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py', '.md']]
        paths += [ROOT / p for p in subprocess.check_output(['git', 'ls-files', 'crates', 'Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml'], text=True).splitlines()]
        paths += [ROOT / 'scripts' / p for p in ['compare_saved_runtime.py', 'workflow_io.py', 'summarize_owned_sample.py']]
        artifact = ROOT / '.work/call-capacity-credit-edit-token-02/artifacts/caa66fcf85d85196264fd2fc5b024918f36a9fccc8237d79af7987182796b1d9.rbc'
        assert sha(artifact) == artifact.stem
        paths.append(artifact)
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD']).strip()
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        work = ROOT / '.work' / NAME
        work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), source_revision=revision, frozen=frozen,
            target=str(target.relative_to(ROOT)), same_source_root=True, required_free_bytes=needed,
            allocated_target_bytes=allocated, minimum_child_gib=8, controls=754, expected_commands=2,
            original_project_guest_commands=0, native_guest_unit_tests=True,
            executable_code_publications="unit controls only", production_store_admission=False, performance_measurement=False))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_', 'READONLY_', 'TRANSACTION_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0', CARGO_PROFILE_RELEASE_DEBUG='1', CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0', RUST_TEST_THREADS='2', CARGO_TERM_COLOR='never', PYTHONDONTWRITEBYTECODE='1')
        cargo = ['cargo', '+nightly-2026-09-08', 'test', '--release', '--lib', '-p', 'rust-interp-bytecode',
                 '--locked', '--offline', '--jobs', '2', '--manifest-path', str(ROOT / 'Cargo.toml'), '--target-dir', str(target)]
        commands=[('bytecode-debug',[x for x in cargo if x!='--release'],{},ROOT,377),
                  ('bytecode-release',cargo,{},ROOT,377)]
        records = []
        for label, command, extra, cwd, tests in commands:
            require_space(ROOT, 8)
            if command[0] == 'cargo':
                assert shutil.disk_usage(ROOT).free >= needed, 'build admission no longer holds'
            start = time.time()
            child, out, err = capture(command, cwd=cwd, env=env | extra, receipt_path=work / 'active.json', receipt=dict(label=label))
            for stream, payload in [('stdout', out), ('stderr', err)]:
                (work / (label + '.' + stream)).write_text(payload)
            records.append(dict(label=label, command=command, extra_env=extra, pid=child.pid,
                returncode=child.returncode, seconds=time.time() - start,
                stdout_sha256=sha(work / (label + '.stdout')), stderr_sha256=sha(work / (label + '.stderr'))))
            write(work / 'records.json', records)
            assert child.returncode == 0, (out + err)[-6000:]
            if tests:
                if label == 'python-controls':
                    assert 'Ran 2 tests' in err and err.rstrip().endswith('OK')
                else:
                    assert f'test result: ok. {tests} passed; 0 failed; 15 ignored;' in out
            assert all(sha(ROOT / p) == h for p, h in frozen.items())
            print(label, 'passed', flush=True)
        out = ROOT / 'results' / NAME
        out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',commands=2,controls=754,bytecode_passed_per_profile=377,
            ignored_per_profile=15,source_revision=revision,raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),
            original_project_guest_commands=0,native_guest_unit_tests=True,performance_measurement=False,
            setup_seconds=sum(r['seconds'] for r in records)))


if __name__ == '__main__':
    main()
