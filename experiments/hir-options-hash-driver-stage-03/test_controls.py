"""Pure command/readback controls and mocked failure sequencing; no child runs."""
import contextlib
import copy
import json
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest import mock

import controls as c


def plan():
    pair = c.B3 / 'lib/rustlib' / c.H / 'lib/librustc_driver-abcd.dylib'
    return dict(roles=dict(build_compiler=str(c.D2), build_sysroot=str(c.B3),
                          runtime_compiler=str(c.E2), application_sysroot=str(c.E2)),
                ordered_driver_pair=[str(pair), str(pair.with_suffix('.rmeta'))],
                sdk='/qualified/SDK', clang='/qualified/clang',
                environment=dict(PATH='/usr/bin:/bin', HOME='/Users/danluu', LANG='C', LC_ALL='C',
                                 SDKROOT='/qualified/SDK', TMPDIR=str(c.ARTIFACTS / 'tmp')))


def link_words(p):
    return ['env', '-u', 'IPHONEOS_DEPLOYMENT_TARGET', 'SDKROOT=' + p['sdk'],
            p['clang'], str(c.ARTIFACTS / 'temporary.o'), p['ordered_driver_pair'][0],
            '-arch', 'arm64', '-L', str(c.E2 / 'lib'), '-o', str(c.ARTIFACTS / 'hash-control-driver'),
            '-Wl,-rpath,' + str(c.E2 / 'lib')]


def raw(words):
    return (shlex.join(words) + '\n').encode()


class Controls(unittest.TestCase):
    def test_exact_role_split_and_no_metadata_execution_of_driver(self):
        p = plan(); rows = c.desired_commands(p)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]['environment']['RUSTC_BOOTSTRAP'], '1')
        self.assertEqual([row['argv'][-1] for row in rows[1:]], ['serial', 'parallel'])
        for row in rows[1:]:
            self.assertNotIn('RUSTC_BOOTSTRAP', row['environment'])
            self.assertEqual(row['argv'][1], str(c.E2))
            self.assertEqual(row['environment']['DYLD_PRINT_LIBRARIES'], '1')

    def test_substituted_beta_application_or_old_runtime_rejects(self):
        for role in plan()['roles']:
            p = plan(); p['roles'][role] = '/old/or/beta/substitute'
            with self.subTest(role=role), self.assertRaises(RuntimeError):
                c.desired_commands(p)

    def test_incomplete_reordered_or_foreign_extern_pair_rejects(self):
        original = plan()['ordered_driver_pair']
        for pair in [original[:1], original[::-1], [original[0], original[1] + '.other'],
                     ['/foreign/librustc_driver-abcd.dylib', '/foreign/librustc_driver-abcd.rmeta']]:
            p = plan(); p['ordered_driver_pair'] = pair
            with self.assertRaises(RuntimeError):
                c.desired_commands(p)

    def test_ambient_flags_wrappers_loader_and_temp_overrides_reject(self):
        for key in ['RUSTFLAGS', 'RUSTC_WRAPPER', 'RUSTC_FORCE_RUSTC_VERSION',
                    'RUSTC_BOOTSTRAP', 'DYLD_LIBRARY_PATH', 'DYLD_PRINT_LIBRARIES', 'LD_PRELOAD']:
            p = plan(); p['environment'][key] = 'value'
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                c.desired_commands(p)
        for key in ['TMPDIR', 'SDKROOT']:
            p = plan(); p['environment'][key] = '/foreign'
            with self.assertRaises(RuntimeError):
                c.desired_commands(p)

    def test_full_linker_command_is_retained_with_role_arguments(self):
        p = plan(); words = link_words(p)
        proof = c.linker_observation(raw(words), p)
        self.assertEqual(proof['argv'], words[4:])
        self.assertEqual(proof['removed'], ['IPHONEOS_DEPLOYMENT_TARGET'])
        self.assertEqual(proof['environment'], {'SDKROOT': p['sdk']})

    def test_linker_name_in_environment_does_not_prove_executable(self):
        p = plan(); words = link_words(p)
        words[4:5] = ['DESCRIPTION=' + p['clang'], '/foreign/clang']
        with self.assertRaises(RuntimeError):
            c.linker_observation(raw(words), p)

    def test_wrong_link_roles_duplicate_output_and_trailing_records_reject(self):
        p = plan(); words = link_words(p)
        for old, new in [(p['ordered_driver_pair'][0], '/foreign/driver.dylib'),
                         ('arm64', 'x86_64'), ('SDKROOT=' + p['sdk'], 'SDKROOT=/foreign'),
                         ('-Wl,-rpath,' + str(c.E2 / 'lib'), '-Wl,-rpath,/foreign')]:
            changed = [new if word == old else word for word in words]
            with self.subTest(old=old), self.assertRaises(RuntimeError):
                c.linker_observation(raw(changed), p)
        for value in [raw(words + ['-o', '/foreign']), raw(words) + b'other\n', raw(words)[:-1],
                      raw(words[:4] + ['SDKROOT=' + p['sdk']] + words[4:])]:
            with self.assertRaises(RuntimeError):
                c.linker_observation(value, p)

    def failure_flow(self, compilation_fails):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); evidence = base / 'hir-options-hash-driver-mocked'; evidence.mkdir()
            artifacts = base / 'owned-artifacts'
            with mock.patch.object(c, 'ARTIFACTS', artifacts):
                p = plan(); p['children'] = c.desired_commands(p)
                p['evidence_roots'] = [str(evidence)]
                provider = str(c.E2 / 'lib/librustc_driver-abcd.dylib')
                p['runtime_private_providers'] = {provider: {'mocked': True}}
                owned = mock.Mock()
                owned.workload_lock.return_value = contextlib.nullcontext()
                def write(path, value):
                    path.write_text(json.dumps(value))
                owned.write.side_effect = write
                monitor = mock.Mock(); monitor.rejection.return_value = None
                def compile_child(command, **kwargs):
                    out = kwargs['output']; out.mkdir()
                    receipt = dict(status='failed' if compilation_fails else 'finished', returncode=1 if compilation_fails else 0)
                    write(out / 'receipt.json', receipt)
                    (out / 'stdout').write_bytes(raw(link_words(p))); (out / 'stderr').write_bytes(b'')
                    binary = artifacts / 'hash-control-driver'; binary.write_bytes(b'mocked-binary'); binary.chmod(0o700)
                    return receipt
                monitor.run.side_effect = compile_child
                closure = dict(files={str(artifacts / 'hash-control-driver'): {'mocked': True},
                                      **p['runtime_private_providers']})
                failed_serial = dict(status='failed', child_may_be_live=True, probe_may_be_live=False)
                with mock.patch.object(c.owned_driver, 'run', return_value=failed_serial) as driver, \
                     mock.patch.object(c.loader_trace, 'process') as readback:
                    with self.assertRaises(RuntimeError):
                        c.execute(p, evidence_root=evidence, canonical_fd=123, owned=owned,
                                  monitor=monitor, check_inputs=mock.Mock(), inspect_closure=lambda _: copy.deepcopy(closure))
                    self.assertEqual(monitor.run.call_count, 1)
                    self.assertEqual(driver.call_count, 0 if compilation_fails else 1)
                    if not compilation_fails:
                        self.assertEqual(driver.call_args.args[0][-1], 'serial')
                    readback.assert_not_called()

    def test_compile_failure_cannot_start_driver(self):
        self.failure_flow(True)

    def test_failed_unresolved_serial_prevents_parallel(self):
        self.failure_flow(False)


if __name__ == '__main__':
    unittest.main()
