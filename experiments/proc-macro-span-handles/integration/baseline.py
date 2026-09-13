#!/usr/bin/env python3
"""Run the frozen real bridge fixture against the installed, unchanged span store."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'experiments/stable-cgu'))
import custom_compiler as compiler_api
import owned_stage as owned

POLICY = 'native-stock-span-bridge-baseline-v1'
COMPILER_KEY = 'f9fb3e5f59b8567fffd32c936a9864d0baee77038574236710fbcec75a57d33f'
COMPILER_SOURCE = '58e1e1f5311f4424ea81def4763081f6da62d9b3'
FIXTURE_COMMIT = 'c964a9e0bb128372f28f41bd78a72bba1b42d007'
TESTS = (
    'span_transport_grows_and_reuses_handles_in_both_strategies',
    'stale_same_thread_span_reaches_real_dispatcher_and_is_rejected',
    'token_stream_drop_order_survives_span_store_change',
    'nested_dispatch_and_both_panic_boundaries_restore_bridge_state',
)
INPUTS = HERE / 'baseline-inputs.json'
HELPERS = ('scripts/custom_compiler.py', 'scripts/supervise_experiment.py',
           'experiments/stable-cgu/owned_stage.py')


def regular(path):
    owned.require(path.is_file() and not path.is_symlink()
                  and path.resolve(strict=True) == path, 'indirect or missing input: ' + str(path))
    return path.read_bytes()


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def frozen_sources():
    specification = json.loads(regular(INPUTS))
    owned.require(specification['policy'] == POLICY
                  and specification['fixture_commit'] == FIXTURE_COMMIT
                  and specification['compiler_key'] == COMPILER_KEY
                  and specification['compiler_source_commit'] == COMPILER_SOURCE,
                  'different baseline input policy')
    result = {}
    for name, expected in specification['files'].items():
        path = Path(name)
        owned.require(not path.is_absolute() and '..' not in path.parts,
                      'invalid frozen input name')
        data = regular(ROOT / name)
        owned.require(sha_bytes(data) == expected, 'frozen fixture/patch changed: ' + name)
        result[name] = data
    for path in [INPUTS, Path(__file__).resolve(), HERE / 'test_baseline.py',
                 HERE / 'baseline-README.md', *(ROOT / name for name in HELPERS)]:
        result[str(path.relative_to(ROOT))] = regular(path)
    return specification, result


def native_inputs(compiler, specification):
    owned.require(compiler.key == COMPILER_KEY
                  and compiler.identity['provenance']['source_commit'] == COMPILER_SOURCE
                  and compiler.identity['provenance']['stage'] == 2,
                  'baseline requires the exact installed complete Cmono compiler')
    files = compiler.identity['files']
    prefix = 'lib/rustlib/' + compiler.host + '/lib/'
    selected = {'bin/rustc': files['bin/rustc']}
    for crate in ('proc_macro', 'std', 'core', 'alloc', 'test'):
        names = [name for name in files if name.startswith(prefix + 'lib' + crate + '-')
                 and name.endswith('.rlib') and '/' not in name[len(prefix):]]
        owned.require(len(names) == 1, 'missing/ambiguous native ' + crate)
        selected[names[0]] = files[names[0]]
    for name, expected in specification['native_source_files'].items():
        owned.require(files.get(name) == expected, 'native bridge source is not the stock span store')
        selected[name] = expected
    return selected


def environment(compiler, work, inherited):
    owned.require(not any(name.startswith(('DYLD_', 'LD_')) for name in inherited),
                  'dynamic loader overrides are not permitted')
    # This direct-rustc control intentionally inherits no Rust/Cargo/test flags,
    # injected compiler/wrapper, macro state, SDK selection or user PATH. The
    # actual complete allowlisted environment is retained in every receipt.
    env = dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin', LANG='C', LC_ALL='C',
               TMPDIR=str(work / 'tmp'), RUST_TEST_THREADS='1', RUST_BACKTRACE='0')
    if 'HOME' in inherited:
        env['HOME'] = inherited['HOME']
    return compiler.environment(env)


def commands(compiler, work):
    binary = work / 'artifacts/span_bridge_baseline'
    source = work / 'source/experiments/proc-macro-span-handles/integration/bridge.rs'
    return [
        ('compile', [str(compiler.rustc), '--test', '--edition=2024',
                     '--crate-name', 'span_bridge_baseline', '--sysroot', str(compiler.sysroot),
                     '--error-format=json', '--emit=link,dep-info=' + str(work / 'artifacts/bridge.d'),
                     str(source), '-o', str(binary)]),
        ('tests', [str(binary), '--test-threads=1', '--nocapture', '--format=pretty', '--color=never']),
    ]


def test_result(returncode, stdout):
    names = re.findall(r'^test ([A-Za-z0-9_:]+) \.\.\. ok$', stdout, re.MULTILINE)
    summaries = re.findall(
        r'^test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored; '
        r'(\d+) measured; (\d+) filtered out; finished in [^\n]+$', stdout, re.MULTILINE)
    owned.require(returncode == 0 and sorted(names) == sorted(TESTS)
                  and summaries == [('ok', '4', '0', '0', '0', '0')]
                  and re.findall(r'^running (\d+) tests?$', stdout, re.MULTILINE) == ['4'],
                  'bridge harness did not pass all four exact unfiltered controls')
    return dict(passed=4, failed=0, ignored=0, measured=0, filtered=0, exact_names=names)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler-root', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--workload-lock', type=Path, required=True)
    parser.add_argument('--lock-wait-seconds', type=float, default=600)
    args = parser.parse_args()
    owned.require(__debug__ and re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', args.run_id), 'invalid run ID')
    owned.require(args.compiler_root.resolve(strict=True) == args.compiler_root
                  and args.compiler_root.is_dir(), 'compiler owner must be an ordinary absolute directory')
    work = ROOT / '.work' / args.run_id
    owned.require(not (ROOT / '.work').is_symlink(), 'work directory must not redirect ownership')
    work.mkdir(parents=True, exist_ok=False)
    rows = []
    result = dict(policy=POLICY, status='waiting', owner=str(ROOT), work=str(work),
        pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(),
        compiler_key=COMPILER_KEY, fixture_commit=FIXTURE_COMMIT,
        benchmark=False, patched_span_store=False, compiler_rebuilt=False,
        qualification_scope='baseline real Client::run bridge fixture only',
        workload_lock=str(args.workload_lock), lock_wait_seconds=args.lock_wait_seconds)
    owned.write(work / 'result.json', result)
    owned.write(work / 'commands.json', rows)
    try:
        with owned.workload_lock(args.workload_lock, args.lock_wait_seconds):
            result.update(status='admitted', admitted_at=time.time(), free_bytes_before=owned.disk(work))
            owned.write(work / 'result.json', result)
            specification, sources = frozen_sources()
            compiler = compiler_api.load_compiler(args.compiler_root, COMPILER_KEY)
            selected = native_inputs(compiler, specification)
            ready_path = args.compiler_root / '.work/compilers' / COMPILER_KEY / 'ready.json'
            ready = regular(ready_path)
            (work / 'compiler-ready.json').write_bytes(ready)
            for name, data in sources.items():
                destination = work / 'source' / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
            (work / 'tmp').mkdir()
            (work / 'artifacts').mkdir()
            env = environment(compiler, work, os.environ)
            python = Path(sys.executable).resolve(strict=True)
            python_identity = dict(executable=str(python), sha256=owned.sha(python), version=sys.version)
            planned = commands(compiler, work)
            source_hashes = {name: sha_bytes(data) for name, data in sources.items()}
            artifact_hash = None

            def guard():
                owned.require(frozen_sources()[1] == sources, 'baseline source/helper inputs changed')
                owned.require(compiler_api.load_compiler(args.compiler_root, COMPILER_KEY) == compiler
                              and regular(ready_path) == ready, 'installed compiler identity changed')
                owned.require(all(owned.sha(compiler.sysroot / name) == h for name, h in selected.items()),
                              'selected native compiler/library/source bytes changed')
                owned.require(all(regular(work / 'source' / name) == data for name, data in sources.items()),
                              'owned source snapshot changed')
                owned.require(owned.sha(python) == python_identity['sha256'], 'runner Python changed')
                if artifact_hash is not None:
                    owned.require(owned.sha(work / 'artifacts/span_bridge_baseline') == artifact_hash,
                                  'native bridge test executable changed')

            guard()
            owned.write(work / 'plan.json', dict(policy=POLICY, status='prepared for execution',
                compiler_owner=str(args.compiler_root), compiler_key=COMPILER_KEY,
                compiler_sysroot=str(compiler.sysroot), compiler=compiler.identity['compiler'],
                compiler_provenance=compiler.identity['provenance'], native_inputs=selected,
                compiler_ready_sha256=sha_bytes(ready), fixture_commit=FIXTURE_COMMIT,
                inputs=specification, source_files=source_hashes, environment=env, python=python_identity,
                commands=[dict(label=label, argv=command) for label, command in planned],
                expected_tests=list(TESTS), benchmark=False, patched_span_store=False,
                profile='ordinary rustc test defaults; installed native std profile recorded above',
                inherited_environment_names_not_forwarded=sorted(set(os.environ) - {'HOME'})))
            for label, command in planned:
                guard()
                directory = work / 'commands' / label
                try:
                    owned.run(command, cwd=work, env=env, out=directory, capacity_root=work)
                finally:
                    receipt = directory / 'receipt.json'
                    if receipt.is_file():
                        rows.append(json.loads(receipt.read_bytes()))
                        owned.write(work / 'commands.json', rows)
                    guard()
                if label == 'compile':
                    binary = work / 'artifacts/span_bridge_baseline'
                    owned.require(binary.is_file() and not binary.is_symlink()
                                  and os.access(binary, os.X_OK), 'native test binary was not produced')
                    owned.require((work / 'artifacts/bridge.d').is_file(), 'missing native dep-info')
                    artifact_hash = owned.sha(binary)
                    owned.write(work / 'artifact.json', dict(path=str(binary), sha256=artifact_hash,
                        compiler_key=COMPILER_KEY, native_inputs=selected,
                        fixture_sha256=source_hashes['experiments/proc-macro-span-handles/integration/bridge.rs']))
                else:
                    counts = test_result(rows[-1]['returncode'], (directory / 'stdout').read_text())
            guard()
            owned.require(len(rows) == 2 and all(row['returncode'] == 0 for row in rows),
                          'incomplete baseline command history')
            result.update(status='passed', finished_at=time.time(), completed_commands=2,
                artifact_sha256=artifact_hash, frozen_inputs_unchanged=True, **counts,
                plan_sha256=owned.sha(work / 'plan.json'),
                evidence_files={str(p.relative_to(work)): owned.sha(p) for p in sorted(work.rglob('*'))
                                if p.is_file() and p != work / 'result.json'
                                and not p.is_relative_to(work / 'tmp')})
            owned.write(work / 'result.json', result)
            print(json.dumps(dict(status='passed', passed=4, native_commands=2,
                compiler_key=COMPILER_KEY, artifact_sha256=artifact_hash,
                benchmark=False, patched_span_store=False)))
    except BaseException as error:
        result.update(status='failed', finished_at=time.time(), error=repr(error), completed_commands=len(rows))
        owned.write(work / 'result.json', result)
        raise


if __name__ == '__main__':
    main()
