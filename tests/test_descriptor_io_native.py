"""Opt-in native/exported descriptor controls; caller owns canonical workload lock.

No tool/std installation, compiler build or automatic workload admission occurs
here. The supervising runner must freeze inputs, compiler/tool/std identities,
environment and exact child records before running this suite.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import unittest

REQUIRED = ['RUST_INTERP_TEST_RUSTC', 'RUST_INTERP_TEST_EXPORTER', 'RUST_INTERP_TEST_VM',
            'RUST_INTERP_TEST_STD_SYSROOT', 'RUST_INTERP_TEST_ARTIFACT_DIR']
ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(all(os.environ.get(name) for name in REQUIRED),
                     'requires explicitly admitted compiler, exporter, VM, std and evidence directory')
class DescriptorIoNativeTests(unittest.TestCase):
    def setUp(self):
        self.rustc, self.exporter, self.vm, self.std, evidence = [Path(os.environ[n]).resolve(strict=True) for n in REQUIRED]
        self.work = evidence / self._testMethodName
        self.work.mkdir()
        self.env = {name: os.environ[name] for name in ['PATH', 'HOME', 'TMPDIR'] if name in os.environ}
        self.env.update(LC_ALL='C', LANG='C', TZ='UTC')
        self.sequence = 0

    def invoke(self, args, *, cwd=None, env=None):
        self.sequence += 1
        command = list(map(str, args))
        cwd = cwd or self.work
        environment = self.env | dict(env or {})
        receipt = self.work / f'command-{self.sequence:03}.json'
        row = dict(command=command, cwd=str(cwd), parent_pid=os.getpid(), started_at=time.time(),
                   environment=environment, status='starting')
        receipt.write_text(json.dumps(row, indent=2) + '\n')
        process = subprocess.Popen(command, cwd=cwd, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            row.update(pid=process.pid, status='running')
            receipt.write_text(json.dumps(row, indent=2) + '\n')
        finally:
            try:
                stdout, stderr = process.communicate()
            finally:
                process.wait()
        row.update(returncode=process.returncode, status='finished', finished_at=time.time())
        for name, value in [('stdout', stdout), ('stderr', stderr)]:
            path = self.work / f'command-{self.sequence:03}.{name}'
            path.write_bytes(value)
            row[name] = dict(path=str(path), sha256=hashlib.sha256(value).hexdigest())
        receipt.write_text(json.dumps(row, indent=2) + '\n')
        self.assertNotIn(b'internal compiler error', stderr)
        return process.returncode, stdout, stderr

    def export(self, source, output):
        return self.invoke([self.exporter, source, '--crate-name', 'descriptor_io_fixture', '--edition=2024',
                            '--emit=metadata', '--sysroot', self.std, '-Copt-level=0', '-o', output.with_suffix('.rmeta')],
                           env={'RUST_INTERP_ENTRY': 'rust_interp_entry', 'RUST_INTERP_OUTPUT': str(output),
                                'RUST_INTERP_DEMAND_BODIES': '0', 'RUST_INTERP_DEMAND_CACHE': '0'})

    def test_native_and_both_engines_create_append_truncate_errors_and_default_refusal(self):
        source = self.work / 'fixture.rs'
        source.write_bytes((ROOT / 'tests/descriptor_io_fixture.rs').read_bytes())
        native = self.work / 'native'
        artifact = self.work / 'fixture.rbc'
        result = self.invoke([self.rustc, source, '--edition=2024', '-Copt-level=0', '-o', native])
        self.assertEqual(result[0], 0, result[2])
        result = self.export(source, artifact)
        self.assertEqual(result[0], 0, result[2])
        directories = {name: self.work / name for name in ['native-files', 'interpreter-files', 'jit-files', 'disabled']}
        for path in directories.values(): path.mkdir()
        disabled = self.invoke([self.vm, artifact, 0], cwd=directories['disabled'])
        self.assertNotEqual(disabled[0], 0)
        self.assertIn(b'guest descriptor I/O is disabled', disabled[2])
        self.assertEqual(list(directories['disabled'].iterdir()), [])
        for phase in [0, 1, 2]:
            expected = self.invoke([native, phase], cwd=directories['native-files'])
            self.assertEqual(expected[0], 0, expected[2])
            contents = (directories['native-files'] / 'descriptor-data.bin').read_bytes()
            for engine in ['interpreter', 'jit']:
                result = self.invoke([self.vm, '--guest-descriptor-io', '--engine', engine, artifact, phase],
                                     cwd=directories[engine + '-files'])
                self.assertEqual(result, expected)
                self.assertEqual((directories[engine + '-files'] / 'descriptor-data.bin').read_bytes(), contents)

    def test_unsupported_fcntl_and_bad_abi_are_export_errors_before_any_effect(self):
        cases = [
            ('dynamic', 'fn fcntl(fd:i32, command:i32, ...) -> i32;', 'fcntl(3, value as i32)', b'constant F_GETFD'),
            ('setfd', 'fn fcntl(fd:i32, command:i32, ...) -> i32;', 'fcntl(3, 2, 1i32)', b'invalid fcntl signature'),
            ('write_width', 'fn write(fd:i32, bytes:*const u8, size:u32) -> isize;', 'write(3, std::ptr::null(), 0)', b'invalid write signature'),
            ('open_mode', 'fn open(path:*const i8, flags:i32, ...) -> i32;', 'open(c"file".as_ptr(), 0x201, 0usize)', b'invalid open signature'),
            ('close_return', 'fn close(fd:i32) -> i64;', 'close(3)', b'invalid close signature'),
        ]
        for name, signature, expression, diagnostic in cases:
            source = self.work / (name + '.rs')
            source.write_text(f'unsafe extern "C" {{ {signature} }}\n'
                              f'pub fn rust_interp_entry(value:u64)->u64 {{ unsafe {{ {expression} as u64 }} }}\nfn main() {{}}\n')
            artifact = self.work / (name + '.rbc')
            result = self.export(source, artifact)
            self.assertNotEqual(result[0], 0)
            self.assertIn(diagnostic, result[2])
            self.assertFalse(artifact.exists())


if __name__ == '__main__':
    unittest.main()
