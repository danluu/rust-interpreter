"""One bounded unittest process; no compiler, provider, network or child calls."""
import json
import os
from pathlib import Path
import resource
import signal
import sys
import unittest

HERE = Path(__file__).resolve().parent
SOURCE = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/old-compiler-directory-modes-01')
REMOVER = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/old-compiler-partial-retirement-01')
OWNER = HERE.parents[1]
WORK = OWNER / '.work/old-compiler-directory-mode-controls-01'
MODULES = ['test_directory_modes']
MAX_FILE = 256 * 1024


def main():
    assert Path.cwd() == SOURCE and sys.dont_write_bytecode and not sys.flags.optimize
    assert Path(os.environ['TMPDIR']) == WORK / 'tmp'
    assert Path(os.environ['TMPDIR']).resolve(strict=True) == WORK / 'tmp'
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_FILE, MAX_FILE))
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    signal.alarm(120)
    # Bound cumulative writable names, not just the final surviving fixture
    # tree. RLIMIT_FSIZE covers every file and both inherited raw streams.
    # This is a resource guard for frozen tests, not a general security sandbox.
    freeze = json.loads((HERE / 'inputs.json').read_bytes())
    writable, directories, local_reads = set(), set(), set()
    def audit(event, args):
        if event.startswith(('subprocess.', 'os.exec', 'os.posix_spawn', 'socket.')) or event in ['os.system', 'os.fork', 'os.forkpty', 'os.kill', 'os.killpg']:
            raise RuntimeError('pure controls cannot launch a process or network connection')
        if event == 'open':
            name, mode, flags = args
            if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                assert isinstance(name, (str, bytes)), 'unattributed writable descriptor open'
                path = Path(os.fsdecode(name)).absolute()
                assert path.resolve(strict=False).is_relative_to(WORK / 'tmp') or path == WORK / 'result.json'
                writable.add(str(path)); assert len(writable) <= 256, 'fixture writable-name cap exceeded'
            elif isinstance(name, (str, bytes)):
                route = Path(os.fsdecode(name))
                if not route.is_absolute():
                    # The audit event omits dir_fd. These exact fixture leaf
                    # opens are anchored by the admitted held-FD helper (or
                    # TemporaryDirectory cleanup), not by the child cwd.
                    assert str(route) in {'tree', 'a', 'deep', 'z', 'root-file',
                                          'payload', 'moved', 'outside', 'keep'}
                    return
                path = route
                if path.resolve(strict=False).is_relative_to(WORK / 'tmp'):
                    return
                if str(path).startswith('/Users/danluu/dev/'):
                    if path.suffix == '.pyc':
                        raise FileNotFoundError('controls require frozen Python source')
                    assert str(path) in freeze['files'], 'unfrozen local input: '+str(path)
                    local_reads.add(str(path))
        elif event in ['os.link', 'os.symlink', 'os.rename']:
            for name in args[:2]:
                path = Path(os.fsdecode(name)).absolute()
                assert path.resolve(strict=False).is_relative_to(WORK / 'tmp'), 'fixture mutation escapes temporary tree'
        elif event == 'os.mkdir':
            name, mode, directory_fd = args
            assert directory_fd == -1, 'unattributed relative directory creation'
            path = Path(os.fsdecode(name)).absolute()
            assert path.resolve(strict=False).is_relative_to(WORK / 'tmp')
            directories.add(str(path)); assert len(directories) <= 2048, 'fixture directory cap exceeded'
    sys.addaudithook(audit)
    sys.path.insert(0, str(REMOVER))
    sys.path.insert(0, str(SOURCE))
    suite = unittest.defaultTestLoader.loadTestsFromNames(MODULES)
    expected = freeze['expected_names']
    def names(item):
        if isinstance(item, unittest.TestSuite):
            return [name for test in item for name in names(test)]
        return [item.id()]
    assert sorted(names(suite)) == expected and len(expected) == freeze['controls'] == 10
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    for module in list(sys.modules.values()):
        path = getattr(module, '__file__', None)
        if path and path.startswith('/Users/danluu/dev/'):
            assert str(Path(path).resolve(strict=True)) in freeze['files'], path
    report = dict(status='passed' if result.wasSuccessful() else 'failed', tests_run=result.testsRun,
                  failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
                  expected_failures=len(result.expectedFailures), unexpected_successes=len(result.unexpectedSuccesses),
                  expected_names=expected, local_reads=sorted(local_reads), writable_names=len(writable), directories=len(directories),
                  maximum_file_bytes=MAX_FILE, maximum_writable_names=256,
                  maximum_directory_names=2048, child_processes=0, compiler_calls=0, provider_probes=0, network_calls=0, signal_calls=0)
    (WORK / 'result.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    assert result.wasSuccessful() and result.testsRun == freeze['controls'] and not result.skipped
    assert not result.expectedFailures and not result.unexpectedSuccesses
    signal.alarm(0)


if __name__ == '__main__':
    main()
