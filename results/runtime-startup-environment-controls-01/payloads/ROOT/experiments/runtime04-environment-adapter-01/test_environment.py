"""Pure startup controls and unchanged Controller admission sentinels.

No process, provider, runtime constructor beyond its early admission check, or
environment mutation is used. The Controller receives a fake os namespace.
"""
import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import environment as policy

CONTROLLER = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/experiments/hir-options-hash/runtime-installation-01/controller.py')


def fixture(value='0x1F5:0x0:0x52'):
    workload = {'PATH':'/fixture/bin', 'HOME':'/fixture/home', 'TMPDIR':'/fixture/work/tmp'}
    passed = {'PATH':'/usr/bin', 'HOME':'/fixture/home'}
    observed = dict(passed)
    if value is not None:
        observed[policy.CF] = value
    return workload, passed, {name:dict(observed) for name in policy.OBSERVATIONS}


def derive(workload, passed, observations, **kwargs):
    return policy.derive(workload, passed, observations,
                         platform=kwargs.get('platform','darwin'), uid=kwargs.get('uid',501))


class Environment(unittest.TestCase):
    def test_exact_darwin_without_startup_addition(self):
        w,p,o=fixture(None);self.assertEqual(derive(w,p,o)['launch_environment'],w)

    def test_exact_non_darwin_without_startup_addition(self):
        w,p,o=fixture(None);self.assertEqual(derive(w,p,o,platform='linux')['launch_environment'],w)

    def test_observed_cf_is_explicit_and_workload_is_unchanged(self):
        w,p,o=fixture();before=copy.deepcopy((w,p,o));result=derive(w,p,o)
        self.assertEqual((w,p,o),before)
        self.assertEqual(result['launch_environment'],dict(w,**{policy.CF:'0x1F5:0x0:0x52'}))
        self.assertEqual(policy.validate(w,result),result['launch_environment'])

    def test_numeric_spelling_is_preserved(self):
        for value in ['501:0:82','0X1f5:00:0X52','000501:0:82']:
            w,p,o=fixture(value);self.assertEqual(derive(w,p,o)['launch_environment'][policy.CF],value)

    def test_preexisting_cf_remains_exact(self):
        w,p,o=fixture();value=o[policy.OBSERVATIONS[0]][policy.CF]
        w[policy.CF]=p[policy.CF]=value
        self.assertEqual(derive(w,p,o)['launch_environment'],w)

    def test_existing_cf_conflict_is_rejected(self):
        w,p,o=fixture();w[policy.CF]='501:0:1'
        with self.assertRaisesRegex(RuntimeError,'conflicts'):derive(w,p,o)

    def test_unknown_addition_is_rejected(self):
        for name in ['DYLD_LIBRARY_PATH','RUSTFLAGS','UNDECLARED']:
            w,p,o=fixture()
            for value in o.values():value[name]=''
            with self.assertRaisesRegex(RuntimeError,'unadmitted'):derive(w,p,o)

    def test_removed_passed_variable_is_rejected(self):
        w,p,o=fixture()
        for value in o.values():del value['PATH']
        with self.assertRaisesRegex(RuntimeError,'passed'):derive(w,p,o)

    def test_changed_passed_variable_is_rejected(self):
        w,p,o=fixture()
        for value in o.values():value['PATH']='/foreign'
        with self.assertRaisesRegex(RuntimeError,'passed'):derive(w,p,o)

    def test_cf_on_other_platform_is_rejected(self):
        w,p,o=fixture()
        with self.assertRaises(RuntimeError):derive(w,p,o,platform='linux')

    def test_wrong_uid_is_rejected(self):
        w,p,o=fixture('502:0:82')
        with self.assertRaisesRegex(RuntimeError,'actual UID'):derive(w,p,o)

    def test_uid_is_an_exact_nonnegative_integer(self):
        for uid in [True,False,501.0,-1,'501']:
            with self.assertRaisesRegex(RuntimeError,'integer UID'):derive(*fixture(),uid=uid)

    def test_malformed_cf_is_rejected(self):
        for value in ['501:0','501:0:82:0','-501:0:82','501:-1:82','501:0:','501:0:0x',
                      '501:0:0x100000000','501:0:12345678901','501:0: 82','+501:0:82','501:0:8_2']:
            with self.subTest(value=value),self.assertRaises(RuntimeError):derive(*fixture(value))

    def test_changed_observation_is_rejected(self):
        for name in policy.OBSERVATIONS:
            w,p,o=fixture();o[name][policy.CF]='501:0:82'
            with self.assertRaisesRegex(RuntimeError,'environment changed'):derive(w,p,o)

    def test_missing_or_extra_observation_is_rejected(self):
        for change in ['missing','extra']:
            w,p,o=fixture()
            if change=='missing':del o[policy.OBSERVATIONS[0]]
            else:o['foreign']=dict(p)
            with self.assertRaisesRegex(RuntimeError,'complete preparation'):derive(w,p,o)

    def test_maps_reject_nonstring_or_invalid_entries(self):
        for bad in [{1:'a'},{'A':True},{'A':1},{'A':None},{'A\0':'x'},{'A':'x\0'},{'A=B':'x'},{'':'x'}]:
            w,p,o=fixture()
            with self.assertRaises(RuntimeError):derive(bad,p,o)

    def test_result_and_input_aliases_are_independent(self):
        w,p,o=fixture();proof=derive(w,p,o);before=copy.deepcopy(proof)
        w['PATH']='changed';p['PATH']='changed';o[policy.OBSERVATIONS[0]]['PATH']='changed'
        self.assertEqual(proof,before)
        proof['observations'][policy.OBSERVATIONS[0]]['PATH']='new'
        self.assertNotEqual(proof['observations'][policy.OBSERVATIONS[1]]['PATH'],'new')

    def test_validation_rejects_forged_or_extra_proof(self):
        for key,value in [('policy','foreign'),('uid',501.0),('launch_environment',{}),('extra',True)]:
            w,p,o=fixture();proof=derive(w,p,o);proof[key]=value
            with self.assertRaises(RuntimeError):policy.validate(w,proof)

    def test_validation_result_is_detached(self):
        w,p,o=fixture();proof=derive(w,p,o);result=policy.validate(w,proof)
        result['PATH']='foreign';self.assertEqual(proof['launch_environment']['PATH'],w['PATH'])

    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'duplicate'):policy.decode('{"PATH":"a","PATH":"b"}')


class Admission(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('_startup_original_controller_fixture',CONTROLLER)
        self.controller=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.controller)

    def reach(self, expected, observed):
        c=self.controller
        plan=dict(work=str(c.R/'.work/hir-options-hash-runtime-preflight-fixture'),phase='preflight',
            owner=str(c.R),capacity=dict(entry_gib=24,stop_gib=9,floor_gib=8,
                combined_namespace_bytes=14*2**30,evidence_bytes=256*2**20),
            launch_environment=expected,specification={'path':'/fixture/specification.json'})
        sentinel=Mock(side_effect=LookupError('admission passed; stop before specification/provider work'))
        monitor=SimpleNamespace(owned=object())
        with patch.object(c,'os',SimpleNamespace(environ=observed)),patch.object(c.Path,'cwd',return_value=c.R):
            try:
                c.Controller(plan=plan,inputs_sha256='0'*64,q=None,recipe=None,
                    reader=SimpleNamespace(reader=SimpleNamespace(monitor=object())),monitor=monitor,
                    check_frozen=Mock(),read_json=sentinel,read_bytes=Mock(),sha=Mock())
            finally:self.calls=sentinel.call_count

    def test_exact_plain_environment_reaches_next_read(self):
        with self.assertRaisesRegex(LookupError,'admission passed'):self.reach({'LANG':'C'},{'LANG':'C'})
        self.assertEqual(self.calls,1)

    def test_explicit_cf_environment_reaches_next_read(self):
        w,p,o=fixture();launch=derive(w,p,o)['launch_environment']
        with self.assertRaisesRegex(LookupError,'admission passed'):self.reach(launch,dict(launch))
        self.assertEqual(self.calls,1)

    def test_undeclared_startup_addition_fails_before_read(self):
        w,p,o=fixture();launch=derive(w,p,o)['launch_environment']
        with self.assertRaisesRegex(RuntimeError,'exact runtime launch context'):self.reach(w,launch)
        self.assertEqual(self.calls,0)

    def test_mutated_explicit_startup_value_fails_before_read(self):
        w,p,o=fixture();launch=derive(w,p,o)['launch_environment'];observed=dict(launch)
        observed[policy.CF]='501:0:83'
        with self.assertRaisesRegex(RuntimeError,'exact runtime launch context'):self.reach(launch,observed)
        self.assertEqual(self.calls,0)
