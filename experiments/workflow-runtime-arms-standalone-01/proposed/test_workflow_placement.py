"""New placement behavior only, using owned temporary script stubs.

No real interpreter, compiler provider, application or benchmark is imported.
"""
from contextlib import ExitStack
from pathlib import Path
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch

import workflow_placement as placement


class Placement(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        temporary = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.owner = Path(temporary).resolve()/'owner'
        self.adjacent = self.owner/'experiments'/placement.DIRECTORY
        self.scripts = self.owner/'scripts'
        self.adjacent.mkdir(parents=True)
        self.scripts.mkdir()
        for name in [*placement.ENTRIES, 'workflow_runtime_arms.py', 'workflow_placement.py']:
            (self.adjacent/name).write_text('raise AssertionError("fixture must not be imported")\n')
        (self.scripts/'interpreter.py').write_text('raise AssertionError("provider must not be imported")\n')
        self.stack.enter_context(patch.object(placement, '__file__', str(self.adjacent/'workflow_placement.py')))
        self.stack.enter_context(patch.object(sys, 'path', list(sys.path)))
        self.stack.enter_context(patch.dict(sys.modules))
        for name in ['interpreter', 'bench_e2e_workflow', 'workflow_runtime_arms']:
            sys.modules.pop(name, None)

    def entry(self):
        return self.adjacent/'bench_e2e_workflow.py'

    def test_routes_derive_the_existing_owner(self):
        self.assertEqual(placement.routes(self.entry()), (self.owner, self.adjacent, self.scripts))

    def test_noncanonical_layout_is_rejected(self):
        for path in ['relative/bench_e2e_workflow.py', self.owner/'scripts/bench_e2e_workflow.py',
                     self.adjacent/'unknown.py', self.adjacent/'..'/placement.DIRECTORY/'bench_e2e_workflow.py']:
            with self.subTest(path=path), self.assertRaises(RuntimeError):
                placement.routes(path)

    def test_both_entries_select_adjacent_then_original_scripts_without_imports(self):
        for name in placement.ENTRIES:
            self.assertEqual(placement.configure(self.adjacent/name), self.owner)
            self.assertEqual(sys.path[:2], [str(self.adjacent), str(self.scripts)])
        self.assertNotIn('interpreter', sys.modules)
        self.assertNotIn('bench_e2e_workflow', sys.modules)
        self.assertNotIn('workflow_runtime_arms', sys.modules)

    def test_foreign_search_path_cannot_win(self):
        foreign = self.owner/'foreign'
        foreign.mkdir()
        (foreign/'interpreter.py').write_text('raise AssertionError("foreign")\n')
        sys.path.insert(0, str(foreign))
        placement.configure(self.entry())
        self.assertEqual(sys.path[:3], [str(self.adjacent), str(self.scripts), str(foreign)])

    def test_adjacent_interpreter_shadow_is_rejected(self):
        (self.adjacent/'interpreter.py').write_text('raise AssertionError("shadow")\n')
        with self.assertRaisesRegex(RuntimeError, 'import search'):
            placement.configure(self.entry())

    def test_preloaded_foreign_interpreter_is_rejected_before_path_change(self):
        module = ModuleType('interpreter')
        module.__file__ = str(self.adjacent/'bench_e2e_workflow.py')
        module.ROOT = self.owner
        sys.modules['interpreter'] = module
        before = list(sys.path)
        with self.assertRaisesRegex(RuntimeError, 'selected source module differs'):
            placement.configure(self.entry())
        self.assertEqual(sys.path, before)

    def test_preloaded_original_script_cannot_replace_adjacent_runner(self):
        path = self.scripts/'bench_e2e_workflow.py'
        path.write_text('raise AssertionError("old runner")\n')
        module = ModuleType('bench_e2e_workflow')
        module.__file__ = str(path)
        sys.modules['bench_e2e_workflow'] = module
        with self.assertRaisesRegex(RuntimeError, 'selected source module differs'):
            placement.configure(self.entry())

    def test_preloaded_interpreter_owner_mismatch_is_rejected(self):
        module = ModuleType('interpreter')
        module.__file__ = str(self.scripts/'interpreter.py')
        module.ROOT = self.owner/'different'
        sys.modules['interpreter'] = module
        with self.assertRaisesRegex(RuntimeError, 'another provider owner'):
            placement.configure(self.entry())

    def test_expected_loaded_modules_are_accepted(self):
        for name, path in [('interpreter', self.scripts/'interpreter.py'),
                           ('bench_e2e_workflow', self.adjacent/'bench_e2e_workflow.py')]:
            module = ModuleType(name)
            module.__file__ = str(path)
            module.ROOT = self.owner
            sys.modules[name] = module
            placement.check_module(name, path, root=self.owner)
        self.assertEqual(placement.configure(self.entry()), self.owner)

    def test_missing_helper_is_rejected(self):
        (self.adjacent/'workflow_runtime_arms.py').unlink()
        with self.assertRaisesRegex(RuntimeError, 'missing or indirect'):
            placement.configure(self.entry())

    def test_symlinked_entry_is_rejected(self):
        target = self.adjacent/'real.py'
        self.entry().rename(target)
        self.entry().symlink_to(target)
        with self.assertRaisesRegex(RuntimeError, 'runner path is indirect'):
            placement.configure(self.entry())

    def test_symlinked_provider_scripts_are_rejected(self):
        target = self.owner/'real-scripts'
        self.scripts.rename(target)
        self.scripts.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, 'scripts directory is indirect'):
            placement.configure(self.entry())

    def test_nonadjacent_placement_helper_is_rejected(self):
        with patch.object(placement, '__file__', str(self.scripts/'interpreter.py')):
            with self.assertRaisesRegex(RuntimeError, 'not adjacent'):
                placement.configure(self.entry())


if __name__ == '__main__':
    unittest.main()
