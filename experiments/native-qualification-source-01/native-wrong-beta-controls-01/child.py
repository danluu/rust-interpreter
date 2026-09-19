"""One bounded unittest process; no compiler, provider, network or child calls."""
import json
import os
from pathlib import Path
import resource
import signal
import sys
import unittest

HERE = Path(__file__).resolve().parent
SOURCE = HERE.with_name('hir-options-hash-native-reconciliation-01')
OWNER = HERE.parents[1]
WORK = OWNER / '.work/native-wrong-beta-controls-01'
MODULES = ['test_wrong_beta']
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
    writable, directories = set(), set()
    def audit(event, args):
        if event.startswith(('subprocess.', 'os.exec', 'os.posix_spawn')) or event in ['os.system', 'socket.connect', 'os.kill', 'os.killpg']:
            raise RuntimeError('pure controls cannot launch a process or network connection')
        if event == 'open':
            name, mode, flags = args
            if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                assert isinstance(name, (str, bytes)), 'unattributed writable descriptor open'
                path = Path(os.fsdecode(name)).absolute()
                assert path.resolve(strict=False).is_relative_to(WORK / 'tmp') or path == WORK / 'result.json'
                writable.add(str(path)); assert len(writable) <= 256, 'fixture writable-name cap exceeded'
        elif event == 'os.mkdir':
            name, mode, directory_fd = args
            assert directory_fd == -1, 'unattributed relative directory creation'
            path = Path(os.fsdecode(name)).absolute()
            assert path.resolve(strict=False).is_relative_to(WORK / 'tmp')
            directories.add(str(path)); assert len(directories) <= 2048, 'fixture directory cap exceeded'
    sys.addaudithook(audit)
    sys.path.insert(0, str(SOURCE))
    suite = unittest.defaultTestLoader.loadTestsFromNames(MODULES)
    expected = json.loads((HERE / 'inputs.json').read_bytes())['expected_names']
    def names(item):
        if isinstance(item, unittest.TestSuite):
            return [name for test in item for name in names(test)]
        return [item.id()]
    assert sorted(names(suite)) == expected and len(expected) == 11
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    freeze = json.loads((HERE / 'inputs.json').read_bytes())
    for module in list(sys.modules.values()):
        path = getattr(module, '__file__', None)
        if path and path.startswith('/Users/danluu/dev/'):
            assert str(Path(path).resolve(strict=True)) in freeze['files'], path
    report = dict(status='passed' if result.wasSuccessful() else 'failed', tests_run=result.testsRun,
                  failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
                  expected_failures=len(result.expectedFailures), unexpected_successes=len(result.unexpectedSuccesses),
                  expected_names=expected, writable_names=len(writable), directories=len(directories),
                  maximum_file_bytes=MAX_FILE, maximum_writable_names=256,
                  maximum_directory_names=2048, child_processes=0, compiler_calls=0)
    (WORK / 'result.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    assert result.wasSuccessful() and result.testsRun == 11 and not result.skipped
    assert not result.expectedFailures and not result.unexpectedSuccesses
    signal.alarm(0)


if __name__ == '__main__':
    main()
