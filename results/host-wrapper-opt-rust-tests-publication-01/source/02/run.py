"""Four bound std-only Rust test crates; no Cargo/exporter build or timing."""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
WORK = ROOT / '.work/host-wrapper-opt-rust-tests-02'
OUT = ROOT / 'results/host-wrapper-opt-rust-tests-02'
LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
UTIL = ROOT / 'experiments/host-build-opt-01/qualify-fixture-02.py'
IO = R / 'scripts/workflow_io.py'
CRATES = ('host_codegen', 'host_library', 'host_proc_macro', 'wrapper_route')


def require(value, message):
    if not value:
        raise RuntimeError(message)


def file(path):
    path = Path(path)
    def stamp():
        s = path.lstat()
        return [s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns]
    before = stamp()
    require(stat.S_ISREG(before[2]), 'ordinary source/tool file required')
    digest = hashlib.sha256()
    length = 0
    with path.open('rb') as stream:
        while block := stream.read(2**20):
            digest.update(block)
            length += len(block)
    require(stamp() == before and length == before[4], 'input changed while reading')
    return dict(path=str(path), sha256=digest.hexdigest(), bytes=length, identity=before)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_names(path):
    text = Path(path).read_text()
    names = re.findall(r'#\[test\]\s*fn\s+(\w+)\s*\(', text)
    require(names and len(names) == len(set(names)) and '#[ignore' not in text,
            'finite explicit tests without ignored cases')
    return sorted(names)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--binding', type=Path, required=True)
    parser.add_argument('--binding-sha256', required=True)
    args = parser.parse_args()
    require(sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd() == R,
            'exact -B/unoptimized Python/R cwd')
    raw = args.binding.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == args.binding_sha256, 'binding hash')
    binding = json.loads(raw)
    require(binding['schema_version'] == 1 and binding['policy'] == 'host-wrapper-std-only-tests-v1', 'binding policy')
    require(list(binding['tests']) == sorted(CRATES), 'four fixed test crates')
    needed = {str(HERE/'run.py'), str(UTIL), str(IO)}
    needed.update(row['source'] for row in binding['tests'].values())
    source_root = ROOT/'experiments/host-wrapper-opt-01/crates/mir-export/src'
    needed.update(str(source_root/name) for name in ('wrapper_route.rs', 'host_proc_macro.rs'))
    require(needed <= set(binding['sources']), 'complete local executable source closure')
    # Authenticate task Python before import. The complete compiler/source inputs
    # are read under canonical before any child, then fully read again afterward.
    for path in needed:
        require(file(path)['sha256'] == binding['sources'][path], 'pre-import source changed')
    utils = load(UTIL, 'host_wrapper_rust_test_utilities')
    utils.WORK, utils.OUT = WORK, OUT
    io = load(IO, 'host_wrapper_rust_test_io')
    require(not os.path.lexists(WORK) and not os.path.lexists(OUT), 'fresh outputs required')
    with LOCK.open('r') as lock:
        deadline = time.monotonic() + 600
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                require(time.monotonic() < deadline, 'canonical wait exceeded600s')
                time.sleep(.1)
        require(shutil.disk_usage(ROOT).free >= 2**30, 'entry requires1GiB free')
        WORK.mkdir(); OUT.mkdir()
        for name in ('fixture', 'tmp', 'bin'):
            (WORK/name).mkdir()
        record = dict(status='running', pid=os.getpid(), parent_pid=os.getppid(),
            argv=sys.argv, cwd=str(Path.cwd()), started_at=time.time(), binding=file(args.binding),
            benchmark=False, bytecode_qualified=False, full_exporter_qualified=False,
            no_signals=True, retries=0)
        utils.write(OUT/'record.json', record)
        try:
            before = {p:file(p) for p in binding['sources']}
            require(all(before[p]['sha256'] == sha for p,sha in binding['sources'].items()), 'source/compiler input changed')
            utils.write(OUT/'source-before.json', before)
            tools_before = {p:file(p) for p in binding['tools']}
            require(all(tools_before[p]['sha256'] == sha for p,sha in binding['tools'].items()), 'tool changed')
            utils.write(OUT/'tools-before.json', tools_before)
            fixture = json.loads(Path(binding['fixture_binding']['path']).read_bytes())
            require(file(binding['fixture_binding']['path'])['sha256'] == binding['fixture_binding']['sha256'], 'closed fixture binding')
            require(binding['compiler_roles'] == fixture['compiler_roles'], 'same proven D2/B3 recipe')
            roles = binding['compiler_roles']
            environment = {k:os.environ[k] for k in ('HOME','PATH','USER','LOGNAME') if k in os.environ}
            environment.update(TMPDIR=str(WORK/'tmp'), LANG='C', LC_ALL='C',
                PYTHONDONTWRITEBYTECODE='1', RUST_BACKTRACE='0',
                RUST_INTERP_RUNTIME_COMPILER=roles['runtime']['executable']['path'],
                RUST_INTERP_SYSROOT=roles['runtime']['default_sysroot'],
                RUST_INTERP_RUSTC_COMMIT=roles['runtime_source_commit'])
            results = []
            for name in CRATES:
                row = binding['tests'][name]
                require(test_names(row['source']) == row['names'], 'expected names differ from unchanged source')
                executable = WORK/'bin'/name
                command = [roles['build']['executable']['path'], '--edition=2024', '--test',
                    '--crate-name', name, *roles['build_rustflags'], '-Copt-level=0', '-Cdebuginfo=0',
                    row['source'], '-o', str(executable)]
                utils.invoke(command, environment, 'compile-'+name, io)
                built = file(executable)
                stdout, stderr = utils.invoke([str(executable), '--test-threads=1'], environment, 'test-'+name, io)
                actual = re.findall(r'^test ([A-Za-z0-9_:]+) \.\.\. ok$', stdout, re.M)
                require(sorted(actual) == row['names'] and len(actual) == len(set(actual)), 'actual exact Rust test names')
                require(f'test result: ok. {len(actual)} passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;' in stdout,
                        'complete unfiltered Rust test result')
                require(not stderr and file(executable) == built, 'test stderr or executable changed')
                results.append(dict(crate=name, names=actual, executable=built))
            after = {p:file(p) for p in binding['sources']}
            tools_after = {p:file(p) for p in binding['tools']}
            require(after == before and tools_after == tools_before, 'source/tool changes')
            utils.write(OUT/'source-after.json', after)
            utils.write(OUT/'tools-after.json', tools_after)
            result = dict(status='passed', suites=results, tests=sum(len(r['names']) for r in results),
                commands=8, benchmark=False, bytecode_qualified=False, full_exporter_qualified=False,
                compiler_roles_cargo_suite_run=False, footprint=utils.footprint())
            utils.write(OUT/'result.json', result)
            record.update(status='passed', result=file(OUT/'result.json'))
        except BaseException as error:
            record.update(status='failed', error=repr(error))
            raise
        finally:
            record.update(finished_at=time.time())
            utils.write(OUT/'record.json', record)


if __name__ == '__main__':
    main()
