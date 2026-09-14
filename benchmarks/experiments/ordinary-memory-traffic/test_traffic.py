import os
from pathlib import Path
import sys
import unittest
from traffic import analyze, memory
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'benchmarks/experiments/ordinary-register-census'))
from test_memory import text_words

WORDS = [0xf9400009, 0xf900041f, 0xf97ffc1c, 0xd2900010, 0x8b100010,
         0xf9400209, 0xd2800110, 0xf2a00030, 0x8b100010, 0xf900021f,
         0xb9400009, 0x3dc00009, 0xf9400609, 0xf8408009]


class Traffic(unittest.TestCase):
    def test_independent_assembler(self):
        self.assertEqual(text_words(Path(os.environ['ORDINARY_TRAFFIC_OBJECT'])), WORDS)

    def test_real_recipes_and_half_direction(self):
        accesses, addresses = analyze(WORDS)
        self.assertEqual(set(accesses), {0, 1, 2, 5, 9})
        self.assertEqual(addresses, {3: 5, 4: 5, 6: 9, 7: 9, 8: 9})
        self.assertEqual([(a['slot'], a['half'], a['direction'], a['zero_store'])
                          for a in accesses.values()],
                         [(0, 'low', 'load', False), (0, 'high', 'store', True),
                          (2047, 'high', 'load', False), (2048, 'low', 'load', False),
                          (4096, 'high', 'store', True)])

    def test_other_bases_and_all_payloads(self):
        for base in range(32):
            for payload in range(32):
                word = 0xf9400000 | base << 5 | payload
                self.assertEqual(memory(word)['base'], base)
                self.assertEqual(memory(word)['payload'], payload)
                self.assertEqual(bool(analyze([word])[0]), base == 0)

    def test_middle_entries_and_region_boundaries_decline(self):
        recipe = WORDS[6:10]
        for entry in [1, 2, 3]:
            self.assertEqual(analyze(recipe, [entry]), ({}, {}))
        self.assertEqual(len(analyze(recipe, [0])[0]), 1)
        for start in [1, 2, 3]:
            self.assertEqual(analyze(recipe[start:]), ({}, {}))

    def test_malformed_materialization_declines(self):
        suffix = [0x8b100010, 0xf9400209]
        for prefix in [[], [0xd2800010], [0xd2900030], # zero / unaligned
                       [0xd2900011], [0xd2900010, 0xf2a00010], # wrong rd / zero MOVK
                       [0xd2900010, 0xf2800030], # zero shift MOVK
                       [0xd2900010, 0xf2a00030, 0xf2a00050], # repeated shift
                       [0xd2900010, 0xf2c00030, 0xf2a00030], # reversed shifts
                       [0xd2900010, 0xf2e00030], # out of Reg range
                       [0xd2900010, 0xd503201f]]: # intervening word
            self.assertEqual(analyze(prefix + suffix), ({}, {}), prefix)

    def test_out_of_subset_memory_declines(self):
        for word in [0xb9400009, 0x39400009, 0x79400009, 0x3dc00009,
                     0xf8408009, 0xa9402809, 0xf9800009, 0xb9800009, 0xffffffff]:
            self.assertIsNone(memory(word), hex(word))


if __name__ == '__main__':
    unittest.main()
