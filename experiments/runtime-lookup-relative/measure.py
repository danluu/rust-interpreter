"""Compare real immutable installation lookup with identical validation inputs."""
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OWNER = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
RKEY = 'eca3d1317ba4c852d64de435aa0f0e5d87ae63bd4eb96cfafacc7b0a85841d03'
SKEY = 'e4d1cd29bf4dbac5f9cbf6a92c77a562b89f7079c4474653f180346a00f24b63'
sys.path.insert(0, str(ROOT / 'scripts'))
import runtime_compiler
import std_mir_source_paths


def main():
    # Import both implementations in both worker modes. Imports stay outside
    # the component clock; process totals still are not ordinary launcher time.
    spec = importlib.util.spec_from_file_location('baseline_runtime_compiler',
        Path(__file__).with_name('baseline_runtime_compiler.py'))
    baseline = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = baseline
    spec.loader.exec_module(baseline)
    if sys.argv[1:] == ['baseline']:
        compiler_module = baseline
    elif sys.argv[1:] == ['candidate']:
        compiler_module = runtime_compiler
    else:
        raise RuntimeError('select baseline or candidate')
    start_cpu, start = time.process_time(), time.perf_counter()
    compiler = compiler_module.load_runtime_compiler(OWNER, RKEY)
    middle = time.perf_counter()
    std = std_mir_source_paths.load(OWNER, SKEY, compiler, 'immutable-source-paths-v2:shared')
    end, end_cpu = time.perf_counter(), time.process_time()
    print(json.dumps(dict(mode=sys.argv[1], runtime_key=compiler.key, std_key=std[2],
        runtime_sysroot=str(compiler.sysroot), std_sysroot=str(std[0]),
        identity_digest=runtime_compiler.digest(compiler.identity),
        runtime_seconds=middle-start, std_seconds=end-middle, lookup_seconds=end-start,
        lookup_cpu_seconds=end_cpu-start_cpu)))


if __name__ == '__main__':
    main()
