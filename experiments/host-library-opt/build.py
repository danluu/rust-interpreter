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
    args = parser.parse_args()
    path = args.plan.resolve(strict=True)
    plan = json.loads(path.read_bytes())
    require(plan['owner'] == str(ROOT) and plan['qualification_policy'] == HOST_LIBRARY_BUILD_POLICY,
            'not this owned host-library plan')
    source = ROOT / 'benchmarks/experiments/host-proc-macro/build.py'
    spec = importlib.util.spec_from_file_location('recorded_public_build', source)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.execute(path)


if __name__ == '__main__':
    main()
