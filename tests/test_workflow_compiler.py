"""Compiler configuration cannot alter setup or mislabel saved edited builds."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import bench_e2e_workflow as workflow
import workflow_compiler as compiler
import test_build_workflow as fixture

KEY='c'*64
STD='d'*64
FLAGS=['-Zhir-body-cache-reuse=false','--remap-path-prefix=/space path=/virtual']
RUNTIME=dict(key=KEY,policy='owned-native-runtime-compiler-v1',rustc='/installed/rustc',
             rustc_sha256='e'*64,compiler='actual rustc version')
PREPARED=dict(key=STD,sysroot='/installed/std',target='aarch64-apple-darwin')


class CompilerConfigurationTests(unittest.TestCase):
    def test_explicit_options_reject_implicit_builds_before_setup(self):
        complete=['--runtime-compiler-key',KEY,'--baseline-tool-key','a'*64,'--candidate-tool-key','a'*64,'--batch']
        for args in [complete[:-1], ['--runtime-compiler-key',KEY],complete+['--std-mir'],
                     complete+['--std-mir-key',STD],complete+['--build-tool-opt-level','1'],
                     ['--std-mir-key',STD],['--baseline-guest-rustflag=-Zhir-body-cache-reuse=false'],
                     ['--guest-rustflag=one\x1ftwo']]:
            with self.subTest(args=args),patch.object(sys,'argv',['workflow',*args]), \
                    patch.object(workflow,'checked_tools') as tools, \
                    patch.object(workflow,'capture') as capture, \
                    contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                workflow.main()
            tools.assert_not_called();capture.assert_not_called()

    def test_encoded_arguments_preserve_spaces_and_default_transport(self):
        base={'HOME':'/home'}
        env=compiler.flag_environment(base,FLAGS,True)
        self.assertEqual(env['CARGO_ENCODED_RUSTFLAGS'],'\x1f'.join(FLAGS))
        self.assertEqual(base,{'HOME':'/home'})
        self.assertEqual(compiler.flag_environment(base,[]),base)
        self.assertEqual(compiler.flag_environment(base,['-Zmir-opt-level=3'])['RUSTFLAGS'],'-Zmir-opt-level=3')
        for flags in [[''],['a\x00b'],['a\x1fb']]:
            with self.assertRaises(RuntimeError):compiler.rustflags(flags)


class RuntimeHistoryTests(unittest.TestCase):
    setUp=fixture.BuildWorkflowVerifierTests.setUp
    make_report=fixture.BuildWorkflowVerifierTests.make_report
    verify=fixture.BuildWorkflowVerifierTests.verify

    def configure(self,flags=FLAGS):
        self.report['runtime_compiler']=dict(RUNTIME,prepared_std=PREPARED)
        self.report['std_mir']=dict(key=STD)
        self.report['guest_rustflag_encoding']='launcher-arguments'
        for mode in ['baseline','candidate']:
            self.report['tool_builds'][mode]['guest_rustflags']=list(flags)
        for row in self.rows:
            if row['mode']=='native':continue
            call=row['calls'][0]
            call['command']+=compiler.arguments(KEY,STD)+['--std-mir']+['--rustflag='+flag for flag in flags]
            call['launch'].update(custom_compiler=dict(RUNTIME,stable_cgu_partitioning='off'),
                std_mir=PREPARED.copy(),std_mir_policy='metadata-sysroot-v2-shared-source-paths-release-backtrace',
                application_rustflags=list(flags))
            lines=call['stderr'].splitlines()
            call['stderr']='\n'.join(line for line in lines if not line.startswith('rust-interp-launch: '))+'\n'
            call['stderr']+='rust-interp-launch: '+json.dumps(call['launch'])+'\n'

    def test_complete_runtime_history_is_verified(self):
        self.configure()
        self.assertEqual(self.verify()['commands'],66)

    def test_encoded_custom_flags_and_native_check_floor_remain_separate(self):
        self.report['guest_rustflag_encoding']='cargo-unit-separator'
        self.report['check_floor']={}
        self.report['native_control'].update(rustflags=['-Cdebuginfo=1'],test_threads='default')
        for mode in ['baseline','candidate']:
            self.report['tool_builds'][mode]['guest_rustflags']=list(FLAGS)
        for row in self.rows:
            row['calls'][0]['encoded_rustflags']='-Cdebuginfo=1' if row['mode']=='native' else '\x1f'.join(FLAGS)
        checks=[];previous=None
        for order in self.report['mode_orders']:
            row=next(r for r in self.rows if r['cycle']==order['cycle'] and r['state']==order['state'])
            checks.append(dict(cycle=row['cycle'],state=row['state'],phase=row['phase'],
                source_sha256=row['source_sha256'],previous_source_sha256=previous,
                returncode=0,seconds=1.0,cpu_seconds=2.0,cpu=fixture.cpu(1.0,1.0),stdout='',
                command=['cargo','+nightly','check','--jobs','2','--profile','test']))
            previous=row['source_sha256']
        (self.raw/'check-records.json').write_text(json.dumps(checks))
        self.assertEqual(self.verify()['check_commands'],22)
        call=next(row for row in self.rows if row['mode']=='candidate')['calls'][0]
        call['encoded_rustflags']='-Cdebuginfo=1'
        with self.assertRaisesRegex(RuntimeError,'encoded guest compiler flags differ'):self.verify()

    def test_different_runtime_key_binary_version_or_std_is_rejected(self):
        self.configure()
        call=next(row for row in self.rows if row['mode']=='candidate')['calls'][0]
        for field in ['key','rustc_sha256','compiler']:
            original=copy.deepcopy(call)
            call['launch']['custom_compiler'][field]='different'
            with self.subTest(field=field),self.assertRaisesRegex(RuntimeError,'runtime compiler differs'):self.verify()
            call.clear();call.update(original)
        call['launch']['std_mir']['key']='f'*64
        with self.assertRaisesRegex(RuntimeError,'standard library differs'):self.verify()

    def test_flags_must_match_argv_and_actual_launch_without_ambient_injection(self):
        self.configure()
        call=next(row for row in self.rows if row['mode']=='candidate')['calls'][0]
        for change in [lambda c:c['command'].pop(),
                       lambda c:c['launch']['application_rustflags'].append('-Zother'),
                       lambda c:c.update(encoded_rustflags='-Zother')]:
            original=copy.deepcopy(call);change(call)
            with self.assertRaisesRegex(RuntimeError,'application compiler arguments differ'):self.verify()
            call.clear();call.update(original)

    def test_independent_compiler_flag_expectations_are_preserved(self):
        self.configure()
        self.report.pop('aa_control')
        self.report['comparison']['identical_bytecode_required']=False
        expected={mode:list(FLAGS) for mode in ['baseline','candidate']}
        expected['candidate'][0]='-Zhir-body-cache-reuse=true'
        self.report['tool_builds']['candidate']['guest_rustflags']=list(expected['candidate'])
        for row in self.rows:
            if row['mode']!='candidate':continue
            call=row['calls'][0]
            call['command']=[arg.replace('--rustflag=-Zhir-body-cache-reuse=false',
                            '--rustflag=-Zhir-body-cache-reuse=true') for arg in call['command']]
            call['launch']['application_rustflags']=list(expected['candidate'])
            lines=call['stderr'].splitlines()
            call['stderr']='\n'.join(line for line in lines if not line.startswith('rust-interp-launch: '))+'\n'
            call['stderr']+='rust-interp-launch: '+json.dumps(call['launch'])+'\n'
        self.verify() # Save complete synthetic history.
        result=fixture.verifier.verify(self.report,compiler_flags=expected)
        self.assertEqual(result['compiler_comparison']['expected_guest_flags'],expected)
        expected['candidate'][0]='-Zunplanned=true'
        with self.assertRaisesRegex(RuntimeError,'independent expectation'):
            fixture.verifier.verify(self.report,compiler_flags=expected)


if __name__=='__main__':unittest.main()
