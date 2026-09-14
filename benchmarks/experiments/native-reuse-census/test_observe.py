import copy, random, unittest
from observe import compare, aggregate, native_weights


def report(edges):
    return dict(global_sha256='global', functions=[dict(id=i, name=str(i), body_sha256='body'+str(i),
        layout_sha256='layout'+str(i), direct_callees=targets, operations=2, serialized_bytes=100)
        for i, targets in enumerate(edges)])


class IdentityControls(unittest.TestCase):
    def test_body_change_with_identical_interface_invalidates_direct_callers(self):
        a=report([[1],[2],[],[]]); b=copy.deepcopy(a); b['functions'][2]['body_sha256']='changed'
        result=compare(a,b)
        self.assertEqual(result['self_equal'],[0,1,3])
        self.assertEqual(result['self_and_call_layouts'],[0,1,3])
        self.assertEqual(result['self_and_direct_bodies'],[0,3])
        self.assertEqual(result['transitive_direct_bodies'],[3])
        self.assertEqual(aggregate(b,result,{0:20,3:50})['conditions']['transitive_direct_bodies']['reference_native_bytes'],50)

    def test_cycles_and_global_invalidation(self):
        a=report([[1],[0,2],[],[]]); b=copy.deepcopy(a); b['functions'][2]['body_sha256']='changed'
        self.assertEqual(compare(a,b)['transitive_direct_bodies'],[3])
        b['global_sha256']='other'
        result=compare(a,b); self.assertEqual(result['self_and_call_layouts'],[])
        self.assertEqual(result['transitive_direct_bodies'],[])

    def test_reverse_closure_matches_independent_forward_walk(self):
        rng=random.Random(380129)
        for _ in range(160):
            n=rng.randrange(2,24); a=report([sorted({rng.randrange(n) for _ in range(rng.randrange(5))}) for _ in range(n)])
            b=copy.deepcopy(a); changed={i for i in range(n) if rng.randrange(5)==0}
            for i in changed: b['functions'][i]['body_sha256']='changed'+str(i)
            expected=[]
            for root in range(n):
                seen=set(); todo=[root]
                while todo:
                    node=todo.pop()
                    if node in seen: continue
                    seen.add(node); todo.extend(b['functions'][node]['direct_callees'])
                if not seen & changed: expected.append(root)
            self.assertEqual(compare(a,b)['transitive_direct_bodies'],expected)

    def test_code_weights_require_exact_body_and_map_identity(self):
        a=report([[],[]]); b=copy.deepcopy(a); b['functions'][1]['body_sha256']='changed'
        mapping=dict(code_bytes=30,ranges=[dict(offset=0,end=10,function=0,name='0'),dict(offset=10,end=30,function=1,name='1')])
        self.assertEqual(native_weights(mapping,a,b),{0:10})
        mapping['ranges'][0]['name']='wrong'
        with self.assertRaises(AssertionError): native_weights(mapping,a,b)


if __name__=='__main__': unittest.main()
