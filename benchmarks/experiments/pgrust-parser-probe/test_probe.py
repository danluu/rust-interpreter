import json
from pathlib import Path
import unittest

import probe


class NativeTargetTests(unittest.TestCase):
    def output(self):
        return 'running 2 tests\ntest tests::b ... ok\ntest tests::a ... ok\ntest result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s\n'

    def artifact(self, **changes):
        row = dict(reason='compiler-artifact', target=dict(name='gram_core', kind=['lib'], src_path='/src/lib.rs'),
                   profile=dict(test=True), executable='/target/gram_core-tests')
        row.update(changes)
        return json.dumps(row) + '\n'

    def test_complete_inventory_is_canonical_and_does_not_depend_on_thread_completion_order(self):
        self.assertEqual(probe.native_inventory(self.output(), 2), ['tests::a', 'tests::b'])

    def test_missing_extra_and_duplicate_names_are_rejected(self):
        for text in [self.output().replace('test tests::b ... ok\n', ''),
                     self.output() + 'test tests::c ... ok\n', self.output().replace('tests::b', 'tests::a')]:
            with self.subTest(text=text), self.assertRaises(AssertionError): probe.native_inventory(text, 2)

    def test_failures_ignored_filters_and_incomplete_summaries_are_rejected(self):
        for old, new in [('tests::b ... ok', 'tests::b ... FAILED'), ('tests::b ... ok', 'tests::b ... ignored'),
                         ('0 filtered out', '1 filtered out'), ('0 ignored', '1 ignored'),
                         ('2 passed', '1 passed'), ('running 2 tests', 'running 3 tests')]:
            with self.subTest(old=old), self.assertRaises(AssertionError):
                probe.native_inventory(self.output().replace(old, new), 2)

    def test_exact_root_test_executable_is_selected_among_dependency_artifacts(self):
        dependency = self.artifact(target=dict(name='mcx', kind=['lib'], src_path='/dep/lib.rs'), profile=dict(test=False))
        self.assertEqual(probe.native_target(dependency + self.artifact(), Path('/src/lib.rs')), Path('/target/gram_core-tests'))

    def test_ambiguous_missing_or_wrong_target_executables_are_rejected(self):
        for text in ['', self.artifact() * 2, self.artifact(executable=None),
                     self.artifact(target=dict(name='gram_core', kind=['bin'], src_path='/src/lib.rs')),
                     self.artifact(target=dict(name='gram_core', kind=['lib'], src_path='/other/lib.rs'))]:
            with self.subTest(text=text), self.assertRaises(AssertionError): probe.native_target(text, Path('/src/lib.rs'))

    def test_non_artifact_output_cannot_supply_an_executable(self):
        noise = 'a native test message\n{not json\n' + self.artifact(reason='compiler-message')
        self.assertEqual(probe.native_target(noise + self.artifact(), Path('/src/lib.rs')), Path('/target/gram_core-tests'))
        with self.assertRaises(AssertionError): probe.native_target(noise, Path('/src/lib.rs'))


if __name__ == '__main__':
    unittest.main()
