import unittest
from words import analyze, decode, reg, FLAGS

ZERO10 = 0xaa1f03ea
OK = 0xaa1f03e0
FAIL = 0xd2800020
RET = 0xd65f03c0


class WordsTest(unittest.TestCase):
    def test_dead_high_chain_preserves_live_low_value_and_memory(self):
        # Dead x10 select exposes both high getters; low store must survive.
        words = [0xaa1f03eb, 0xaa1f03ec, 0x9a8c116a,
                 0xf9000049, OK, RET]
        result = analyze(words)
        self.assertEqual(result['dead_word_offsets'], [0, 1, 2])
        self.assertEqual(result['successful_path_bounds'], (3, 3))

    def test_movk_reads_prior_low_bits(self):
        result = analyze([0xd2800029, 0xf2a00049, 0xf9000049, ZERO10, OK, RET])
        self.assertEqual(result['dead_word_offsets'], [3])

    def test_flags_used_across_conditional_paths(self):
        # CMP x9,x10; B.EQ success; one extra dead high write on fallthrough.
        result = analyze([0xeb0a013f, 0x54000040, ZERO10, OK, RET])
        self.assertEqual(result['dead_word_offsets'], [2])
        self.assertEqual(result['successful_path_bounds'], (0, 1))
        self.assertEqual(decode(0xeb0a013f, 0, 2).writes, 1 << FLAGS)

    def test_failure_paths_are_not_successful_commits(self):
        result = analyze([0x54000080, ZERO10, OK, RET, FAIL, RET])
        self.assertEqual(result['successful_path_bounds'], (1, 1))
        self.assertEqual(result['successful_returns'], 1)

    def test_memory_accesses_and_sp_adjustments_are_preserved(self):
        result = analyze([0xd10043ff, 0xf94003ea, 0xf90007ea, 0x910043ff, OK, RET])
        self.assertEqual(result['dead_words'], 0)
        self.assertEqual(decode(0x910043ff, 0, 2).reads, reg(31, True))
        self.assertEqual(decode(ZERO10, 0, 2).reads, 0)

    def test_vector_chain_preserves_integer_result(self):
        words = [0x9e670120, 0x0e205800, 0x0e31b800, 0x0e013c09]
        self.assertEqual(analyze(words + [0xf9000049, OK, RET])['dead_words'], 0)
        self.assertEqual(analyze(words + [OK, RET])['dead_word_offsets'], list(range(4)))

    def test_diamond_merge_keeps_both_definitions(self):
        # A late use keeps x10 defined on either predecessor.
        result = analyze([0x54000060, ZERO10, 0x14000002, 0xd280002a,
                          0xf900044a, OK, RET])
        self.assertEqual(result['dead_words'], 0)

    def test_unknown_external_loop_and_return_status_fail_closed(self):
        for words in ([0, OK, RET], [0x14000006, OK, RET],
                      [0x14000000, OK, RET], [ZERO10, RET]):
            with self.subTest(words=words), self.assertRaises(AssertionError): analyze(words)


if __name__ == '__main__': unittest.main()
