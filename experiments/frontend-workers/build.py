#!/usr/bin/env python3
"""Use the shared public build, then qualify the final key; never time a screen."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock
from custom_compiler import file_digest, require
from frontend_worker_screen import BUILD_POLICY, public_build, validate_qualification
from public_tool_publication import materialize_screen_command, retained_command
from qualified_public_tools import validate_live_inputs
from workflow_io import write_json


def shared_builder():
    path = ROOT / 'benchmarks/experiments/host-proc-macro/build.py'
    spec = importlib.util.spec_from_file_location('recorded_public_build', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def qualification_handoff(plan, publication):
    owner = Path(plan['screen_owner'])
    key = publication['tool_key']
    require(publication['status'] == 'published' and {p['owner'] for p in publication['installations']} ==
            {plan['owner'], str(owner)}, 'worker build lacks both owned publications')
    public = public_build(owner / '.work/interpreter-tools' / key, key, Path.read_bytes)
    require(public['plan'] == plan, 'worker publication belongs to another plan')
    validate_live_inputs(public, rehash=True)
    # Qualification executes in the same owner as the existing shared std and
    # eventual screen. Integration must preserve the actual compiled sources.
    required = dict(plan['workspace_sources'])
    required.update({p: h for p, h in plan['harness'].items() if p.startswith(('scripts/', 'experiments/frontend-workers/'))})
    for name, expected in required.items():
        path = owner / name
        require(path.resolve(strict=True) == path and file_digest(path) == expected,
                'worker qualification source/harness is not integrated: ' + name)
    request = plan['worker_qualification']
    argv = [request['python'], str(owner / 'experiments/frontend-workers/qualify.py'),
        '--tool-key', key, '--run-dir', request['run_dir'], '--lock', plan['workload_admission']['lock'],
        '--lock-wait-seconds', str(plan['workload_admission']['wait_seconds'])]
    return public, argv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--qualify', type=Path, metavar='PUBLISHED_JSON')
    mode.add_argument('--materialize', type=Path, metavar='PUBLISHED_JSON')
    args = parser.parse_args()
    path = args.plan.resolve(strict=True)
    plan = json.loads(path.read_bytes())
    require(plan['owner'] == str(ROOT) and plan['qualification_policy'] == BUILD_POLICY,
            'not this owned worker build plan')
    if not args.qualify and not args.materialize:
        shared_builder().execute(path)
        return
    publication = json.loads((args.qualify or args.materialize).read_bytes())
    with Path(plan['workload_admission']['lock']).open('a') as lock:
        acquire_lock(lock, plan['workload_admission']['wait_seconds'])
        if args.materialize:
            result = materialize_screen_command(plan, publication, output=plan['screen_request']['materialize_to'])
            print(json.dumps(result))
            return
        public, command = qualification_handoff(plan, publication)
        work = Path(plan['commands'][0]['receipt']).parent
        destination = work / 'qualification-handoff.json'
        require(not destination.exists(), 'worker qualification handoff already exists; retain this attempt')
        write_json(destination, dict(status='ready-for-separate-qualification-admission', argv=command,
            tool_key=publication['tool_key'], performance_claim=False, commands_expected=30))
    # The qualifier acquires the canonical lock itself. Never hold a parent
    # lock while waiting for that child. retained_command always drains/waits.
    environment = {k: v for k, v in os.environ.items()
        if not k.startswith(tuple(plan['clean_environment']['remove_prefixes']))
        and k not in plan['clean_environment']['remove']}
    require(not any(k.startswith(('LD_', 'DYLD_')) for k in environment), 'loader override is unsupported')
    retained_command(command, cwd=plan['screen_owner'], env=environment,
                     directory=work, label='worker-qualification')
    shared = plan['shared_std']; compiler = public['composition']['public_compiler']
    std = dict(shared, rustc=compiler['rustc_path'], rustc_sha256=compiler['rustc_sha256'],
               sysroot=str(Path(shared['path']).parent / 'sysroot'))
    with Path(plan['workload_admission']['lock']).open('a') as lock:
        acquire_lock(lock, plan['workload_admission']['wait_seconds'])
        checked = validate_qualification(plan['worker_qualification']['result'], publication['tool_key'],
                                         public, std, Path.read_bytes)
        write_json(work / 'worker-qualified.json', checked)
    print(json.dumps(dict(status='worker-qualified', tool_key=publication['tool_key'],
                         commands=30, screen_executed=False)))


if __name__ == '__main__':
    main()
