"""Small process/receipt failure checks; no Rust compilation or benchmarks."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DRIVER = load('strict_warm_profile_under_test', HERE / 'profile.py')
STDOUT = b'compiler stdout\n' * 2048
STDERR = b'compiler stderr\n' * 65536


class ProfileProcesses(unittest.TestCase):
    def wrapper(self, folder, *, fail_receipt=False, pass_fds=()):
        compiler = folder / 'rustc'
        compiler.write_text('#!' + sys.executable + '\n' + '''
import json, os, sys
from pathlib import Path
root = Path(os.environ['PROFILE_TEST_ROOT'])
proof = {'args': sys.argv[1:]}
if 'PROFILE_TEST_FD' in os.environ:
    proof['jobserver_token'] = os.read(int(os.environ['PROFILE_TEST_FD']), 1).decode()
(root / 'compiler.json').write_text(json.dumps(proof))
for fd, data in [(1, b'compiler stdout\\n' * 2048), (2, b'compiler stderr\\n' * 65536)]:
    while data:
        data = data[os.write(fd, data):]
(root / 'completed').write_text('done')
sys.exit(int(os.environ['PROFILE_TEST_EXIT']))
''')
        compiler.chmod(0o755)
        (folder / 'units').mkdir()
        # The harness records completion before independent cleanup. A broken
        # wrapper fails the assertion but never leaves its fake compiler behind.
        harness = '''
import importlib.util, json, os, subprocess, sys
from pathlib import Path
root = Path(os.environ['PROFILE_TEST_ROOT'])
spec = importlib.util.spec_from_file_location('wrapper_under_test', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
children = []
real_popen = subprocess.Popen
def tracked(*args, **kwargs):
    child = real_popen(*args, **kwargs)
    children.append(child)
    return child
module.subprocess.Popen = tracked
real_write = module.write_json
def receipt(path, value):
    if os.environ['PROFILE_TEST_FAIL'] == '1' and value['status'] == 'running':
        raise OSError('simulated receipt storage failure')
    return real_write(path, value)
module.write_json = receipt
sys.argv = [sys.argv[1], str(root / 'rustc'), '--emit=metadata', 'input.rs']
outcome = {'unexpected_failure': True}
try:
    code = module.main()
    outcome = {'code': code}
except BaseException as error:
    code = 23 if isinstance(error, OSError) else 24
    outcome = {'error': str(error)}
finally:
    outcome['completed_before_cleanup'] = (root / 'completed').exists()
    for child in children:
        child.communicate()
    (root / 'outcome.json').write_text(json.dumps(outcome))
sys.exit(code)
'''
        env = dict(os.environ, PROFILE_TEST_ROOT=str(folder),
                   PROFILE_TEST_FAIL='1' if fail_receipt else '0',
                   PROFILE_TEST_EXIT='0' if fail_receipt else '17',
                   STRICT_WARM_PROFILE_UNITS=str(folder / 'units'),
                   STRICT_WARM_PROFILE_PHASES='1',
                   STRICT_WARM_PROFILE_REAL_WRAPPER=str(compiler))
        if pass_fds:
            env['PROFILE_TEST_FD'] = str(pass_fds[0])
            env['CARGO_MAKEFLAGS'] = '--jobserver-auth=' + ','.join(map(str, pass_fds))
        command = [sys.executable, '-c', harness, str(HERE / 'profile_wrapper.py')]
        with (folder / 'stdout').open('wb') as stdout, (folder / 'stderr').open('wb') as stderr:
            child = subprocess.Popen(command, cwd=folder, env=env,
                                     stdout=stdout, stderr=stderr, pass_fds=pass_fds)
            try:
                (folder / 'child.json').write_text(json.dumps(dict(pid=child.pid,
                    parent_pid=os.getpid(), command=command, cwd=str(folder))))
            finally:
                child.wait()
        return child.returncode, json.loads((folder / 'outcome.json').read_text())

    def test_wrapper_preserves_large_streams_exit_status_and_jobserver(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            read_fd, write_fd = os.pipe()
            try:
                os.write(write_fd, b'+')
                code, outcome = self.wrapper(folder, pass_fds=(read_fd, write_fd))
            finally:
                os.close(read_fd)
                os.close(write_fd)
            self.assertEqual(code, 17)
            self.assertTrue(outcome['completed_before_cleanup'])
            self.assertEqual((folder / 'stdout').read_bytes(), STDOUT)
            self.assertEqual((folder / 'stderr').read_bytes(), STDERR)
            proof = json.loads((folder / 'compiler.json').read_text())
            self.assertEqual(proof['jobserver_token'], '+')
            self.assertEqual(proof['args'], [str(folder / 'rustc'), '-Ztime-passes',
                '-Ztime-passes-format=json', '--emit=metadata', 'input.rs'])

    def test_wrapper_receipt_failure_still_drains_and_waits(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            code, outcome = self.wrapper(folder, fail_receipt=True)
            self.assertEqual(code, 23)
            self.assertIn('receipt storage failure', outcome['error'])
            self.assertTrue(outcome['completed_before_cleanup'])
            self.assertEqual((folder / 'stdout').read_bytes(), STDOUT)

    def test_driver_receipt_failure_waits_before_returning(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            completed = folder / 'completed'
            gate = folder / 'gate'
            command = [sys.executable, '-c',
                'import pathlib,sys,time; gate=pathlib.Path(sys.argv[1]); '
                'exec("while not gate.exists(): time.sleep(0.001)"); '
                'time.sleep(0.05); pathlib.Path(sys.argv[2]).write_text("done")',
                str(gate), str(completed)]
            children = []
            real_popen = subprocess.Popen

            def tracked(*args, **kwargs):
                child = real_popen(*args, **kwargs)
                children.append(child)
                return child

            def failed_receipt(*args):
                gate.write_text('go')
                raise OSError('simulated receipt storage failure')

            try:
                with patch.object(DRIVER, 'write_json', failed_receipt), patch.object(
                        DRIVER.subprocess, 'Popen', tracked), contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(OSError, 'receipt storage failure'):
                        DRIVER.run(command, folder, os.environ.copy(), folder, 'fake')
                self.assertTrue(completed.exists(), 'driver returned while its child was still running')
            finally:
                gate.write_text('go')
                for child in children:
                    child.wait()


if __name__ == '__main__':
    unittest.main()
