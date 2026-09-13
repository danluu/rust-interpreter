"""Qualify the exact guarded VM/current compiler combination, without retiming."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write


def main():
    run = 'guarded-ranges-main-qualification-01'
    build_path = ROOT / 'results/guarded-ranges-main-compose-01/summary.json'
    harness_path = ROOT / 'results/guarded-ranges-main-python-tests-01/summary.json'
    build, harness = [json.loads(p.read_text()) for p in [build_path, harness_path]]
    assert build['status'] == harness['status'] == 'passed'
    assert build['tests_reused_from'] == 'guarded-ranges-build-01'
    assert harness['tests'] == 132 and harness['skipped'] == 10
    inputs = ROOT / harness['raw'] / 'inputs.json'
    assert sha(inputs) == harness['inputs_sha256']
    frozen = json.loads(inputs.read_text())
    for p in [build_path, harness_path, inputs]: frozen[str(p.relative_to(ROOT))] = sha(p)
    folder = ROOT / '.work/interpreter-tools' / build['tool_key']
    for name, digest in build['binaries'].items():
        assert sha(folder / name) == digest
        frozen[str((folder / name).relative_to(ROOT))] = digest
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
           and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                         'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR',
                         'CARGO_BUILD_TARGET', 'CARGO_BUILD_BUILD_DIR', 'RUST_TEST_THREADS']}
    assert not any(k.startswith('DYLD_') for k in env)
    env.update(PYTHONDONTWRITEBYTECODE='1', CARGO_TERM_COLOR='never')
    work = ROOT / '.work' / run
    work.mkdir(exist_ok=False)
    records = []
    write(work / 'plan.json', dict(owner=str(ROOT), tool_key=build['tool_key'], frozen=frozen,
          commands=263, performance_measurement=False, stages=['cache', 'cargo', 'projects']))
    stages = [
        ('cache', 203, 'guarded-ranges-cache-02',
         [sys.executable, str(ROOT / 'benchmarks/experiments/composed-development/qualify_cache.py'),
          '--run-id', 'guarded-ranges-cache-02', '--build', str(build_path),
          '--automatic-cache', '--guarded-ranges-candidate']),
        ('cargo', 20, 'guarded-ranges-main-cargo-01',
         [sys.executable, str(Path(__file__).with_name('qualify_cargo.py')),
          '--run-id', 'guarded-ranges-main-cargo-01', '--build', str(build_path), '--harness', str(harness_path)]),
        ('projects', 40, 'guarded-ranges-main-projects-01',
         [sys.executable, str(Path(__file__).with_name('qualify_projects.py')),
          '--run-id', 'guarded-ranges-main-projects-01', '--build', str(build_path), '--harness', str(harness_path)]),
    ]
    for label, expected, name, command in stages:
        assert all(sha(ROOT / p) == digest for p, digest in frozen.items())
        child, out, err = capture(command, cwd=ROOT, env=env,
            receipt_path=work / 'active.json', receipt=dict(stage=label))
        for suffix, text in [('stdout', out), ('stderr', err)]:
            (work / (label + '.' + suffix)).write_text(text)
        row = dict(stage=label, pid=child.pid, command=command, returncode=child.returncode,
                   stdout_sha256=sha(work / (label + '.stdout')), stderr_sha256=sha(work / (label + '.stderr')))
        records.append(row)
        write(work / 'records.json', records)
        assert child.returncode == 0, err[-6000:]
        path = ROOT / 'results' / name / 'summary.json'
        proof = json.loads(path.read_text())
        assert proof['status'] == 'passed' and proof['commands'] == expected
        if label == 'cargo':
            assert proof['tool_keys'] == dict(baseline=build['tool_key'], candidate=build['tool_key'])
        else:
            assert proof['tool_key'] == build['tool_key']
        row.update(commands=expected, summary=str(path.relative_to(ROOT)), summary_sha256=sha(path))
        write(work / 'records.json', records)
        print(label, expected, 'commands passed', flush=True)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        assert all(sha(ROOT / p) == digest for p, digest in frozen.items())
        assert all(sha(ROOT / r['summary']) == r['summary_sha256'] for r in records)
        assert sum(r['commands'] for r in records) == 263
        destination = ROOT / 'results' / run
        destination.mkdir(exist_ok=False)
        write(destination / 'summary.json', dict(status='passed', commands=263, tool_key=build['tool_key'],
              performance_measurement=False, private_details_redacted=True, stages=records,
              exact_measured_vm=True, component_tests_reused=True, complete_tool_qualified=True,
              raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'), records_sha256=sha(work / 'records.json')))


if __name__ == '__main__':
    main()
