"""Pure historical-record fixtures; no real catalog or provider path is opened.

The integration fixtures replace only saved read/hash/frozen boundaries with
in-memory records. They qualify the adapter, not actual predecessor bytes.
"""
import copy
from contextlib import ExitStack
from pathlib import Path
import stat
import unittest
from unittest.mock import patch

import verify as audit


def canonical(size=13, inode=101, digest='a'*64):
    return dict(sha256=digest, size=size,
                identity=dict(dev=1, ino=inode, mode=stat.S_IFREG | 0o644,
                              size=size, mtime_ns=17, ctime_ns=19, nlink=2))


def historical(row):
    return dict(sha256=row['sha256'], stamp=[row['identity'][key] for key in
        ['dev', 'ino', 'mode', 'size', 'mtime_ns', 'ctime_ns', 'nlink']])


class InheritedRecordsTests(unittest.TestCase):
    def normalize(self, row):
        # The new normalizer must remain pure even when fixture paths exist in
        # other tests. No source/provider or stat callback is needed here.
        with ExitStack() as stack:
            for name in ['read', 'raw', 'sha', 'frozen', 'identity']:
                stack.enter_context(patch.object(audit, name, side_effect=AssertionError('unexpected I/O')))
            return audit.canonical_inherited_record(row)

    def rejected(self, row):
        with self.assertRaises(RuntimeError):
            self.normalize(row)

    def fixture(self):
        source = Path('/fixture/source')
        first, second = canonical(), canonical(0, 102, 'b'*64)
        inherited = dict(files={'/fixture/first': historical(first), '/fixture/second': second},
                         links={'/fixture/link': {'target': 'first', 'stamp': [1, 2, 3]}},
                         absent_paths=['/fixture/absent'], plan_sha256='c'*64)
        freeze = dict(files={'/fixture/first': first, '/fixture/second': copy.deepcopy(second)},
                      links=copy.deepcopy(inherited['links']), absent_paths=['/fixture/absent', '/fixture/later'])
        documents = {source/'inputs.json': inherited}
        digests = {source/'plan.json': 'c'*64}
        return source, inherited, freeze, documents, digests

    def inherited(self, source, freeze, documents, digests):
        allowed = set(documents) | set(digests)
        def frozen(path, actual):
            self.assertIs(actual, freeze)
            path = Path(path)
            self.assertIn(path, allowed)
            return path
        def read(path):
            self.assertIn(Path(path), documents)
            return copy.deepcopy(documents[Path(path)])
        def sha(path):
            self.assertIn(Path(path), digests)
            return digests[Path(path)]
        with patch.object(audit, 'frozen', side_effect=frozen), \
             patch.object(audit, 'read', side_effect=read), \
             patch.object(audit, 'sha', side_effect=sha), \
             patch.object(audit, 'raw', side_effect=AssertionError('unexpected file read')):
            return audit.inherited_inputs(source, freeze)

    def test_exact_historical_stamp_mapping(self):
        row = canonical()
        self.assertEqual(self.normalize(historical(row)), row)
        self.assertEqual(self.normalize(historical(row))['identity']['nlink'], 2)

    def test_saved_compiler_and_run_make_wire_examples(self):
        # Copied metadata only, from O's retained schema assessment 6aaf27fc.
        # These records do not open or independently qualify the actual files.
        examples = [
            ('9cc45372322b2ed9a1aebf225ea9e2317b73776b64621515d0257f96ed8e057f',
             [16777229, 1055215030, 33152, 2651, 1789785629958101592, 1789785629958101592, 1]),
            ('ebf3372e5268fd78362d776a083fc07106ea9aed20d49e6130d7b07e3a0ea631',
             [16777229, 1055322736, 33152, 13516, 1789786370838112978, 1789786370838112978, 1]),
        ]
        for digest, stamp in examples:
            expected = dict(sha256=digest, size=stamp[3], identity=dict(
                dev=stamp[0], ino=stamp[1], mode=stamp[2], nlink=stamp[6], size=stamp[3],
                mtime_ns=stamp[4], ctime_ns=stamp[5]))
            with self.subTest(digest=digest):
                self.assertEqual(self.normalize(dict(sha256=digest, stamp=stamp)), expected)

    def test_canonical_roundtrip_has_no_mutable_alias(self):
        row = canonical(); before = copy.deepcopy(row)
        normalized = self.normalize(row)
        self.assertEqual(normalized, before)
        normalized['identity']['ino'] += 1
        self.assertEqual(row, before)

    def test_empty_and_maximum_size_and_internal_hardlinks_are_preserved(self):
        for size in [0, 2**30]:
            row = canonical(size); row['identity']['nlink'] = 3
            self.assertEqual(self.normalize(row), row)
            self.assertEqual(self.normalize(historical(row)), row)

    def test_historical_input_is_not_mutated(self):
        row = historical(canonical()); before = copy.deepcopy(row)
        normalized = self.normalize(row); normalized['identity']['mtime_ns'] = 99
        self.assertEqual(row, before)

    def test_unknown_hybrid_and_incomplete_row_schemas_are_rejected(self):
        row = canonical()
        candidates = [None, [], {}, {'sha256': 'a'*64}, row | {'extra': 0},
                      historical(row) | {'size': row['size']}, row | {'stamp': historical(row)['stamp']}]
        for key in row:
            candidates.append({name: value for name, value in row.items() if name != key})
        for candidate in candidates:
            with self.subTest(candidate=candidate):
                self.rejected(candidate)

    def test_malformed_hashes_are_rejected_in_both_shapes(self):
        for digest in [None, 1, b'a'*64, '', 'a'*63, 'a'*65, 'A'*64, 'g'*64, 'a'*63+'\n']:
            for row in [canonical(), historical(canonical())]:
                row['sha256'] = digest
                with self.subTest(digest=digest, shape=list(row)):
                    self.rejected(row)

    def test_stamp_requires_exact_list_and_length(self):
        stamp = historical(canonical())['stamp']
        for value in [None, tuple(stamp), {}, stamp[:-1], stamp+[1], '1234567']:
            with self.subTest(value=value):
                self.rejected(dict(sha256='a'*64, stamp=value))

    def test_each_stamp_component_rejects_boolean_float_string_and_null(self):
        for index in range(7):
            for value in [True, False, 1.0, '1', None]:
                row = historical(canonical()); row['stamp'][index] = value
                with self.subTest(index=index, value=value):
                    self.rejected(row)

    def test_canonical_identity_has_exact_seven_keys(self):
        row = canonical()
        candidates = [None, [], row['identity'] | {'extra': 1}]
        candidates += [{name: value for name, value in row['identity'].items() if name != key}
                       for key in row['identity']]
        for candidate in candidates:
            with self.subTest(candidate=candidate):
                self.rejected(row | {'identity': candidate})

    def test_each_identity_component_rejects_boolean_float_string_and_null(self):
        for key in audit.FIELDS:
            for value in [True, False, 1.0, '1', None]:
                row = canonical(); row['identity'][key] = value
                with self.subTest(key=key, value=value):
                    self.rejected(row)

    def test_canonical_size_requires_integer_and_exact_identity_size(self):
        for value in [True, False, 13.0, '13', None, 12, 14, -1, 2**30+1]:
            with self.subTest(value=value):
                self.rejected(canonical() | {'size': value})

    def test_nonordinary_modes_are_rejected_in_both_shapes(self):
        for mode in [0, -1, 0o200000, stat.S_IFDIR | 0o700, stat.S_IFLNK | 0o777,
                     stat.S_IFIFO | 0o600, stat.S_IFSOCK | 0o600, stat.S_IFCHR | 0o600]:
            row = canonical(); row['identity']['mode'] = mode
            for candidate in [row, historical(row)]:
                with self.subTest(mode=mode, shape=list(candidate)):
                    self.rejected(candidate)

    def test_invalid_identity_ranges_and_payload_bounds_are_rejected(self):
        for key, value in [('dev', -1), ('ino', 0), ('ino', -1), ('nlink', 0),
                           ('nlink', -1), ('mtime_ns', -1), ('ctime_ns', -1),
                           ('size', -1), ('size', 2**30+1)]:
            row = canonical(); row['identity'][key] = value
            if key == 'size':
                row['size'] = value
            for candidate in [row, historical(row)]:
                with self.subTest(key=key, value=value, shape=list(candidate)):
                    self.rejected(candidate)

    def test_mixed_historical_catalog_preserves_current_header_and_all_rows(self):
        source, original, freeze, documents, digests = self.fixture()
        before = copy.deepcopy((original, freeze))
        self.assertEqual(self.inherited(source, freeze, documents, digests), original)
        self.assertEqual((original, freeze), before)

    def test_missing_current_row_and_noncanonical_current_shape_are_rejected(self):
        for replacement in [None, historical(canonical())]:
            source, _, freeze, documents, digests = self.fixture()
            if replacement is None:
                del freeze['files']['/fixture/first']
            else:
                freeze['files']['/fixture/first'] = replacement
            with self.subTest(replacement=replacement), self.assertRaises(RuntimeError):
                self.inherited(source, freeze, documents, digests)

    def test_same_sha_and_size_cannot_hide_changed_identity(self):
        for key in ['dev', 'ino', 'mode', 'nlink', 'mtime_ns', 'ctime_ns']:
            source, _, freeze, documents, digests = self.fixture()
            freeze['files']['/fixture/first']['identity'][key] += 1
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                self.inherited(source, freeze, documents, digests)

    def test_different_digest_or_size_is_rejected(self):
        for changed in ['sha256', 'size']:
            source, _, freeze, documents, digests = self.fixture()
            row = freeze['files']['/fixture/first']
            if changed == 'sha256':
                row['sha256'] = 'd'*64
            else:
                row['size'] += 1; row['identity']['size'] += 1
            with self.subTest(changed=changed), self.assertRaises(RuntimeError):
                self.inherited(source, freeze, documents, digests)

    def test_bool_int_relabeling_is_rejected_in_complete_row_comparison(self):
        source, _, freeze, documents, digests = self.fixture()
        freeze['files']['/fixture/first']['identity']['dev'] = True
        with self.assertRaises(RuntimeError):
            self.inherited(source, freeze, documents, digests)

    def test_plan_hash_link_and_absence_guards_remain_required(self):
        for changed in ['plan', 'link', 'absence']:
            source, _, freeze, documents, digests = self.fixture()
            if changed == 'plan':
                digests[source/'plan.json'] = 'd'*64
            elif changed == 'link':
                freeze['links']['/fixture/link']['target'] = 'foreign'
            else:
                freeze['absent_paths'].remove('/fixture/absent')
            with self.subTest(changed=changed), self.assertRaises(RuntimeError):
                self.inherited(source, freeze, documents, digests)

    def test_reconciliation_base_retains_complete_original_rows(self):
        _, original, freeze, _, _ = self.fixture()
        source = audit.RECON_SOURCE
        base_path = audit.NATIVE_SOURCE/'inputs.json'
        base_hash = '8569abb81a61e34b6b5a892116af5218557ceb0436ab8dbf8a31f2aec55b1b1d'
        delta = dict(files={}, links={}, absent_paths=[], plan_sha256='d'*64,
                     base_inputs=dict(path=str(base_path), sha256=base_hash))
        documents = {source/'inputs.json': delta, base_path: original}
        digests = {source/'plan.json': 'd'*64, base_path: base_hash,
                   audit.NATIVE_SOURCE/'plan.json': 'c'*64}
        self.assertEqual(self.inherited(source, freeze, documents, digests), delta)
        del freeze['files']['/fixture/second']
        with self.assertRaises(RuntimeError):
            self.inherited(source, freeze, documents, digests)

    def test_foreign_and_nested_reconciliation_bases_are_rejected(self):
        for changed in ['source', 'path', 'hash', 'nested']:
            source, original, freeze, _, _ = self.fixture()
            base_path = audit.NATIVE_SOURCE/'inputs.json'
            base_hash = '8569abb81a61e34b6b5a892116af5218557ceb0436ab8dbf8a31f2aec55b1b1d'
            delta = dict(files={}, plan_sha256='d'*64,
                         base_inputs=dict(path=str(base_path), sha256=base_hash))
            source = source if changed == 'source' else audit.RECON_SOURCE
            if changed == 'path':
                delta['base_inputs']['path'] = '/fixture/foreign/inputs.json'
            elif changed == 'hash':
                delta['base_inputs']['sha256'] = 'f'*64
            elif changed == 'nested':
                original['base_inputs'] = dict(path='/fixture/nested', sha256='e'*64)
            documents = {source/'inputs.json': delta, base_path: original}
            digests = {source/'plan.json': 'd'*64, base_path: base_hash,
                       audit.NATIVE_SOURCE/'plan.json': 'c'*64}
            with self.subTest(changed=changed), self.assertRaises(RuntimeError):
                self.inherited(source, freeze, documents, digests)


if __name__ == '__main__':
    unittest.main()
