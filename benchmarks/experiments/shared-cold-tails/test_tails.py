import unittest
from tails import EPILOGUE, branch_word, census, eligible


class Tails(unittest.TestCase):
    def test_exact_shape_rejects_control_flow_and_changed_state(self):
        tail = (0xd2800020,) + EPILOGUE
        self.assertTrue(eligible(tail))
        self.assertFalse(eligible((0x14000000,) + EPILOGUE))
        self.assertFalse(eligible((0xd2800021,) + EPILOGUE))
        for i in range(len(EPILOGUE)):
            changed = list(tail)
            changed[1+i] ^= 1
            self.assertFalse(eligible(changed))
        self.assertFalse(eligible(EPILOGUE))
        self.assertFalse(eligible(tail + (0xd65f03c0,)))

    def test_status_parts_require_original_order_and_keep_every_bit(self):
        tail = (0xd29fffe0, 0xf2bfffe0, 0xf2dfffe0, 0xf2ffffe0) + EPILOGUE
        self.assertTrue(eligible(tail))
        self.assertFalse(eligible((tail[0],tail[2],tail[1]) + EPILOGUE))
        self.assertFalse(eligible((tail[0],0xf2800020) + EPILOGUE))
        other = (0xd29fffc0,) + tail[1:]
        result = census([(0,tail),(64,other),(128,tail)])
        self.assertEqual([r['offset'] for r in result['replacements']], [128])
        self.assertEqual(result['saved_bytes'], 48)

    def test_signed_branch_boundaries_are_exact(self):
        base = 1 << 28
        for delta in [-(1<<25), -1, 0, 1, (1<<25)-1]:
            word = branch_word(base, base+delta*4)
            value = word & 0x3ffffff
            if value & (1<<25): value -= 1<<26
            self.assertEqual(base+value*4, base+delta*4)
        self.assertIsNone(branch_word(base,base-(1<<25)*4-4))
        self.assertIsNone(branch_word(base,base+(1<<25)*4))
        with self.assertRaises(AssertionError): branch_word(1,0)

    def test_only_earlier_retained_tail_is_a_target(self):
        tail = (0xd2800020,) + EPILOGUE
        result = census([(0,tail),(40,tail),(80,tail)])
        self.assertEqual([r['target'] for r in result['replacements']], [0,0])
        self.assertEqual(result['saved_bytes'], 72)
        self.assertEqual(census([(0,tail)])['saved_bytes'],0)
        self.assertEqual(census([(0,tail),(40,tail)],0)['saved_bytes'],0)

    def test_resource_and_distance_declines_do_not_share(self):
        a,b = (0xd2800020,)+EPILOGUE,(0xd2800040,)+EPILOGUE
        result=census([(0,a),(40,b),(80,b),(120,a)],1)
        self.assertEqual([r['offset'] for r in result['replacements']],[120])
        self.assertEqual(result['declined'],2)
        self.assertEqual(census([(0,a),(1<<28,a)],1)['saved_bytes'],0)
        with self.assertRaises(AssertionError): census([(0,a),(4,a)])

    def test_replacement_executes_identical_terminal_word_trace(self):
        # Independent path walk: each replacement takes exactly one branch to
        # an original retained tail; compare the complete state-changing trace.
        bodies=[(0xd2800020,)+EPILOGUE,(0xd2800040,)+EPILOGUE]
        rows=[(i*64,bodies[(i*7)%2]) for i in range(64)]
        result=census(rows)
        originals=dict(rows)
        replacements={r['offset']:r for r in result['replacements']}
        for offset,expected in rows:
            if offset in replacements:
                instruction=replacements[offset]['branch_word']
                signed=instruction & 0x3ffffff
                if signed & 0x2000000: signed-=0x4000000
                target=offset+signed*4
                self.assertNotIn(target,replacements)
                self.assertEqual(originals[target],expected)


if __name__ == '__main__': unittest.main()
