"""Freeze the direct POSIX-check comparison without running controls or lookups."""
import ast
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PRIOR = ROOT / 'experiments/runtime-lookup'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')


def main():
    assert Path.cwd() == ROOT and sys.dont_write_bytecode and not sys.flags.optimize
    plan = json.loads((PRIOR / 'plan.json').read_bytes())
    for row in plan['children']:
        row['command'] = [arg.replace(str(PRIOR / 'measure.py'), str(HERE / 'measure.py'))
                          for arg in row['command']]
    plan['environment']['__CF_USER_TEXT_ENCODING'] = '0x1F5:0x0:0x0'
    plan.update(baseline_commit='237510c3', baseline_sha256=sha(HERE / 'baseline_runtime_compiler.py'),
                candidate_sha256=sha(ROOT / 'scripts/runtime_compiler.py'),
                application_benchmark=False, performance_target_qualified=False,
                adoption_policy='README.md: all controls and identities; both paired medians and order strata negative; >=10/12 better pairs per metric')
    write(HERE / 'plan.json', plan)
    prior = json.loads((PRIOR / 'inputs.json').read_bytes())
    files = [Path(name) for name in prior['files'] if not Path(name).is_relative_to(PRIOR)]
    files += [HERE / name for name in ('prepare.py', 'run.py', 'measure.py',
              'baseline_runtime_compiler.py', 'README.md', 'plan.json')]
    files += [PRIOR / 'plan.json', PRIOR / 'inputs.json']
    files = sorted(set(files))
    assert all(path.is_file() and path.resolve(strict=True) == path for path in files)
    frozen = dict(files={str(path): sha(path) for path in files},
                  python=dict(path=str(Path(sys.executable).resolve()), sha256=sha(sys.executable)))
    write(HERE / 'inputs.json', frozen)
    python = '/opt/homebrew/bin/python3'
    launch = dict(cwd=str(ROOT), environment=plan['environment'],
        command=[python, '-B', str(ROOT / 'scripts/supervise_experiment.py'), '--run-id',
                 'runtime-relative-lookup-supervisor-01', '--', python, '-B',
                 str(HERE / 'run.py'), sha(HERE / 'inputs.json')],
        helper_sha256=sha(HERE / 'run.py'), plan_sha256=sha(HERE / 'plan.json'),
        inputs_sha256=sha(HERE / 'inputs.json'), status='prepared-unexecuted')
    write(HERE / 'launch.json', launch)
    for name in ('prepare.py', 'run.py', 'measure.py'):
        ast.parse((HERE / name).read_bytes())
    print(json.dumps(dict(launch_sha256=sha(HERE / 'launch.json'),
                         inputs_sha256=launch['inputs_sha256'], files=len(files),
                         bytes=sum(path.stat().st_size for path in files)), sort_keys=True))


if __name__ == '__main__':
    main()
