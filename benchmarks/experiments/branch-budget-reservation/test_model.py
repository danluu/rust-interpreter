import random
import unittest
from model import Region,plan,simulate,oracle
from scope import budget_words

class Tests(unittest.TestCase):
    def test_short_branch_refunds_the_exact_unchosen_difference(self):
        n={0:Region(1,(1,5)),1:Region(2,(10,)),5:Region(4,(10,)),10:Region(2,())}
        short=simulate(n,[0,1,10],7)
        long=simulate(n,[0,5,10],7)
        self.assertEqual((short['reservations'],short['refunds'],short['outcome'][2]),(1,1,2))
        self.assertEqual((long['reservations'],long['refunds'],long['outcome'][2]),(1,0,0))
        for path in [[0,1,10],[0,5,10]]:
            faults=[None]+[(i,k) for i,pc in enumerate(path) for k in range(n[pc].cost)]
            self.compare(n,path,range(11),faults)

    def test_cut_backedge_refunds_before_next_checked_entry(self):
        n={0:Region(2,(0,2)),2:Region(3,())}
        p=plan(n);self.assertEqual(p['credit'][0],5)
        r=simulate(n,[0,0,2],10)
        self.assertEqual((r['reservations'],r['refunds'],r['outcome'][2]),(2,1,3))
        self.compare(n,[0,0,2],range(12))

    def compare(self,nodes,path,budgets,faults=(None,),external=()):
        for budget in budgets:
            for fault in faults:
                result=simulate(nodes,path,budget,fault,external)
                self.assertEqual(result['outcome'],oracle(nodes,path,budget,fault))
                for row in result['publications']:self.assertEqual(row['remaining'],row['expected'])

    def test_chain_reserves_once(self):
        n={0:Region(2,(2,)),2:Region(3,(5,)),5:Region(1,())}
        p=plan(n);self.assertEqual(p['credit'],{5:1,2:4,0:6})
        self.compare(n,[0,2,5],range(10))
        r=simulate(n,[0,2,5],6);self.assertEqual((r['reservations'],r['refunds']),(1,0))

    def test_multi_successor_node_reserves_maximum(self):
        n={0:Region(1,(1,5)),1:Region(2,(10,)),5:Region(4,(10,)),10:Region(2,())}
        self.assertEqual(plan(n)['credit'][0],7)
        for path in [[0,1,10],[0,5,10]]:self.compare(n,path,range(12))

    def test_backedges_and_self_edges_cut(self):
        n={0:Region(2,(2,)),2:Region(3,(0,)),5:Region(2,(5,))}
        self.assertEqual(plan(n)['fast'],{5:(),2:(),0:(2,)})
        self.compare(n,[0,2,0,2,0],range(20));self.compare(n,[5]*5,range(12))

    def test_guarded_target_and_missing_native_region(self):
        n={0:Region(1,(1,)),1:Region(2,(3,),True),3:Region(3,(99,))}
        self.assertEqual(plan(n)['fast'],{3:(),1:(3,),0:()})
        self.compare(n,[0,1,3],range(9))

    def test_cap_cuts_with_all_nodes_retained(self):
        n={i:Region(1024,(i+1,) if i<6 else ()) for i in range(7)}
        p=plan(n);self.assertEqual(p['fast'][2],());self.assertEqual(p['credit'][3],4096)
        self.compare(n,list(range(7)),[0,1,1023,1024,4095,4096,7168,8000])

    def test_every_external_entry_and_refund_boundary(self):
        n={0:Region(2,(2,)),2:Region(3,(5,)),5:Region(1,())}
        for start in range(3):
            path=[0,2,5][start:]
            for external in [(),(0,),(1,),(2,),(0,1,2)]:self.compare(n,path,range(10),external=external)
        r=simulate(n,[0,2,5],6,external=(1,2));self.assertEqual((r['reservations'],r['refunds']),(3,2))

    def test_every_fault_and_short_budget_prefix(self):
        n={0:Region(2,(2,)),2:Region(4,(6,)),6:Region(3,(0,))};path=[0,2,6,0,2]
        faults=[None]+[(i,k) for i,pc in enumerate(path) for k in range(n[pc].cost)]
        self.compare(n,path,range(19),faults)

    def test_fault_refunds_future_but_retains_current_region_debit(self):
        n={0:Region(3,(3,)),3:Region(5,())}
        r=simulate(n,[0,3],8,fault=(0,0))
        self.assertEqual(r['outcome'][2],7)
        self.assertEqual(r['publications'][-1],dict(visit=0,kind='native_fault',remaining=5,expected=5))
        self.assertEqual(r['refunds'],1)
        r=simulate(n,[0,3],4,fault=(0,0));self.assertEqual(r['publications'][-1]['kind'],'tail_fault')
        self.assertEqual(r['publications'][-1]['remaining'],3)

    def test_all_three_node_graphs_short_walks(self):
        for mask in range(512):
            n={i:Region(i+1,tuple(j for j in range(3) if mask&(1<<(i*3+j)))) for i in range(3)}
            for start in n:
                paths=[[start]]
                for _ in range(3):paths=[p+[t] for p in paths for t in n[p[-1]].successors] or paths
                for path in paths:self.compare(n,path,range(sum(n[pc].cost for pc in path)+2))

    def test_seeded_longer_walks(self):
        rng=random.Random(3190919)
        for _ in range(500):
            n={i:Region(rng.randrange(1,20),tuple(sorted(rng.sample(range(9),rng.randrange(4)))),rng.randrange(5)==0) for i in range(9)}
            path=[rng.randrange(9)]
            while len(path)<30 and n[path[-1]].successors:path.append(rng.choice(n[path[-1]].successors))
            total=sum(n[pc].cost for pc in path)
            self.compare(n,path,[0,total//2,total,total+1,2**64-1],external=range(0,len(path),3))

    def test_rejects_invalid_shapes(self):
        for n in [{},{-1:Region(1,())},{0:Region(0,())},{0:Region(1025,())},{0:Region(1,(-1,))},
                  {0:Region(1,(1,1))},{0:Region(1,[])},{0:Region(True,())},{0:Region(1,(),1)}]:
            with self.assertRaises(ValueError):plan(n)
        with self.assertRaises(ValueError):simulate({0:Region(1,()),1:Region(1,())},[0,1],5)

    def test_exact_native_budget_decoder(self):
        for cost in [1,2,32,1024]:
            words=[0xd280000a|(cost<<5),0xeb0a02df,0x54000103,0xcb0a02d6]
            self.assertTrue(budget_words(words,cost))
            for i in range(4):
                bad=words.copy();bad[i]^=1;self.assertFalse(budget_words(bad,cost))
        self.assertFalse(budget_words([],0))

if __name__=='__main__':unittest.main()
