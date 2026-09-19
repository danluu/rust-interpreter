"""Owned tiny physical fixtures; no producer imports or real provider reads.

Only the sibling audit_io module is imported. All mutations, links and FIFO
fixtures stay inside a TemporaryDirectory. These tests have not been executed
by the source author; a separately frozen ordinary control run is required.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest


def load_io():
    target = Path(__file__).with_name('audit_io.py')
    spec = importlib.util.spec_from_file_location('runtime05_saved_io_fixture', target)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Physical(unittest.TestCase):
    def setUp(self):
        self.io = load_io()
        self.temporary = tempfile.TemporaryDirectory(prefix='runtime05-io-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.input = self.root/'input.json'
        self.input.write_bytes(b'{"fixture":1}\n')
        self.row = self.record(self.input)

    def record(self, path):
        data = path.read_bytes()
        return dict(size=len(data), sha256=hashlib.sha256(data).hexdigest(),
                    identity=self.io.stamp(path.lstat()))

    def access(self, **kwargs):
        return self.io.Access({str(self.input):self.row}, **kwargs)

    def test_complete_file_callbacks_and_final_readback(self):
        access = self.access()
        self.assertEqual(access.file(self.input), self.input)
        self.assertEqual(access.read_json(self.input), {'fixture':1})
        self.assertEqual(access.sha(self.input), self.row['sha256'])
        self.assertEqual(access.identity(self.input), self.row['identity'])
        self.assertEqual(access.record(self.input), dict(path=str(self.input), **self.row))
        access.recheck(full=True)
        self.assertEqual(access.checked, {str(self.input):self.row})

    def test_undeclared_path_rejected_before_guard_or_read(self):
        def forbidden():
            raise AssertionError('scope refusal must precede IO guard')
        access = self.access(guard=forbidden)
        with self.assertRaisesRegex(RuntimeError, 'undeclared'):
            access.read_bytes(self.root/'missing')

    def test_historical_paths_rejected_by_every_physical_api(self):
        historical = self.root/'historical-copy'
        historical.write_bytes(b'owned historical bytes')
        access = self.access(historical_paths=[str(historical)], output_roots=[self.root])
        for method in [access.file, access.record, access.sha, access.identity,
                       access.read_bytes, access.read_json, access.directory_record, access.inventory]:
            with self.assertRaisesRegex(RuntimeError, 'historical proof copy'):
                method(historical)
        self.assertEqual(historical.read_bytes(), b'owned historical bytes')

    def test_historical_row_cannot_be_declared_current(self):
        with self.assertRaisesRegex(RuntimeError, 'declared current'):
            self.access(historical_paths=[str(self.input)])

    def test_exact_frozen_and_output_scopes_remain_distinct(self):
        output = self.root/'output'; output.mkdir(); data = output/'record'; data.write_bytes(b'actual')
        access = self.access(output_roots=[output])
        self.assertEqual(access.read_bytes(data, frozen=False), b'actual')
        with self.assertRaisesRegex(RuntimeError, 'undeclared'):
            access.read_bytes(data, frozen=True)
        with self.assertRaisesRegex(RuntimeError, 'undeclared'):
            access.read_bytes(self.input, frozen=False)
        with self.assertRaisesRegex(RuntimeError, 'nonoverlapping'):
            self.access(output_roots=[self.root, output])

    def test_leaf_symlink_never_supplies_payload(self):
        leaf = self.root/'alias'; leaf.symlink_to(self.input)
        access = self.access(output_roots=[self.root])
        with self.assertRaises((RuntimeError, OSError)):
            access.read_bytes(leaf)

    def test_ancestor_symlink_is_rejected(self):
        real = self.root/'real'; real.mkdir(); payload = real/'data'; payload.write_bytes(b'x')
        alias = self.root/'alias'; alias.symlink_to(real, target_is_directory=True)
        access = self.access(output_roots=[self.root])
        with self.assertRaises((RuntimeError, OSError)):
            access.read_bytes(alias/'data')

    def test_preexisting_fifo_refused_without_opening_for_payload(self):
        fifo = self.root/'fifo'; os.mkfifo(fifo)
        access = self.access(output_roots=[self.root])
        with self.assertRaisesRegex(RuntimeError, 'entry kind'):
            access.read_bytes(fifo)

    def test_size_cap_is_enforced_before_collecting(self):
        with self.assertRaisesRegex(RuntimeError, 'read bound'):
            self.access().read_bytes(self.input, limit=1)
        for limit in [True, -1, self.io.MAX_FILE+1]:
            with self.assertRaisesRegex(RuntimeError, 'read limit'):
                self.access().read_bytes(self.input, limit=limit)

    def test_current_hash_and_identity_are_both_required(self):
        for field in ['sha256', 'identity']:
            row = copy.deepcopy(self.row)
            if field == 'sha256':
                row[field] = '0'*64
            else:
                row[field]['ino'] += 1
            access = self.io.Access({str(self.input):row})
            with self.assertRaisesRegex(RuntimeError, 'frozen physical'):
                access.sha(self.input)

    def test_mutation_during_streaming_is_rejected(self):
        calls = []
        def mutate():
            calls.append(1)
            if len(calls) == 2:
                self.input.write_bytes(b'{"fixture":2}\n')
        with self.assertRaisesRegex(RuntimeError, 'changed during read'):
            self.access(guard=mutate).read_bytes(self.input)

    def test_post_eof_guard_cannot_replace_leaf(self):
        calls = []
        def mutate():
            calls.append(1)
            if len(calls) == 3:
                replacement = self.root/'replacement'; replacement.write_bytes(self.input.read_bytes())
                replacement.replace(self.input)
        with self.assertRaisesRegex(RuntimeError, 'changed during read'):
            self.access(guard=mutate).read_bytes(self.input)

    def test_post_eof_guard_cannot_replace_held_ancestor(self):
        directory = self.root/'route'; directory.mkdir(); payload = directory/'bytes'; payload.write_bytes(b'stable')
        calls = []
        def mutate():
            calls.append(1)
            if len(calls) == 3:
                directory.rename(self.root/'old-route'); directory.mkdir(); (directory/'bytes').write_bytes(b'stable')
        access = self.io.Access({str(payload):self.record(payload)}, guard=mutate)
        with self.assertRaisesRegex(RuntimeError, 'ancestor route changed'):
            access.read_bytes(payload)

    def test_repeated_output_read_retains_first_observation(self):
        output = self.root/'output'; output.write_bytes(b'one')
        access = self.access(output_roots=[self.root]); access.read_bytes(output)
        output.write_bytes(b'two')
        with self.assertRaisesRegex(RuntimeError, 'first complete file observation'):
            access.read_bytes(output)
        self.assertEqual(access.checked[str(output)]['sha256'], hashlib.sha256(b'one').hexdigest())

    def test_duplicate_and_nonfinite_json_refused(self):
        for index, data in enumerate([b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}']):
            output = self.root/str(index); output.write_bytes(data)
            access = self.access(output_roots=[self.root])
            with self.assertRaises((RuntimeError, ValueError)):
                access.read_json(output)

    def test_exact_directory_entries_and_stability(self):
        directory = self.root/'snapshots'; directory.mkdir(); (directory/'one.gz').write_bytes(b'owned fixture')
        entry = self.io.stamp(directory.lstat())
        access = self.access(entries={str(directory):entry})
        self.assertEqual(access.directory_record(directory), dict(identity=entry, children=['one.gz']))
        (directory/'extra').write_bytes(b'x')
        with self.assertRaisesRegex(RuntimeError, 'declared directory changed'):
            access.directory_record(directory)

    def test_inventory_includes_every_directory_and_file(self):
        output = self.root/'prefix'; output.mkdir(); (output/'inner').mkdir(); (output/'inner/data').write_bytes(b'x')
        access = self.access(output_roots=[output]); before = access.inventory(output)
        self.assertEqual(set(before), {'.', 'inner', 'inner/data'})
        self.assertEqual(before['inner/data']['sha256'], hashlib.sha256(b'x').hexdigest())
        self.assertEqual(before['inner']['kind'], 'directory')
        self.assertEqual(access.inventory(output), before)
        (output/'unexpected').write_bytes(b'new')
        with self.assertRaisesRegex(RuntimeError, 'complete directory changed'):
            access.inventory(output)

    def test_inventory_refuses_any_symlink(self):
        output = self.root/'prefix'; output.mkdir(); (output/'alias').symlink_to(self.input)
        access = self.access(output_roots=[output])
        with self.assertRaisesRegex(RuntimeError, 'entry kind'):
            access.inventory(output)

    def test_final_recheck_catches_saved_output_mutation(self):
        output = self.root/'output'; output.write_bytes(b'one')
        access = self.access(output_roots=[self.root]); access.sha(output)
        output.write_bytes(b'two')
        with self.assertRaisesRegex(RuntimeError, 'first complete file observation'):
            access.recheck(full=True)


class Inspection(unittest.TestCase):
    def setUp(self):
        self.io = load_io()
        self.row = dict(size=1, sha256='a'*64, identity=dict(dev=1, ino=2,
            mode=stat.S_IFREG | 0o600, nlink=1, size=1, mtime_ns=3, ctime_ns=4))
        self.prepared = dict(files={'/fixture/original':self.row}, snapshot_inputs=['/fixture/original'],
            links={}, absent_paths=['/fixture/absent'], executor_routes={}, plan_sha256='b'*64,
            unusual_typed_header=dict(integer=1, flag=True, nested=[False, 0, None]))

    def test_disjoint_union_preserves_headers_and_original_selection(self):
        extra = {'/fixture/auditor':copy.deepcopy(self.row)}; original = copy.deepcopy(self.prepared)
        answer = self.io.inspection_union(self.prepared, extra, historical_paths=['/fixture/historical'])
        self.assertTrue(self.io.same(answer['prepared'], original))
        self.assertTrue(self.io.same(self.prepared, original))
        self.assertEqual(set(answer['value']['files']), {'/fixture/original', '/fixture/auditor'})
        self.assertEqual(answer['value']['snapshot_inputs'], ['/fixture/original'])
        self.assertEqual(answer['report']['additional_paths'], ['/fixture/auditor'])
        self.assertEqual(answer['report']['additional_bytes'], 1)
        answer['value']['files']['/fixture/original']['identity']['ino'] += 1
        self.assertTrue(self.io.same(self.prepared, original))

    def test_identical_overlap_gets_no_new_file_or_byte_credit(self):
        answer = self.io.inspection_union(self.prepared, copy.deepcopy(self.prepared['files']), historical_paths=[])
        self.assertEqual(answer['report']['additional_files'], 0)
        self.assertEqual(answer['report']['additional_bytes'], 0)
        self.assertTrue(self.io.same(answer['value'], self.prepared))

    def test_overlap_cannot_relabel_any_prepared_field(self):
        for field in ['sha256', 'identity']:
            extra = copy.deepcopy(self.prepared['files'])
            if field == 'sha256':
                extra['/fixture/original'][field] = 'c'*64
            else:
                extra['/fixture/original'][field]['ino'] += 1
            with self.assertRaisesRegex(RuntimeError, 'relabel'):
                self.io.inspection_union(self.prepared, extra, historical_paths=[])

    def test_bool_integer_record_relabelling_is_refused(self):
        for place in ['size', 'identity']:
            extra = {'/fixture/auditor':copy.deepcopy(self.row)}
            if place == 'size':
                extra['/fixture/auditor']['size'] = True
            else:
                extra['/fixture/auditor']['identity']['nlink'] = True
            with self.assertRaises(RuntimeError):
                self.io.inspection_union(self.prepared, extra, historical_paths=[])

    def test_historical_path_cannot_enter_any_current_representation(self):
        for role in ['files', 'snapshot_inputs', 'extra']:
            prepared = copy.deepcopy(self.prepared); extra = {}; name = '/fixture/historical'
            if role == 'files':
                prepared['files'][name] = copy.deepcopy(self.row)
            elif role == 'extra':
                extra[name] = copy.deepcopy(self.row)
            else:
                prepared[role].append(name)
            with self.assertRaisesRegex(RuntimeError, 'historical copy'):
                self.io.inspection_union(prepared, extra, historical_paths=[name])

    def test_real_prepared_retirement_absence_is_preserved_without_invention(self):
        prepared = copy.deepcopy(self.prepared); historical = '/fixture/retired-copy'
        prepared['absent_paths'].append(historical); before = copy.deepcopy(prepared)
        answer = self.io.inspection_union(prepared, {'/fixture/auditor':self.row},
                                         historical_paths=[historical])
        self.assertTrue(self.io.same(answer['prepared'], before))
        self.assertTrue(self.io.same(answer['value']['absent_paths'], before['absent_paths']))
        self.assertNotIn(historical, answer['value']['files'])
        self.assertNotIn(historical, answer['value']['snapshot_inputs'])
        without = self.io.inspection_union(self.prepared, {}, historical_paths=[historical])
        self.assertNotIn(historical, without['value']['absent_paths'])

    def test_compact_or_ambiguous_input_is_not_a_complete_union(self):
        for field in ['file_table_base', 'file_table_integrity']:
            prepared = copy.deepcopy(self.prepared); prepared[field] = {}
            with self.assertRaisesRegex(RuntimeError, 'expanded prepared'):
                self.io.inspection_union(prepared, {}, historical_paths=[])
        for names in [['/fixture/z', '/fixture/a'], ['/fixture/a', '/fixture/a']]:
            with self.assertRaisesRegex(RuntimeError, 'sorted unique'):
                self.io.inspection_union(self.prepared, {}, historical_paths=names)

    def test_unsafe_file_routes_and_changed_union_cap_rejected(self):
        for name in ['/fixture/../escape', '//fixture/a', '/fixture/./a', '/fixture/a\n']:
            with self.assertRaisesRegex(RuntimeError, 'canonical absolute'):
                self.io.inspection_union(self.prepared, {name:self.row}, historical_paths=[])
        self.io.MAX_FILES = 1
        with self.assertRaisesRegex(RuntimeError, 'file table'):
            self.io.inspection_union(self.prepared, {'/fixture/auditor':self.row}, historical_paths=[])
