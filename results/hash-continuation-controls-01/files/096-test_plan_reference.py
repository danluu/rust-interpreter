"""Adversarial pure controls for lossless external JSON members."""
import copy
import hashlib
import unittest

import plan_reference as reference


class PlanReferenceTests(unittest.TestCase):
    def setUp(self):
        self.raw = b'{"options":[true,1,1.0,null],"nested":{"key":"value"}}\n'
        self.ref = dict(path='/owned/already-frozen.json', sha256=hashlib.sha256(self.raw).hexdigest())
        self.full = dict(metadata=reference.parsed(self.raw), flags=[False, 2], extra={'keep': 9})
        self.wire = reference.split(self.full, member='metadata', reference=self.ref, read_bytes=self.read)

    def read(self, name):
        self.assertEqual(name, self.ref['path'])
        return self.raw

    def expand(self, wire=None, **kwargs):
        return reference.expand(self.wire if wire is None else wire,
                                expected_reference=kwargs.pop('expected_reference', self.ref),
                                read_bytes=kwargs.pop('read_bytes', self.read), **kwargs)

    def test_full_typed_roundtrip_and_no_aliasing(self):
        original = copy.deepcopy(self.full)
        output = self.expand()
        self.assertEqual(reference.encoded(output), reference.encoded(original))
        output['metadata']['nested']['key'] = 'changed'
        output['extra']['keep'] = 10
        self.assertEqual(self.full, original)
        self.assertEqual(self.wire['remainder']['extra']['keep'], 9)

    def test_changed_referenced_bytes_rejected_before_parse(self):
        with self.assertRaises(ValueError):
            self.expand(read_bytes=lambda _: self.raw.replace(b'1.0', b'2.0'))

    def test_different_reviewed_reference_rejected(self):
        other = dict(self.ref, path='/owned/other.json')
        with self.assertRaises(ValueError):
            self.expand(expected_reference=other)

    def test_member_overlap_cannot_replace_remainder(self):
        wire = copy.deepcopy(self.wire)
        wire['remainder']['metadata'] = self.full['metadata']
        with self.assertRaises(ValueError):
            self.expand(wire)

    def test_changed_remainder_rejected(self):
        wire = copy.deepcopy(self.wire)
        wire['remainder']['extra']['keep'] = 10
        with self.assertRaises(ValueError):
            self.expand(wire)

    def test_typed_mismatch_not_python_equality(self):
        document = copy.deepcopy(self.full)
        document['metadata']['options'][0] = 1
        with self.assertRaises(ValueError):
            reference.split(document, member='metadata', reference=self.ref, read_bytes=self.read)

    def test_false_integer_integrity_rejected(self):
        for value in [True, 1.0, -1, 0, reference.MAX_BYTES + 1]:
            with self.subTest(value=value):
                wire = copy.deepcopy(self.wire)
                wire['integrity']['bytes'] = value
                with self.assertRaises(ValueError):
                    self.expand(wire)

    def test_unknown_envelope_and_integrity_fields_rejected(self):
        for target in ['envelope', 'integrity', 'reference']:
            with self.subTest(target=target):
                wire = copy.deepcopy(self.wire)
                (wire if target == 'envelope' else wire[target])['unknown'] = 0
                with self.assertRaises(ValueError):
                    self.expand(wire)

    def test_duplicate_and_nonfinite_reference_json_rejected(self):
        for raw in [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}']:
            with self.subTest(raw=raw):
                ref = dict(self.ref, sha256=hashlib.sha256(raw).hexdigest())
                with self.assertRaises(ValueError):
                    reference.split(self.full, member='metadata', reference=ref, read_bytes=lambda _: raw)

    def test_noncanonical_reference_paths_rejected(self):
        for name in ['relative.json', '/owned/../other.json', '/owned//a.json', '//owned/a.json', '/', '/owned/a\n.json']:
            with self.subTest(name=name):
                ref = dict(self.ref, path=name)
                with self.assertRaises(ValueError):
                    reference.split(self.full, member='metadata', reference=ref, read_bytes=lambda _: self.raw)

    def test_non_json_and_depth_rejected(self):
        for value in [{1: 'wrong'}, {'x': object()}, {'x': float('inf')}]:
            with self.assertRaises(ValueError):
                reference.encoded(value)
        value = 0
        for _ in range(reference.MAX_DEPTH + 1):
            value = [value]
        with self.assertRaises(ValueError):
            reference.encoded(value)

    def test_missing_member_and_wrong_reference_shape_rejected(self):
        with self.assertRaises(ValueError):
            reference.split(self.full, member='absent', reference=self.ref, read_bytes=self.read)
        with self.assertRaises(ValueError):
            reference.split(self.full, member='metadata', reference={'path': self.ref['path']}, read_bytes=self.read)


if __name__ == '__main__':
    unittest.main()
