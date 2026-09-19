"""Metadata/CLI fixtures only; no filesystem, compiler or workload imports."""
import argparse
import contextlib
import copy
import io
from types import SimpleNamespace
import unittest

import workflow_runtime_arms as arms

A, B, SA, SB, TA, TB = (c*64 for c in 'abcdef')


def options(**changes):
    value = dict(runtime_compiler_key=None, std_mir_key=None,
        baseline_runtime_compiler_key=A, candidate_runtime_compiler_key=B,
        baseline_std_mir_key=None, candidate_std_mir_key=None, std_mir=False,
        baseline_tool_key=TA, candidate_tool_key=TB, batch=True,
        build_tool_opt_level=None, aa_control=False)
    value.update(changes)
    return SimpleNamespace(**value)


def proof(key):
    return dict(key=key, policy='owned-native-runtime-compiler-v1',
        rustc='/fixture/'+key+'/bin/rustc', rustc_sha256=key,
        compiler='rustc 1.100.0-dev\ncommit-hash: '+key[:40]+'\n')


def fixture(standard=False):
    choice = arms.select(options(std_mir=standard,
        baseline_std_mir_key=SA if standard else None,
        candidate_std_mir_key=SB if standard else None))
    proofs = dict(baseline=proof(A), candidate=proof(B))
    stds = {mode: None if not standard else dict(key=key,sysroot='/fixture/'+key,target='fixture-host')
            for mode,key in [('baseline',SA),('candidate',SB)]}
    tools = dict(baseline=dict(directory='/fixture/tools-a',tool_key=TA),
                 candidate=dict(directory='/fixture/tools-b',tool_key=TB))
    return choice, proofs, stds, tools


class Selection(unittest.TestCase):
    def test_legacy_default_is_delegated_unchanged(self):
        self.assertIsNone(arms.select(options(baseline_runtime_compiler_key=None,candidate_runtime_compiler_key=None)))

    def test_legacy_shared_runtime_and_std_are_delegated(self):
        self.assertIsNone(arms.select(options(runtime_compiler_key=A,std_mir_key=SA,std_mir=True,
            baseline_runtime_compiler_key=None,candidate_runtime_compiler_key=None)))

    def test_complete_distinct_arms_route_exact_arguments(self):
        value=arms.select(options())
        self.assertEqual(arms.arguments(value,'baseline'),['--runtime-compiler-key',A])
        self.assertEqual(arms.arguments(value,'candidate'),['--runtime-compiler-key',B])

    def test_prepared_std_routes_to_its_own_arm(self):
        value=fixture(True)[0]
        self.assertEqual(arms.arguments(value,'candidate'),['--runtime-compiler-key',B,
            '--std-mir-policy','source-paths-v2-shared','--std-mir-key',SB])

    def test_one_runtime_arm_is_rejected(self):
        for field in ['baseline_runtime_compiler_key','candidate_runtime_compiler_key']:
            with self.subTest(field=field),self.assertRaises(RuntimeError):arms.select(options(**{field:None}))

    def test_shared_runtime_conflicts_even_if_equal(self):
        with self.assertRaises(RuntimeError):arms.select(options(runtime_compiler_key=A))

    def test_shared_std_conflicts_with_per_arm_mode(self):
        with self.assertRaises(RuntimeError):arms.select(options(std_mir_key=SA))

    def test_std_cannot_select_per_arm_mode_without_runtimes(self):
        with self.assertRaises(RuntimeError):arms.select(options(baseline_runtime_compiler_key=None,
            candidate_runtime_compiler_key=None,baseline_std_mir_key=SA))

    def test_std_requires_two_keys_and_explicit_policy(self):
        for changes in [dict(std_mir=True),dict(std_mir=True,baseline_std_mir_key=SA),
                        dict(baseline_std_mir_key=SA,candidate_std_mir_key=SB)]:
            with self.subTest(changes=changes),self.assertRaises(RuntimeError):arms.select(options(**changes))

    def test_batch_and_both_toolsets_are_required(self):
        for changes in [dict(batch=False),dict(baseline_tool_key=None),dict(candidate_tool_key=None)]:
            with self.subTest(changes=changes),self.assertRaises(RuntimeError):arms.select(options(**changes))

    def test_host_profile_override_is_rejected(self):
        with self.assertRaises(RuntimeError):arms.select(options(build_tool_opt_level=2))

    def test_malformed_and_nonstring_keys_are_rejected(self):
        for value in ['', 'A'*64, 'a'*63, 'z'*64, True, 4]:
            with self.subTest(value=value),self.assertRaises(RuntimeError):arms.select(options(candidate_runtime_compiler_key=value))

    def test_aa_rejects_different_runtime_or_std(self):
        for changes in [dict(aa_control=True),dict(aa_control=True,candidate_runtime_compiler_key=A,
            std_mir=True,baseline_std_mir_key=SA,candidate_std_mir_key=SB)]:
            with self.subTest(changes=changes),self.assertRaises(RuntimeError):arms.select(options(**changes))

    def test_aa_allows_identical_runtime_and_std(self):
        value=arms.select(options(aa_control=True,candidate_runtime_compiler_key=A,std_mir=True,
                                 baseline_std_mir_key=SA,candidate_std_mir_key=SA))
        self.assertEqual(value['arms']['baseline'],value['arms']['candidate'])

    def test_native_mode_cannot_receive_custom_flags(self):
        with self.assertRaises(RuntimeError):arms.arguments(arms.select(options()),'native')

    def test_cli_four_explicit_keys_roundtrip(self):
        parser=argparse.ArgumentParser();arms.add_arguments(parser)
        value=parser.parse_args(['--baseline-runtime-compiler-key',A,'--candidate-runtime-compiler-key',B,
            '--baseline-std-mir-key',SA,'--candidate-std-mir-key',SB])
        self.assertEqual(vars(value),dict(baseline_runtime_compiler_key=A,candidate_runtime_compiler_key=B,
            baseline_std_mir_key=SA,candidate_std_mir_key=SB))

    def test_cli_duplicate_even_identical_value_is_rejected(self):
        for option in ['--baseline-runtime-compiler-key','--candidate-runtime-compiler-key',
                       '--baseline-std-mir-key','--candidate-std-mir-key']:
            parser=argparse.ArgumentParser();arms.add_arguments(parser)
            with self.subTest(option=option),contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                parser.parse_args([option,A,option,A])

    def test_cli_malformed_key_is_rejected(self):
        parser=argparse.ArgumentParser();arms.add_arguments(parser)
        with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            parser.parse_args(['--baseline-runtime-compiler-key','not-a-key'])


class Binding(unittest.TestCase):
    def setup_binding(self,choice=None,wrong_load=False,wrong_tool=False,wrong_proof=False):
        selected,_,_,tools=fixture();choice=selected if choice is None else choice;events=[]
        def load(k):
            events.append(('load',k))
            actual=B if wrong_load else k
            return SimpleNamespace(key=actual,environment=lambda env:events.append(('environment',actual,dict(env))))
        def validate(directory,tool,compiler):
            events.append(('tool',directory,tool,compiler.key))
            if wrong_tool:raise RuntimeError('fixture tool belongs to another actual runtime')
        def receipt(compiler):return proof(B if wrong_proof else compiler.key)
        return choice,tools,events,dict(load_runtime=load,validate_tool=validate,environment={'LANG':'C'},runtime_receipt=receipt)

    def test_each_arm_tool_is_validated_with_selected_runtime(self):
        c,t,events,callbacks=self.setup_binding();r,p=arms.bind(c,t,**callbacks)
        self.assertEqual([(v[2],v[3]) for v in events if v[0]=='tool'],[(TA,A),(TB,B)])
        self.assertEqual([r[m].key for m in arms.MODES],[A,B]);self.assertEqual(p['baseline'],proof(A))

    def test_same_runtime_load_is_shared_but_both_tools_checked(self):
        c=arms.select(options(candidate_runtime_compiler_key=A));c,t,events,cb=self.setup_binding(c)
        arms.bind(c,t,**cb)
        self.assertEqual([v for v in events if v[0]=='load'],[('load',A)])
        self.assertEqual(len([v for v in events if v[0]=='tool']),2)

    def test_wrong_loaded_key_is_rejected_before_tool(self):
        c,t,events,cb=self.setup_binding(wrong_load=True)
        with self.assertRaises(RuntimeError):arms.bind(c,t,**cb)
        self.assertFalse(any(v[0]=='tool' for v in events))

    def test_actual_tool_validation_failure_propagates(self):
        c,t,events,cb=self.setup_binding(wrong_tool=True)
        with self.assertRaises(RuntimeError):arms.bind(c,t,**cb)
        self.assertEqual(len([v for v in events if v[0]=='load']),1)

    def test_wrong_runtime_receipt_is_rejected(self):
        c,t,_,cb=self.setup_binding(wrong_proof=True)
        with self.assertRaises(RuntimeError):arms.bind(c,t,**cb)

    def test_missing_or_extra_tool_arm_is_rejected(self):
        for mode in ['native','baseline']:
            c,t,_,cb=self.setup_binding()
            if mode=='native':t[mode]=t['baseline']
            else:del t[mode]
            with self.subTest(mode=mode),self.assertRaises(RuntimeError):arms.bind(c,t,**cb)


class Receipts(unittest.TestCase):
    def test_complete_runtime_std_tool_associations_roundtrip(self):
        c,p,s,t=fixture(True);value=arms.receipts(c,p,s,t)
        self.assertEqual(arms.validate_receipts(value,t),value)
        self.assertIsInstance(value['arms']['baseline']['runtime']['compiler'],str)

    def test_returned_receipts_are_detached(self):
        c,p,s,t=fixture(True);value=arms.receipts(c,p,s,t);saved=copy.deepcopy((c,p,s,t))
        value['arms']['baseline']['runtime']['compiler']='changed'
        value['selection']['arms']['candidate']['std_key']=SA
        self.assertEqual((c,p,s,t),saved)

    def test_swapped_runtime_arm_is_rejected(self):
        c,p,s,t=fixture();p['baseline'],p['candidate']=p['candidate'],p['baseline']
        with self.assertRaises(RuntimeError):arms.receipts(c,p,s,t)

    def test_swapped_std_arm_is_rejected(self):
        c,p,s,t=fixture(True);s['baseline'],s['candidate']=s['candidate'],s['baseline']
        with self.assertRaises(RuntimeError):arms.receipts(c,p,s,t)

    def test_swapped_tool_receipt_is_rejected(self):
        c,p,s,t=fixture();value=arms.receipts(c,p,s,t);value['arms']['baseline']['tool_key']=TB
        with self.assertRaises(RuntimeError):arms.validate_receipts(value,t)

    def test_unexpected_receipt_fields_are_rejected(self):
        c,p,s,t=fixture();value=arms.receipts(c,p,s,t)
        for target in ['top','arm','runtime']:
            changed=copy.deepcopy(value);where=changed if target=='top' else changed['arms']['baseline']
            if target=='runtime':where=where['runtime']
            where['invented']=True
            with self.subTest(target=target),self.assertRaises(RuntimeError):arms.validate_receipts(changed,t)

    def test_nonactual_compiler_version_shape_is_rejected(self):
        c,p,s,t=fixture();p['baseline']['compiler']={'version':'fixture'}
        with self.assertRaises(RuntimeError):arms.receipts(c,p,s,t)

    def test_false_prepared_std_policy_is_rejected(self):
        c,p,s,t=fixture(True);s['baseline']=None
        with self.assertRaises(RuntimeError):arms.receipts(c,p,s,t)

    def test_each_call_reaches_exact_existing_validator(self):
        c,p,s,t=fixture(True);value=arms.receipts(c,p,s,t);seen=[]
        for mode in arms.MODES:
            call={'launch':{'tool_key':t[mode]['tool_key']}}
            arms.verify_call(value,mode,call,verify_runtime_call=lambda call,runtime,std:seen.append((runtime,std)))
        self.assertEqual(seen,[(p['baseline'],s['baseline']),(p['candidate'],s['candidate'])])

    def test_foreign_call_tool_is_rejected_before_runtime_validator(self):
        c,p,s,t=fixture();value=arms.receipts(c,p,s,t);seen=[]
        with self.assertRaises(RuntimeError):arms.verify_call(value,'baseline',{'launch':{'tool_key':TB}},
            verify_runtime_call=lambda *args:seen.append(args))
        self.assertEqual(seen,[])

    def test_existing_command_runtime_rejection_propagates(self):
        c,p,s,t=fixture();value=arms.receipts(c,p,s,t)
        def reject(call,runtime,std):raise RuntimeError('fixture command selects another runtime')
        with self.assertRaises(RuntimeError):arms.verify_call(value,'baseline',{'launch':{'tool_key':TA}},
            verify_runtime_call=reject)


if __name__=='__main__':
    unittest.main()
