import unittest
from attribute_census import identity


class Parts(unittest.TestCase):
    def rows(self):
        return [dict(offset=0, end=8, function=1, pc=2, part='load_data', access='none'),
                dict(offset=8, end=12, function=1, pc=2, part='store_data', access='none'),
                dict(offset=16, end=20, function=1, pc=3, part='load_data', access='none')]

    def test_multiple_parts_remain_ambiguous(self):
        self.assertEqual(identity(self.rows(), [0, 4]), ('load_data', 'none'))
        self.assertEqual(identity(self.rows(), [4, 8]), ('ambiguous', 'ambiguous'))

    def test_foreign_operations_gaps_and_unaligned_pcs_rejected(self):
        for offsets in [[4, 16], [12], [1], [20], [-4]]:
            with self.assertRaises(AssertionError):
                identity(self.rows(), offsets)


if __name__ == '__main__':
    unittest.main()
