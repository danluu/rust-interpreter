import unittest
from model import word_delta

class DeltaTests(unittest.TestCase):
    def test_equal_and_size(self):
        self.assertTrue(word_delta([1, 2], [1, 2])['equal_words'])
        self.assertFalse(word_delta([1], [1, 2])['same_word_count'])

    def test_sp_load_store_offsets(self):
        for op in [0xf9400000, 0xf9000000]:
            for offset in [0, 100, 4000]:
                a=op | offset<<10 | 31<<5 | 9
                row=word_delta([a], [a+(6<<10)])
                self.assertEqual(row['shifted_sp_accesses'], [0])
                self.assertEqual(row['other_changes'], [])

    def test_base_register_opcode_and_direction_differ(self):
        a=0xf9400000 | 100<<10 | 31<<5 | 9
        for b in [a-(6<<10), a+(5<<10), (a+(6<<10))^1, (a+(6<<10))^(1<<5), (a+(6<<10))^(1<<22)]:
            row=word_delta([a],[b]);self.assertEqual(row['shifted_sp_accesses'], [])
            self.assertEqual(len(row['other_changes']),1)

    def test_non_sp_and_other_instruction(self):
        for a in [0xf9400000 | 100<<10 | 1<<5 | 9, 0xd2800009]:
            row=word_delta([a],[a+(6<<10)])
            self.assertEqual(row['shifted_sp_accesses'], [])
            self.assertEqual(len(row['other_changes']),1)
