import random
import unittest
from model import RET, ZERO_STATUS, category, costs, graph

MOV = 0xAA0003E1
FAIL = 0xD2800029


def branch(pc, target):
    return 0x14000000 | ((target - pc) & 0x3FFFFFF)


def cond(pc, target):
    return 0x54000000 | (((target - pc) & 0x7FFFF) << 5)


class ModelTests(unittest.TestCase):
    def test_failure_paths_are_excluded(self):
        words = [cond(0, 4), MOV, ZERO_STATUS, RET, FAIL, RET]
        self.assertEqual(costs(words)['bounds']['words'], dict(min=4, max=4))
        self.assertEqual(costs(words)['bounds']['replay_reachable_words'], dict(min=1, max=1))

    def test_alternative_success_paths_have_separate_bounds(self):
        words = [cond(0, 4), MOV, MOV, branch(3, 5), MOV, ZERO_STATUS, RET]
        self.assertEqual(costs(words)['bounds']['words'], dict(min=4, max=6))

    def test_invariant_errors_are_not_success(self):
        words = [cond(0, 3), ZERO_STATUS, RET, 0xD2800049, RET]
        self.assertEqual(costs(words)['bounds']['words'], dict(min=3, max=3))
        self.assertEqual(costs(words)['bounds']['replay_reachable_words'], dict(min=0, max=0))

    def test_reject_cycles_and_external_edges(self):
        for words in [[branch(0, 0)], [branch(0, 8)], [MOV], [branch(0, -1)]]:
            with self.subTest(words=words), self.assertRaises(ValueError):
                costs(words)

    def test_reject_unmodeled_control_flow(self):
        for word in [0xD63F0200, 0xD61F0200, 0x94000000, 0xB4000000, 0x36000000, 0xD4000001, 0x5400000E]:
            with self.subTest(word=hex(word)), self.assertRaises(ValueError):
                costs([word, ZERO_STATUS, RET])

    def test_reject_unproven_return_status(self):
        for words in [[RET], [MOV, RET], [0xD2800069, RET], [cond(0, 2), ZERO_STATUS, RET]]:
            with self.subTest(words=words), self.assertRaises(ValueError):
                costs(words)

    def test_integer_memory_categories(self):
        for load, store in [(0x39400000, 0x39000000), (0x79400000, 0x79000000), (0xB9400000, 0xB9000000), (0xF9400000, 0xF9000000)]:
            for base, prefix in [(31, 'sp_relative'), (11, 'other_base')]:
                self.assertEqual(category(load | (base << 5) | 9), prefix + '_load')
                self.assertEqual(category(store | (base << 5) | 9), prefix + '_store')

    def test_path_enumeration_oracle(self):
        rng = random.Random(23017)
        # Compare DP bounds with enumeration of every path in 512 distinct DAGs.
        # The oracle enumerates actual word indices; it does not use DP state.
        for _ in range(512):
            n = rng.randrange(3, 12)
            words = [rng.choice([MOV, 0xF94003E9, 0xF90003E9]) for _ in range(n)]
            for pc in range(n - 1):
                if rng.randrange(2):
                    words[pc] = cond(pc, rng.randrange(pc + 1, n + 1))
            words += [ZERO_STATUS, RET]
            edges, _, _ = graph(words)
            paths = []
            def walk(pc, path):
                path = [*path, pc]
                if words[pc] == RET:
                    paths.append(path)
                for to in edges[pc]:
                    walk(to, path)
            walk(0, [])
            observed = costs(words)['bounds']
            for key in ['words', 'control', 'sp_relative_load', 'sp_relative_store', 'other']:
                values = [sum(key == 'words' or category(words[pc]) == key for pc in path) for path in paths]
                self.assertEqual(observed.get(key, dict(min=0, max=0)), dict(min=min(values), max=max(values)))


if __name__ == '__main__':
    unittest.main()
