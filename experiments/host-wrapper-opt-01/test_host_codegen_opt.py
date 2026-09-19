"""Pure publication, arm and real launcher transport tests; mocked children only."""
import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
sys.path[:0] = [str(HERE), str(R/'scripts'), str(R/'tests')]
import host_codegen_opt as policy
import interpreter
assert Path(interpreter.__file__).resolve() == HERE/'interpreter.py'
import test_runtime_tools as runtime_fixture
import runtime_tools
import std_mir


class HostCodegenLauncherTests(unittest.TestCase):
    mono = False
    run_process = runtime_fixture.RuntimeToolsTests.run_process
    launch = runtime_fixture.RuntimeToolsTests.launch
    save = runtime_fixture.RuntimeToolsTests.save
    runtime_launch = runtime_fixture.RuntimeToolsTests.runtime_launch

    def setUp(self):
        runtime_fixture.RuntimeToolsTests.setUp(self)
        self.capabilities['export_options'].append(policy.POLICY)
        self.capabilities['host_codegen_opt'] = copy.deepcopy(policy.CAPABILITY)
        self.query = '\n'.join([json.dumps(policy.CAPABILITY), str(self.compiler.sysroot), json.dumps(self.binding)])+'\n'
        policy.bind_recorded_wrapper_capability(self.binaries, self.capabilities, self.compiler, self.query)
        self.save()

    def invoke(self, mode):
        standard = (self.root/'std', self.compiler.host, 'e'*64,
                    dict(identity=dict(policy='metadata-sysroot-v2-shared-source-paths-release-backtrace')))
        with patch.object(std_mir, 'checked_std_mir', return_value=standard):
            return self.runtime_launch('--std-mir', '--std-mir-policy', 'source-paths-v2-shared',
                '--std-mir-key', 'e'*64, '--host-codegen-opt', mode)

    def test_off_on_off_real_launcher_preserves_profiles_and_separates_cache(self):
        paths = []
        with patch.dict(os.environ, {'CARGO_PROFILE_DEV_OPT_LEVEL': '1', 'OPT_LEVEL': '0', 'DEBUG': 'true'}):
            for mode in ['off', 'on', 'off']:
                self.invocations.clear()
                status, [receipt] = self.invoke(mode)
                self.assertEqual(status, 0)
                cargo, vm = self.invocations
                env = cargo[1]['env']; paths.append(env['CARGO_TARGET_DIR'])
                self.assertEqual(env['CARGO_PROFILE_DEV_OPT_LEVEL'], '1')
                self.assertFalse(any('BUILD_OVERRIDE' in k for k in env))
                self.assertEqual((env['OPT_LEVEL'], env['DEBUG']), ('0', 'true'))
                self.assertEqual(env.get(policy.ENVIRONMENT), 'on' if mode == 'on' else None)
                self.assertNotIn(policy.ENVIRONMENT, vm[1]['env'])
                self.assertEqual(env['RUST_INTERP_COMPILER_RUSTC'], str(self.compiler.rustc))
                self.assertEqual(env['RUSTC_WRAPPER'], str(self.tools/policy.WRAPPER))
                self.assertEqual(receipt.get('host_codegen_opt'), policy.receipt(self.capabilities) if mode == 'on' else None)
        self.assertEqual(paths[0], paths[2]); self.assertNotEqual(paths[0], paths[1])

    def test_unqualified_capability_refuses_before_any_child(self):
        del self.capabilities['host_codegen_wrapper']; self.save()
        with self.assertRaisesRegex(RuntimeError, 'matching combined'):
            self.invoke('on')
        self.assertEqual(self.invocations, [])

    def test_mismatched_physical_wrapper_or_runtime_refuses(self):
        for field in ['sha256', 'compiler_sysroot']:
            original = copy.deepcopy(self.capabilities)
            self.capabilities['host_codegen_wrapper'][field] = 'wrong'; self.save()
            with self.assertRaises(RuntimeError): self.invoke('on')
            self.capabilities = original; self.save()
        self.assertEqual(self.invocations, [])

    def test_legacy_flags_still_refuse_with_runtime(self):
        for flag in ['--host-proc-macro-opt', '--host-library-opt']:
            with self.assertRaises(SystemExit): self.runtime_launch(flag, 'on')
        self.assertEqual(self.invocations, [])

    def test_publication_query_requires_exact_policy_runtime_and_single_binding(self):
        for fault in range(5):
            caps = copy.deepcopy(self.capabilities); del caps['host_codegen_wrapper']
            lines = self.query.splitlines()
            if fault == 0:
                changed = dict(policy.CAPABILITY, opt_level=True); lines[0] = json.dumps(changed)
            elif fault == 1: lines[1] = '/other/sysroot'
            elif fault == 2: lines[2] = '{}'
            elif fault == 3: lines.append('extra')
            else: caps['host_codegen_wrapper'] = {}
            with self.assertRaises(RuntimeError):
                policy.bind_recorded_wrapper_capability(self.binaries, caps, self.compiler, '\n'.join(lines))


class HostCodegenArmTests(unittest.TestCase):
    def args(self, **changes):
        value = argparse.Namespace(baseline_host_codegen_opt='off', candidate_host_codegen_opt='on',
            batch=True, std_mir=True, baseline_tool_key='a'*64, candidate_tool_key='a'*64,
            build_tool_opt_level=None, runtime_compiler_key='b'*64, std_mir_key='c'*64,
            baseline_runtime_compiler_key=None, candidate_runtime_compiler_key=None,
            baseline_std_mir_key=None, candidate_std_mir_key=None, aa_control=False, expect_identical_bytecode=True)
        for k, v in changes.items(): setattr(value, k, v)
        return value

    def test_modes_default_and_namespace_are_compatible(self):
        self.assertIsNone(policy.select(self.args(baseline_host_codegen_opt=None, candidate_host_codegen_opt=None)))
        self.assertEqual(policy.namespace('old', 'off'), 'old')
        self.assertEqual(policy.arguments('off'), [])
        self.assertEqual(policy.arguments('on'), ['--host-codegen-opt', 'on'])
        self.assertNotEqual(policy.namespace('old', 'on'), 'old')

    def test_per_arm_selection_refuses_confounded_or_unpaired_settings(self):
        self.assertEqual(policy.select(self.args())['modes'], dict(baseline='off', candidate='on'))
        for change in [dict(candidate_host_codegen_opt=None), dict(candidate_tool_key='d'*64),
            dict(aa_control=True), dict(expect_identical_bytecode=False), dict(std_mir=False),
            dict(build_tool_opt_level=3), dict(runtime_compiler_key=None)]:
            with self.subTest(change=change), self.assertRaises(RuntimeError): policy.select(self.args(**change))
        self.assertEqual(policy.select(self.args(aa_control=True, baseline_host_codegen_opt='on'))['modes'],
                         dict(baseline='on', candidate='on'))

    def test_bind_rejects_guest_or_job_confound_before_reading_tools(self):
        selected=policy.select(self.args())
        with self.assertRaises(RuntimeError):policy.bind_comparison(selected,dict(baseline={'engine':'jit'},candidate={'engine':'interpreter'}),{},dict(baseline=2,candidate=2))
        with self.assertRaises(RuntimeError):policy.bind_comparison(selected,dict(baseline={},candidate={}),{},dict(baseline=2,candidate=1))

    def test_duplicate_mode_option_refuses(self):
        parser = argparse.ArgumentParser(); policy.add_arguments(parser)
        with self.assertRaises(SystemExit): parser.parse_args(['--baseline-host-codegen-opt=off', '--baseline-host-codegen-opt=on'])

    def test_saved_call_matches_bound_receipt_and_rejects_alias_or_mutation(self):
        wrapper = dict(sha256='a'*64, capability=copy.deepcopy(policy.CAPABILITY))
        receipt = dict(mode='on', policy=policy.POLICY, capability=copy.deepcopy(policy.CAPABILITY),
            wrapper=wrapper, cargo_profiles='unchanged', build_script_environment='unchanged', std_preparation='unchanged')
        selected = dict(policy=policy.POLICY, modes=dict(baseline='off', candidate='on'), receipt=receipt)
        call = dict(command=['python', 'interpreter.py', '--host-codegen-opt', 'on'],
            launch=dict(host_codegen_opt=copy.deepcopy(receipt), compiler_wrapper=dict(name=policy.WRAPPER, sha256='a'*64)))
        policy.verify_call(selected, 'candidate', call)
        for fault in range(4):
            bad = copy.deepcopy(call)
            if fault == 0: bad['command'][-2:] = ['--host-codegen-opt=on']
            elif fault == 1: bad['launch']['host_codegen_opt']['capability']['opt_level'] = 1
            elif fault == 2: bad['launch']['compiler_wrapper']['sha256'] = 'b'*64
            else: bad['command'] += ['--host-codegen-opt', 'on']
            with self.assertRaises(RuntimeError): policy.verify_call(selected, 'candidate', bad)
        with self.assertRaises(RuntimeError): policy.verify_call(selected, 'baseline', call)
        policy.verify_call(None, 'baseline', dict(command=['python', 'interpreter.py'], launch={}))

    def test_report_cannot_waive_rbc_or_change_runtime(self):
        runtime = dict(rustc='/runtime/bin/rustc', rustc_sha256='a'*64, compiler='rustc fixture', prepared_std={'key':'b'*64})
        roles = dict(runtime=dict(executable=dict(path=runtime['rustc'], sha256=runtime['rustc_sha256']),
            verbose_version=runtime['compiler'], default_sysroot='/runtime'))
        receipt = dict(mode='on', policy=policy.POLICY, capability=copy.deepcopy(policy.CAPABILITY),
            wrapper=dict(capability=copy.deepcopy(policy.CAPABILITY), compiler_roles=roles, compiler_sysroot='/runtime'))
        report = dict(batch=True, comparison=dict(identical_bytecode_required=True), runtime_compiler=runtime,
            tool_builds={m:dict(tool_key='c'*64) for m in policy.MODES}, custom_build_jobs=dict(baseline=2,candidate=2),
            host_codegen=dict(policy=policy.POLICY, modes=dict(baseline='off',candidate='on'),receipt=receipt))
        policy.validate_report(report)
        for fault in range(5):
            bad=copy.deepcopy(report)
            if fault==0:bad['comparison']['identical_bytecode_required']=False
            elif fault==1:bad['runtime_compiler']['rustc_sha256']='d'*64
            elif fault==2:bad['aa_control']=True
            elif fault==3:bad['custom_build_jobs']['candidate']=1
            else:bad['tool_builds']['candidate']['guest_rustflags']=['different']
            with self.assertRaises(RuntimeError):policy.validate_report(bad)


if __name__ == '__main__':
    unittest.main(verbosity=2)
