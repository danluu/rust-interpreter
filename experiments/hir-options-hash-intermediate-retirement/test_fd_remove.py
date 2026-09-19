"""Tiny owned filesystem fixtures; no N access or process invocation."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import fd_remove as f

def identity(path):return f.identity(path.lstat())
def snapshot(root):
    rows={'.':dict(kind='directory',identity=identity(root))}
    for path in root.rglob('*'):
        if path.is_dir():row=dict(kind='directory',identity=identity(path))
        else:row=dict(kind='file',identity=identity(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        rows[str(path.relative_to(root))]=row
    return rows

class RemovalControls(unittest.TestCase):
    def fixture(self,base):
        root=base/'tree';(root/'nested/deeper').mkdir(parents=True)
        (root/'nested/deeper/a.o').write_bytes(b'object-a')
        (root/'nested/deeper/b.rmeta').write_bytes(b'metadata-b')
        (root/'keep').write_bytes(b'protected')
        ledger=base/'ledger.jsonl';ledger.touch()
        return root,ledger
    def remove(self,root,ledger,rows,selected):
        return f.remove_files(root,rows,selected,identity(root.parent),ledger,lambda:None)
    def events(self,ledger):return [json.loads(line) for line in ledger.read_text().splitlines()] if ledger.exists() else []
    def test_nested_files_keep_directories_and_record_bookkeeping(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,ledger=self.fixture(Path(tmp));rows=snapshot(root)
            selected=['nested/deeper/a.o','nested/deeper/b.rmeta']
            remaining=self.remove(root,ledger,rows,selected)
            self.assertEqual(snapshot(root),remaining)
            self.assertEqual((root/'keep').read_bytes(),b'protected')
            self.assertTrue((root/'nested/deeper').is_dir())
            events=self.events(ledger)
            self.assertEqual([row['event'] for row in events],['intent','unlinked','validated']*2)
            self.assertEqual([row['relative'] for row in events if row['event']=='unlinked'],selected)
    def test_hardlink_is_rejected_before_intent_or_unlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,ledger=self.fixture(Path(tmp));os.link(root/'nested/deeper/a.o',Path(tmp)/'outside-alias')
            rows=snapshot(root)
            with self.assertRaisesRegex(RuntimeError,'alias'):self.remove(root,ledger,rows,['nested/deeper/a.o'])
            self.assertEqual(snapshot(root),rows);self.assertEqual(self.events(ledger),[])
            self.assertEqual((Path(tmp)/'outside-alias').read_bytes(),b'object-a')
    def test_changed_identity_is_rejected_without_unlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,ledger=self.fixture(Path(tmp));rows=snapshot(root)
            (root/'nested/deeper/a.o').write_bytes(b'changed')
            with self.assertRaisesRegex(RuntimeError,'entry|parent'):self.remove(root,ledger,rows,['nested/deeper/a.o'])
            self.assertTrue((root/'nested/deeper/a.o').exists());self.assertEqual(self.events(ledger),[])
    def test_changed_bytes_are_rejected_even_with_current_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,ledger=self.fixture(Path(tmp));rows=snapshot(root)
            (root/'nested/deeper/a.o').write_bytes(b'changed!')
            rows['nested/deeper/a.o']['identity']=identity(root/'nested/deeper/a.o')
            with self.assertRaisesRegex(RuntimeError,'bytes'):self.remove(root,ledger,rows,['nested/deeper/a.o'])
            self.assertTrue((root/'nested/deeper/a.o').exists());self.assertEqual(self.events(ledger),[])
    def test_post_unlink_failure_retains_durable_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,ledger=self.fixture(Path(tmp));rows=snapshot(root)
            with mock.patch.object(f,'post_unlink',side_effect=RuntimeError('injected postcondition')):
                with self.assertRaisesRegex(RuntimeError,'injected'):self.remove(root,ledger,rows,['nested/deeper/a.o'])
            self.assertFalse((root/'nested/deeper/a.o').exists())
            self.assertTrue((root/'nested/deeper/b.rmeta').exists())
            self.assertEqual([row['event'] for row in self.events(ledger)],['intent','unlinked'])
    def test_completion_publication_failure_preserves_intent_uncertainty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,ledger=self.fixture(Path(tmp));rows=snapshot(root);publish=f.event
            def failing(path,row):
                if row['event']=='unlinked':raise OSError('injected completion publication failure')
                publish(path,row)
            with mock.patch.object(f,'event',side_effect=failing):
                with self.assertRaisesRegex(OSError,'publication'):self.remove(root,ledger,rows,['nested/deeper/a.o'])
            self.assertFalse((root/'nested/deeper/a.o').exists())
            self.assertEqual([row['event'] for row in self.events(ledger)],['intent'])

if __name__=='__main__':unittest.main()
