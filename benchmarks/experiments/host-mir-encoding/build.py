#!/usr/bin/env python3
"""Qualify only the host wrapper; retain immutable guest VM/exporter bytes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

SOURCE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SOURCE / 'scripts'))
import interpreter
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write

BASELINE = '49746a2218dbfdccacac0031f47e7a13b0440489c226979ff3374f6f899e09f9'
TOOLCHAIN = 'nightly-2026-09-08'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace-root', required=True, type=Path)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--after-experiment', required=True)
    parser.add_argument('--after-supervisor', required=True, type=int)
    args = parser.parse_args()
    root = args.workspace_root.resolve(strict=True)
    interpreter.ROOT = root
    assert re.fullmatch(r'host-mir-build-\d{2}', args.run_id)
    assert re.fullmatch(r'[a-z0-9-]+', args.after_experiment)
    assert (root / '.work/benchmark.lock').is_file()
    assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=SOURCE).strip()
    source_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE, text=True).strip()
    paths = [SOURCE / p for p in ['rust-toolchain.toml', 'crates/mir-export/src/wrapper_main.rs',
        'crates/mir-export/src/wrapper_route.rs', 'crates/mir-export/tests/wrapper_route.rs',
        'benchmarks/experiments/host-mir-encoding/PLAN.md',
        'benchmarks/experiments/host-mir-encoding/build.py',
        'scripts/interpreter.py', 'scripts/compare_saved_runtime.py', 'scripts/workflow_io.py']]
    frozen = {str(p.relative_to(root)): sha(p) for p in paths}
    work = root / '.work' / args.run_id
    work.mkdir(exist_ok=False)
    write(work / 'plan.json', dict(owner=str(root), source=str(SOURCE), source_commit=source_commit,
        frozen=frozen, baseline=BASELINE, after_experiment=args.after_experiment,
        after_supervisor=args.after_supervisor, expected_tests_per_profile=16,
        minimum_free_gib=4, codegen_workers=2, performance_measurement=False))
    waited = time.monotonic()
    while True:
        prior = json.loads((root / '.work/experiments' / args.after_experiment / 'status.json').read_text())
        assert prior['owner'] == str(root) and prior['supervisor_pid'] == args.after_supervisor
        if prior['status'] == 'finished':
            assert prior['returncode'] == 0, 'prerequisite comparisons did not complete'
            break
        if time.monotonic() - waited >= 30:
            print('Waiting for the owned capacity controller and mandatory guards', flush=True)
            waited = time.monotonic()
        time.sleep(1)
    with (root / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        assert all(sha(root / p) == digest for p, digest in frozen.items())
        retained, _ = interpreter.installed_tools(BASELINE)
        original_binaries = json.loads((retained / 'ready.json').read_text())
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                             'RUSTC_WORKSPACE_WRAPPER', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET']}
        env['CARGO_TERM_COLOR'] = 'never'
        records = []

        def run(label, command):
            require_space(root, 4)
            child, out, err = capture(list(map(str, command)), cwd=SOURCE, env=env,
                receipt_path=work / 'active.json', receipt=dict(label=label))
            for suffix, text in [('stdout', out), ('stderr', err)]:
                (work / (label + '.' + suffix)).write_text(text)
            records.append(dict(label=label, command=list(map(str, command)), pid=child.pid,
                returncode=child.returncode, stdout_sha256=sha(work / (label + '.stdout')),
                stderr_sha256=sha(work / (label + '.stderr'))))
            write(work / 'commands.json', records)
            assert child.returncode == 0, label + ' failed'
            return out

        compiler = Path(run('resolve-rustc', ['rustup', 'which', '--toolchain', TOOLCHAIN, 'rustc']).strip())
        version = run('rustc-version', [compiler, '-vV'])
        assert 'commit-hash: cea272fa356e94bd2ee2cadf376630aa0683867a' in version
        tests = {}
        for profile, opt in [('debug', '0'), ('release', '3')]:
            executable = work / ('routing-' + profile)
            run('compile-' + profile, [compiler, '--edition=2024', '--test',
                SOURCE / 'crates/mir-export/tests/wrapper_route.rs', '-C', 'opt-level=' + opt,
                '-C', 'codegen-units=2', '-o', executable])
            output = run('test-' + profile, [executable, '--test-threads=2'])
            counts, = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;', output)
            assert counts == ('16', '0', '0'), counts
            tests[profile] = dict(passed=16, failed=0, ignored=0)
        wrapper = work / 'rust-interp-rustc-wrapper'
        run('build-wrapper', [compiler, '--edition=2024', '--crate-name', 'rust_interp_rustc_wrapper',
            SOURCE / 'crates/mir-export/src/wrapper_main.rs', '-C', 'opt-level=3',
            '-C', 'codegen-units=2', '-C', 'debuginfo=1', '-o', wrapper])
        assert all(sha(root / p) == digest for p, digest in frozen.items())
        binaries = dict(original_binaries, **{'rust-interp-rustc-wrapper': sha(wrapper)})
        composition = dict(kind='host-mir-wrapper-candidate', schema_version=1,
            source_commit=source_commit, vm_and_exporter_key=BASELINE, binaries=binaries)
        key = hashlib.sha256(json.dumps(composition, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        with (root / '.work/interpreter-tools.lock').open('a') as publication:
            acquire_lock(publication, 45)
            installed = root / '.work/interpreter-tools' / key
            installed.mkdir(exist_ok=False)
            for name in binaries:
                shutil.copy2(wrapper if name == wrapper.name else retained / name, installed / name)
                assert sha(installed / name) == binaries[name]
            caps = json.loads((retained / 'capabilities.json').read_text())
            caps.update(tool_key=key, exporter_sha256=binaries['rust-interp-mir-export'])
            write(installed / 'capabilities.json', caps)
            write(installed / 'source.json', dict(tool_key=key, composition=composition, files=frozen,
                source_commit=source_commit, source=str(SOURCE), compiler_sha256=sha(compiler),
                key_algorithm='SHA256 of canonical composition JSON'))
            write(installed / 'ready.json', binaries)
        interpreter.installed_tools(key)
        out = root / 'results' / args.run_id
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', dict(status='passed', tool_key=key, source_commit=source_commit,
            binaries=binaries, composition=composition, tests=tests, commands=len(records),
            compiler_sha256=sha(compiler), raw=str(work.relative_to(root)),
            evidence={name: sha(work / (name + '.json')) for name in ['plan', 'commands']},
            performance_measurement=False, real_cargo_qualification_pending=True))
        print('PASS', key, tests, flush=True)


if __name__ == '__main__':
    main()
