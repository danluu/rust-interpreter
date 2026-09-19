"""Focused actual integration functions with owned temporary files only.

These fixtures do not qualify a runtime, substitute saved receipts, or change
the original53 controls. No provider, compiler, or subprocess is invoked.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import audit

_spec = importlib.util.spec_from_file_location('tail_test_qualified_access',
    audit.QUALIFIED_AUDIT/'audit_io.py')
access = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(access)


class TailTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='saved-audit-tail-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.outer = self.root/'supervisor'; self.outer.mkdir()
        self.preparation = self.root/'preparation'; self.preparation.mkdir()
        self.source = self.root/'supervise.py'; self.source.write_bytes(b'owned writer fixture\n')
        self.command = ['owned-python','-B','owned-controller.py']
        self.launch = dict(command=['owned-python','-B',str(self.source),'--run-id',self.outer.name,'--',*self.command])
        self.plan = dict(owner=str(self.root), command=self.command,
            supervisor_sha256=self.sha(self.source))
        (self.outer/'plan.json').write_bytes(audit.encoded(self.plan))
        (self.outer/'command.log').write_bytes(b'owned child output\n')
        # Nonempty supervisor bytes must be retained, not silently dropped.
        (self.outer/'supervisor.log').write_bytes(b'owned supervisor output\n')
        self.supervisor = dict(cwd=str(self.root),command=self.command,
            plan_sha256=self.sha(self.outer/'plan.json'),
            log_sha256=self.sha(self.outer/'command.log'))
        (self.outer/'status.json').write_bytes(audit.encoded(self.supervisor))

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def row(self, path):
        return dict(size=path.stat().st_size,sha256=self.sha(path),identity=access.stamp(path.stat()))

    def supervisor_proof(self):
        io = access.Access({str(self.source):self.row(self.source)},output_roots=[self.outer])
        return audit.supervisor_output_readback(io,self.outer,self.launch,self.supervisor,source=self.source)

    def test_supervisor_four_outputs_and_both_distinct_raw_streams(self):
        proof = self.supervisor_proof()
        self.assertEqual(proof['membership']['files'],4)
        self.assertEqual(proof['supervisor_stream']['sha256'],self.sha(self.outer/'supervisor.log'))
        self.assertEqual(proof['supervisor_stream']['identity'],access.stamp((self.outer/'supervisor.log').stat()))
        self.assertEqual(proof['command_stream']['sha256'],self.supervisor['log_sha256'])
        self.assertNotEqual(proof['command_stream']['sha256'],proof['supervisor_stream']['sha256'])

    def test_missing_supervisor_stream_rejected(self):
        (self.outer/'supervisor.log').unlink()
        with self.assertRaisesRegex(RuntimeError,'closed output membership'):
            self.supervisor_proof()

    def test_unexpected_supervisor_output_rejected(self):
        (self.outer/'unexpected').write_bytes(b'')
        with self.assertRaisesRegex(RuntimeError,'closed output membership'):
            self.supervisor_proof()

    def test_supervisor_writer_rebinding_rejected(self):
        self.plan['supervisor_sha256']='0'*64
        (self.outer/'plan.json').write_bytes(audit.encoded(self.plan))
        self.supervisor['plan_sha256']=self.sha(self.outer/'plan.json')
        with self.assertRaisesRegex(RuntimeError,'writer/owner/command'):
            self.supervisor_proof()

    def test_complete_preparation_source_union(self):
        path=self.root/'extra.py';path.write_bytes(b'extra source\n');rows={str(path):self.row(path)}
        proof=audit.preparation_source_equality(rows,copy.deepcopy(rows))
        self.assertEqual(proof['files'],1)
        self.assertEqual(proof['table_sha256'],hashlib.sha256(audit.encoded(rows)).hexdigest())

    def test_missing_preparation_source_rejected(self):
        rows={str(self.source):self.row(self.source)}
        with self.assertRaisesRegex(RuntimeError,'omitted or relabeled'):
            audit.preparation_source_equality(rows,{})

    def test_preparation_typed_row_change_rejected(self):
        rows={str(self.source):self.row(self.source)};changed=copy.deepcopy(rows)
        changed[str(self.source)]['identity']['nlink']=True
        self.assertEqual(rows[str(self.source)]['identity']['nlink'],1)
        with self.assertRaisesRegex(RuntimeError,'omitted or relabeled'):
            audit.preparation_source_equality(rows,changed)

    def invocation(self, original, retained, *, bad_hash=False):
        source=self.root/'original.json';source.write_bytes(original)
        (self.preparation/'invocation.json').write_bytes(retained)
        reference=dict(path=str(source),sha256='0'*64 if bad_hash else self.sha(source))
        io=access.Access({str(source):self.row(source)},output_roots=[self.preparation])
        return audit.preparation_invocation_readback(io,self.preparation,reference)

    def test_reserialized_invocation_preserves_both_raw_hashes(self):
        original=b'{\n  "phase": "preflight", "count": 1\n}\n'
        retained=b'{"count":1,"phase":"preflight"}\n'
        proof=self.invocation(original,retained)
        self.assertTrue(proof['complete_typed_equality'])
        self.assertFalse(proof['same_raw_bytes'])
        self.assertEqual(proof['original']['sha256'],hashlib.sha256(original).hexdigest())
        self.assertEqual(proof['retained']['sha256'],hashlib.sha256(retained).hexdigest())

    def test_changed_retained_invocation_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'changed typed JSON'):
            self.invocation(b'{"phase":"preflight"}',b'{"phase":"installation"}')

    def test_boolean_cannot_replace_integer_in_retained_invocation(self):
        with self.assertRaisesRegex(RuntimeError,'changed typed JSON'):
            self.invocation(b'{"count":1}',b'{"count":true}')

    def test_original_invocation_hash_must_match_external_reference(self):
        with self.assertRaisesRegex(RuntimeError,'original preparation invocation'):
            self.invocation(b'{}',b'{}',bad_hash=True)


if __name__ == '__main__':
    unittest.main()
