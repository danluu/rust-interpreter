"""Unrun source-only controls; mock all Cargo/compiler/VM processes."""
from contextlib import ExitStack, redirect_stderr
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import frontend_workers
import interpreter


class FrontendWorkersTests(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        self.root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        self.tools = self.root / 'tools'
        self.tools.mkdir()
        self.key = 'a' * 64
        self.manifest = {name: 'b' * 64 for name in interpreter.CURRENT_TOOL_BINARIES}
        (self.tools/'ready.json').write_text(json.dumps(self.manifest))
        self.caps = dict(schema_version=1, bytecode_version=5, tool_key=self.key,
            exporter_sha256='b' * 64,
            export_options=['frontend-workers-v1', 'function-cache-auto'],
            frontend_workers=frontend_workers.CAPABILITY,
            frontend_worker_wrapper=dict(sha256='b' * 64, capability=frontend_workers.CAPABILITY))
        self.save_caps()
        (self.root/'Cargo.toml').write_text('[package]\nname="fixture"\nversion="0.0.0"\n')
        (self.root/'selected.rmeta.rbc').write_bytes(b'checked-bytecode')
        self.calls = []
        self.returncode = 0
        stack.enter_context(patch.dict(os.environ, {'RUST_INTERP_LAUNCH_STATS': '1'}, clear=True))
        stack.enter_context(patch.object(interpreter, 'ROOT', self.root))
        self.installed = stack.enter_context(patch.object(interpreter, 'installed_tools', return_value=(self.tools,self.key)))
        stack.enter_context(patch.object(interpreter.subprocess, 'run', self.process))

    def save_caps(self):
        (self.tools/'capabilities.json').write_text(json.dumps(self.caps))

    def process(self, command, **kwargs):
        self.calls.append((command,kwargs))
        if command[0] == 'cargo':
            event = dict(reason='compiler-artifact', profile=dict(test=False),
                         filenames=[str(self.root/'selected.rmeta')])
            return subprocess.CompletedProcess(command,self.returncode,json.dumps(event))
        self.assertEqual(command[0],str(self.tools/'rust-interp-vm'))
        return subprocess.CompletedProcess(command,0)

    def launch(self, *flags):
        output = io.StringIO()
        argv = ['interpreter.py','--manifest-path',str(self.root/'Cargo.toml'),
            '--package','fixture','--entry','selected','--tool-key',self.key,*flags]
        with patch.object(sys,'argv',argv), redirect_stderr(output):
            status = interpreter.main()
        reports = [json.loads(line.removeprefix('rust-interp-launch: '))
                   for line in output.getvalue().splitlines() if line.startswith('rust-interp-launch: ')]
        return status,reports

    def test_modes_are_isolated_and_only_cargo_receives_explicit_workers(self):
        targets = []
        for flags in [(), ('--frontend-workers','1'), ('--frontend-workers','2'), ('--frontend-workers','1')]:
            self.calls.clear()
            status,reports = self.launch(*flags,'--jobs','2','--function-cache','auto')
            self.assertEqual(status,0)
            cargo,vm = self.calls
            self.assertEqual(cargo[0][cargo[0].index('--jobs')+1],'2')
            self.assertEqual(cargo[1]['env']['RUST_INTERP_FUNCTION_CACHE'],'auto')
            targets.append(cargo[1]['env']['CARGO_TARGET_DIR'])
            self.assertNotIn('RUST_INTERP_FRONTEND_WORKERS',vm[1]['env'])
            if flags:
                self.assertEqual(cargo[1]['env']['RUST_INTERP_FRONTEND_WORKERS'],flags[1])
                self.assertEqual(reports[0]['frontend_workers']['compiler_arg'],'-Zthreads='+flags[1])
            else:
                self.assertNotIn('RUST_INTERP_FRONTEND_WORKERS',cargo[1]['env'])
        self.assertEqual(len(set(targets)),3)
        self.assertEqual(targets[1],targets[3])

    def test_omission_keeps_legacy_tools_and_ignores_ambient_worker_setting(self):
        (self.tools/'capabilities.json').unlink()
        with patch.dict(os.environ,{'RUST_INTERP_FRONTEND_WORKERS':'2'}):
            self.assertEqual(self.launch()[0],0)
        self.assertTrue(all('RUST_INTERP_FRONTEND_WORKERS' not in kw['env'] for _,kw in self.calls))
        self.calls.clear()
        with self.assertRaises(RuntimeError):self.launch('--frontend-workers','1')
        self.assertEqual(self.calls,[])

    def test_capability_requires_matching_exporter_wrapper_and_compiler(self):
        for field in ['exporter_sha256','frontend_worker_wrapper','frontend_workers']:
            original = self.caps[field]
            self.caps[field] = 'wrong' if field == 'exporter_sha256' else {}
            self.save_caps()
            with self.assertRaises(RuntimeError):self.launch('--frontend-workers','2')
            self.caps[field] = original
        self.assertEqual(self.calls,[])

    def test_publication_binds_exact_wrapper_capability_and_preserves_legacy(self):
        caps = dict(self.caps)
        caps.pop('frontend_worker_wrapper')
        probe = subprocess.CompletedProcess([],0,json.dumps(frontend_workers.CAPABILITY))
        with patch.object(frontend_workers.subprocess,'run',return_value=probe) as run:
            frontend_workers.bind_wrapper_capability(self.tools,self.manifest,caps)
            self.assertEqual(caps['frontend_worker_wrapper'],self.caps['frontend_worker_wrapper'])
            self.assertEqual(run.call_args.args[0],
                [str(self.tools/'rust-interp-rustc-wrapper'),'--rust-interp-frontend-worker-capability'])
            probe.stdout = '{}'
            with self.assertRaises(RuntimeError):
                frontend_workers.bind_wrapper_capability(self.tools,self.manifest,caps)
            run.reset_mock()
            frontend_workers.bind_wrapper_capability(self.tools,self.manifest,dict(export_options=[]))
            run.assert_not_called()

    def test_conflicting_environment_fails_before_loading_tools(self):
        for name,value in [('RUSTFLAGS','-Zthreads=2'),('CARGO_ENCODED_RUSTFLAGS','-Z\x1fthreads=1'),
                ('CARGO_TARGET_AARCH64_APPLE_DARWIN_RUSTFLAGS','--jobs-frontend=2'),
                ('RUSTFLAGS','-j2'),('RUSTFLAGS','@flags'),('RUSTC','/other/rustc'),
                ('RUST_INTERP_HOST_PROC_MACRO_OPT','3'), ('RUSTFLAGS','-Zcache-proc-macros=yes'),
                ('RUST_INTERP_COMPILER_ARGV_RECORD_DIR','/recording'),
                ('RUST_INTERP_STABLE_MONO_CGU_PARTITIONING','on')]:
            with self.subTest(name=name,value=value), patch.dict(os.environ,{name:value}):
                with self.assertRaises(SystemExit):self.launch('--frontend-workers','2')
        self.installed.assert_not_called()
        self.assertEqual(self.calls,[])

    def test_native_settings_are_preserved_and_failed_check_never_runs_vm(self):
        flags = '--jobs-backend=2 --jobs-linker=1 -Copt-level=1 -Ccodegen-units=16'
        with patch.dict(os.environ,{'RUSTFLAGS':flags}):
            self.returncode = 101
            self.assertEqual(self.launch('--frontend-workers','2')[0],101)
        self.assertEqual(len(self.calls),1)
        self.assertEqual(self.calls[0][1]['env']['RUSTFLAGS'],flags)

    def test_borrowck_combination_and_invalid_counts_fail_before_tools(self):
        for flags in [('--frontend-workers','2','--borrowck-cache','reuse'),
                      ('--frontend-workers','0'),('--frontend-workers','3'),
                      ('--frontend-workers','2','--stable-mono-cgu-partitioning','off'),
                      ('--frontend-workers','2','--cargo-key','a'*64)]:
            with self.assertRaises(SystemExit):self.launch(*flags)
        self.installed.assert_not_called()


if __name__ == '__main__':
    unittest.main()
