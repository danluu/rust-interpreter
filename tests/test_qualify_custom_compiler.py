"""Small fault checks for the real harness; no compiler/Cargo/VM is executed."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import qualify_custom_compiler as qualification


class QualificationTests(unittest.TestCase):
    def test_public_command_keeps_structured_compiler_messages_and_duplicate_units(self):
        command = qualification.public_command(Path('/owned/source'), 'host', Path('/owned/target'))
        formats = [arg for arg in command if isinstance(arg, str) and arg.startswith('--message-format=')]
        self.assertEqual(formats, ['--message-format=json'])
        message = dict(level='error', code={'code': 'E0308'}, message='mismatched types',
                       spans=[], children=[], rendered='error[E0308]: mismatched types')
        diagnostic = json.dumps(dict(reason='compiler-message', message=message))
        cargo_json = diagnostic + '\n' + diagnostic + '\n' + json.dumps(dict(reason='build-finished', success=False))
        core = qualification.core_diagnostics(qualification.diagnostic_records(cargo_json), Path('/owned'))
        self.assertEqual(len(core), 2)
        self.assertTrue(all(item['code'] == 'E0308' for item in core))
        rendered_only = json.dumps(dict(reason='build-finished', success=False))
        self.assertEqual(qualification.diagnostic_records(rendered_only), [])

    def test_real_cargo_route_parser_requires_both_target_roles_and_host_tools(self):
        wrapper, rustc = Path('/owned tools/wrapper'), Path('/owned compiler/rustc')
        lines = []
        for name, kind, target in [('custom_shared', 'rlib', ''),
                ('custom_shared', 'rlib', '--target=host'), ('custom_macros', 'proc-macro', ''),
                ('build_script_build', 'bin', ''), ('custom_compiler_fixture', 'lib', '--target host')]:
            lines.append(f"     Running `CARGO_PKG_NAME=fixture '{wrapper}' '{rustc}' --crate-name {name} "
                         f'--crate-type {kind} {target}`')
        routes = qualification.compiler_routes('\n'.join(lines), wrapper, rustc)
        qualification.validate_routes(routes, 'host')
        with self.assertRaisesRegex(RuntimeError, 'guest shared'):
            qualification.validate_routes([r for r in routes if not
                (r['crate'] == 'custom_shared' and r['target'])], 'host')
        with self.assertRaisesRegex(RuntimeError, 'different rustc'):
            qualification.compiler_routes('\n'.join(lines).replace(str(rustc), '/stock/rustc'), wrapper, rustc)

    def test_expected_compile_error_cannot_hide_execution_or_success(self):
        bad = dict(returncode=1, stderr='error[E0515]: cannot return reference', stdout='')
        qualification.validate_failure(bad, 'E0515')
        for change in [dict(returncode=0), dict(stdout='0\n'),
                       dict(stderr=bad['stderr'] + '\nrust-interp-launch: {}'),
                       dict(stderr='error[E0308]: mismatch')]:
            with self.assertRaises(RuntimeError):
                qualification.validate_failure(bad | change, 'E0515')

    def test_receipt_rejects_wrong_std_mode_and_replaced_bytecode(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            target = root / 'caches/off/target'; target.mkdir(parents=True)
            artifact = target / 'fixture.rbc'; artifact.write_bytes(b'checked bytecode')
            compiler = SimpleNamespace(key='compiler-key', rustc=root / 'rustc',
                identity={'files': {'bin/rustc': 'compiler-hash'}, 'compiler': 'rustc -vV'})
            std = dict(key='std-off', sysroot='/std/off', target='host')
            report = dict(tool_key='tools', custom_compiler=dict(key=compiler.key,
                rustc=str(compiler.rustc), rustc_sha256='compiler-hash', compiler='rustc -vV',
                stable_cgu_partitioning='off'), std_mir=std,
                toolchain_lookup=dict(mode='cached', outcome='owned-manifest'),
                workspace_path=str(target.parent), artifact_path=str(artifact),
                artifact_sha256=qualification.file_digest(artifact))
            row = dict(returncode=0, stderr='rust-interp-launch: ' + json.dumps(report))
            qualification.validate_launch(row, compiler, 'off', 'tools', std, root / 'caches')
            with self.assertRaisesRegex(RuntimeError, 'std namespace'):
                qualification.validate_launch(row, compiler, 'off', 'tools', std | {'key': 'std-on'}, root / 'caches')
            artifact.write_bytes(b'replaced')
            with self.assertRaisesRegex(RuntimeError, 'bytecode'):
                qualification.validate_launch(row, compiler, 'off', 'tools', std, root / 'caches')

    def test_fixture_is_local_and_has_distinct_actual_body_edits(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'fixture'
            qualification.fixture(source)
            self.assertEqual((source / 'shared/src/lib.rs').read_bytes(), qualification.shared_source(3))
            self.assertNotEqual(qualification.shared_source(3), qualification.shared_source(7))
            self.assertIn('codegen-units=2', (source / 'Cargo.toml').read_text())
            self.assertIn('[build-dependencies]', (source / 'Cargo.toml').read_text())
            self.assertIn('proc-macro=true', (source / 'macros/Cargo.toml').read_text())

    def test_structured_diagnostics_preserve_semantics_and_reject_stale_cache_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            message = dict(level='error', code={'code': 'E0308'}, message='mismatched types',
                spans=[dict(file_name=str(root / 'fixture.rs'), line_start=3, is_primary=True)],
                children=[dict(level='note', message='expected u32', spans=[])], rendered='colored output')
            cargo = json.dumps(dict(reason='compiler-message', message=message))
            cache = json.dumps(message | {'$message_type': 'diagnostic'})
            self.assertEqual(qualification.core_diagnostics(qualification.diagnostic_records(cargo), root),
                             qualification.core_diagnostics(qualification.diagnostic_records(cache), root))
            changed = message | {'message': 'different semantics'}
            self.assertNotEqual(qualification.core_diagnostics([message], root),
                                qualification.core_diagnostics([changed], root))
            target = root / 'target'; target.mkdir()
            output = target / 'output-lib-fixture'; output.write_text(cache)
            records, files = qualification.changed_diagnostics(target, {})
            self.assertEqual(records, qualification.diagnostic_records(cache))
            self.assertEqual(files, {str(output): cache})
            with self.assertRaisesRegex(RuntimeError, 'did not retain'):
                qualification.changed_diagnostics(target, qualification.diagnostic_files(target))


if __name__ == '__main__':
    unittest.main()
