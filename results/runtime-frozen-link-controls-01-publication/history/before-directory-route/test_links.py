"""Real owned temporary directories and symlinks; no provider paths or probes."""
import copy
import hashlib
import os
from pathlib import Path
import tempfile
import unittest

from links import FrozenLinks, STAMP_FIELDS, stamp


class FrozenLinkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        # macOS's /var alias is outside the fixture and not an input assumption.
        self.root = Path(self.tmp.name).resolve(strict=True)
        self.real = self.root/'real'; self.real.mkdir()
        self.file = self.real/'payload'; self.file.write_bytes(b'exact frozen payload\n')
        self.alias = self.root/'alias'; self.alias.symlink_to('real', target_is_directory=True)
        self.leaf = self.real/'leaf'; self.leaf.symlink_to('payload')
        self.name = str(self.alias/'leaf')
        self.row = self.freeze(self.name)
        self.files = {str(self.file): self.record(self.file)}
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def record(self, value):
        p = Path(value); before = stamp(p.lstat()); raw = p.read_bytes()
        self.assertEqual(stamp(p.lstat()), before)
        return dict(identity=before,size=len(raw),sha256=hashlib.sha256(raw).hexdigest())

    def freeze(self, name):
        identity = stamp(Path(name).lstat())
        return dict(stamp=[identity[k] for k in STAMP_FIELDS], target=os.readlink(name),
                    resolved=str(Path(name).resolve(strict=True)))

    def read(self, name):
        self.calls.append(name)
        self.assertIn(name,self.files)
        self.assertEqual(str(Path(name).resolve(strict=True)),name)
        row = self.record(name); self.assertEqual(row,self.files[name])
        return row

    def verifier(self, name=None, row=None, read=None):
        return FrozenLinks({name or self.name: row or self.row},read_file=read or self.read)

    def test_relative_parent_alias_preserves_frozen_leaf_and_file_bytes(self):
        v = self.verifier(); proof = v.verify(self.name)
        self.assertEqual(proof['resolved_file'],self.files[str(self.file)])
        self.assertFalse(proof['ancestors_were_in_original_freeze'])
        self.assertEqual(self.calls,[str(self.file)])
        self.assertEqual([r['path'] for r in proof['current_ancestor_observations']['links']],
                         [str(self.alias),str(self.leaf)])
        self.assertEqual(v.recheck()[self.name],proof)

    def test_link_with_ordinary_ancestors(self):
        name=str(self.leaf); self.assertEqual(self.verifier(name,self.freeze(name)).verify(name)['resolved_file'],self.files[str(self.file)])

    def test_absolute_parent_alias(self):
        self.alias.unlink();self.alias.symlink_to(self.real,target_is_directory=True)
        self.assertEqual(self.verifier().verify(self.name)['resolved_identity'],self.files[str(self.file)]['identity'])

    def test_two_parent_aliases_and_relative_dotdot(self):
        outer=self.root/'outer';outer.symlink_to('alias',target_is_directory=True)
        self.leaf.unlink();self.leaf.symlink_to('../real/payload')
        name=str(outer/'leaf');v=self.verifier(name,self.freeze(name))
        self.assertEqual(len(v.verify(name)['current_ancestor_observations']['links']),3)

    def test_absolute_leaf_target(self):
        self.leaf.unlink();self.leaf.symlink_to(self.file)
        self.assertEqual(self.verifier(row=self.freeze(self.name)).verify(self.name)['resolved_file'],self.files[str(self.file)])

    def test_directory_endpoint_is_metadata_only(self):
        link=self.root/'directory';link.symlink_to('real',target_is_directory=True)
        v=self.verifier(str(link),self.freeze(str(link)),read=lambda _:self.fail('directory is not a byte file'))
        self.assertIsNone(v.verify(str(link))['resolved_file'])

    def test_dot_directory_endpoint(self):
        self.leaf.unlink();self.leaf.symlink_to('.',target_is_directory=True)
        name=str(self.leaf);v=self.verifier(name,self.freeze(name),read=lambda _:self.fail('directory is not a file'))
        self.assertEqual(v.verify(name)['frozen_row']['resolved'],str(self.real))

    def test_rejects_undeclared_name(self):
        with self.assertRaisesRegex(RuntimeError,'undeclared'):
            self.verifier().verify(str(self.leaf))

    def test_rejects_noncanonical_declared_path(self):
        with self.assertRaisesRegex(RuntimeError,'canonical'):
            self.verifier(str(self.alias)+'/../alias/leaf')

    def test_rejects_bool_in_frozen_stamp(self):
        row=copy.deepcopy(self.row);row['stamp'][0]=True
        with self.assertRaisesRegex(RuntimeError,'typed'):
            self.verifier(row=row)

    def test_rejects_extra_frozen_row_field(self):
        row=dict(self.row,extra=True)
        with self.assertRaisesRegex(RuntimeError,'exact frozen'):
            self.verifier(row=row)

    def test_rejects_leaf_text_mismatch(self):
        row=dict(self.row,target='./payload')
        with self.assertRaisesRegex(RuntimeError,'leaf identity/text'):
            self.verifier(row=row).verify(self.name)

    def test_rejects_leaf_stamp_mismatch(self):
        row=copy.deepcopy(self.row);row['stamp'][1]+=1
        with self.assertRaisesRegex(RuntimeError,'leaf identity/text'):
            self.verifier(row=row).verify(self.name)

    def test_rejects_resolved_route_mismatch(self):
        row=dict(self.row,resolved=str(self.root/'different'))
        with self.assertRaisesRegex(RuntimeError,'resolved route'):
            self.verifier(row=row).verify(self.name)

    def test_rejects_leaf_replaced_with_regular_file(self):
        self.leaf.unlink();self.leaf.write_bytes(b'payload')
        with self.assertRaisesRegex(RuntimeError,'not a symlink'):
            self.verifier().verify(self.name)

    def test_rejects_dangling_target(self):
        self.file.unlink()
        with self.assertRaises(FileNotFoundError):
            self.verifier().verify(self.name)

    def test_rejects_cyclic_target(self):
        self.leaf.unlink();self.leaf.symlink_to('leaf')
        row=dict(stamp=[stamp(self.leaf.lstat())[k] for k in STAMP_FIELDS],target='leaf',resolved=str(self.file))
        with self.assertRaisesRegex(RuntimeError,'expansion count'):
            self.verifier(row=row).verify(self.name)

    def test_strict_file_reader_rejects_changed_payload(self):
        self.file.write_bytes(b'changed payload\n')
        with self.assertRaises(AssertionError):
            self.verifier().verify(self.name)

    def test_rejects_target_file_proof_identity_mismatch(self):
        def bad(name):
            row=self.read(name);row['identity']['ino']+=1;return row
        with self.assertRaisesRegex(RuntimeError,'file proof'):
            self.verifier(read=bad).verify(self.name)

    def test_parent_alias_replaced_during_file_callback_is_rejected(self):
        def mutate(name):
            result=self.read(name);self.alias.unlink();self.alias.symlink_to('./real',target_is_directory=True);return result
        with self.assertRaisesRegex(RuntimeError,'link changed during'):
            self.verifier(read=mutate).verify(self.name)

    def test_leaf_replaced_during_file_callback_is_rejected(self):
        def mutate(name):
            result=self.read(name);self.leaf.rename(self.real/'old-leaf');self.leaf.symlink_to('payload');return result
        with self.assertRaisesRegex(RuntimeError,'link changed during'):
            self.verifier(read=mutate).verify(self.name)

    def test_directory_route_replaced_during_callback_is_rejected(self):
        def mutate(name):
            result=self.read(name);self.real.rename(self.root/'moved');self.real.mkdir();return result
        with self.assertRaisesRegex(RuntimeError,'directory route changed'):
            self.verifier(read=mutate).verify(self.name)

    def test_first_alias_observation_cannot_be_replaced_on_later_call(self):
        v=self.verifier();first=v.verify(self.name)
        self.alias.unlink();self.alias.symlink_to('./real',target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError,'first audit observation'):
            v.verify(self.name)
        self.assertEqual(v.checked[self.name],first)

    def test_input_rows_and_returned_observations_are_independent_copies(self):
        rows={self.name:copy.deepcopy(self.row)};v=FrozenLinks(rows,read_file=self.read)
        rows[self.name]['target']='wrong';result=v.verify(self.name);result['frozen_row']['target']='wrong'
        self.assertEqual(v.recheck()[self.name]['frozen_row']['target'],'payload')


if __name__ == '__main__':
    unittest.main()
