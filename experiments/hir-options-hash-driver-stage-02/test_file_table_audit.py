"""Tiny independent-auditor cross-checks; synthetic payload paths are never opened.

Only the base JSON fixture and its owned TemporaryDirectory may be touched.
The reviewed harness supplies the exact generic helper and verifier modules.
"""
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
import verify as audit


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode()


def synthetic_row(size=13, digest='a' * 64, inode=101):
    return dict(size=size, sha256=digest,
                identity=dict(dev=1, ino=inode, mode=stat.S_IFREG | 0o644,
                              size=size, mtime_ns=10, ctime_ns=11, nlink=2))


class Catalog:
    def __init__(self, root):
        self.root = root
        self.parent = root / 'parent'
        self.path = self.parent / 'kept' / 'base.json'
        self.path.parent.mkdir(parents=True)
        self.base = dict(files={'/fixture/original': synthetic_row(),
                                '/fixture/alias': synthetic_row()},
                         links={'/fixture/link': {'target': 'original', 'stamp': [1, 2]}},
                         absent_paths=['/fixture/absent'], snapshot_inputs=['/fixture/original'],
                         plan_sha256='c' * 64, python='/fixture/python',
                         launch_environment={'LANG': 'C'},
                         context={'flag': True, 'integer': 1, 'real': 1.0, 'nested': [None, 'base']})
        self.publish(canonical(self.base))
        self.full = copy.deepcopy(self.base)
        self.full['files'][str(self.path)] = self.base_row()
        self.full['files']['/fixture/new'] = synthetic_row(7, 'b' * 64, 202)
        self.full['links']['/fixture/new-link'] = {'target': 'new', 'stamp': [3, 4]}
        self.full['absent_paths'].append('/fixture/new-absence')
        self.full['snapshot_inputs'] = ['/fixture/new', str(self.path), '/fixture/alias', '/fixture/original']
        self.full['context']['nested'].append({'flag': False, 'real': -0.0})
        self.full['plan_sha256'] = 'd' * 64
        self.full['launch_environment']['CONTEXT'] = 'current'

    def publish(self, data):
        self.path.write_bytes(data)
        self.bytes = data
        self.digest = hashlib.sha256(data).hexdigest()

    def base_row(self):
        info = self.path.stat()
        return dict(size=len(self.bytes), sha256=self.digest,
                    identity={key: getattr(info, 'st_' + key) for key in table.IDENTITY_FIELDS})

    def reference(self):
        return dict(path=str(self.path), sha256=self.digest)

    def compact(self):
        return table.split(self.full, base_path=str(self.path), base_sha256=self.digest)

    def rebind_base(self, compact):
        compact['file_table_base'] = self.reference()
        compact['files'][str(self.path)] = self.base_row()
        self.rebind_integrity(compact)

    def rebind_integrity(self, compact):
        files = self.base['files'] | compact['files']
        compact['file_table_integrity'] = dict(sha256=hashlib.sha256(canonical(files)).hexdigest(),
            count=len(files), total_bytes=sum(row['size'] for row in files.values()))

    def replace_ancestor_keep_exact_leaf(self):
        before = self.base_row()
        moved = self.root / 'old-parent'
        self.parent.rename(moved)
        self.parent.mkdir()
        (moved / 'kept').rename(self.parent / 'kept')
        if self.base_row() != before:
            raise AssertionError('route-only fixture unexpectedly changed the leaf identity')


class FileTableAuditTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='file-table-audit-fixture-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.serial = 0

    def fixture(self):
        self.serial += 1
        return Catalog(self.root / str(self.serial))

    def complete(self, fixture, compact):
        return audit.complete_file_table(compact, expected_base=fixture.reference())

    def refused_by_both(self, fixture, compact):
        with self.assertRaises((RuntimeError, ValueError, OSError)):
            self.complete(fixture, compact)
        with self.assertRaises((RuntimeError, ValueError, OSError)):
            table.expand(compact)

    def test_full_roundtrip_preserves_headers_types_order_and_aliases(self):
        fixture = self.fixture()
        original = canonical(fixture.full)
        compact = fixture.compact()
        before = canonical(compact)
        observed = self.complete(fixture, compact)
        self.assertEqual(canonical(observed), canonical(table.expand(compact)))
        self.assertEqual(canonical(observed), original)
        self.assertEqual(canonical(compact), before)
        self.assertEqual(canonical(fixture.full), original)
        self.assertEqual(set(observed['files']), set(fixture.full['files']))
        self.assertEqual(observed['snapshot_inputs'], fixture.full['snapshot_inputs'])
        self.assertEqual(observed['files']['/fixture/original'], observed['files']['/fixture/alias'])
        self.assertEqual(fixture.path.read_bytes(), fixture.bytes)

    def test_reconstructed_objects_do_not_alias_caller_metadata_or_rows(self):
        fixture = self.fixture()
        compact = fixture.compact()
        before = canonical(compact)
        observed = self.complete(fixture, compact)
        observed['files']['/fixture/new']['identity']['ino'] += 1
        observed['files']['/fixture/original']['identity']['ino'] += 1
        observed['context']['nested'].append('changed')
        observed['links']['/fixture/new-link']['target'] = 'changed'
        self.assertEqual(canonical(compact), before)
        self.assertEqual(canonical(self.complete(fixture, compact)), canonical(fixture.full))

    def test_exact_expected_base_is_required_before_any_open(self):
        fixture = self.fixture()
        compact = fixture.compact()
        for expected in [dict(path=str(fixture.path), sha256='f' * 64),
                         dict(path='/fixture/unread', sha256=fixture.digest),
                         dict(fixture.reference(), extra=1),
                         dict(path=str(fixture.path), sha256=True)]:
            with self.subTest(expected=expected):
                with patch.object(audit.os, 'open', side_effect=AssertionError('base must not open')):
                    with self.assertRaises(RuntimeError):
                        audit.complete_file_table(compact, expected_base=expected)

    def test_reference_and_integrity_need_exact_schemas(self):
        for field in ['file_table_base', 'file_table_integrity']:
            for mutation in ['missing-sha', 'extra-field']:
                with self.subTest(field=field, mutation=mutation):
                    fixture = self.fixture()
                    compact = fixture.compact()
                    if mutation == 'missing-sha':
                        del compact[field]['sha256']
                    else:
                        compact[field]['extra'] = 1
                    self.refused_by_both(fixture, compact)

    def test_equal_and_changed_base_delta_overlap_are_rejected(self):
        for digest in ['a' * 64, 'f' * 64]:
            with self.subTest(digest=digest):
                fixture = self.fixture()
                compact = fixture.compact()
                compact['files']['/fixture/original'] = synthetic_row(digest=digest)
                fixture.rebind_integrity(compact)
                self.refused_by_both(fixture, compact)

    def test_missing_base_file_or_new_delta_row_is_rejected(self):
        for role in ['base-file', 'new-file']:
            with self.subTest(role=role):
                fixture = self.fixture()
                compact = fixture.compact()
                name = str(fixture.path) if role == 'base-file' else '/fixture/new'
                del compact['files'][name]
                compact['snapshot_inputs'].remove(name)
                self.refused_by_both(fixture, compact)

    def test_typed_size_and_identity_corruption_survives_no_integrity_relabel(self):
        for scope, field in [('row', 'size')] + [('identity', key) for key in table.IDENTITY_FIELDS]:
            for replacement in [True, 1.0]:
                with self.subTest(scope=scope, field=field, replacement=replacement):
                    fixture = self.fixture()
                    compact = fixture.compact()
                    row = compact['files']['/fixture/new']
                    if scope == 'row':
                        row['size'] = replacement
                        row['identity']['size'] = replacement
                    else:
                        row['identity'][field] = replacement
                    fixture.rebind_integrity(compact)
                    self.refused_by_both(fixture, compact)

    def test_exact_row_identity_mode_and_size_contract(self):
        for mutation in ['row-extra', 'identity-missing', 'identity-extra', 'directory', 'size-mismatch', 'uppercase-sha']:
            with self.subTest(mutation=mutation):
                fixture = self.fixture()
                compact = fixture.compact()
                row = compact['files']['/fixture/new']
                if mutation == 'row-extra':
                    row['extra'] = 1
                elif mutation == 'identity-missing':
                    del row['identity']['ctime_ns']
                elif mutation == 'identity-extra':
                    row['identity']['extra'] = 1
                elif mutation == 'directory':
                    row['identity']['mode'] = stat.S_IFDIR | 0o700
                elif mutation == 'size-mismatch':
                    row['identity']['size'] += 1
                else:
                    row['sha256'] = 'A' * 64
                fixture.rebind_integrity(compact)
                self.refused_by_both(fixture, compact)

    def test_integrity_sha_count_bytes_and_counter_types_are_bound(self):
        for key, replacement in [('sha256', '0' * 64), ('count', 3), ('total_bytes', 1),
                                 ('count', True), ('count', 4.0), ('total_bytes', False)]:
            with self.subTest(key=key, replacement=replacement):
                fixture = self.fixture()
                compact = fixture.compact()
                compact['file_table_integrity'][key] = replacement
                self.refused_by_both(fixture, compact)

    def test_nested_or_partial_base_reference_is_rejected_with_rebound_sha(self):
        for field in ['file_table_base', 'file_table_integrity']:
            with self.subTest(field=field):
                fixture = self.fixture()
                compact = fixture.compact()
                base = copy.deepcopy(fixture.base)
                base[field] = fixture.reference()
                fixture.publish(canonical(base))
                fixture.rebind_base(compact)
                self.refused_by_both(fixture, compact)

    def test_base_cannot_include_its_own_row(self):
        fixture = self.fixture()
        compact = fixture.compact()
        base = copy.deepcopy(fixture.base)
        base['files'][str(fixture.path)] = synthetic_row()
        fixture.publish(canonical(base))
        fixture.rebind_base(compact)
        self.refused_by_both(fixture, compact)

    def test_changed_bytes_or_replaced_same_bytes_base_is_rejected(self):
        for mutation in ['bytes', 'identity']:
            with self.subTest(mutation=mutation):
                fixture = self.fixture()
                compact = fixture.compact()
                if mutation == 'bytes':
                    fixture.path.write_bytes(b'x' * len(fixture.bytes))
                else:
                    replacement = fixture.root / 'replacement.json'
                    replacement.write_bytes(fixture.bytes)
                    replacement.replace(fixture.path)
                self.refused_by_both(fixture, compact)

    def test_missing_base_is_rejected(self):
        fixture = self.fixture()
        compact = fixture.compact()
        fixture.path.unlink()
        self.refused_by_both(fixture, compact)

    def test_symlink_leaf_and_ancestor_are_rejected(self):
        for role in ['leaf', 'ancestor']:
            with self.subTest(role=role):
                fixture = self.fixture()
                compact = fixture.compact()
                if role == 'leaf':
                    target = fixture.path.with_name('actual.json')
                    fixture.path.rename(target)
                    fixture.path.symlink_to(target)
                else:
                    target = fixture.root / 'actual-parent'
                    fixture.parent.rename(target)
                    fixture.parent.symlink_to(target, target_is_directory=True)
                self.refused_by_both(fixture, compact)

    def test_duplicate_keys_nonfinite_and_trailing_raw_base_are_rejected(self):
        cases = [b'{"files":{},"files":{}}', b'{"files":{"x":1,"x":2}}',
                 b'{"value":NaN}', b'{"value":1e400}', b'\xff{}', b'[]']
        fixture = self.fixture()
        cases.append(fixture.bytes + b'{}')
        for raw in cases:
            with self.subTest(raw=raw[:40]):
                fixture = self.fixture()
                compact = fixture.compact()
                fixture.publish(raw)
                fixture.rebind_base(compact)
                self.refused_by_both(fixture, compact)

    def test_noncanonical_logical_names_are_rejected_without_payload_reads(self):
        for name in ['relative', '/fixture/../escape', '/fixture//new', '//fixture/new', '/fixture/new/', '/fixture/\x00bad']:
            with self.subTest(name=name):
                fixture = self.fixture()
                compact = fixture.compact()
                compact['files'][name] = compact['files'].pop('/fixture/new')
                compact['snapshot_inputs'].remove('/fixture/new')
                fixture.rebind_integrity(compact)
                self.refused_by_both(fixture, compact)

    def test_selection_and_file_link_absence_conflicts_are_rejected(self):
        for mutation in ['missing-selection', 'duplicate-selection', 'present-absence', 'present-link']:
            with self.subTest(mutation=mutation):
                fixture = self.fixture()
                compact = fixture.compact()
                if mutation == 'missing-selection':
                    compact['snapshot_inputs'].append('/fixture/missing')
                elif mutation == 'duplicate-selection':
                    compact['snapshot_inputs'].append('/fixture/original')
                elif mutation == 'present-absence':
                    compact['absent_paths'].append('/fixture/original')
                else:
                    compact['links']['/fixture/original'] = {'target': 'elsewhere'}
                self.refused_by_both(fixture, compact)

    def test_python_only_and_nonfinite_metadata_are_rejected(self):
        for value in [(1, 2), {1, 2}, {1: 'integer-key'}, float('nan'), float('inf')]:
            with self.subTest(value=repr(value)):
                fixture = self.fixture()
                compact = fixture.compact()
                compact['new_header'] = value
                self.refused_by_both(fixture, compact)

    def test_declared_bounds_refuse_oversized_integrity_and_file(self):
        for mutation in ['count', 'total', 'file']:
            with self.subTest(mutation=mutation):
                fixture = self.fixture()
                compact = fixture.compact()
                if mutation == 'count':
                    compact['file_table_integrity']['count'] = 180001
                elif mutation == 'total':
                    compact['file_table_integrity']['total_bytes'] = 8 * 2**30 + 1
                else:
                    row = compact['files']['/fixture/new']
                    row['size'] = row['identity']['size'] = 2**30 + 1
                    fixture.rebind_integrity(compact)
                self.refused_by_both(fixture, compact)

    def test_mutation_during_base_read_is_rejected(self):
        for operation in ['generic', 'independent']:
            with self.subTest(operation=operation):
                fixture = self.fixture()
                compact = fixture.compact()
                original_read = os.read
                changed = False

                def read_then_change(descriptor, count):
                    nonlocal changed
                    data = original_read(descriptor, count)
                    if data and not changed:
                        changed = True
                        fixture.path.write_bytes(b'x' * len(fixture.bytes))
                    return data

                with patch.object(os, 'read', side_effect=read_then_change):
                    with self.assertRaises((RuntimeError, ValueError, OSError)):
                        table.expand(compact) if operation == 'generic' else self.complete(fixture, compact)
                self.assertTrue(changed)

    def test_post_read_leaf_mutation_is_rejected_before_return(self):
        self.post_read_mutation('leaf')

    def test_post_read_ancestor_replacement_keeps_leaf_but_is_rejected(self):
        self.post_read_mutation('ancestor')

    def post_read_mutation(self, role):
        for operation in ['generic', 'independent']:
            with self.subTest(operation=operation, role=role):
                fixture = self.fixture()
                compact = fixture.compact()
                original_read = os.read
                original_encoding = audit.audit_json_bytes
                exhausted = False
                changed = False

                def observe_eof(descriptor, count):
                    nonlocal exhausted
                    data = original_read(descriptor, count)
                    if not data:
                        exhausted = True
                    return data

                def mutate():
                    nonlocal changed
                    if exhausted and not changed:
                        changed = True
                        if role == 'leaf':
                            fixture.path.write_bytes(b'x' * len(fixture.bytes))
                        else:
                            fixture.replace_ancestor_keep_exact_leaf()

                def encode_then_mutate(value):
                    data = original_encoding(value)
                    mutate()
                    return data

                with patch.object(os, 'read', side_effect=observe_eof):
                    with patch.object(audit, 'audit_json_bytes', side_effect=encode_then_mutate):
                        with self.assertRaises((RuntimeError, ValueError, OSError)):
                            if operation == 'generic':
                                table.expand(compact, guard=mutate)
                            else:
                                self.complete(fixture, compact)
                self.assertTrue(changed)


if __name__ == '__main__':
    unittest.main()
