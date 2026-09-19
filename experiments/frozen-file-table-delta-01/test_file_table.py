"""Tiny synthetic catalog fixtures; no compiler, provider, process or network calls."""
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

import file_table as table


def fake_row(size=12, digest='a' * 64):
    return dict(size=size, sha256=digest,
                identity=dict(dev=1, ino=101, mode=stat.S_IFREG | 0o644,
                              size=size, mtime_ns=10, ctime_ns=11, nlink=2))


class FileTableTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='file-table-fixture-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.base_path = self.root / 'base.json'
        self.base = dict(files={'/fixture/a': fake_row(), '/fixture/alias': fake_row()},
                         links={'/fixture/link': {'target': 'a', 'stamp': [1, 2]}},
                         absent_paths=['/fixture/absent'], snapshot_inputs=['/fixture/a'],
                         context=dict(integer=1, real=1.0, flag=True, nested=[None, 'original']))
        self.publish_base(self.base)
        self.full = copy.deepcopy(self.base)
        self.full['files'][str(self.base_path)] = self.base_row()
        self.full['files']['/fixture/new'] = fake_row(7, 'b' * 64)
        self.full['links']['/fixture/new-link'] = {'target': 'new', 'stamp': [3, 4]}
        self.full['absent_paths'].append('/fixture/new-absence')
        self.full['snapshot_inputs'] = ['/fixture/new', '/fixture/a', str(self.base_path), '/fixture/alias']
        self.full['context']['nested'].append({'value': False})

    def publish_base(self, document=None, *, raw=None):
        self.raw = table.encoded(document) if raw is None else raw
        self.base_path.write_bytes(self.raw)
        self.digest = hashlib.sha256(self.raw).hexdigest()

    def base_row(self):
        observed = self.base_path.stat()
        return dict(size=len(self.raw), sha256=self.digest,
                    identity={name: getattr(observed, 'st_' + name) for name in table.IDENTITY_FIELDS})

    def split(self, full=None, *, guard=lambda: None):
        return table.split(self.full if full is None else full, base_path=str(self.base_path),
                           base_sha256=self.digest, guard=guard)

    def revised_base(self, document=None, *, raw=None):
        self.publish_base(document, raw=raw)
        self.full['files'][str(self.base_path)] = self.base_row()

    def test_complete_roundtrip_preserves_all_metadata_and_logical_aliases(self):
        before = table.encoded(self.full)
        compact = self.split()
        self.assertEqual(set(compact['files']), {str(self.base_path), '/fixture/new'})
        self.assertEqual(compact['file_table_base'], dict(path=str(self.base_path), sha256=self.digest))
        expected = dict(sha256=hashlib.sha256(table.encoded(self.full['files'])).hexdigest(),
                        count=4, total_bytes=sum(row['size'] for row in self.full['files'].values()))
        self.assertEqual(compact['file_table_integrity'], expected)
        self.assertEqual(table.encoded(table.expand(compact)), before)
        self.assertEqual(table.encoded(self.full), before)
        self.assertEqual(self.base_path.read_bytes(), self.raw)

    def test_returned_documents_have_no_aliases_to_either_input(self):
        compact = self.split()
        saved_compact = table.encoded(compact)
        expanded = table.expand(compact)
        expanded['files']['/fixture/a']['identity']['ino'] = 909
        expanded['context']['nested'].append('changed')
        self.assertEqual(table.encoded(compact), saved_compact)
        compact['files']['/fixture/new']['identity']['ino'] = 808
        compact['links']['/fixture/new-link']['target'] = 'changed'
        self.assertEqual(self.full['files']['/fixture/new']['identity']['ino'], 101)
        self.assertEqual(self.full['links']['/fixture/new-link']['target'], 'new')

    def test_split_refuses_missing_base_row(self):
        del self.full['files']['/fixture/a']
        self.full['snapshot_inputs'].remove('/fixture/a')
        with self.assertRaises(ValueError):
            self.split()

    def test_split_refuses_changed_base_bytes_or_identity(self):
        for key in ('sha256', 'identity'):
            with self.subTest(key=key):
                value = copy.deepcopy(self.full)
                if key == 'sha256':
                    value['files']['/fixture/a']['sha256'] = 'f' * 64
                else:
                    value['files']['/fixture/a']['identity']['ino'] += 1
                with self.assertRaises(ValueError):
                    self.split(value)

    def test_typed_sizes_and_all_identity_fields_reject_bool_or_float(self):
        for replacement in (True, 1.0):
            for scope, field in [('row', 'size')] + [('identity', key) for key in table.IDENTITY_FIELDS]:
                with self.subTest(replacement=replacement, field=field, scope=scope):
                    value = copy.deepcopy(self.full)
                    row = value['files']['/fixture/new']
                    if scope == 'row':
                        row['size'] = replacement
                    else:
                        row['identity'][field] = replacement
                    with self.assertRaises(ValueError):
                        self.split(value)

    def test_exact_row_and_identity_schema_required(self):
        for change in ('extra-row', 'missing-row', 'extra-identity', 'missing-identity', 'size-mismatch'):
            with self.subTest(change=change):
                value = copy.deepcopy(self.full)
                row = value['files']['/fixture/new']
                if change == 'extra-row':
                    row['unreviewed'] = 1
                elif change == 'missing-row':
                    del row['sha256']
                elif change == 'extra-identity':
                    row['identity']['extra'] = 1
                elif change == 'missing-identity':
                    del row['identity']['ctime_ns']
                else:
                    row['identity']['size'] += 1
                with self.assertRaises(ValueError):
                    self.split(value)

    def test_expand_rejects_equal_or_changed_overlap(self):
        for changed in (False, True):
            with self.subTest(changed=changed):
                compact = self.split()
                compact['files']['/fixture/a'] = fake_row(digest=('f' if changed else 'a') * 64)
                with self.assertRaisesRegex(ValueError, 'overlap'):
                    table.expand(compact)

    def test_exact_base_file_row_required_in_both_directions(self):
        for action in ('missing', 'wrong-sha', 'wrong-identity'):
            for operation in ('split', 'expand'):
                with self.subTest(action=action, operation=operation):
                    document = copy.deepcopy(self.full) if operation == 'split' else self.split()
                    rows = document['files']
                    if action == 'missing':
                        del rows[str(self.base_path)]
                        document['snapshot_inputs'].remove(str(self.base_path))
                    elif action == 'wrong-sha':
                        rows[str(self.base_path)]['sha256'] = '0' * 64
                    else:
                        rows[str(self.base_path)]['identity']['ino'] += 1
                    with self.assertRaises(ValueError):
                        self.split(document) if operation == 'split' else table.expand(document)

    def test_expand_rejects_all_integrity_field_forgery(self):
        for key, value in (('sha256', '0' * 64), ('count', 3), ('total_bytes', 0),
                           ('count', True), ('count', 4.0), ('total_bytes', False)):
            with self.subTest(key=key, value=value):
                compact = self.split()
                compact['file_table_integrity'][key] = value
                with self.assertRaises(ValueError):
                    table.expand(compact)

    def test_exact_reference_and_integrity_schemas(self):
        for object_name in ('file_table_base', 'file_table_integrity'):
            for operation in ('extra', 'missing'):
                with self.subTest(object_name=object_name, operation=operation):
                    compact = self.split()
                    if operation == 'extra':
                        compact[object_name]['extra'] = 0
                    else:
                        del compact[object_name]['sha256']
                    with self.assertRaises(ValueError):
                        table.expand(compact)

    def test_base_sha_and_replaced_same_bytes_identity_are_rejected(self):
        compact = self.split()
        compact['file_table_base']['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            table.expand(compact)
        compact = self.split()
        replacement = self.root / 'replacement.json'
        replacement.write_bytes(self.raw)
        os.replace(replacement, self.base_path)
        with self.assertRaisesRegex(ValueError, 'base-file row'):
            table.expand(compact)

    def test_corrupt_or_missing_base_is_rejected(self):
        compact = self.split()
        self.base_path.write_bytes(self.raw.replace(b'original', b'corrupt!'))
        with self.assertRaises(ValueError):
            table.expand(compact)
        self.base_path.unlink()
        with self.assertRaises(FileNotFoundError):
            table.expand(compact)

    def test_nested_partial_or_cyclic_reference_is_rejected(self):
        for field in ('file_table_base', 'file_table_integrity'):
            with self.subTest(field=field):
                base = copy.deepcopy(self.base)
                base[field] = dict(path=str(self.base_path), sha256='0' * 64)
                self.revised_base(base)
                with self.assertRaisesRegex(ValueError, 'nested, cyclic or partial'):
                    self.split()

    def test_base_self_file_row_is_rejected(self):
        base = copy.deepcopy(self.base)
        base['files'][str(self.base_path)] = fake_row()
        self.revised_base(base)
        with self.assertRaisesRegex(ValueError, 'own file row'):
            self.split()

    def test_split_refuses_already_compact_or_partial_input(self):
        for field in ('file_table_base', 'file_table_integrity'):
            with self.subTest(field=field):
                value = copy.deepcopy(self.full)
                value[field] = {}
                with self.assertRaises(ValueError):
                    self.split(value)

    def test_duplicate_json_keys_and_nonfinite_base_constants_are_rejected(self):
        samples = (b'{"files":{},"files":{}}', b'{"files":{"x":1,"x":2}}',
                   b'{"value":NaN}', b'{"value":Infinity}', b'{"value":-Infinity}')
        for raw in samples:
            with self.subTest(raw=raw):
                self.revised_base(raw=raw)
                with self.assertRaises(ValueError):
                    self.split()

    def test_trailing_or_invalid_utf8_base_bytes_are_rejected(self):
        for raw in (self.raw + b'{}', b'\xff{}', b'[]'):
            with self.subTest(raw=raw):
                self.revised_base(raw=raw)
                with self.assertRaises(ValueError):
                    self.split()

    def test_symlink_leaf_and_symlink_ancestor_are_rejected(self):
        actual = self.root / 'actual.json'
        self.base_path.rename(actual)
        self.base_path.symlink_to(actual)
        with self.assertRaises((ValueError, OSError)):
            self.split()
        alias = self.root / 'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises((ValueError, OSError)):
            table.split(self.full, base_path=str(alias / 'actual.json'), base_sha256=self.digest)

    def test_mutation_during_held_read_is_rejected(self):
        original_read = os.read
        changed = False

        def read_then_change(descriptor, count):
            nonlocal changed
            result = original_read(descriptor, count)
            if result and not changed:
                changed = True
                self.base_path.write_bytes(b'x' * len(self.raw))
            return result

        with patch.object(table.os, 'read', side_effect=read_then_change):
            with self.assertRaisesRegex(ValueError, 'changed during read'):
                self.split()
        self.assertTrue(changed)

    def test_replaced_parent_route_during_read_is_rejected(self):
        nested = self.root / 'nested'
        nested.mkdir()
        moved = self.root / 'moved'
        self.base_path.rename(nested / 'base.json')
        self.base_path = nested / 'base.json'
        self.full['files'].pop(str(self.root / 'base.json'))
        self.full['files'][str(self.base_path)] = self.base_row()
        self.full['snapshot_inputs'] = ['/fixture/a']
        original_read = os.read
        changed = False

        def read_then_move(descriptor, count):
            nonlocal changed
            result = original_read(descriptor, count)
            if result and not changed:
                changed = True
                nested.rename(moved)
                nested.mkdir()
            return result

        with patch.object(table.os, 'read', side_effect=read_then_move):
            with self.assertRaises((ValueError, OSError)):
                self.split()
        self.assertTrue(changed)

    def test_guard_mutation_after_read_is_rejected_before_return(self):
        for operation in ('split', 'expand'):
            with self.subTest(operation=operation):
                self.revised_base(self.base)
                compact = self.split()
                original_read = os.read
                exhausted = False
                changed = False

                def observe_eof(descriptor, count):
                    nonlocal exhausted
                    result = original_read(descriptor, count)
                    if not result:
                        exhausted = True
                    return result

                def mutate_after_read():
                    nonlocal changed
                    if exhausted and not changed:
                        changed = True
                        self.base_path.write_bytes(b'x' * len(self.raw))

                with patch.object(table.os, 'read', side_effect=observe_eof):
                    with self.assertRaisesRegex(ValueError, 'base changed during read or construction'):
                        if operation == 'split':
                            self.split(guard=mutate_after_read)
                        else:
                            table.expand(compact, guard=mutate_after_read)
                self.assertTrue(changed)

    def test_noncanonical_paths_and_digest_are_rejected(self):
        for name in ('relative', '/fixture/../escape', '/fixture//a', '//fixture/a', '/fixture/a/', '/fixture/\x00a'):
            with self.subTest(name=name):
                value = copy.deepcopy(self.full)
                value['files'][name] = fake_row()
                with self.assertRaises(ValueError):
                    self.split(value)
        value = copy.deepcopy(self.full)
        value['files']['/fixture/new']['sha256'] = 'A' * 64
        with self.assertRaises(ValueError):
            self.split(value)

    def test_full_snapshot_selection_keeps_order_but_rejects_omission_or_duplicate(self):
        compact = self.split()
        self.assertEqual(compact['snapshot_inputs'], self.full['snapshot_inputs'])
        self.assertEqual(table.expand(compact)['snapshot_inputs'], self.full['snapshot_inputs'])
        for name in ('/fixture/missing', '/fixture/a'):
            with self.subTest(name=name):
                value = self.split()
                value['snapshot_inputs'].append(name)
                with self.assertRaises(ValueError):
                    table.expand(value)

    def test_links_absences_and_complete_metadata_cannot_alias_files(self):
        for key in ('links', 'absent_paths'):
            with self.subTest(key=key):
                value = self.split()
                if key == 'links':
                    value[key]['/fixture/a'] = {'target': 'x'}
                else:
                    value[key].append('/fixture/a')
                with self.assertRaises(ValueError):
                    table.expand(value)

    def test_file_count_and_each_file_and_total_bytes_caps(self):
        with patch.object(table, 'MAXIMUM_FILES', 3):
            with self.assertRaises(ValueError):
                self.split()
        for key, limit in (('MAXIMUM_FILE_BYTES', 6), ('MAXIMUM_TOTAL_BYTES', 20)):
            with self.subTest(key=key):
                with patch.object(table, key, limit):
                    with self.assertRaises(ValueError):
                        self.split()

    def test_base_bound_refuses_before_any_read(self):
        with patch.object(table, 'MAXIMUM_BASE_BYTES', len(self.raw) - 1):
            with patch.object(table.os, 'read', side_effect=AssertionError('read must not occur')):
                with self.assertRaisesRegex(ValueError, 'base JSON exceeds bound'):
                    self.split()

    def test_canonical_table_document_and_json_structure_caps(self):
        for key, limit in (('MAXIMUM_TABLE_BYTES', 1), ('MAXIMUM_DOCUMENT_BYTES', 1),
                           ('MAXIMUM_JSON_DEPTH', 1), ('MAXIMUM_JSON_NODES', 1)):
            with self.subTest(key=key):
                with patch.object(table, key, limit):
                    with self.assertRaises(ValueError):
                        self.split()

    def test_metadata_rejects_python_only_values_and_nonfinite_floats(self):
        for value in ((1, 2), {1, 2}, float('nan'), float('inf'), {1: 'integer-key'}):
            with self.subTest(value=repr(value)):
                full = copy.deepcopy(self.full)
                full['extra'] = value
                with self.assertRaises(ValueError):
                    self.split(full)

    def test_guard_refusal_is_propagated_without_mutation(self):
        before = self.base_path.read_bytes()
        full_before = table.encoded(self.full)

        def refuse():
            raise RuntimeError('fixture capacity refusal')

        with self.assertRaisesRegex(RuntimeError, 'fixture capacity refusal'):
            self.split(guard=refuse)
        self.assertEqual(self.base_path.read_bytes(), before)
        self.assertEqual(table.encoded(self.full), full_before)


if __name__ == '__main__':
    unittest.main()
