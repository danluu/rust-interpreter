import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('hir_capture_upgrade', ROOT / 'experiments/hir-capture-upgrade/upgrade.py')
upgrade = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upgrade)


class UpgradeTests(unittest.TestCase):
    def test_failed_compile_is_repairable_without_claiming_prior_unit_success(self):
        self.assertEqual(upgrade.terminal_state({'prepare': {}}, {'stage': 'check', 'status': 'failed'}), 'failed')
        self.assertEqual(upgrade.terminal_state({'prepare': {}, 'check': {}}, {'stage': 'unit', 'status': 'failed'}), 'failed')
        for completed, terminal in [({}, {'stage': 'check', 'status': 'failed'}),
                ({'prepare': {}}, {'stage': 'unit', 'status': 'failed'}),
                ({'prepare': {}}, {'stage': 'check', 'status': 'passed'})]:
            with self.assertRaises(RuntimeError):
                upgrade.terminal_state(completed, terminal)
        self.assertEqual(upgrade.terminal_state({'prepare': {}, 'check': {}, 'unit': {}},
            {'stage': 'unit', 'status': 'passed'}), 'passed')

    def plan(self):
        names = [*upgrade.old.REQUIRED_TESTS, 'new_control']
        frozen = {'source.py': 'frozen'}
        return dict(owner=str(upgrade.ROOT), source=str(upgrade.SOURCE), inputs=frozen,
            checkpoint=upgrade.CHECKPOINT, stages=upgrade.STAGES, commands=copy.deepcopy(upgrade.old.COMMANDS),
            old_tests=upgrade.old.REQUIRED_TESTS, added_tests=['new_control'], initial_free_gib=16,
            running_floor_gib=8, capacity_stop_gib=9, delta_sha256='a' * 64), frozen, names

    def test_reviewed_hash_binds_commands_tests_and_delta_metadata_before_execution(self):
        original, frozen, names = self.plan()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'plan.json'
            path.write_text(json.dumps(original))
            expected = upgrade.sha(path)
            self.assertEqual(upgrade.load_plan(path, expected, frozen, names), original)
            variants = []
            changed = copy.deepcopy(original); changed['commands']['check'] = ['./x', 'build']; variants.append(changed)
            changed = copy.deepcopy(original); changed['added_tests'] = []; variants.append(changed)
            changed = copy.deepcopy(original); changed['delta_sha256'] = 'b' * 64; variants.append(changed)
            for changed in variants:
                path.write_text(json.dumps(changed))
                with self.assertRaisesRegex(RuntimeError, 'reviewed upgrade plan changed'):
                    upgrade.load_plan(path, expected, frozen, names)
            for changed in variants[:2]:
                path.write_text(json.dumps(changed))
                with self.assertRaisesRegex(RuntimeError, 'fixed source, commands, tests or capacity'):
                    upgrade.load_plan(path, upgrade.sha(path), frozen, names)

    def test_rehashed_owner_or_capacity_downgrade_is_rejected(self):
        original, frozen, names = self.plan()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'plan.json'
            for field, value in [('owner', '/another'), ('source', '/another'), ('initial_free_gib', 8),
                                 ('running_floor_gib', 1), ('capacity_stop_gib', 2)]:
                changed = copy.deepcopy(original); changed[field] = value
                path.write_text(json.dumps(changed))
                with self.assertRaises(RuntimeError):
                    upgrade.load_plan(path, upgrade.sha(path), frozen, names)

    def archive(self, base, data=b'raw\x00evidence'):
        archive, manifest, summary = [base / n for n in ['evidence.tar.gz', 'manifest.json', 'summary.json']]
        with tarfile.open(archive, 'w:gz') as tar:
            entry = tarfile.TarInfo('owned/source.rs'); entry.size = len(data)
            tar.addfile(entry, io.BytesIO(data))
        manifest.write_text(json.dumps({'owned/source.rs': {'source': '/owned/source.rs', 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest()}}))
        summary.write_text(json.dumps({'archive': {'sha256': upgrade.sha(archive)}}))
        return archive, manifest, summary

    def test_archive_binds_exact_historical_bytes_and_complete_origin_mapping(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = self.archive(Path(temp)); expected = upgrade.digest(b'raw\x00evidence')
            upgrade.verify_archive(*paths, {'/owned/source.rs': expected})
            for required in [{'/owned/source.rs': '0' * 64}, {'/missing/source.rs': expected}]:
                with self.assertRaises(RuntimeError):
                    upgrade.verify_archive(*paths, required)
            manifest = json.loads(paths[1].read_text())
            manifest['owned/source.rs']['source'] = '/another/source.rs'
            paths[1].write_text(json.dumps(manifest))
            with self.assertRaisesRegex(RuntimeError, 'source mapping mismatch'):
                upgrade.verify_archive(*paths, {})

    def test_named_controls_require_both_original_and_new_actual_successes(self):
        upgrade.checked_tests('test module::old ... ok\ntest module::new ... ok\n', ['old'], ['new'])
        for text in ['test module::old ... ok\n', 'test module::old ... ok\ntest module::new ... FAILED\n']:
            with self.assertRaisesRegex(RuntimeError, 'new'):
                upgrade.checked_tests(text, ['old'], ['new'])
        manifest, names = upgrade.checkpoint()
        self.assertEqual(len(names), 20)
        self.assertTrue(set(upgrade.old.REQUIRED_TESTS) <= set(names))
        self.assertFalse(manifest['actual_cache_hit_path'])

    def test_delta_preserves_creation_deletion_and_unchanged_files(self):
        self.assertEqual(upgrade.delta_file('file.rs', b'old\n', b'old\n'), b'')
        changed = upgrade.delta_file('file.rs', b'old\n', b'new\n')
        self.assertIn(b'--- a/file.rs\n+++ b/file.rs\n', changed)
        self.assertIn(b'-old\n+new\n', changed)
        self.assertIn(b'new file mode 100644\n--- /dev/null\n', upgrade.delta_file('new.rs', None, b'new\n'))
        self.assertIn(b'deleted file mode 100644\n--- a/old.rs\n+++ /dev/null\n', upgrade.delta_file('old.rs', b'old\n', None))


if __name__ == '__main__':
    unittest.main()
