"""Pure selection/argument tests; no provider modules or std commands are loaded."""
import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def source(name):
    spec = importlib.util.spec_from_file_location('_std07_test_'+name, HERE/(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


factory = source('imports')
cli = source('std_cli')


class AdapterTests(unittest.TestCase):
    def plan(self):
        value = dict(status='prepared-unexecuted', owner=str(factory.R),
            work=str(factory.R/'.work/hir-options-hash-runtime-std-supervision-07-01'),
            run_work=str(factory.R/'.work'/factory.RUN_ID), namespace=factory.NAMESPACE,
            runtime_key='a'*64, application_qualified=False, benchmark=False,
            full_presentation_qualified=False)
        value['command'] = ['/opt/homebrew/bin/python3', '-B', str(HERE/'std_cli.py'),
            '--frozen-sha', {'source_freeze_sha256': True}, *factory.ordinary_arguments(value)]
        return value

    def test_aliases_restore_existing_modules_and_path_after_error(self):
        old, selected = object(), object()
        before = list(sys.path)
        with patch.dict(sys.modules, {'runtime_compiler': old}):
            with self.assertRaisesRegex(RuntimeError, 'fixture'):
                with factory.aliases({'runtime_compiler': selected}):
                    self.assertIs(sys.modules['runtime_compiler'], selected)
                    sys.path.append('/owned-fixture-only')
                    raise RuntimeError('fixture')
            self.assertIs(sys.modules['runtime_compiler'], old)
        self.assertEqual(sys.path, before)

    def test_aliases_remove_previously_absent_name(self):
        name = '_std07_owned_fixture_alias'
        self.assertNotIn(name, sys.modules)
        with factory.aliases({name: object()}):
            self.assertIn(name, sys.modules)
        self.assertNotIn(name, sys.modules)

    def test_checked_load_preserves_actual_module_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve()/'fixture.py'
            path.write_text('VALUE = 7\n')
            seen = []
            name = '_runtime_std_after_installation07_fixture_path'
            self.addCleanup(sys.modules.pop, name, None)
            module = factory.load('fixture_path', path, lambda p: seen.append(p))
            self.assertEqual(seen, [path])
            self.assertEqual(module.__file__, str(path))
            self.assertEqual(module.VALUE, 7)

    def test_refused_source_is_not_executed_or_registered(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve()/'fixture.py'
            path.write_text('raise AssertionError("must not execute")\n')
            def deny(path):
                raise RuntimeError('fixture source refused')
            with self.assertRaisesRegex(RuntimeError, 'source refused'):
                factory.load('fixture_denied', path, deny)
            self.assertNotIn('_runtime_std_after_installation07_fixture_denied', sys.modules)

    def test_cached_private_module_cannot_change_route(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = [Path(directory).resolve()/name for name in ('one.py', 'two.py')]
            first.write_text('VALUE = 1\n'); second.write_text('VALUE = 2\n')
            name = '_runtime_std_after_installation07_fixture_cached'
            self.addCleanup(sys.modules.pop, name, None)
            factory.load('fixture_cached', first, lambda p: None)
            with self.assertRaisesRegex(RuntimeError, 'route changed'):
                factory.load('fixture_cached', second, lambda p: None)

    def test_cli_holds_selected_runtime_through_ordinary_main(self):
        old, selected = object(), object()
        before = list(sys.argv)
        module = SimpleNamespace(__file__='/owned/original/scripts/std_mir_source_paths.py',
                                 ROOT=Path('/owned/original'))
        seen = []
        def ordinary_main():
            seen.append((sys.modules['runtime_compiler'], list(sys.argv), module.ROOT))
            return 7
        module.main = ordinary_main
        with patch.dict(sys.modules, {'runtime_compiler': old}):
            self.assertEqual(cli.invoke(module, factory, {'runtime_compiler': selected}, ['--fixture']), 7)
            self.assertIs(sys.modules['runtime_compiler'], old)
        self.assertEqual(seen, [(selected, [module.__file__, '--fixture'], Path('/owned/original'))])
        self.assertEqual(sys.argv, before)

    def test_cli_restores_arguments_and_aliases_on_ordinary_failure(self):
        old, selected = object(), object()
        before = list(sys.argv)
        def fail():
            self.assertIs(sys.modules['runtime_compiler'], selected)
            raise RuntimeError('ordinary fixture failure')
        module = SimpleNamespace(__file__='/owned/std.py', main=fail)
        with patch.dict(sys.modules, {'runtime_compiler': old}):
            with self.assertRaisesRegex(RuntimeError, 'ordinary fixture failure'):
                cli.invoke(module, factory, {'runtime_compiler': selected}, [])
            self.assertIs(sys.modules['runtime_compiler'], old)
        self.assertEqual(sys.argv, before)

    def test_freeze_placeholder_expands_without_changing_frozen_plan(self):
        plan = self.plan(); before = copy.deepcopy(plan)
        command = factory.command(plan, 'b'*64)
        self.assertEqual(command[4], 'b'*64)
        self.assertEqual(command[5:], factory.ordinary_arguments(plan))
        self.assertEqual(plan, before)

    def test_unbound_runtime_and_status_rejected(self):
        plan = self.plan(); plan['runtime_key'] = None
        with self.assertRaisesRegex(RuntimeError, 'unbound'):
            factory.ordinary_arguments(plan)
        plan = self.plan(); plan['status'] = 'unbound-source-outline-not-executable'
        with self.assertRaisesRegex(RuntimeError, 'unbound'):
            factory.validate_plan(plan, 'b'*64)

    def test_changed_ordinary_arguments_or_extra_dict_rejected(self):
        plan = self.plan(); plan['command'][-1] = '601'
        with self.assertRaisesRegex(RuntimeError, 'command differs'):
            factory.command(plan, 'b'*64)
        plan = self.plan(); plan['command'][4] = {'source_freeze_sha256': 1}
        # Typed equality is required for the only substitution marker.
        with self.assertRaisesRegex(RuntimeError, 'command differs'):
            factory.command(plan, 'b'*64)

    def test_admission_wrapper_matches_complete_ready_identity(self):
        identity = {'admission': {'loader_probe': {'architecture': 'arm64'}}, 'files': {'a': 'b'}}
        factory.publication_identity({'identity': identity},
            {'identity': copy.deepcopy(identity), 'snapshots': []})

    def test_raw_specification_or_changed_admission_identity_rejected(self):
        identity = {'admission': {'loader_probe': {'architecture': 'arm64'}}, 'files': {'a': 'b'}}
        for admission in [identity['admission'], {'identity': identity['admission'], 'snapshots': []},
                          {'identity': identity, 'snapshots': [], 'extra': True}]:
            with self.subTest(admission=admission), self.assertRaisesRegex(RuntimeError, 'wrapper differs'):
                factory.publication_identity({'identity': identity}, admission)


if __name__ == '__main__':
    unittest.main()
