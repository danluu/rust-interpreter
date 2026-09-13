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


if __name__ == '__main__':
    unittest.main()
