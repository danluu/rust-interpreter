"""Freeze a saved-output continuation; never repeat the eighteen frontend commands."""
import ast
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('exporter_frontend_continue', HERE / 'continue.py')
c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)


def ref(path):
    return dict(path=str(path), sha256=c.sha(path))


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True); stream.write('\n')


def main():
    prior = c.read(c.f.HERE / 'inputs.json')
    control_path = c.OWNER / '.work/runtime-exporter-telemetry-controls-01/summary.json'
    control = c.read(control_path)
    assert control['status'] == 'passed' and control['controls'] == 8
    assert control['helper_sha256'] == c.sha(HERE / 'telemetry.py')
    terminal = c.read(c.f.WORK / 'receipt.json')
    assert c.sha(c.f.WORK / 'receipt.json') == 'f939f98a0912eb6bd151006a4cfcabf8b72d4ce1050c712839de6242e727a5b6'
    assert terminal['status'] == 'failed' and len(terminal['commands']) == 32
    plan = dict(c.read(c.f.HERE / 'plan.json'))
    plan.update(policy='runtime-exporter-frontend-continuation-v1', status='prepared-unexecuted',
        failed_frontend_plan=ref(c.f.HERE / 'plan.json'), failed_frontend_receipt=ref(c.f.WORK / 'receipt.json'),
        failed_tool_closures=ref(c.f.WORK / 'tool-closures.json'), children=plan['children'][32:],
        completed_compiler_commands_rerun=0, saved_frontend_commands=18, actual_postguard_commands=8,
        direct_frontend_controls=0, fresh_binary_otool_commands=0, retained_binary_otool_commands=6,
        comparison_contract='Lossless known telemetry separation; raw compiler diagnostic bytes equal; unknown lines rejected',
        telemetry_source=ref(HERE / 'telemetry.py'), telemetry_controls=ref(control_path), prior_failed_attempt_preserved=True)
    assert len(plan['children']) == 8
    write(HERE / 'plan.json', plan)
    files = dict(prior['files'])
    additions = [HERE / name for name in ('continue.py', 'telemetry.py', 'test_telemetry.py', 'prepare.py', 'plan.json')]
    additions += [c.f.HERE / 'inputs.json', c.f.HERE / 'launch.json',
        c.OWNER / '.work/runtime-exporter-frontend-launch-01.actual.json',
        c.OWNER / '.work/runtime-exporter-telemetry-controls-launch-01.actual.json',
        c.OWNER / '.work/runtime-exporter-telemetry-controls-independent-verification-01.json',
        c.OWNER / '.work/run_runtime_exporter_telemetry_controls_01.py',
        c.OWNER / '.work/runtime-exporter-telemetry-controls-inputs-01.json',
        c.OWNER / '.work/runtime-exporter-telemetry-controls-launch-01.json']
    for directory in (c.f.WORK, c.OWNER / '.work/experiments/runtime-exporter-frontend-supervisor-01',
                      c.OWNER / '.work/runtime-exporter-telemetry-controls-01',
                      c.OWNER / '.work/experiments/runtime-exporter-telemetry-controls-supervisor-01'):
        additions += c.m.ordinary_files(directory)
    for path in additions:
        row = c.m.file_record(path)
        assert str(path) not in files or files[str(path)] == row['sha256']
        files[str(path)] = row['sha256']
    for path, value in files.items(): assert c.sha(path) == value, path
    frozen = dict(schema_version=1, files=files, plan_sha256=c.sha(HERE / 'plan.json'),
                  python=prior['python'], launch_environment=prior['launch_environment'], status='source-only-unexecuted')
    write(HERE / 'inputs.json', frozen)
    python = frozen['python']['path']; supervisor = c.OWNER / 'scripts/supervise_experiment.py'
    launch = dict(status='prepared-unexecuted-awaiting-root-review', owner=str(c.OWNER), environment=frozen['launch_environment'],
        command=[python, '-B', str(supervisor), '--run-id', 'runtime-exporter-frontend-continue-supervisor-01', '--',
                 python, '-B', str(HERE / 'continue.py'), '--inputs-sha256', c.sha(HERE / 'inputs.json')],
        helper=ref(HERE / 'continue.py'), inputs=ref(HERE / 'inputs.json'), plan=ref(HERE / 'plan.json'),
        supervisor=ref(supervisor), python=frozen['python'], expected_children=8, capacity=plan['capacity'],
        canonical_lock=plan['canonical_lock'], wait_seconds=600, exporter_builds=0, VM_builds=0,
        compiler_builds=0, publication=False, guest_execution=False, benchmark=False, completed_compiler_commands_rerun=0)
    write(HERE / 'launch.json', launch)
    for name in ('continue.py', 'telemetry.py', 'test_telemetry.py', 'prepare.py'): ast.parse((HERE / name).read_text())
    print(json.dumps(dict(launch=ref(HERE / 'launch.json'), helper=launch['helper'], inputs=launch['inputs'],
                         plan=launch['plan'], files=len(files)), indent=2))


if __name__ == '__main__':
    main()
