"""Draft ordinary pure regressions. UNRUN; no compiler/provider calls."""
import argparse
import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

import host_build_profiles as h
import workflow_runtime_arms


def args(**values):
    d = dict(baseline_tool_key='a'*64, build_tool_opt_level=None,
             native_build_tool_opt_level=None, baseline_build_tool_opt_level=None,
             candidate_build_tool_opt_level=None)
    d.update(values)
    return SimpleNamespace(**d)


class HostProfiles(unittest.TestCase):
    def test_default_compatibility(self):
        self.assertIsNone(h.select(args()))
        self.assertEqual(h.namespace('run','baseline',None),'run:baseline')
        self.assertEqual(h.target(Path('/run'),'native',None),Path('/run/native'))

    def test_global_and_explicit_precedence(self):
        value=h.select(args(build_tool_opt_level=1,candidate_build_tool_opt_level=3,
                            native_build_tool_opt_level=0))
        self.assertEqual(value['modes'],dict(native=0,baseline=1,candidate=3))
        old=h.select(args(baseline_tool_key=None,build_tool_opt_level=2))
        self.assertEqual(old['modes'],dict(native=2,interpreter=2,jit=2))

    def test_ambient_profiles_cannot_leak(self):
        original={'PATH':'unchanged','RUSTFLAGS':'guest flags',
                  'CARGO_PROFILE_TEST_OPT_LEVEL':'z',
                  'CARGO_PROFILE_DEV_BUILD_OVERRIDE_OPT_LEVEL':'2',
                  'CARGO_PROFILE_TEST_BUILD_OVERRIDE_DEBUG_ASSERTIONS':'false',
                  'CARGO_PROFILE_RELEASE_OVERFLOW_CHECKS':'false'}
        before=copy.deepcopy(original)
        value=h.select(args(candidate_build_tool_opt_level=3))
        env=h.environment(original,value,'candidate')
        self.assertEqual(env,{'PATH':'unchanged','RUSTFLAGS':'guest flags',
            'CARGO_PROFILE_DEV_BUILD_OVERRIDE_OPT_LEVEL':'3',
            'CARGO_PROFILE_TEST_BUILD_OVERRIDE_OPT_LEVEL':'3'})
        self.assertEqual(original,before)
        self.assertEqual(h.environment(original,value,'baseline'),
                         {'PATH':'unchanged','RUSTFLAGS':'guest flags'})

    def test_profile_and_mode_cache_isolation(self):
        a=h.select(args(build_tool_opt_level=0))
        b=h.select(args(build_tool_opt_level=3))
        names={h.namespace('same',m,v) for m in ('baseline','candidate') for v in (a,b)}
        self.assertEqual(len(names),4)
        self.assertNotEqual(h.target('/work','native',a),h.target('/work','native',b))
        self.assertNotEqual(h.target('/work','check',b),h.target('/work','native',b))

    def test_typed_and_complete_selection(self):
        for bad in (True,-1,4,'3'):
            with self.subTest(bad=bad),self.assertRaises(RuntimeError):
                h.validate(dict(policy=h.POLICY,modes=dict(native=0,baseline=0,candidate=bad)),
                           ('native','baseline','candidate'))
        with self.assertRaises(RuntimeError):
            h.select(args(baseline_tool_key=None,native_build_tool_opt_level=3))

    def test_duplicate_cli_rejected(self):
        parser=argparse.ArgumentParser();h.add_arguments(parser)
        with self.assertRaises(SystemExit):
            parser.parse_args(['--candidate-build-tool-opt-level','3',
                               '--candidate-build-tool-opt-level','0'])

    def test_actual_call_profile_must_match(self):
        value=h.select(args(candidate_build_tool_opt_level=3))
        env=h.environment({},value,'candidate')
        h.verify_call({'host_build_profile':h.receipt(env)},value,'candidate')
        for bad in ({},{'host_build_profile':{}},
                    {'host_build_profile':dict(h.receipt(env),CARGO_PROFILE_TEST_BUILD_OVERRIDE_OPT_LEVEL='0')}):
            with self.subTest(bad=bad),self.assertRaises(RuntimeError):
                h.verify_call(bad,value,'candidate')

    def test_summary_and_aa_cannot_hide_profile_difference(self):
        value=h.select(args(baseline_build_tool_opt_level=0,candidate_build_tool_opt_level=3))
        report=dict(comparison={},host_build_profiles=value,native_control={'host_build_opt_level':None},
            tool_builds={m:{'host_build_opt_level':value['modes'][m]} for m in ('baseline','candidate')})
        h.verify_summary(report)
        report['aa_control']=True
        with self.assertRaises(RuntimeError):h.verify_summary(report)
        report['aa_control']=False;report['tool_builds']['candidate']['host_build_opt_level']=0
        with self.assertRaises(RuntimeError):h.verify_summary(report)
        report['tool_builds']['candidate']['host_build_opt_level']=3
        del report['native_control']['host_build_opt_level']
        with self.assertRaises(RuntimeError):h.verify_summary(report)
        report['native_control']['host_build_opt_level']=None
        report['tool_builds']['baseline']['host_build_opt_level']=False
        with self.assertRaises(RuntimeError):h.verify_summary(report)

    def test_ordinary_native_environment_preserves_host_only_override(self):
        path=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918/scripts/workflow_controls.py')
        spec=importlib.util.spec_from_file_location('original_native_controls',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        value=h.select(args(native_build_tool_opt_level=3))
        env=h.environment({'PATH':'unchanged'},value,'native')
        self.assertEqual(module.native_environment(env,'repository',[]),env)
        # The legacy explicit target-profile option remains a separate operation.
        legacy=module.native_environment(env,'o0-incremental',[])
        self.assertEqual(h.receipt(legacy),h.receipt(env))
        self.assertEqual(legacy['CARGO_PROFILE_TEST_OPT_LEVEL'],'0')

    def test_runtime_selection_keeps_exact_keys_with_host_profiles(self):
        value=args(build_tool_opt_level=3,runtime_compiler_key=None,std_mir_key=None,
            baseline_runtime_compiler_key='b'*64,candidate_runtime_compiler_key='b'*64,
            baseline_std_mir_key=None,candidate_std_mir_key=None,std_mir=False,
            batch=True,candidate_tool_key='a'*64,aa_control=True)
        self.assertEqual(h.select(value)['modes'],dict(native=3,baseline=3,candidate=3))
        selected=workflow_runtime_arms.select(value)
        self.assertEqual(selected['arms']['baseline']['runtime_key'],'b'*64)
        value.candidate_runtime_compiler_key='c'*64
        with self.assertRaises(RuntimeError):workflow_runtime_arms.select(value)


if __name__=='__main__':unittest.main(verbosity=2)
