import copy
import unittest
from analyze import compare


def fixture():
    def row(i,body,key,callees,ops,size):return dict(function=i,name_sha256=str(i)*64,
        body_sha256=body*64,necessary_inputs_sha256=key*64,direct_callees=callees,
        operations=ops,serialized_bytes=size)
    return dict(artifact_sha256='a'*64,identities=dict(namespace_sha256='b'*64,uses_heap=False,
        functions=[row(0,'c','d',[1],10,100),row(1,'e','f',[],2,20)]))


class IdentityComparison(unittest.TestCase):
    def test_callee_edit_separates_local_body_from_dependent_invalidation(self):
        before=fixture();after=copy.deepcopy(before);after['artifact_sha256']='0'*64
        after['identities']['functions'][1].update(body_sha256='1'*64,necessary_inputs_sha256='2'*64)
        after['identities']['functions'][0]['necessary_inputs_sha256']='3'*64
        result=compare(before,after)
        self.assertEqual(result['same_body_at_same_id'],1)
        self.assertEqual(result['same_necessary_inputs'],0)
        self.assertEqual(result['callee_dependent_invalidations'],1)

    def test_global_invalidation_is_not_attributed_to_callees(self):
        before=fixture();after=copy.deepcopy(before)
        after['artifact_sha256']='0'*64;after['identities']['namespace_sha256']='1'*64
        for i,f in enumerate(after['identities']['functions']):f['necessary_inputs_sha256']=str(i+2)*64
        result=compare(before,after)
        self.assertEqual(result['same_body_at_same_id'],2)
        self.assertEqual(result['same_necessary_inputs'],0)
        self.assertEqual(result['callee_dependent_invalidations'],0)

    def test_unchanged_inputs_count_bytecode_size_without_runtime_weighting(self):
        result=compare(fixture(),fixture())
        self.assertEqual(result['same_necessary_inputs'],2)
        self.assertEqual(result['same_necessary_input_operations'],12)
        self.assertEqual(result['same_necessary_input_bytes'],120)
        self.assertTrue(result['identical_artifact'])

    def test_changed_identity_scope_or_inconsistent_key_claims_fail(self):
        for mutation in [lambda r:r['identities'].update(namespace_sha256='0'*64),
                         lambda r:r['identities']['functions'][0].update(body_sha256='0'*64),
                         lambda r:r['identities']['functions'][0].update(operations=11),
                         lambda r:r['identities']['functions'][1].update(necessary_inputs_sha256='0'*64),
                         lambda r:r['identities']['functions'][0].update(function=True),
                         lambda r:r['identities']['functions'][0].update(direct_callees=[1,1])]:
            before=fixture();after=copy.deepcopy(before);after['artifact_sha256']='9'*64;mutation(after)
            with self.assertRaises(AssertionError):compare(before,after)


if __name__=='__main__':unittest.main()
