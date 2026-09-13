#!/usr/bin/env python3
"""Run the shared public build and three host-library histories; never a screen."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from custom_compiler import require
from qualified_public_tools import HOST_LIBRARY_BUILD_POLICY


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--materialize', type=Path, metavar='PUBLISHED_JSON')
    args = parser.parse_args()
    path = args.plan.resolve(strict=True)
    plan = json.loads(path.read_bytes())
    require(plan['owner'] == str(ROOT) and plan['qualification_policy'] == HOST_LIBRARY_BUILD_POLICY,
            'not this owned host-library plan')
    if args.materialize:
        from compare_saved_runtime import acquire_lock
        from host_library_screen import CAMPAIGN_LOCK
        from public_tool_publication import materialize_screen_command
        require(Path(plan['workload_admission']['lock']) == CAMPAIGN_LOCK, 'unexpected host-library lock')
        with CAMPAIGN_LOCK.open('a') as lock:
            acquire_lock(lock, plan['workload_admission']['wait_seconds'])
            result = materialize_screen_command(plan, json.loads(args.materialize.read_bytes()),
                                                output=plan['screen_request']['materialize_to'])
        print(json.dumps(result))
        return
    source = ROOT / 'benchmarks/experiments/host-proc-macro/build.py'
    spec = importlib.util.spec_from_file_location('recorded_public_build', source)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.execute(path)


if __name__ == '__main__':
    main()
