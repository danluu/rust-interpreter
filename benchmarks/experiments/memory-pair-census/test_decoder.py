import unittest
from decoder import pair


def single(load, target, base, scaled_offset):
    return (0xf9400000 if load else 0xf9000000) | scaled_offset << 10 | base << 5 | target


class Eligibility(unittest.TestCase):
    def test_offset_boundaries_and_same_base(self):
        for load in [False, True]:
            for offset in [0, 1, 62, 63, 64, 4094]:
                result = pair(single(load, 9, 11, offset), single(load, 10, 11, offset + 1))
                self.assertEqual(result is not None, offset <= 63)
                if result: self.assertEqual(result['offset'], offset * 8)
            self.assertIsNone(pair(single(load, 9, 11, 0), single(load, 10, 12, 1)))
            self.assertIsNone(pair(single(load, 9, 11, 0), single(load, 10, 11, 2)))

    def test_load_overlap_and_store_aliases(self):
        for left, right in [(11, 10), (9, 11), (9, 9), (31, 31)]:
            self.assertIsNone(pair(single(True, left, 11, 0), single(True, right, 11, 1)))
            self.assertIsNotNone(pair(single(False, left, 11, 0), single(False, right, 11, 1)))
        self.assertIsNone(pair(single(False, 9, 31, 0), single(False, 10, 31, 1)))

    def test_different_width_direction_addressing_and_invalid_words(self):
        first, second = single(True, 9, 11, 0), single(True, 10, 11, 1)
        for a, b in [(first, single(False, 10, 11, 1)), (first & ~0x40000000, second & ~0x40000000),
                     (0x3dc00169, 0x3dc0056a), (0xf8408569, second), (-1, second), (first, 1 << 32)]:
            self.assertIsNone(pair(a, b))


if __name__ == '__main__': unittest.main()
