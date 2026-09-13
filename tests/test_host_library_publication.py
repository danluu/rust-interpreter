"""Pure host-library policy boundaries using the shared archive fixture."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from test_qualified_public_tools import archive
import qualified_public_tools as q
from public_tool_publication import materialize_screen_command


class HostLibraryPublicationTests(unittest.TestCase):
    def validate(self, fixture, policy=q.HOST_LIBRARY_BUILD_POLICY):
        tool, key, data = fixture
        return q.validate_public_tool(tool, key, lambda p: data[str(p.relative_to(tool))],
                                      qualification_policy=policy)

    def test_actual_wrapper_both_identities_and_acyclic_qualification(self):
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('live filesystem read')):
            checked = self.validate(archive(library=True))
            self.assertEqual(len(checked['commands']), 9)
            self.assertEqual(checked['correctness']['results']['real-histories']['passed'], 3)
            self.assertNotIn('tool_key', checked['correctness'])
            cap = checked['capability']
            self.assertEqual(cap['host_library_wrapper']['compiler_sysroot'], cap['compiler_sysroot'])
            self.assertEqual(cap['host_library_wrapper']['sha256'],
                             checked['composition']['binaries']['rust-interp-rustc-wrapper'])
            # Existing typed worker and legacy macro archives stay accepted.
            self.validate(archive(worker=True), q.WORKER_BUILD_POLICY)
            self.validate(archive(), None)

    def test_policies_cannot_be_relabelled_or_materialized_as_macro(self):
        for fixture, policy in [(archive(library=True), None),
                                (archive(worker=True), q.HOST_LIBRARY_BUILD_POLICY),
                                (archive(), q.HOST_LIBRARY_BUILD_POLICY)]:
            with self.subTest(policy=policy), self.assertRaisesRegex(RuntimeError, 'qualification policy'):
                self.validate(fixture, policy)
        with self.assertRaisesRegex(RuntimeError, 'host-library screen request'):
            materialize_screen_command({'qualification_policy': q.HOST_LIBRARY_BUILD_POLICY}, {}, output='/unused')

    def test_rehashed_wrapper_probe_cannot_change_compiled_sysroot_or_policy(self):
        def wrong_root(_, data):
            name = 'provenance/logs/wrapper-capabilities.stdout'
            lines = data[name].decode().splitlines(); lines[1] = '/another/compiler'
            data[name] = ('\n'.join(lines) + '\n').encode()
        with self.assertRaisesRegex(RuntimeError, 'compiled sysroot'):
            self.validate(archive(wrong_root, library=True))
        def wrong_policy(_, data):
            name = 'provenance/logs/wrapper-capabilities.stdout'
            lines = data[name].decode().splitlines()
            cap = json.loads(lines[0]); cap['opt_level'] = 2; lines[0] = json.dumps(cap)
            data[name] = ('\n'.join(lines) + '\n').encode()
        with self.assertRaisesRegex(RuntimeError, 'capability'):
            self.validate(archive(wrong_policy, library=True))

    def test_rehashed_missing_or_skipped_real_histories_fail(self):
        def skipped(_, data):
            data['provenance/logs/real-histories.stderr'] = b'Ran 3 tests in 0.001s\n\nOK (skipped=3)\n'
        def failed(_, data):
            name = 'provenance/receipts/real-histories.json'
            value = json.loads(data[name]); value['returncode'] = 1; data[name] = json.dumps(value).encode()
        for change in [skipped, failed]:
            with self.subTest(change=change.__name__), self.assertRaises(RuntimeError):
                self.validate(archive(change, library=True))

    def test_rekeyed_plan_cannot_omit_capture_or_override_other_commands(self):
        for kind in ['missing-capture', 'alternate-tools', 'override-build', 'missing-probe', 'missing-harness']:
            def change(composition, data):
                name = 'provenance/build-plan.json'; plan = json.loads(data[name])
                if kind == 'missing-capture':del plan['commands'][8]['environment_overrides']['RUST_INTERP_TEST_ARTIFACT_DIR']
                if kind == 'alternate-tools':plan['commands'][8]['environment_overrides']['RUST_INTERP_TEST_WRAPPER'] = '/another/wrapper'
                if kind == 'override-build':plan['commands'][3]['environment_overrides'] = {'RUSTFLAGS': '-Copt-level=3'}
                if kind == 'missing-probe':plan['commands'].pop(7)
                if kind == 'missing-harness':del plan['harness']['tests/test_host_proc_macro_native.py']
                data[name] = json.dumps(plan).encode()
                composition['build']['plan_sha256'] = q.sha(data[name])
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                self.validate(archive(change, library=True))


if __name__ == '__main__':
    unittest.main()
