import random
import unittest
from graph import analyze, components, cycle_at, range_cycle, successors

IMM = 'Imm { dst: 0, value: 0 }'
CALL = 'Call { function: 1, args: [], destination: 0 }'
def jump(pc): return 'Jump { target: %d }' % pc
def switch(a,b): return 'Switch { value: 0, cases: [(0, %d)], otherwise: %d }' % (a,b)

class GraphTests(unittest.TestCase):
    def test_unit_fallthrough_variant(self):
        self.assertEqual(successors('ResetThreadLocals',0,2),((1,),False))
        self.assertEqual(analyze(['ResetThreadLocals',jump(0)])['cycles'][0]['other_effects'],1)
        for ops in [['ResetThreadLocals'],['ResetThreadLocals { }','Return']]:
            with self.assertRaises(ValueError):analyze(ops)

    def test_diamond(self):
        g=analyze([switch(1,3),IMM,jump(4),IMM,'Return'])
        self.assertEqual(g['cycles'],[])
        self.assertEqual(g['unreachable_operations'],0)

    def test_self_loop(self):
        g=analyze([jump(0)])
        self.assertEqual(g['cycles'][0]['entries'],[0])
        self.assertEqual(cycle_at(g,0),0)

    def test_multiple_exits(self):
        g=analyze([switch(1,4),switch(2,5),IMM,jump(0),'Return','Return'])
        self.assertEqual(g['cycles'][0]['exits'],[4,5])
        self.assertEqual(g['cycles'][0]['operations'],4)

    def test_multiple_entries(self):
        g=analyze([switch(1,2),jump(2),switch(1,3),'Return'])
        self.assertEqual(g['cycles'][0]['entries'],[1,2])

    def test_unreachable_cycle(self):
        g=analyze(['Return',jump(1)])
        self.assertFalse(g['cycles'][0]['reachable'])
        self.assertEqual(g['cycles'][0]['entries'],[])
        self.assertEqual(g['unreachable_operations'],1)

    def test_calls_fall_through(self):
        g=analyze([CALL,jump(0)])
        self.assertEqual(g['cycles'][0]['calls'],1)
        self.assertEqual(g['cycles'][0]['operations'],2)

    def test_trap_is_terminal(self):
        g=analyze(['Trap { message: "escaped \\" text" }',jump(0)])
        self.assertEqual(g['cycles'],[])
        self.assertEqual(g['unreachable_operations'],1)

    def test_switch_full_width_duplicate_and_empty(self):
        text='Switch { value: 0, cases: [(0, 1), (0, 2), (%d, 1)], otherwise: 2 }' % (2**128-1)
        self.assertEqual(successors(text,0,3),((1,2),True))
        self.assertEqual(successors('Switch { value: 0, cases: [(0, 1), (0, 2)], otherwise: 0 }',0,3),((0,1),True))
        self.assertEqual(successors('Switch { value: 0, cases: [], otherwise: 0 }',0,1),((0,),True))

    def test_invalid_branches(self):
        for text in [jump(-1),jump(2),'Switch { value: 0, cases: [(0, 2)], otherwise: 0 }',
            'Switch { value: 0, cases: [(0, 0),garbage], otherwise: 0 }',
            'Switch { value: 0, cases: [(%d, 0)], otherwise: 0 }' % 2**128]:
            with self.subTest(text=text),self.assertRaises(ValueError): successors(text,0,2)

    def test_unknown_and_falloff(self):
        for ops in [[IMM],['CallNever { destination: 0 }','Return'],['Return garbage'],['Trap { message: bad }']]:
            with self.subTest(ops=ops),self.assertRaises(ValueError):analyze(ops)

    def test_budget_and_bounds(self):
        for edges in [[],[(2,)],[(True,)]]:
            with self.assertRaises(ValueError):components(edges)
        with self.assertRaises(ValueError):successors(IMM,0,1_000_001)
        with self.assertRaises(ValueError):analyze([])

    def test_range_assignment(self):
        g=analyze([IMM,switch(2,4),IMM,jump(1),'Return'])
        self.assertIsNone(range_cycle(g,0,4))
        self.assertEqual(range_cycle(g,1,4),cycle_at(g,1))
        self.assertEqual(range_cycle(g,4,5),-1)
        with self.assertRaises(ValueError):range_cycle(g,1,6)

    def test_large_chain_without_recursion(self):
        edges=[(i+1,) for i in range(19999)]+[()]
        groups,_=components(edges)
        self.assertEqual(len(groups),20000)

    def test_exhaustive_graph_oracle(self):
        # Independent transitive-closure equivalence, all 512 directed 3-node graphs.
        for mask in range(512):
            edges=[tuple(j for j in range(3) if mask & (1 << (3*i+j))) for i in range(3)]
            self.check_oracle(edges)

    def test_random_graph_oracle(self):
        rng=random.Random(971)
        for _ in range(250):
            n=rng.randrange(1,18)
            self.check_oracle([tuple(j for j in range(n) if rng.randrange(5)==0) for i in range(n)])

    def test_cfg_against_pc_reachability(self):
        rng=random.Random(864)
        for _ in range(250):
            n=rng.randrange(2,25);ops=[];edges=[]
            for pc in range(n):
                kind=rng.randrange(4) if pc+1<n else 3
                a,b=rng.randrange(n),rng.randrange(n)
                if kind==0:ops.append(IMM);edges.append((pc+1,))
                elif kind==1:ops.append(jump(a));edges.append((a,))
                elif kind==2:ops.append(switch(a,b));edges.append(tuple(sorted({a,b})))
                else:ops.append('Return');edges.append(())
            reach=[set(row) for row in edges]
            for k in range(n):
                for i in range(n):
                    if k in reach[i]:reach[i].update(reach[k])
            expected={tuple(j for j in range(n) if j in reach[i] and i in reach[j]) for i in range(n) if i in reach[i]}
            g=analyze(ops)
            actual={tuple(pc for lo,hi in c['ranges'] for pc in range(lo,hi)) for c in g['cycles']}
            self.assertEqual(actual,expected)

    def check_oracle(self,edges):
        reach=[set([i,*row]) for i,row in enumerate(edges)]
        for k in range(len(edges)):
            for i in range(len(edges)):
                if k in reach[i]:reach[i].update(reach[k])
        expected={tuple(j for j in range(len(edges)) if j in reach[i] and i in reach[j]) for i in range(len(edges))}
        groups,membership=components(edges)
        self.assertEqual({tuple(g) for g in groups},expected)
        for group_id,group in enumerate(groups):
            for node in group:self.assertEqual(membership[node],group_id)

if __name__=='__main__':unittest.main()
