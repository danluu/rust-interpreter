import hashlib
import struct
import unittest
from native_identity import compare_native


def fixture(base):
    # Independently encoded three-word address then BLR, and two leaf bodies.
    target = base + 20
    words = [0xd503201f, 0xd2800010 | ((target & 0xffff) << 5),
             0xf2a00010 | (((target >> 16) & 0xffff) << 5),
             0xf2c00010 | (((target >> 32) & 0xffff) << 5), 0xd63f0200,
             0xd65f03c0, 0xd65f03c0]
    code = struct.pack('<7I', *words)
    mapping = dict(pid=1, arena_base=base, code_bytes=len(code),
        code_sha256=hashlib.sha256(code).hexdigest(), functions=[
            dict(function=0, offset=0, end=20, spans=[dict(kind='transition', pc=0, offset=0, end=20)]),
            dict(function=1, offset=20, end=24, spans=[dict(kind='scalar_leaf')]),
            dict(function=2, offset=24, end=28, spans=[dict(kind='scalar_leaf')])])
    profile = dict(functions=[dict(name='caller',operations=['Call']),
                              dict(name='leaf',operations=['Return']),
                              dict(name='other',operations=['Return'])])
    return [mapping, code, profile]


def word_change(args, index, value):
    code = bytearray(args[1]);struct.pack_into('<I',code,index*4,value)
    args[1] = bytes(code);args[0]['code_sha256'] = hashlib.sha256(code).hexdigest()


class NativeIdentity(unittest.TestCase):
    def test_different_arenas_preserve_target_identity_and_every_other_bit(self):
        a,b = fixture(0x123456780000),fixture(0x234567890000)
        result = compare_native(*a,*b)
        self.assertEqual(result['scalar_target_sites'],1)
        self.assertEqual(result['native_bytes'],28)
        self.assertEqual(compare_native(*a,*a)['normalized_sha256'],result['normalized_sha256'])

    def test_actual_operand_rendering_still_requires_checked_relocation(self):
        a,b=fixture(0x123456780000),fixture(0x234567890000)
        for item in [a,b]:item[2]['functions'][0]['operations']=['Call { function: 1, args: [2], destination: 3 }']
        self.assertEqual(compare_native(*a,*b)['scalar_target_sites'],1)
        word_change(a,1,0xd2800010 | (24<<5))
        with self.assertRaises(AssertionError):compare_native(*a,*b)

    def test_unknown_or_different_body_targets_and_noncanonical_sequences_fail(self):
        for index, word in [(1,0xd2800010 | (21<<5)), (1,0xd2800010 | (24<<5)),
                            (2,0xf2c00010 | (0x5678<<5)), (2,0xf2a00010),
                            (1,0xd2800011 | (20<<5)), (4,0xd63f0220)]:
            a,b = fixture(0x123456780000),fixture(0x123456780000)
            word_change(a,index,word)
            with self.assertRaises(AssertionError):compare_native(*a,*b)

    def test_non_address_bytes_layout_roles_and_execution_drift_fail(self):
        def change_instruction(a):word_change(a,0,0xd503203f)
        for mutation in [change_instruction,
                         lambda a:a[0]['functions'][0].update(end=16),
                         lambda a:a[0]['functions'][0]['spans'][0].update(offset=8),
                         lambda a:a[2]['functions'][0].update(operations=['Return']),
                         lambda a:a[2]['functions'][0].update(interpreted=[1])]:
            a,b = fixture(0x123456780000),fixture(0x234567890000)
            mutation(a)
            with self.assertRaises(AssertionError):compare_native(*a,*b)


if __name__ == '__main__':unittest.main()
