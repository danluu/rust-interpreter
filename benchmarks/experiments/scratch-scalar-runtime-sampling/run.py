"""Sample two fresh adopted scratch/scalar VMs; record diagnostic evidence only."""
import argparse
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
from interpreter import installed_tools
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/scalar-runtime-sampling'))
from attribute import attribute, read


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'scratch-scalar-runtime-sampling-\d{2}', args.run_id)
    suffix = args.run_id.rsplit('-', 1)[1]
    lock = (ROOT / '.work/benchmark.lock').open('a')
    acquire_lock(lock, 45)
    require_space(ROOT, 12)
    build_path = ROOT / 'results/scratch-memory-values-build-02/summary.json'
    qualified_path = ROOT / 'results/scratch-memory-values-qualification-01/summary.json'
    profile_path = ROOT / 'results/scratch-memory-values-profile-01/summary.json'
    reference_path = ROOT / 'results/current-runtime-boundaries-02/summary.json'
    build, qualified, profiles, reference = map(read, [build_path, qualified_path, profile_path, reference_path])
    assert build['status'] == qualified['status'] == profiles['status'] == reference['status'] == 'passed'
    assert build['tests'] == dict({'test-debug': 608, 'test-release': 608})
    assert qualified['commands'] == 121 and qualified['scalar_enabled_strict_cargo']
    assert profiles['commands'] == 6 and profiles['exact_per_pc_counts'] and profiles['exact_operation_map_reconstruction']
    key = 'df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
    expected_vm = '6ac4dd9e964e0ebb0a050f8412c8ec8877bd197e8ad7876832db378ed03ca7cf'
    assert build['tool_key'] == qualified['tool_key'] == profiles['tool_key'] == key
    tool, _ = installed_tools(key)
    assert sha(tool / 'rust-interp-vm') == build['binaries']['rust-interp-vm'] == expected_vm
    source = ROOT / build['source_manifest']
    assert sha(source) == build['source_manifest_sha256']
    source_record = read(source)
    paths = [build_path, qualified_path, profile_path, reference_path, source]
    for p, h in source_record['frozen'].items():
        if p.startswith('crates/') or p in ['Cargo.lock', 'Cargo.toml']:
            assert sha(ROOT / p) == h
            paths.append(ROOT / p)
    for name in ['scratch-memory-values-build-02', 'scratch-memory-values-qualification-01', 'scratch-memory-values-profile-01']:
        for filename in ['closure.json', 'terminal.json']:
            p = ROOT / 'results' / name / filename
            record = read(p)
            if filename == 'terminal.json':
                assert record['status'] == 'finished' and record['returncode'] == 0
            else:
                assert record['status'] == 'closed'
                assert record['summary_sha256'] == sha(ROOT / 'results' / name / 'summary.json')
            paths.append(p)
    adoption = ROOT / 'results/scratch-scalar-main-qualification-01'
    adopted, closed = read(adoption / 'summary.json'), read(adoption / 'closure.json')
    assert adopted['status'] == 'passed' and adopted['tool_key'] == key
    assert adopted['all_frozen_inputs_verified'] and closed['status'] == 'closed'
    assert sha(adoption / 'summary.json') == closed['summary_sha256']
    paths += [adoption / n for n in ['summary.json', 'closure.json', 'terminal.json']]
    # The attribution implementation is unchanged; retain its nine completed
    # contracts through exact source/record bindings rather than rerunning them.
    previous = ROOT / '.work/scalar-runtime-sampling-01'
    prior_plan, prior_rows = read(previous / 'plan.json'), read(previous / 'records.json')
    controls, = [r for r in prior_rows if r['label'] == 'controls']
    assert controls['returncode'] == 0
    assert sha(previous / 'controls.stderr') == controls['stderr_sha256']
    assert 'Ran 9 tests' in (previous / 'controls.stderr').read_text()
    for name, digest in prior_plan['frozen'].items():
        if name.startswith('scripts/') or name.startswith((
            'benchmarks/experiments/scalar-runtime-sampling/',
            'benchmarks/experiments/scalar-private-transfers/native_observation.py',
            'benchmarks/experiments/scalar-private-transfers/test_native_observation.py',
            'benchmarks/experiments/operation-map/')):
            assert sha(ROOT / name) == digest, name
            paths.append(ROOT / name)
    paths += [previous / n for n in ['plan.json', 'records.json', 'controls.stdout', 'controls.stderr']]
    paths += [tool / n for n in build['binaries']]
    paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py', '.md']]
    paths += [ROOT / 'scripts' / n for n in ['sample_owned_vm.py', 'summarize_owned_sample.py',
        'compare_saved_runtime.py', 'workflow_io.py', 'interpreter.py', 'supervise_experiment.py']]
    paths += [ROOT / 'benchmarks/experiments' / p for p in [
        'scalar-private-transfers/native_observation.py', 'scalar-private-transfers/test_native_observation.py',
        'operation-map/attribute.py', 'operation-map/maps.py', 'operation-map/test_attribute.py']]
    cases = []
    for index, label in enumerate(['block', 'exhaustive']):
        item, = [p for p in reference['profiles'] if p['index'] == index]
        original, = [p for p in profiles['comparisons'] if p['index'] == index and p['mode'] == 'candidate']
        assert item['name'] == original['name']
        for field in ['artifact', 'catalog']:
            p = ROOT / item[field]
            assert sha(p) == item[field + '_sha256']
            paths.append(p)
        p = ROOT / original['profile_path']
        assert sha(p) == original['profile_sha256']
        paths.append(p)
        cases.append((label, item, p))
    frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    work = ROOT / '.work' / args.run_id
    work.mkdir(exist_ok=False)
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    write(work / 'plan.json', dict(owner=str(ROOT), source_revision=revision, frozen=frozen,
        tool_key=key, vm_sha256=expected_vm, guest_commands=2, expected_child_commands=4,
        reused_controls=9, initial_gib=12, minimum_child_gib=8, sample_seconds=3,
        performance_measurement=False, profile_used_for_static_identity_only=True))
    env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_'))}
    assert not any(k.startswith('DYLD_') for k in env)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    rows, reports = [], []

    def verify():
        assert all(sha(ROOT / p) == h for p, h in frozen.items()), 'frozen input changed'

    def execute(label, command, cwd=ROOT):
        verify()
        require_space(ROOT, 8)
        child, out, err = capture(command, cwd=cwd, env=env, receipt_path=work / 'active.json', receipt=dict(label=label))
        for stream, payload in [('stdout', out), ('stderr', err)]:
            (work / (label + '.' + stream)).write_text(payload)
        rows.append(dict(label=label, pid=child.pid, command=command, returncode=child.returncode,
            stdout_sha256=sha(work / (label + '.stdout')), stderr_sha256=sha(work / (label + '.stderr'))))
        write(work / 'records.json', rows)
        assert child.returncode == 0, err + out
        verify()
        print(label, 'passed', flush=True)
        return out, err

    lock.close()
    for label, item, static_profile in cases:
        run = 'scratch-scalar-runtime-sample-' + label + '-' + suffix
        execute(label + '-sample', [sys.executable, 'scripts/sample_owned_vm.py',
            '--tool-key', key, '--artifact', str(ROOT / item['artifact']), '--artifact-sha256', item['artifact_sha256'],
            '--run-id', run, '--repetitions', '1', '--duration', '3',
            '--instruction-limit', str(item['limits']['instructions']), '--allocation-limit', str(item['limits']['allocations']),
            '--jit-persistent-registers', '--jit-resumable-calls', '--jit-scalar-calls', '--dump-code', '--jit-operation-map',
            '--select-test', item['name'], '--suite-catalog', str(ROOT / item['catalog']),
            '--lock-wait-seconds', '45', '--minimum-free-bytes', str(8 * 1024**3)])
        with (ROOT / '.work/benchmark.lock').open('a') as analysis_lock:
            acquire_lock(analysis_lock, 45)
            execute(label + '-summary', [sys.executable, 'scripts/summarize_owned_sample.py', '--run-id', run])
            require_space(ROOT, 8)
            reports.append(dict(case=label, run_id=run, **attribute(run, static_profile, expected_vm)))
            verify()
            print(label, reports[-1]['by_label'], flush=True)
    verify()
    destination = ROOT / 'results' / args.run_id
    destination.mkdir(exist_ok=False)
    write(destination / 'summary.json', dict(status='passed', tool_key=key, vm_sha256=expected_vm,
        guest_commands=2, commands=len(rows), reused_controls=9, cases=reports,
        all_frozen_inputs_verified=True, raw=str(work.relative_to(ROOT)),
        plan_sha256=sha(work / 'plan.json'), records_sha256=sha(work / 'records.json'),
        performance_measurement=False, profile_used_for_static_identity_only=True))


if __name__ == '__main__':
    main()
