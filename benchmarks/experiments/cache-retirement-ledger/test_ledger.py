import copy
import json
from pathlib import Path
import tempfile
import unittest

from ledger import reconcile, sha


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def receipt(self, name, files=3, size=40, mutate_plan=None, mutate_result=None):
        raw = self.root / '.work' / name
        raw.mkdir(parents=True)
        plan = dict(owner=str(self.root), roots=[dict(path='.work/example/native', files=files, logical_bytes=size)],
                    files=files, logical_bytes=size)
        if mutate_plan:
            mutate_plan(plan)
        (raw / 'plan.json').write_text(json.dumps(plan))
        result = dict(status='passed', all_protected_hashes_unchanged=True, raw=str(raw.relative_to(self.root)),
                      plan_sha256=sha(raw / 'plan.json'), files_removed=files, logical_bytes_removed=size)
        if mutate_result:
            mutate_result(result)
        summary = self.root / 'results' / name / 'summary.json'
        summary.parent.mkdir(parents=True)
        summary.write_text(json.dumps(result))
        return str(summary.relative_to(self.root))

    def test_recheck_links_prior_retirement_without_recounting_roots(self):
        old = self.receipt('old')
        empty = self.receipt('empty', 0, 0)
        result = reconcile(self.root, [old, empty])
        self.assertEqual((result['unique_roots'], result['roots_with_recorded_removals'], result['empty_rechecks']), (1, 1, 1))
        self.assertEqual(result['roots'][0]['removal_receipts'], [old])
        self.assertEqual(result['roots'][0]['empty_rechecks'], [empty])
        self.assertEqual(result['cache_files_inspected'], 0)
        self.assertFalse((self.root / '.work/example').exists())

    def test_modified_plan_and_wrong_owner_reject(self):
        summary = self.receipt('bad-hash', mutate_result=lambda r: r.update(plan_sha256='0'*64))
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            reconcile(self.root, [summary])
        summary = self.receipt('bad-owner', mutate_plan=lambda p: p.update(owner='/somewhere/else'))
        with self.assertRaisesRegex(ValueError, 'owner mismatch'):
            reconcile(self.root, [summary])

    def test_failed_or_unpreserved_cleanup_rejects(self):
        for index, fields in enumerate([dict(status='failed'), dict(all_protected_hashes_unchanged=False)]):
            summary = self.receipt(str(index), mutate_result=lambda r: r.update(fields))
            with self.assertRaisesRegex(ValueError, 'did not complete'):
                reconcile(self.root, [summary])

    def test_escaping_and_noncanonical_paths_reject(self):
        for index, path in enumerate(['.work/../outside', '/outside', '.work//cache', '.work/cache/']):
            summary = self.receipt(str(index), mutate_plan=lambda p: p['roots'][0].update(path=path))
            with self.assertRaisesRegex(ValueError, 'noncanonical'):
                reconcile(self.root, [summary])
        with self.assertRaisesRegex(ValueError, 'noncanonical'):
            reconcile(self.root, ['results/../elsewhere'])

    def test_duplicate_receipts_and_roots_reject(self):
        summary = self.receipt('repeat')
        with self.assertRaisesRegex(ValueError, 'duplicate cleanup'):
            reconcile(self.root, [summary, summary])
        summary = self.receipt('root-repeat', mutate_plan=lambda p: p['roots'].append(copy.deepcopy(p['roots'][0])))
        with self.assertRaisesRegex(ValueError, 'duplicate root'):
            reconcile(self.root, [summary])

    def test_nonreconciling_or_negative_counts_reject(self):
        summary = self.receipt('wrong-total', mutate_result=lambda r: r.update(files_removed=4))
        with self.assertRaisesRegex(ValueError, 'totals'):
            reconcile(self.root, [summary])
        for index, count in enumerate([-1, True, 1.5]):
            summary = self.receipt('bad-count-'+str(index), mutate_result=lambda r: r.update(files_removed=count))
            with self.assertRaisesRegex(ValueError, 'invalid cleanup count'):
                reconcile(self.root, [summary])

    def test_empty_file_removal_is_distinct_from_empty_recheck(self):
        result = reconcile(self.root, [self.receipt('empty-file', 1, 0)])
        self.assertEqual(result['roots_with_recorded_removals'], 1)
        self.assertEqual(result['empty_rechecks'], 0)
        summary = self.receipt('impossible', 0, 1)
        with self.assertRaisesRegex(ValueError, 'bytes claimed'):
            reconcile(self.root, [summary])


if __name__ == '__main__':
    unittest.main()
