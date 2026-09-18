"""Pure controls over saved metadata; no compiler, Cargo or Stage is started."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

import metadata as m


class MetadataControls(unittest.TestCase):
    def setUp(self):
        raw = (m.OLDWORK / 'plan/cargo-metadata.json').read_text()
        self.metadata = json.loads(raw.replace(str(m.OLDWORK / 'source'), str(m.OWNER)))
        self.stage = object.__new__(m.Stage)
        self.stage.data = m.read(m.HERE / 'plan.json')

    def test_saved_complete_package_set_is_admitted(self):
        result = self.stage.dependencies(self.metadata)
        self.assertEqual(len(result['packages']), 30)

    def test_duplicate_package_cannot_replace_missing_package(self):
        self.metadata['packages'][1] = copy.deepcopy(self.metadata['packages'][0])
        with self.assertRaisesRegex(RuntimeError, 'resolved workspace differs'):
            self.stage.dependencies(self.metadata)

    def test_changed_features_are_rejected(self):
        self.metadata['resolve']['nodes'][0]['features'].append('unreviewed-feature')
        with self.assertRaisesRegex(RuntimeError, 'dependency features changed'):
            self.stage.dependencies(self.metadata)

    def test_unfrozen_target_source_is_rejected(self):
        self.metadata['packages'][0]['targets'][0]['src_path'] = str(m.HERE / 'test_metadata.py')
        with self.assertRaisesRegex(RuntimeError, 'unfrozen Cargo target source'):
            self.stage.dependencies(self.metadata)

    def test_support_order_survives_sorted_json(self):
        paths = self.stage.data['support_executables']
        self.assertEqual(list(paths), ['cargo', 'clang', 'python'])
        calls = []
        fake = SimpleNamespace(data=self.stage.data, closure=lambda path: calls.append(str(path)))
        result = m.Stage.support_closures(fake)
        self.assertEqual(calls, [paths[name] for name in ('cargo', 'python', 'clang')])
        self.assertEqual(list(result), ['cargo', 'python', 'clang'])


if __name__ == '__main__':
    unittest.main()
