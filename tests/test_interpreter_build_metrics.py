"""Exercise the launcher's timing boundary without running Cargo or a VM."""
from contextlib import ExitStack, redirect_stderr, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import allocation_trace
import interpreter

checked_export_option = interpreter.require_export_option


class FakeClock:
    def __init__(self):
        self.wall = 100.0
        self.cpu = {resource.RUSAGE_SELF: [10.0, 20.0],
                    resource.RUSAGE_CHILDREN: [30.0, 40.0]}

    def advance(self, wall, launcher=(0.0, 0.0), children=(0.0, 0.0)):
        self.wall += wall
        for who, delta in [(resource.RUSAGE_SELF, launcher),
                           (resource.RUSAGE_CHILDREN, children)]:
            self.cpu[who] = [a + b for a, b in zip(self.cpu[who], delta)]

    def usage(self, who):
        user, system = self.cpu[who]
        return SimpleNamespace(ru_utime=user, ru_stime=system)


class InterpreterBuildMetricsTests(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        self.root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        self.tools = self.root / 'tools'
        self.tools.mkdir()
        (self.tools / 'ready.json').write_text(json.dumps({
            name: 'b' * 64 for name in interpreter.CURRENT_TOOL_BINARIES}))
        self.manifest = self.root / 'Cargo.toml'
        self.manifest.write_text('[package]\nname="fixture"\nversion="0.1.0"\n')
        self.artifact = self.root / 'libfixture.rmeta.rbc'
        self.artifact.write_bytes(b'selected bytecode')
        self.call_report = Path(str(self.artifact) + '.calls.json')
        self.selection_report = Path(str(self.artifact) + '.selection.json')
        self.entry_catalog = Path(str(self.artifact) + '.entries.json')
        self.call_report.write_text(json.dumps(dict(
            kind='unavailable-calls', schema_version=1, strict_frontend=True,
            trap_unsupported_calls=True, unavailable_calls=[],
            artifact_sha256=hashlib.sha256(self.artifact.read_bytes()).hexdigest())))
        self.clock = FakeClock()
        self.invocations = []
        self.cargo_returncode = 0
        self.vm_returncode = 0
        self.before_vm = None
        self.stderr = io.StringIO()
        self.stdout = io.StringIO()
        self.argv = ['interpreter.py', '--manifest-path', str(self.manifest),
                     '--package', 'fixture', '--tool-key', 'a' * 64,
                     '--entry', 'selected', '--jobs', '2', '--engine', 'jit',
                     '--jit-resumable-calls', '--jit-persistent-registers',
                     '--instruction-limit', '1234', '--allocation-limit', '23']
        stack.enter_context(patch.object(interpreter, 'ROOT', self.root))
        stack.enter_context(patch.object(interpreter, 'installed_tools', self.installed_tools))
        stack.enter_context(patch.object(interpreter, 'require_export_option'))
        stack.enter_context(patch.object(interpreter.fcntl, 'flock'))
        stack.enter_context(patch.object(interpreter.time, 'perf_counter', lambda: self.clock.wall))
        self.getrusage = stack.enter_context(patch.object(
            interpreter.resource, 'getrusage', side_effect=self.clock.usage))
        stack.enter_context(patch.object(interpreter.subprocess, 'run', self.run_process))
        stack.enter_context(patch.object(allocation_trace, 'selected_trace', self.selected_trace))
        original_open = Path.open

        def owned_open(path, *args, **kwargs):
            handle = original_open(path, *args, **kwargs)
            if path.name == 'invocation.lock':
                stack.callback(handle.close)
            return handle

        stack.enter_context(patch.object(Path, 'open', owned_open))
        original_read = Path.read_bytes

        def read_bytes(path):
            data = original_read(path)
            if path == self.artifact:
                self.clock.advance(3.0, launcher=(.125, .25))
            elif path == self.call_report:
                self.clock.advance(4.0, launcher=(.25, .5))
            elif path == self.selection_report:
                self.clock.advance(6.0, launcher=(.25, .5))
            elif path == self.entry_catalog:
                self.clock.advance(4.0, launcher=(.25, .5))
            return data

        stack.enter_context(patch.object(Path, 'read_bytes', read_bytes))

    def installed_tools(self, key):
        # Distinct pre-Cargo child work must count only toward build-to-ready.
        self.clock.advance(2.0, launcher=(1.0, 2.0), children=(3.0, 4.0))
        return self.tools, key

    def selected_trace(self, artifact):
        self.assertEqual(artifact, self.artifact)
        self.clock.advance(6.0, launcher=(.5, .75))
        return dict(kind='allocation-trace')

    def run_process(self, command, **kwargs):
        self.invocations.append((command, kwargs))
        if command[0] == 'cargo':
            self.clock.advance(5.0, launcher=(.5, .25), children=(7.0, 11.0))
            event = dict(reason='compiler-artifact', profile=dict(test='--profile' in command),
                         filenames=[str(self.root / 'libfixture.rmeta')])
            return subprocess.CompletedProcess(command, self.cargo_returncode, json.dumps(event))
        self.assertEqual(command[0], str(self.tools / 'rust-interp-vm'))
        self.before_vm = self.clock.wall
        # Large VM costs make accidental inclusion in either build metric clear.
        self.clock.advance(1000.0, launcher=(2.0, 3.0), children=(200.0, 300.0))
        return subprocess.CompletedProcess(command, self.vm_returncode)

    def launch(self, extra=(), stats=True, arguments=('7', '9')):
        argv = [*self.argv, *extra, *(['--', *arguments] if arguments else [])]
        with patch.object(sys, 'argv', argv), \
                patch.dict(os.environ, {'RUST_INTERP_LAUNCH_STATS': '1' if stats else '0'}), \
                redirect_stderr(self.stderr), redirect_stdout(self.stdout):
            return interpreter.main()

    def launch_stats(self):
        prefix = 'rust-interp-launch: '
        return [json.loads(line[len(prefix):]) for line in self.stderr.getvalue().splitlines()
                if line.startswith(prefix)]

    def discovery_report(self):
        names = ['selected', 'sibling']
        tests = [dict(name=name, native_name=name, function=name, descriptor='descriptor_' + name,
                      status='classified', harness='libtest', ignored=False, should_panic=False,
                      ordinary_test=True, ignore_reason=None, panic_message=None) for name in names]
        return dict(kind='test-discovery', schema_version=1, strict_frontend=True,
                    executed=False, harness='libtest', target='fixture', count=len(tests), tests=tests)

    def isolated_suite(self, filtered=False):
        self.argv = ['interpreter.py', '--manifest-path', str(self.manifest),
                     '--package', 'fixture', '--tool-key', 'a' * 64, '--test-body',
                     '--engine', 'jit', '--jit-resumable-calls', '--isolated-batch', 'prepared',
                     '--suite-workers', '2', '--suite-report', str(self.root / 'suite.json')]
        self.argv += ['--test-filter', ''] if filtered else ['--entry', 'selected', '--entry', 'sibling']
        (self.tools / 'capabilities.json').write_text(json.dumps(dict(
            schema_version=1, bytecode_version=5, tool_key='a' * 64,
            exporter_sha256='b' * 64, export_options=['entry-catalog', 'filtered-tests'])))
        digest = hashlib.sha256(b'selected bytecode').hexdigest()
        self.selection_report.write_text(json.dumps(dict(self.discovery_report(),
            kind='test-selection', filter=dict(pattern='', exact=False),
            selected=['selected', 'sibling'], skipped_ignored=[], artifact_sha256=digest)))
        self.entry_catalog.write_text(json.dumps(dict(schema_version=1, bytecode_version=5,
            artifact_sha256=digest, entries=[dict(name='selected'), dict(name='sibling')])))

    def test_ready_includes_launcher_checks_and_waited_build_children_but_excludes_vm(self):
        self.assertEqual(self.launch(['--allocation-trace', '--trap-unsupported-calls']), 0)
        [stats] = self.launch_stats()
        self.assertEqual(stats['build_to_ready_seconds'], 23.0)
        self.assertEqual(stats['build_to_ready_seconds'], self.before_vm - 100.0)
        self.assertEqual(stats['cargo_seconds'], 5.0)
        self.assertEqual(stats['cargo_cpu'], dict(user_seconds=7.0, system_seconds=11.0,
                                                total_seconds=18.0))
        self.assertEqual(stats['build_to_ready_cpu'], dict(
            user_seconds=12.5, system_seconds=19.0, total_seconds=31.5,
            self=dict(user_seconds=2.5, system_seconds=4.0, total_seconds=6.5),
            children=dict(user_seconds=10.0, system_seconds=15.0, total_seconds=25.0)))
        self.assertEqual(stats['execution_seconds'], 1000.0)
        self.assertEqual(stats['launcher_seconds'], 1023.0)
        self.assertEqual(stats['call_report_verify_seconds'], 7.0)
        self.assertEqual(stats['allocation_trace_verify_seconds'], 6.0)
        self.assertEqual(stats['artifact_hash_seconds'], 3.0)
        cargo, vm = self.invocations
        self.assertEqual(cargo[0], ['cargo', '+' + interpreter.TOOLCHAIN, 'check',
            '--manifest-path', str(self.manifest.resolve()), '--package', 'fixture',
            '--lib', '--locked', '--offline', '--jobs', '2',
            '--message-format=json-render-diagnostics'])
        self.assertEqual(vm[0], [str(self.tools / 'rust-interp-vm'), '--engine', 'jit',
            '--jit-resumable-calls', '--jit-persistent-registers', '--instruction-limit',
            '1234', '--allocation-limit', '23', str(self.artifact), '7', '9'])
        self.assertEqual(cargo[1]['env'], vm[1]['env'])
        self.assertNotIn('RUST_INTERP_LAUNCH_STATS', cargo[1]['env'])

    def test_missing_artifact_does_not_claim_ready_or_start_vm(self):
        self.artifact.unlink()
        with self.assertRaisesRegex(RuntimeError, 'did not select a valid bytecode sidecar'):
            self.launch()
        self.assertEqual(len(self.invocations), 1)
        self.assertEqual(self.launch_stats(), [])

    def test_function_reuse_is_explicit_and_applies_only_to_the_cargo_child(self):
        self.assertEqual(self.launch(['--function-cache', 'reuse']), 0)
        cargo, vm = self.invocations
        self.assertEqual(cargo[1]['env']['RUST_INTERP_FUNCTION_CACHE'], 'reuse')
        self.assertNotIn('RUST_INTERP_FUNCTION_CACHE', vm[1]['env'])
        interpreter.require_export_option.assert_called_once_with(
            self.tools, 'a' * 64, 'function-cache-reuse')
        self.assertEqual(self.launch_stats()[0]['function_cache'], 'reuse')

    def test_ambient_function_reuse_cannot_enable_the_default_route(self):
        with patch.dict(os.environ, {'RUST_INTERP_FUNCTION_CACHE': 'reuse'}):
            self.assertEqual(self.launch(), 0)
        self.assertTrue(all('RUST_INTERP_FUNCTION_CACHE' not in args['env']
                            for _, args in self.invocations))
        self.assertEqual(self.launch_stats()[0]['function_cache'], 'off')

    def test_function_reuse_does_not_launch_vm_after_a_failed_check(self):
        self.cargo_returncode = 101
        self.assertEqual(self.launch(['--function-cache', 'reuse']), 101)
        self.assertEqual(len(self.invocations), 1)
        self.assertEqual(self.invocations[0][0][0], 'cargo')
        self.assertIsNone(self.before_vm)
        self.assertEqual(self.launch_stats(), [])

    def test_function_reuse_rejects_an_older_installed_exporter(self):
        (self.tools / 'capabilities.json').write_text(json.dumps(dict(
            schema_version=1, bytecode_version=5, tool_key='a' * 64,
            exporter_sha256='b' * 64, export_options=['entry-catalog'])))
        with patch.object(interpreter, 'require_export_option', checked_export_option):
            with self.assertRaisesRegex(RuntimeError,
                    'installed exporter does not support --function-cache-reuse'):
                self.launch(['--function-cache', 'reuse'])
        self.assertEqual(self.invocations, [])

    def test_function_reuse_rejects_unqualified_modes_before_starting_work(self):
        for selection in [['--test-body', '--list-tests'],
                          ['--test-body', '--audit-entries', str(self.root / 'absent.json')],
                          ['--entry', 'selected', '--allocation-trace']]:
            with self.subTest(selection=selection):
                argv = ['interpreter.py', '--package', 'fixture',
                        '--function-cache', 'reuse', *selection]
                with patch.object(sys, 'argv', argv), redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as error:
                        interpreter.main()
                self.assertEqual(error.exception.code, 2)
        self.assertEqual(self.invocations, [])

    def test_failed_call_report_validation_does_not_claim_ready_or_start_vm(self):
        report = json.loads(self.call_report.read_text())
        report['artifact_sha256'] = '0' * 64
        self.call_report.write_text(json.dumps(report))
        with self.assertRaisesRegex(RuntimeError, 'incompatible unavailable-call report'):
            self.launch(['--trap-unsupported-calls'])
        self.assertEqual(len(self.invocations), 1)
        self.assertEqual(self.launch_stats(), [])

    def test_failed_allocation_trace_validation_does_not_claim_ready_or_start_vm(self):
        with patch.object(allocation_trace, 'selected_trace',
                          side_effect=RuntimeError('invalid allocation trace')):
            with self.assertRaisesRegex(RuntimeError, 'invalid allocation trace'):
                self.launch(['--allocation-trace'])
        self.assertEqual(len(self.invocations), 1)
        self.assertEqual(self.launch_stats(), [])

    def test_failed_cargo_does_not_claim_ready_or_start_vm(self):
        self.cargo_returncode = 19
        self.assertEqual(self.launch(), 19)
        self.assertEqual(len(self.invocations), 1)
        self.assertEqual(self.launch_stats(), [])

    def test_audit_only_command_does_not_claim_execution_readiness(self):
        selection = self.root / 'selection.json'
        selection.write_text(json.dumps(['selected']))
        audit = self.root / 'libfixture.rmeta.audit.json'
        audit.write_text(json.dumps(dict(kind='lowering-audit', schema_version=1,
            strict_frontend=True, executed=False,
            entries=[dict(entry='selected', status='lowered')])))
        self.argv = ['interpreter.py', '--manifest-path', str(self.manifest),
                     '--package', 'fixture', '--tool-key', 'a' * 64,
                     '--test-body', '--audit-entries', str(selection)]
        self.assertEqual(self.launch(arguments=()), 0)
        [stats] = self.launch_stats()
        self.assertIn('cargo_cpu', stats)
        self.assertNotIn('build_to_ready_seconds', stats)
        self.assertNotIn('build_to_ready_cpu', stats)
        self.assertEqual(len(self.invocations), 1)
        self.assertIsNone(self.before_vm)

    def test_list_tests_does_not_claim_execution_readiness(self):
        listing = self.root / 'libfixture.rmeta.tests.json'
        listing.write_text(json.dumps(self.discovery_report()))
        self.argv = ['interpreter.py', '--manifest-path', str(self.manifest),
                     '--package', 'fixture', '--tool-key', 'a' * 64,
                     '--test-body', '--list-tests']
        self.assertEqual(self.launch(arguments=()), 0)
        [stats] = self.launch_stats()
        self.assertEqual(stats['mode'], 'test-discovery')
        self.assertFalse(stats['executed'])
        self.assertIn('cargo_cpu', stats)
        self.assertNotIn('build_to_ready_seconds', stats)
        self.assertNotIn('build_to_ready_cpu', stats)
        self.assertEqual(len(self.invocations), 1)
        self.assertIsNone(self.before_vm)

    def test_filtered_suite_checks_are_inside_readiness_and_worker_execution_is_outside(self):
        self.isolated_suite(filtered=True)
        self.assertEqual(self.launch(arguments=()), 0)
        [stats] = self.launch_stats()
        # Tools + Cargo + selection/hash verification + two catalog reads +
        # artifact provenance. All suite workers start in the subsequent VM.
        self.assertEqual(stats['build_to_ready_seconds'], 27.0)
        self.assertEqual(stats['build_to_ready_seconds'], self.before_vm - 100.0)
        self.assertEqual(stats['test_selection_verify_seconds'], 9.0)
        self.assertEqual(stats['artifact_hash_seconds'], 3.0)
        self.assertEqual(stats['build_to_ready_cpu'], dict(
            user_seconds=12.5, system_seconds=19.25, total_seconds=31.75,
            self=dict(user_seconds=2.5, system_seconds=4.25, total_seconds=6.75),
            children=dict(user_seconds=10.0, system_seconds=15.0, total_seconds=25.0)))
        self.assertEqual(stats['cargo_cpu']['total_seconds'], 18.0)
        self.assertEqual(stats['execution_seconds'], 1000.0)
        self.assertEqual(stats['suite_workers_requested'], 2)
        self.assertEqual(len(self.invocations), 2)
        vm = self.invocations[1][0]
        self.assertEqual(vm[vm.index('--suite-workers') + 1], '2')
        self.assertEqual(vm[vm.index('--suite-catalog') + 1], str(self.entry_catalog))

    def test_invalid_isolated_entry_catalog_does_not_claim_ready_or_start_vm(self):
        self.isolated_suite()
        self.entry_catalog.write_text(json.dumps(dict(schema_version=1, bytecode_version=5,
            entries=[dict(name='different_selection')])))
        with self.assertRaisesRegex(RuntimeError, 'entry catalog does not match requested tests'):
            self.launch(arguments=())
        self.assertEqual(len(self.invocations), 1)
        self.assertEqual(self.launch_stats(), [])

    def test_invalid_filtered_selection_does_not_claim_ready_or_start_vm(self):
        self.isolated_suite(filtered=True)
        selection = json.loads(self.selection_report.read_text())
        selection['artifact_sha256'] = '0' * 64
        self.selection_report.write_text(json.dumps(selection))
        with self.assertRaisesRegex(RuntimeError, 'selected bytecode digest differs'):
            self.launch(arguments=())
        self.assertEqual(len(self.invocations), 1)
        self.assertEqual(self.launch_stats(), [])

    def test_vm_failure_preserves_ready_metrics_and_failure_exit(self):
        self.vm_returncode = 23
        self.assertEqual(self.launch(), 23)
        [stats] = self.launch_stats()
        self.assertEqual(stats['build_to_ready_seconds'], 10.0)
        self.assertEqual(stats['execution_seconds'], 1000.0)

    def test_stats_disabled_does_not_read_cpu_counters_or_emit_metrics(self):
        self.assertEqual(self.launch(stats=False), 0)
        self.getrusage.assert_not_called()
        self.assertEqual(len(self.invocations), 2)
        self.assertEqual(self.launch_stats(), [])


if __name__ == '__main__':
    unittest.main()
