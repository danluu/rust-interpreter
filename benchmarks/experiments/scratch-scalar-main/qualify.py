"""Qualify a source-identical runtime integration with main's Python contracts."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write

CANDIDATE = 'b462d9e6'
MAIN = '701cc006'
RUN = 'scratch-scalar-main-qualification-01'
REUSED = [
    'scratch-memory-values-build-02', 'scratch-memory-values-qualification-01',
    'scratch-memory-values-profile-01', 'scratch-memory-values-real-controls-01',
    'scratch-memory-values-full-01', 'scratch-memory-values-parser-01',
    'scratch-memory-values-parser-edits-incremental-01',
    'scratch-memory-values-parser-edits-repository-01',
]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def read(path):
    return json.loads(path.read_text())


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        assert not git('diff', '--name-only', 'HEAD').strip()
        revision = git('rev-parse', 'HEAD').decode().strip()
        assert not git('diff', '--name-only', CANDIDATE, '--', 'crates',
                       'Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml', '.cargo').strip()
        changed = git('diff', '--name-only', CANDIDATE, '--', 'scripts').decode().splitlines()
        assert changed == ['scripts/runtime_compiler.py'], changed
        assert not git('diff', '--name-only', MAIN, '--', changed[0]).strip()
        assert not git('diff', '--name-only', CANDIDATE, '--', 'tests/test_isolated_launcher.py').strip()
        # This is an optional installer module, not a dependency of the stock
        # launcher's unchanged production Python scripts.
        for name in git('ls-files', 'scripts').decode().splitlines():
            if name.endswith('.py') and name != changed[0]:
                assert 'import runtime_compiler' not in (ROOT / name).read_text()
                assert 'from runtime_compiler' not in (ROOT / name).read_text()

        evidence = {}
        summaries = {}
        def bind(path, expected=None):
            digest = sha(path)
            if expected is not None:
                assert digest == expected, str(path)
            evidence[str(path.relative_to(ROOT))] = digest

        for run in REUSED:
            result = ROOT / 'results' / run
            summary, closure, terminal = [read(result / n) for n in
                                           ['summary.json', 'closure.json', 'terminal.json']]
            assert summary['status'] == 'passed' and closure['status'] == 'closed', run
            assert terminal['status'] == 'finished' and terminal['returncode'] == 0, run
            for name in ['summary', 'terminal']:
                bind(result / (name + '.json'), closure[name + '_sha256'])
            bind(result / 'closure.json')
            raw = ROOT / summary['raw']
            for name in ['plan', 'records']:
                if name + '_sha256' in summary:
                    bind(raw / (name + '.json'), summary[name + '_sha256'])
            for name in ['source_bindings', 'bindings', 'evidence']:
                if name in closure:
                    bind(ROOT / closure[name], closure[name + '_sha256'])
            if 'snapshot' in closure:
                for name in ['sources', 'evidence']:
                    bind(ROOT / closure['snapshot'] / (name + '.json'), closure[name + '_sha256'])
            if 'final_audit_path' in summary:
                bind(raw / summary['final_audit_path'], summary['final_audit_sha256'])
            summaries[run] = summary

        build = summaries[REUSED[0]]
        assert build['tests'] == {'test-debug': 608, 'test-release': 608}
        assert build['ignored_per_profile'] == 13
        strict = summaries[REUSED[1]]
        assert strict['commands'] == 121 and strict['strict_rejections'] == ['type', 'borrow']
        assert strict['scalar_partial_artifact_rejections']
        profiles = summaries['scratch-memory-values-profile-01']
        assert profiles['commands'] == 6 and profiles['exact_logical_counts_memory_and_entropy']
        assert profiles['exact_per_pc_counts'] and profiles['exact_operation_map_reconstruction']
        real = summaries['scratch-memory-values-real-controls-01']
        assert real['commands'] == 13 and real['native_assertion_outcomes_match'] and real['deterministic_controls_exact']
        parser = summaries['scratch-memory-values-parser-01']
        assert parser['custom_tests_passed'] == 114 and parser['original_assertions_match']
        assert all(summaries[run]['tool_key'] == build['tool_key'] for run in REUSED[:4] + [REUSED[5]])
        full = summaries['scratch-memory-values-full-01']
        assert full['commands'] == 726 and full['all_five_gates_passed'] and not full['unstarted_cases']
        for profile in ['incremental', 'repository']:
            s = summaries['scratch-memory-values-parser-edits-' + profile + '-01']
            assert s['commands'] == 88 and s['original_tests'] == 114 and s['measurement']['gate_passed']
            assert s['tool_keys']['candidate'] == build['tool_key']
        installed = ROOT / '.work/interpreter-tools' / build['tool_key']
        for name, digest in build['binaries'].items():
            bind(installed / name, digest)
        for name in ['source.json', 'ready.json', 'capabilities.json']:
            bind(installed / name)
        plan = read(ROOT / build['raw'] / 'plan.json')
        rust = {p: h for p, h in plan['frozen'].items()
                if p.startswith('crates/') or p in ['Cargo.toml', 'Cargo.lock']}
        for name, digest in rust.items():
            assert sha(ROOT / name) == digest, name

        tracked = git('ls-files', '-z').decode().split('\0')
        inputs = [p for p in tracked if p and (p.endswith('.py') or
            p.startswith(('crates/', 'scripts/', 'tests/', '.cargo/')) or
            p in ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml'] or
            p.startswith('benchmarks/experiments/scratch-scalar-main/'))]
        frozen = {p: sha(ROOT / p) for p in inputs}
        work = ROOT / '.work' / RUN
        work.mkdir(exist_ok=False)
        command = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v']
        write(work / 'plan.json', dict(owner=str(ROOT), source_revision=revision,
            candidate_revision=git('rev-parse', CANDIDATE).decode().strip(),
            main_revision=git('rev-parse', MAIN).decode().strip(), frozen=frozen,
            evidence=evidence, rust_inputs=rust, changed_production_scripts=changed,
            tool_key=build['tool_key'], binaries=build['binaries'], command=command,
            minimum_child_gib=8, reused_results=REUSED, performance_measurement=False))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_'))
               and k not in ['RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        child, out, err = capture(command, cwd=ROOT, env=env,
            receipt_path=work / 'active.json', receipt=dict(stage='merged Python contracts'))
        (work / 'stdout').write_text(out)
        (work / 'stderr').write_text(err)
        write(work / 'record.json', dict(command=command, pid=child.pid, returncode=child.returncode,
            stdout_sha256=sha(work / 'stdout'), stderr_sha256=sha(work / 'stderr')))
        assert child.returncode == 0, (out + err)[-5000:]
        count, = re.findall(r'Ran (\d+) tests? in ', err)
        ending, = re.findall(r'^OK(?: \(skipped=(\d+)\))?$', err, re.M)
        assert int(count) >= 334
        assert re.search(r'^test_scalar_calls_require_fully_checked_resumable_jit_before_tools .* \.\.\. ok$', err, re.M)
        assert 'test_runtime_source_qualification.' in err and 'test_runtime_compiler.' in err
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        assert all(sha(ROOT / p) == h for p, h in evidence.items())
        assert git('rev-parse', 'HEAD').decode().strip() == revision
        result = ROOT / 'results' / RUN
        result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', source_revision=revision,
            commands=1, tests=int(count), skipped=int(ending or 0),
            tool_key=build['tool_key'], binaries=build['binaries'], unchanged_rust_inputs=len(rust),
            frozen_inputs=len(frozen), evidence_files=len(evidence), all_frozen_inputs_verified=True,
            preserved_main_module=changed[0], unchanged_stock_launcher=True,
            reused_results=REUSED, new_guest_commands=0, performance_measurement=False,
            raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'),
            record_sha256=sha(work / 'record.json')))
        print('PASS:', count, 'merged Python contracts;', ending or 0, 'skipped; exact qualified runtime retained', flush=True)


if __name__ == '__main__':
    main()
