import random
import unittest
from model import analyze_span, dead_definitions, direct_target, words

MOV10 = 0xaa1f03ea
MOV9 = 0xaa1f03e9


class OrdinaryBoundaries(unittest.TestCase):
    def test_overwrite_requires_no_observation_and_preserves_live_out(self):
        self.assertEqual(analyze_span([MOV10, MOV10], 0, 2, set())['dead'], [0])
        self.assertEqual(analyze_span([MOV10, MOV9], 0, 2, set())['dead'], [])
        self.assertEqual(analyze_span([MOV10, 0xaa0a03e9, MOV10], 0, 3, set())['dead'], [])

    def test_targets_and_span_boundaries_preserve_bypassed_definitions(self):
        # An external jump to the second definition prevents analyzing across it.
        self.assertEqual(analyze_span([MOV10, MOV10], 0, 2, {1})['dead'], [])
        self.assertEqual(analyze_span([MOV10, MOV10], 0, 1, set())['dead'], [])
        self.assertEqual(analyze_span([MOV10, MOV10], 1, 2, set())['dead'], [])

    def test_branch_encodings_positive_negative_and_widths(self):
        for opcode, bits, shift in [(0x14000000,26,0),(0x94000000,26,0),
                (0x54000001,19,5),(0x34000009,19,5),(0xb5000009,19,5),
                (0x36000009,14,5),(0xb7000009,14,5)]:
            for delta in [-(1 << (bits-1)), -1, 0, 1, (1 << (bits-1))-1]:
                word = opcode | ((delta & ((1 << bits)-1)) << shift)
                self.assertEqual(direct_target(word, 100), 100+delta)
        self.assertIsNone(direct_target(MOV10, 1))

    def test_unknown_calls_branches_and_memory_effects_are_barriers(self):
        for barrier in [0, 0xffffffff, 0xd63f0200, 0xd61f0200, 0x14000001,
                        0x54000020, 0x34000029, 0x36000029, 0xd65f03c0]:
            self.assertEqual(analyze_span([MOV10, barrier, MOV10], 0, 3, set())['dead'], [])
        # Loads can overwrite a temporary but are never removed themselves.
        self.assertEqual(analyze_span([MOV10, 0xf940000a, MOV10], 0, 3, set())['dead'], [0])
        self.assertEqual(analyze_span([MOV10, 0xf900000a, MOV10], 0, 3, set())['dead'], [])
        self.assertEqual(analyze_span([0xd10043ff, 0x910043ff], 0, 2, set())['dead'], [])

    def test_movk_flags_and_vector_dependencies_remain_live(self):
        self.assertEqual(analyze_span([0xd2800029,0xf2a00049], 0, 2, set())['dead'], [])
        seq=[0xeb0a013f,0x9a8c116a,0xeb0a013f]
        self.assertEqual(analyze_span(seq,0,len(seq),set())['dead'], [])
        seq=[0x9e670120,0x0e205800,0x0e31b800,0x0e013c09]
        self.assertEqual(analyze_span(seq,0,len(seq),set())['dead'], [])

    def test_bounded_spans_decline_without_opportunities(self):
        result=analyze_span([MOV10]*(words.MAX_WORDS+1),0,words.MAX_WORDS+1,set())
        self.assertTrue(result['declined']);self.assertEqual(result['dead'],[])

    def test_independent_dependency_graph_oracle(self):
        rng=random.Random(0x20260919)
        for _ in range(1000):
            ops=[]
            for pc in range(rng.randrange(1,65)):
                reads=rng.getrandbits(8);writes=1 << rng.randrange(8)
                ops.append(words.Word(reads,writes,rng.randrange(4)!=0,(pc+1,),'abstract'))
            # Build the forward definition graph, then retain roots observed
            # by side effects or final register state. Independent of liveness.
            latest=[None]*34;deps=[];roots=set()
            for pc,op in enumerate(ops):
                deps.append({latest[r] for r in range(34) if op.reads & (1<<r) and latest[r] is not None})
                if not op.pure:roots.add(pc)
                for r in range(34):
                    if op.writes & (1<<r):latest[r]=pc
            roots.update(p for p in latest if p is not None)
            needed=set();pending=list(roots)
            while pending:
                pc=pending.pop()
                if pc not in needed:needed.add(pc);pending.extend(deps[pc])
            self.assertEqual(dead_definitions(ops),{pc for pc,op in enumerate(ops) if op.pure and pc not in needed})


if __name__ == '__main__':
    unittest.main()
