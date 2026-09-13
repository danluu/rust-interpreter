"""Inspect actual register initialization and typed entry edges without executing guests."""
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 10)
        proof_path = ROOT / 'results/parser-runtime-profile-01/summary.json'
        proof = json.loads(proof_path.read_text())
        assert proof['status'] == 'passed' and proof['statistics']['jit_declined_functions'] == 1
        missing, = proof['executed_without_published_code']
        old = ROOT / proof['raw']
        assert all(sha(old / p) == h for p, h in proof['evidence'].items())
        prior = json.loads((old / 'plan.json').read_text())
        artifact = Path(prior['command'][-1])
        assert sha(artifact) == prior['frozen'][str(artifact.relative_to(ROOT))]
        work = ROOT / '.work/parser-function-initialization-01'
        work.mkdir(exist_ok=False)
        target = ROOT / '.work/fixed-frame-clear-combined-build-01/target'
        paths = [Path(__file__), proof_path, old / 'plan.json', artifact,
                 ROOT / 'Cargo.toml', ROOT / 'Cargo.lock', ROOT / 'rust-toolchain.toml']
        paths += [p for p in (ROOT / 'crates/bytecode').rglob('*')
                  if p.is_file() and (p.suffix == '.rs' or p.name == 'Cargo.toml')]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        command = ['cargo', '+nightly-2026-09-08', 'test', '--release', '--locked', '--offline',
                   '--jobs', '2', '--target-dir', str(target), '-p', 'rust-interp-bytecode', '--lib',
                   'jit::local_memory_tests::observe_function_initialization_shape', '--',
                   '--ignored', '--exact', '--nocapture', '--test-threads=1']
        write(work / 'plan.json', dict(owner=str(ROOT), frozen=frozen, command=command,
            function=missing, expected_commands=1, offline_emissions=0,
            guest_commands=0, executable_code_publications=0, initial_gib=10,
            per_command_gib=8, performance_measurement=False))
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                             'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never', CARGO_INCREMENTAL='0', CARGO_PROFILE_DEV_DEBUG='0',
                   CARGO_PROFILE_TEST_DEBUG='0', CARGO_PROFILE_RELEASE_DEBUG='1',
                   EMISSION_INPUT=str(artifact), EMISSION_OUTPUT=str(work / 'initialization.json'),
                   EMISSION_FUNCTION=str(missing['function']))
        require_space(ROOT, 8)
        child, out, err = capture(command, cwd=ROOT, env=env,
                                 receipt_path=work / 'active.json', receipt={})
        (work / 'stdout').write_text(out); (work / 'stderr').write_text(err)
        write(work / 'records.json', [dict(command=command, pid=child.pid, returncode=child.returncode,
              stdout_sha256=sha(work / 'stdout'), stderr_sha256=sha(work / 'stderr'))])
        assert child.returncode == 0 and 'test result: ok. 1 passed; 0 failed;' in out, err
        result = json.loads((work / 'initialization.json').read_text())
        assert result['function'] == missing['function'] and result['name'] == missing['name']
        assert result['operations'] == missing['operations']
        assert result['guest_commands'] == result['executable_code_publications'] == 0
        assert result['register_bytes'] == result['registers'] * 16
        assert type(result['needs_initial_register_zeroes']) is bool
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        destination = ROOT / 'results/parser-function-initialization-01'; destination.mkdir(exist_ok=False)
        write(destination / 'summary.json', dict(status='passed', commands=1, offline_emissions=0,
            guest_commands=0, executable_code_publications=0, result=result,
            frozen_inputs_verified=len(frozen), raw=str(work.relative_to(ROOT)),
            evidence={p.name: sha(p) for p in work.iterdir() if p.is_file()}, performance_measurement=False))
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
