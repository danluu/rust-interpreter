"""Tiny in-memory recipe fixtures; no provider or runtime module is imported.

These tests qualify only independent command/context reconstruction. They do
not claim actual E0080 rendering, loader behavior, or a completed installation.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import types
import unittest

SOURCE = Path(__file__).with_name('recipe.py')
SPEC = importlib.util.spec_from_file_location('runtime_audit04_recipe_fixture', SOURCE)
recipe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recipe)


def unavailable(*args, **kwargs):
    raise AssertionError('constructor, provider, or workload API called by pure reader')


def relative(name):
    path = Path(name)
    if not name or path.is_absolute() or str(path) != name or '..' in path.parts:
        raise ValueError('invalid fixture relative path')
    return name


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def probe_commands(rustc, sysroot, work):
    common = [str(rustc), str(work/'source.rs'), '--crate-type=lib', '--edition=2024',
              '--emit=metadata', '--error-format=json', '--sysroot', str(sysroot)]
    return [common+['-o', str(work/'local.rmeta')],
            common+['-Ztranslate-remapped-path-to-local-path=no', '-o', str(work/'virtual.rmeta')]]


class Recipe(unittest.TestCase):
    def setUp(self):
        self.owner = Path('/fixture/owner')
        self.work = self.owner/'.work/runtime'
        self.identity = dict(files={'bin/rustc': 'a'*64, 'bin/rustdoc': 'b'*64})
        self.runtime = types.SimpleNamespace(
            identity_for=lambda spec: copy.deepcopy(self.identity), digest=digest,
            relative=relative, NAMESPACE='runtime-compilers',
            OVERRIDES=('RUST_SYSROOT', 'RUSTC_FORCE_RUSTC_VERSION',
                       'RUSTC_OVERRIDE_VERSION_STRING', 'FORCE_RUSTC_VERSION'),
            RuntimeCompiler=unavailable, load_runtime_compiler=unavailable,
            install_runtime_compiler=unavailable)
        self.q = types.SimpleNamespace(runtime=self.runtime, probe_commands=probe_commands,
            preflight=unavailable, run_pair=unavailable, final_validator=unavailable)
        self.spec = dict(components=[dict(role='runtime', root='/fixture/provider')],
                         loader={'lib/libdriver.dylib': {}, 'bin/rustc': {}})
        self.env = dict(PATH='/fixture/offline:/usr/bin:/bin', TMPDIR='/fixture/owner/.work/runtime/tmp',
                        SDKROOT='/fixture/sdk', HOME='/fixture/home', LANG='C', PYTHONDONTWRITEBYTECODE='1')

    def preflight(self):
        return recipe.preflight_commands(self.q, self.spec, self.owner, self.work/'source-probe', self.env)

    def final(self):
        return recipe.installation_commands(self.q, self.spec, self.owner, self.work, self.env)

    def test_preflight_exact_two_candidates_and_outputs(self):
        rows = self.preflight()
        self.assertEqual(len(rows), 2)
        self.assertEqual([row['expected'] for row in rows], [[1], [1]])
        self.assertEqual([row['output'] for row in rows],
                         [str(self.work/'source-probe/commands'/str(i)) for i in range(2)])
        self.assertEqual(rows[0]['argv'][0], '/fixture/provider/bin/rustc')
        self.assertEqual(rows[0]['argv'][rows[0]['argv'].index('--sysroot')+1], '/fixture/provider')
        self.assertEqual(rows[0]['cwd'], str(self.work/'source-probe'))

    def test_complete_environment_and_original_are_preserved(self):
        before = copy.deepcopy(self.env)
        rows = self.preflight()
        expected = dict(before, RUSTC='/fixture/provider/bin/rustc', RUSTDOC='/fixture/provider/bin/rustdoc',
                        PATH='/fixture/provider/bin:'+before['PATH'])
        self.assertEqual([row['environment'] for row in rows], [expected, expected])
        self.assertEqual(self.env, before)
        rows[0]['environment']['HOME'] = 'changed fixture'
        self.assertEqual(rows[1]['environment'], expected)

    def test_final_sorted_loader_three_cli_two_source_commands(self):
        key, sysroot, rows = self.final()
        self.assertEqual(key, digest(self.identity))
        self.assertEqual(sysroot, self.owner/'.work/runtime-compilers'/key/'sysroot')
        self.assertEqual(len(rows), len(self.spec['loader'])+5)
        self.assertEqual([r['argv'] for r in rows[:2]],
            [['/usr/bin/otool', '-l', str(sysroot/name)] for name in sorted(self.spec['loader'])])
        self.assertEqual([r['argv'][1:] for r in rows[2:5]], [['-vV'], ['--print', 'sysroot'], ['-Zhelp']])
        self.assertEqual([r['expected'] for r in rows], [[0]]*5+[[1]]*2)
        self.assertEqual([r['output'] for r in rows[:5]], [str(self.work/'commands'/f'{i:03}') for i in range(5)])
        self.assertEqual([r['cwd'] for r in rows], [str(self.owner)]*5+[str(self.work/'source-probe')]*2)

    def test_final_environment_uses_only_derived_final_root(self):
        _, sysroot, rows = self.final()
        expected = dict(self.env, RUSTC=str(sysroot/'bin/rustc'), RUSTDOC=str(sysroot/'bin/rustdoc'),
                        PATH=str(sysroot/'bin')+':'+self.env['PATH'])
        self.assertTrue(all(r['environment'] == expected for r in rows))
        self.assertTrue(all('/fixture/provider' not in str(r) for r in rows))

    def test_absent_rustdoc_payload_does_not_add_rustdoc(self):
        del self.identity['files']['bin/rustdoc']
        self.assertNotIn('RUSTDOC', self.preflight()[0]['environment'])
        self.assertNotIn('RUSTDOC', self.final()[2][0]['environment'])

    def test_explicit_compiler_override_absence_required_in_both_phases(self):
        for key in (*self.runtime.OVERRIDES, 'RUSTC', 'RUSTDOC'):
            with self.subTest(key=key):
                self.env[key] = '/fixture/provider/bin/rustc'
                with self.assertRaises(RuntimeError): self.preflight()
                with self.assertRaises(RuntimeError): self.final()
                del self.env[key]

    def test_loader_override_rejected_in_both_phases(self):
        for key in ['LD_LIBRARY_PATH', 'DYLD_INSERT_LIBRARIES']:
            with self.subTest(key=key):
                self.env[key] = '/fixture/foreign'
                with self.assertRaises(RuntimeError): self.preflight()
                with self.assertRaises(RuntimeError): self.final()
                del self.env[key]

    def test_missing_path_and_nonstring_environment_rejected(self):
        del self.env['PATH']
        with self.assertRaises(RuntimeError): self.preflight()
        self.env['PATH'] = False
        with self.assertRaises(RuntimeError): self.final()

    def test_noncanonical_provider_or_unowned_work_rejected(self):
        self.spec['components'][0]['root'] = '/fixture/provider/../provider'
        with self.assertRaises(RuntimeError): self.preflight()
        self.spec['components'][0]['root'] = '/fixture/provider'
        self.work = Path('/fixture/foreign')
        with self.assertRaises(RuntimeError): self.preflight()
        with self.assertRaises(RuntimeError): self.final()

    def test_duplicate_runtime_component_rejected(self):
        self.spec['components'] *= 2
        with self.assertRaises(RuntimeError): self.preflight()

    def test_unsafe_loader_route_rejected(self):
        self.spec['loader']['../outside'] = {}
        with self.assertRaises(ValueError): self.final()

    def test_invalid_key_and_missing_probe_pair_rejected(self):
        self.runtime.digest = lambda identity: 'foreign'
        with self.assertRaises(RuntimeError): self.final()
        self.runtime.digest = digest
        self.q.probe_commands = lambda *args: []
        with self.assertRaises(RuntimeError): self.preflight()
        with self.assertRaises(RuntimeError): self.final()

    def test_no_constructor_probe_or_installation_api_used(self):
        self.preflight()
        self.final()


if __name__ == '__main__':
    unittest.main(verbosity=2)
