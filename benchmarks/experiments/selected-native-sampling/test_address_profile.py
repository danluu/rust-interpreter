import unittest
from address_profile import decode


class AddressSequenceTests(unittest.TestCase):
    # Exact observed instructions, rebased from code word50 to word0. Each
    # conditional branch targets the original tail at relative word90.
    READ = [0xd280000e, 0xf2e8000e, 0xeb0e017f, 0xcb0e016d,
            0x9a8d316b, 0x9a873051, 0x9a88306f, 0x9a9f308e,
            0xeb1f017f, 0x54000a20, 0xeb0f017f, 0x540009e8,
            0xcb0b01ef, 0xd280020d, 0xeb0d01ff, 0x54000963,
            0x8b0b022b]

    def test_exact_capture_and_truncation(self):
        words = self.READ + [0] * 74
        self.assertEqual(decode(words, 0), dict(start=0, end=17,
            translation_end=8, address=11, size=16, write=False, fault=90))
        for length in range(17):
            self.assertIsNone(decode(words[:length], 0))
        self.assertIsNone(decode(self.READ, 0))  # Fault target must exist.

    def test_guard_changes_are_rejected(self):
        for index in [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 16]:
            words = self.READ + [0] * 74
            words[index] ^= 1
            self.assertIsNone(decode(words, 0), index)
        for index in [9, 11, 15]:
            for change in [1, 32]:  # Wrong condition or a different fault tail.
                words = self.READ + [0] * 74
                words[index] ^= change
                self.assertIsNone(decode(words, 0), (index, change))

    def test_write_and_large_size(self):
        words = self.READ[:16] + [0xeb0e017f, 0x54000923, self.READ[-1]] + [0] * 72
        self.assertTrue(decode(words, 0)['write'])
        words = self.READ[:14] + [0xf2a0002d] + self.READ[14:] + [0] * 74
        words[16] -= 32  # Same target after inserting MOVK before the last guard.
        self.assertEqual(decode(words, 0)['size'], 65552)
        words[14] = 0xf280002d  # MOVK may not repeat the initial 16-bit half.
        self.assertIsNone(decode(words, 0))


if __name__ == '__main__':
    unittest.main()
