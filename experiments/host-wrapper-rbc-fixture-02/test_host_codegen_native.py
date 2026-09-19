"""Combined host policy over the existing real macro/library correctness histories.

The external driver must authenticate sources/tools, bind the published runtime
and prepared std, retain artifacts, and hold the canonical workload lock.
This module builds neither tools nor standard libraries and measures no speedup.
"""
import json
import os
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
sys.path.insert(0, str(ROOT/'experiments/host-wrapper-opt-01'))
sys.path.insert(1, str(R/'tests'))
sys.path.insert(2, str(R/'scripts'))
import host_codegen_opt
import test_host_library_native as library_fixture
import test_host_proc_macro_native as macro_fixture
import workflow_io


@unittest.skipUnless(all(os.environ.get(name) for name in [
    'RUST_INTERP_TEST_EXPORTER','RUST_INTERP_TEST_WRAPPER','RUST_INTERP_TEST_RUSTC',
    'RUST_INTERP_TEST_CARGO','RUST_INTERP_TEST_STD_SYSROOT','RUST_INTERP_TEST_VM',
    'RUST_INTERP_TEST_ARTIFACT_DIR']), 'requires the separately bound published runtime/tool/std fixture')
class HostCodegenNativeTests(library_fixture.HostLibraryNativeTests):
    @classmethod
    def setUpClass(cls):
        macro_fixture.HostProcMacroNativeTests.setUpClass.__func__(cls)
        cls.cargo = Path(os.environ['RUST_INTERP_TEST_CARGO']).resolve(strict=True)

    def setUp(self):
        macro_fixture.HostProcMacroNativeTests.setUp(self)
        self.work = self.work.resolve(strict=True)
        self.sequence = 0
        self.command_sequence = 0
        self.generated_diagnostics = {}
        version = self.invoke([self.rustc,'-vV']); self.assert_success(version)
        self.host = next(line[6:] for line in version.stdout.splitlines() if line.startswith('host: '))
        probe = self.invoke([self.exporter,'--rust-interp-capabilities']); self.assert_success(probe)
        capabilities = json.loads(probe.stdout)
        self.assertIn(host_codegen_opt.POLICY,capabilities['export_options'])
        self.assertIn('compiler-argv-record-v1',capabilities['export_options'])
        self.assertEqual(capabilities['host_codegen_opt'],host_codegen_opt.CAPABILITY)
        self.compiled_sysroot = capabilities['compiler_sysroot']
        self.assertEqual(Path(self.compiled_sysroot),self.rustc.parent.parent)
        roles = capabilities['compiler_roles']
        self.assertEqual(roles['runtime']['executable']['path'],str(self.rustc))
        self.assertEqual(roles['runtime']['verbose_version'],version.stdout)
        probe = self.invoke([self.wrapper,'--rust-interp-host-codegen-capability']); self.assert_success(probe)
        lines = probe.stdout.splitlines()
        self.assertEqual(len(lines),3)
        self.assertEqual(json.loads(lines[0]),host_codegen_opt.CAPABILITY)
        self.assertEqual(lines[1],self.compiled_sysroot)
        self.assertEqual(json.loads(lines[2]),roles)

    def invoke(self, command, env=None):
        actual = self.base_env if env is None else env
        self.command_sequence += 1
        directory = self.work/'commands'/f'{self.command_sequence:04d}'
        directory.mkdir(parents=True)
        command = list(map(str,command))
        if command[0] == str(self.cargo):
            # Keep complete structured compiler diagnostics for the equality
            # check below. Cargo's json-render-diagnostics format instead sends
            # rendered diagnostics to stderr and omits compiler-message events.
            self.assertEqual(command.count('--message-format=json-render-diagnostics'),1)
            command = ['--message-format=json' if arg == '--message-format=json-render-diagnostics'
                       else arg for arg in command]
        child,stdout,stderr = workflow_io.capture(command,cwd=self.work,
            env=actual,receipt_path=directory/'record.json',
            receipt=dict(environment=actual,benchmark=False,scope='real host-policy correctness'))
        (directory/'stdout').write_text(stdout)
        (directory/'stderr').write_text(stderr)
        # Existing fixture assertions consume the ordinary subprocess fields.
        from types import SimpleNamespace
        return SimpleNamespace(returncode=child.returncode,stdout=stdout,stderr=stderr)

    @staticmethod
    def diagnostics(result):
        # Compare complete diagnostic objects, including rendered text and all
        # spans/children; keep non-diagnostic tool messages in the raw receipts.
        values = []
        for line in result.stderr.splitlines():
            if line.startswith('{'):
                value = json.loads(line)
                if value.get('$message_type') == 'diagnostic':
                    code = value.get('code')
                    values.append((value['level'],code.get('code') if code else None,
                        value['message'],value))
        return values

    def environment(self, mode):
        self.assertIn(mode,['off','on'])
        return dict(self.base_env,RUST_INTERP_STD_SYSROOT=str(self.rustc.parent.parent),
            RUST_INTERP_STD_TARGET=self.host,RUST_INTERP_EXPORT_PACKAGE='selected_elsewhere',
            CARGO_PKG_NAME='fixture_dependency',RUST_INTERP_HOST_CODEGEN_OPT=mode,
            RUST_INTERP_COMPILER_RUSTC=str(self.rustc),RUST_INTERP_STABLE_CGU_PARTITIONING='off',
            RUST_INTERP_FUNCTION_CACHE='auto')

    def assert_forwarded(self,path,original,mode,*,cwd,selected=False,std=None):
        fields = path.read_bytes().decode().split('\0')
        self.assertEqual(fields[:4],['rust-interp-compiler-argv-v1',
            'exported' if selected else 'native',self.compiled_sysroot,str(cwd)])
        self.assertEqual(fields[-1],'')
        self.assertEqual(original[0],str(self.rustc))
        kinds = self.values(original,'--crate-type')
        target = self.values(original,'--target')
        library = kinds in [['lib'],['rlib']]
        macro = kinds == ['proc-macro']
        expected = list(original)+['-Zstable-cgu-partitioning=no']
        if target:
            self.assertEqual(target,[self.host])
            self.assertFalse(self.values(original,'--sysroot'))
            expected += ['--sysroot',str(std)]
        if library:
            expected.append('-Zalways-encode-mir=yes')
        linked = any(emit.partition('=')[0] == 'link'
            for value in self.values(original,'--emit') for emit in value.split(','))
        eligible = (library or macro) and linked and not target and not selected and '--test' not in original
        if mode == 'on' and eligible:
            settings = {}
            for i,arg in enumerate(original):
                if arg == '-C' or arg.startswith('-C'):
                    value = original[i+1] if arg == '-C' else arg[2:]
                    name,separator,value = value.partition('=')
                    if not separator:
                        self.assertEqual(name,'prefer-dynamic'); value='yes'
                    settings[name.replace('_','-')] = value
            self.assertNotIn('opt-level',settings); self.assertNotIn('lto',settings)
            expected += ['-Copt-level=3','-Zmir-opt-level=1','-Clto=off']
            if 'debug-assertions' not in settings:
                expected.append('-Cdebug-assertions=yes')
            if 'overflow-checks' not in settings:
                debug = settings.get('debug-assertions','yes')
                self.assertIn(debug,['yes','no','true','false','y','n','on','off'])
                expected.append('-Coverflow-checks='+('no' if debug in ['no','false','n','off'] else 'yes'))
        self.assertEqual(fields[4:-1],expected,str(path))
        return eligible

    def macro(self,source,mode,env,extra=()):
        self.sequence += 1
        records = self.work/'macro-final-argv'/str(self.sequence)
        if mode != 'stock':
            records.mkdir(parents=True)
            env = dict(env,RUST_INTERP_COMPILER_ARGV_RECORD_DIR=str(records))
        result,artifact = macro_fixture.HostProcMacroNativeTests.macro(self,source,mode,env,extra)
        if mode != 'stock':
            paths = list(records.glob('*.argv'));self.assertEqual(len(paths),1)
            receipt = json.loads((self.work/'commands'/f'{self.command_sequence:04d}'/'record.json').read_text())
            self.assertEqual(receipt['command'][0],str(self.wrapper))
            self.assertTrue(self.assert_forwarded(paths[0],receipt['command'][1:],mode,cwd=self.work))
        return result,artifact

    test_uncalled_macro_errors_and_restoration = macro_fixture.HostProcMacroNativeTests.test_uncalled_errors_and_restoration_match_pinned_native_compiler
    test_macro_cfg_debug_and_overflow_checks = macro_fixture.HostProcMacroNativeTests.test_macro_cfg_debug_and_overflow_checks_match_explicit_profile_settings

    def cargo_run(self,mode,state,std,*,expect_failure=False):
        # Reuse the library fixture's source generation/history and preservation,
        # but the combined policy also makes the macro eligible. The original
        # final-role assertion is retained in a dedicated adapted method below.
        records = self.work/'final-argv'/mode/state
        records.mkdir(parents=True)
        original_env = self.base_env
        self.base_env = dict(original_env,RUST_INTERP_COMPILER_ARGV_RECORD_DIR=str(records))
        try:
            bytecode = macro_fixture.HostProcMacroNativeTests.cargo_run(
                self,mode,state,std,expect_failure=expect_failure)
        finally:
            self.base_env = original_env
        if expect_failure:
            diagnostic_stdout = (self.work/'commands'/f'{self.command_sequence:04d}'/'stdout').read_text()
            diagnostics = [event['message'] for line in diagnostic_stdout.splitlines()
                if line.startswith('{') and (event := json.loads(line)).get('reason') == 'compiler-message']
            self.assertTrue(any((d.get('code') or {}).get('code') == 'E0308' for d in diagnostics))
            self.generated_diagnostics[(state,mode)] = diagnostics
            if mode != 'stock':
                self.assertEqual(diagnostics,self.generated_diagnostics[(state,'stock')])
        if bytecode is not None:
            artifact = self.work/'bytecode'/mode/(state+'.rbc')
            artifact.parent.mkdir(parents=True,exist_ok=True);artifact.write_bytes(bytecode)
            self.assert_success(self.invoke([self.vm,'--engine','jit',artifact]))
        if mode == 'stock':
            self.assertEqual(list(records.iterdir()),[])
            return bytecode
        roles = []
        for original in sorted((self.work/'traces'/mode/state).glob('*.json')):
            row = json.loads(original.read_text());args = row['argv']
            if '--crate-name' not in args or args[args.index('--crate-name')+1] == '___':
                continue
            selected = self.values(args,'--crate-name') == ['proc_opt_fixture'] and '--test' in args
            path = records/(('exported' if selected else 'native')+'-'+str(row['pid'])+'.argv')
            self.assertTrue(path.is_file(),str(path))
            eligible = self.assert_forwarded(path,args,mode,cwd=Path(row['cwd']),selected=selected,std=std)
            roles.append(dict(name=self.values(args,'--crate-name'),eligible=eligible,
                guest=bool(self.values(args,'--target')),selected=selected,raw_argv=str(path)))
        if state == 'original':
            self.assertTrue(any(r['name']==['proc_opt_shared'] and r['eligible'] for r in roles))
            self.assertTrue(any(r['name']==['proc_opt_shared'] and r['guest'] for r in roles))
            self.assertTrue(any(r['name']==['build_script_build'] and not r['eligible'] for r in roles))
            self.assertTrue(any(r['name']==['proc_opt_macros'] and r['eligible'] for r in roles))
            self.assertTrue(any(r['selected'] for r in roles))
        (records/'checked-roles.json').write_text(json.dumps(roles,indent=2)+'\n')
        return bytecode


if __name__ == '__main__':
    unittest.main()
