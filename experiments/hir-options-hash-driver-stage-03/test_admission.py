"""In-memory admission negatives; no compiler/provider or concrete preparation."""
from copy import deepcopy
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import Mock, patch

import prepare
import stage


class ReachedDependencies(Exception):
    pass


class Admission(unittest.TestCase):
    def inherited(self):
        return {key: 'bound-'+key for key in stage.BOOTSTRAP_ENVIRONMENT_KEYS} | {
            'PATH': '/explicit/offline-bin:/usr/bin', 'SDKROOT': '/explicit/sdk',
            'HOME': '/explicit/home', 'TMPDIR': '/old/tmp', 'LANG': 'C',
        }

    def model(self):
        values, digests, argv = {}, {}, ['prepare.py']
        for role, root in [('compiler', prepare.COMPILER_WORK), ('beta', stage.BETA_WORK),
                           ('native', stage.NATIVE_WORK), ('run-make', stage.RECIPE_WORK)]:
            audit = Path('/model')/(role+'-audit.json')
            terminal = root/'receipt.json'
            values[audit] = dict(status='verified', receipt_sha256='b'*64)
            values[terminal] = dict(status='passed')
            digests[audit], digests[terminal] = 'a'*64, 'b'*64
            argv.extend(['--'+role+'-audit', str(audit), '--'+role+'-audit-sha256', 'a'*64])
        return values, digests, argv

    def invoke(self, values, digests, argv, expected):
        dependencies = Mock(side_effect=ReachedDependencies)
        def read(path):
            if Path(path) not in values:
                raise FileNotFoundError(path)
            return deepcopy(values[Path(path)])
        with patch.object(sys, 'argv', argv), patch.object(Path, 'cwd', return_value=stage.ROOT), \
             patch.object(prepare, 'read', side_effect=read), \
             patch.object(prepare, 'sha', side_effect=lambda path: digests[Path(path)]), \
             patch.object(stage, 'dependencies', dependencies):
            with self.assertRaises(expected):
                prepare.main()
        if expected is ReachedDependencies:
            dependencies.assert_called_once_with()
        else:
            dependencies.assert_not_called()

    def test_direct_environment_preserves_selected_values_and_omission_record(self):
        inherited = self.inherited(); original = deepcopy(inherited)
        selected, omitted = stage.driver_environment(inherited, Path('/new/tmp'))
        self.assertEqual(inherited, original)
        self.assertEqual(selected, dict(PATH='/explicit/offline-bin:/usr/bin', SDKROOT='/explicit/sdk',
                                       HOME='/explicit/home', TMPDIR='/new/tmp', LANG='C'))
        self.assertEqual(omitted, {key: inherited[key] for key in stage.BOOTSTRAP_ENVIRONMENT_KEYS})

    def test_unknown_compiler_loader_and_other_environment_keys_reject(self):
        for key in ['RUSTFLAGS', 'DYLD_LIBRARY_PATH', 'LD_PRELOAD', 'UNREVIEWED_CONTEXT']:
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                stage.driver_environment(self.inherited() | {key: 'override'}, Path('/new/tmp'))

    def test_missing_expected_bootstrap_key_rejects(self):
        inherited = self.inherited(); del inherited['RUSTUP_DIST_SERVER']
        with self.assertRaises(RuntimeError):
            stage.driver_environment(inherited, Path('/new/tmp'))

    def test_aliases_restore_modules_and_search_path_after_failure(self):
        name = '_hash_admission_test_alias'
        old, replacement = ModuleType(name), ModuleType(name)
        original_path = list(sys.path)
        with patch.dict(sys.modules, {name: old}):
            with self.assertRaises(ReachedDependencies):
                with stage.aliases({name: replacement, '_hash_admission_new_alias': replacement}):
                    self.assertIs(sys.modules[name], replacement)
                    sys.path.insert(0, '/unretained/test/path')
                    raise ReachedDependencies
            self.assertIs(sys.modules[name], old)
            self.assertNotIn('_hash_admission_new_alias', sys.modules)
        self.assertEqual(sys.path, original_path)

    def test_four_bound_successes_reach_dependency_gate_once(self):
        self.invoke(*self.model(), ReachedDependencies)

    def test_missing_audit_rejects_before_dependency_discovery(self):
        values, digests, argv = self.model()
        del values[Path('/model/run-make-audit.json')]
        self.invoke(values, digests, argv, FileNotFoundError)

    def test_each_failed_predecessor_rejects_before_dependency_discovery(self):
        for root in [prepare.COMPILER_WORK, stage.BETA_WORK, stage.NATIVE_WORK, stage.RECIPE_WORK]:
            with self.subTest(root=root):
                values, digests, argv = self.model()
                values[root/'receipt.json']['status'] = 'failed'
                self.invoke(values, digests, argv, RuntimeError)

    def test_unverified_or_mismatched_audit_rejects_before_dependency_discovery(self):
        for mismatch in ['audit-status', 'audit-hash', 'terminal-hash']:
            with self.subTest(mismatch=mismatch):
                values, digests, argv = self.model(); path = Path('/model/native-audit.json')
                if mismatch == 'audit-status': values[path]['status'] = 'prepared-unrun'
                elif mismatch == 'audit-hash': digests[path] = 'c'*64
                else: values[path]['receipt_sha256'] = 'c'*64
                self.invoke(values, digests, argv, RuntimeError)

    def test_invalid_supplied_digest_rejects_before_dependency_discovery(self):
        for digest in ['a'*63, 'A'*64, 'z'*64]:
            with self.subTest(digest=digest):
                values, digests, argv = self.model(); argv[-1] = digest
                self.invoke(values, digests, argv, RuntimeError)


if __name__ == '__main__':
    unittest.main()
