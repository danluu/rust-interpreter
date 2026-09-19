import itertools
import random
import unittest
from model import Region, plan, oracle, simulate
from scope import budget_words


class Tests(unittest.TestCase):
    def test_exact_native_budget_decoder(self):
        for cost in [1, 2, 32, 1024]:
            words = [0xd280000a | (cost<<5), 0xeb0a02df, 0x54000103, 0xcb0a02d6]
            self.assertTrue(budget_words(words, cost))
            for index in range(4):
                damaged = words.copy(); damaged[index] ^= 1
                self.assertFalse(budget_words(damaged, cost))
            self.assertFalse(budget_words(words, cost+1))
        self.assertFalse(budget_words([], 0))

    def compare(self, nodes, path, budgets, faults=(None,), external=()):
        for budget in budgets:
            for fault in faults:
                self.assertEqual(simulate(nodes, path, budget, fault, external)[0], oracle(nodes, path, budget, fault))

    def test_chain_exact_credit_and_entries(self):
        nodes = {0: Region(2, (2,)), 2: Region(3, (5,)), 5: Region(1, ())}
        p = plan(nodes)
        self.assertEqual(p['credit'], {5: 1, 2: 4, 0: 6})
        self.assertEqual(p['incoming'], {2, 5})
        for start in range(3):
            path = [0, 2, 5][start:]
            self.compare(nodes, path, range(10))
        self.assertEqual(simulate(nodes, [0, 2, 5], 6)[1:], (1, 0))

    def test_diamond_uses_longest_branch_without_charging_it(self):
        nodes = {0: Region(1, (1, 5)), 1: Region(2, (10,)), 5: Region(4, (10,)), 10: Region(2, ())}
        self.assertEqual(plan(nodes)['credit'][0], 7)
        for path in [[0, 1, 10], [0, 5, 10]]:
            self.compare(nodes, path, range(12))
        self.assertEqual(simulate(nodes, [0, 1, 10], 7)[0][-1], 2)

    def test_backedges_and_self_edges_always_recheck(self):
        nodes = {0: Region(2, (0, 2)), 2: Region(3, (0,))}
        self.assertEqual(plan(nodes)['fast'], {2: (), 0: (2,)})
        self.compare(nodes, [0, 0, 2, 0, 2, 0], range(22))
        self.assertEqual(simulate(nodes, [0, 2, 0, 2], 30)[1], 2)

    def test_guarded_targets_and_opaque_call_gaps_cut_edges(self):
        nodes = {0: Region(1, (1, 2, 99)), 1: Region(2, (2,), True), 2: Region(3, ())}
        self.assertEqual(plan(nodes)['fast'][0], (2,))
        self.compare(nodes, [0, 1, 2], range(10))
        self.assertEqual(simulate(nodes, [0, 1, 2], 9)[1], 2)

    def test_cap_cuts_without_losing_node_or_other_incoming_credit(self):
        nodes = {i: Region(1024, (i+1,) if i < 6 else ()) for i in range(7)}
        p = plan(nodes)
        self.assertEqual(p['fast'][2], ())
        self.assertEqual(p['credit'][2], 1024)
        self.assertEqual(p['credit'][3], 4096)
        self.assertTrue(all(v <= 4096 for v in p['credit'].values()))
        self.compare(nodes, list(range(7)), [0, 1, 1023, 1024, 4095, 4096, 7168, 8000])

    def test_external_reentry_never_inherits_fast_credit(self):
        nodes = {0: Region(1, (1,)), 1: Region(2, (2,)), 2: Region(3, ())}
        self.compare(nodes, [0, 1, 2], range(9), external=(1, 2))
        self.assertEqual(simulate(nodes, [0, 1, 2], 8, external=(1, 2))[1], 3)

    def test_every_fault_and_budget_prefix(self):
        nodes = {0: Region(2, (2,)), 2: Region(4, (6,)), 6: Region(3, (0,))}
        path = [0, 2, 6, 0, 2]
        faults = [None] + [(visit, op) for visit, pc in enumerate(path) for op in range(nodes[pc].cost)]
        self.compare(nodes, path, range(19), faults)

    def test_all_three_node_graphs_all_short_walks(self):
        for mask in range(512):
            nodes = {i: Region(i+1, tuple(j for j in range(3) if mask & (1 << (i*3+j)))) for i in range(3)}
            p = plan(nodes)
            for start in nodes:
                paths = [[start]]
                for _ in range(3):
                    paths = [path+[t] for path in paths for t in nodes[path[-1]].successors] or paths
                for path in paths:
                    self.compare(nodes, path, range(sum(nodes[pc].cost for pc in path)+2))
            for s, ts in p['fast'].items():
                for t in ts:
                    self.assertGreaterEqual(p['credit'][s]-nodes[s].cost, p['credit'][t])

    def test_seeded_paths_mixed_entries_and_large_budgets(self):
        rng = random.Random(2190919)
        for _ in range(500):
            nodes = {i: Region(rng.randrange(1, 20), tuple(sorted(rng.sample(range(9), rng.randrange(4)))), rng.randrange(5)==0) for i in range(9)}
            path = [rng.randrange(9)]
            while len(path) < 30 and nodes[path[-1]].successors:
                path.append(rng.choice(nodes[path[-1]].successors))
            total = sum(nodes[pc].cost for pc in path)
            self.compare(nodes, path, [0, total//2, total, total+1, 2**64-1], external=range(0,len(path),3))

    def test_malformed_inputs_rejected(self):
        for nodes in [{}, {-1:Region(1,())}, {0:Region(0,())}, {0:Region(1025,())},
                      {0:Region(1,(-1,))}, {0:Region(1,(1,1))}, {0:Region(1,[],False)},
                      {0:Region(True,())}, {0:Region(1,(),1)}]:
            with self.assertRaises(ValueError): plan(nodes)
        with self.assertRaises(ValueError): simulate({0:Region(1,()),1:Region(1,())}, [0,1], 10)

    def test_nominal_emission_overhead_is_counted(self):
        nodes = {0:Region(1,(1,)),1:Region(1,())}
        p = plan(nodes)
        self.assertEqual(p['extra_immediate'], {0,1})
        # 4+4 baseline words versus 5 checked + 2 fast; only one saved word.
        self.assertEqual(4*2 - (5+2), 1)
        isolated = plan({0:Region(1,())})
        self.assertFalse(isolated['extra_immediate'])


if __name__ == '__main__': unittest.main()
