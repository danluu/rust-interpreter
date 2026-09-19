"""Synthetic workspace proof controls; no Cargo/compiler subprocesses."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import ancestor_workspace as workspace
from compose_sysroot import digest


class AncestorControls(unittest.TestCase):
    def fixture(self):
        owner = Path('/owner'); source = owner / '.work/candidate/source'
        acquired = dict(source_files={'Cargo.toml': {}, 'src/bootstrap/Cargo.toml': {}, 'nested/lib/Cargo.toml': {}},
                        backtrace_files={'Cargo.toml': {}, 'crates/test/Cargo.toml': {}})
        before = b'[workspace]\nmembers = ["one"]\nexclude = [".work/sources/cg-clif", ".work/sources/rg-aot"]\n'
        after = b'[workspace]\nmembers = ["one"]\nexclude = [".work"]\n'
        manifests = {name: None for name in workspace.manifest_paths(acquired, source)}
        manifests[str(owner / 'Cargo.toml')] = dict(sha256=digest(after), stamp=[])
        plan = dict(owner=str(owner), ancestor_manifests=manifests,
                    ancestor_workspace=dict(path=str(owner / 'Cargo.toml'), before_sha256=digest(before), after_sha256=digest(after)))
        controls = dict(files={str(owner / 'Cargo.toml'): dict(sha256=digest(before))})
        return plan, acquired, owner, source, before, after, controls

    def test_actual_saved_build02_workspace_contract(self):
        refs = json.loads(Path(__file__).with_name('source-bindings.json').read_bytes())['references']
        def saved(label):
            row = refs[label]; raw = Path(row['path']).read_bytes()
            self.assertEqual(len(raw), row['size'])
            self.assertEqual(digest(raw), row['sha256'])
            return raw
        plan = json.loads(saved('build02_plan'))
        acquired = json.loads(saved('candidate_acquired_catalog'))
        controls = json.loads(saved('workspace_controls_historical_catalog'))
        before, after = saved('build02_original_parent'), saved('build02_current_parent')
        source = Path(plan['owner']) / '.work/hir-options-hash-compiler-01/source'
        paths = workspace.contract(plan, acquired, plan['owner'], source, before, after, controls)
        self.assertEqual(paths, set(plan['ancestor_manifests']))

    def test_exact_workspace_transition_and_complete_present_absent_path_set(self):
        args = self.fixture()
        paths = workspace.contract(*args)
        self.assertIn('/Cargo.toml', paths)
        self.assertIn('/owner/.work/Cargo.toml', paths)
        self.assertIn('/owner/.work/candidate/source/library/backtrace/crates/Cargo.toml', paths)
        self.assertEqual(paths, set(args[0]['ancestor_manifests']))

    def test_omitted_or_extra_ancestor_path_is_rejected(self):
        for extra in [False, True]:
            args = list(self.fixture())
            if extra:
                args[0]['ancestor_manifests']['/unrelated/Cargo.toml'] = None
            else:
                del args[0]['ancestor_manifests']['/owner/.work/Cargo.toml']
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                workspace.contract(*args)

    def test_other_workspace_changes_rejected_even_with_matching_supplied_hash(self):
        for after in [b'[workspace]\nmembers=["other"]\nexclude=[".work"]\n',
                      b'[workspace]\nmembers=["one"]\nexclude=[".work", "other"]\n']:
            args = list(self.fixture()); args[5] = after
            args[0]['ancestor_workspace']['after_sha256'] = digest(after)
            args[0]['ancestor_manifests']['/owner/Cargo.toml']['sha256'] = digest(after)
            with self.assertRaises(ValueError):
                workspace.contract(*args)

    def test_historical_catalog_must_keep_original_not_current_parent(self):
        args = list(self.fixture())
        args[-1]['files']['/owner/Cargo.toml']['sha256'] = digest(args[5])
        with self.assertRaises(ValueError):
            workspace.contract(*args)

    def test_noncanonical_source_members_and_missing_bootstrap_rejected(self):
        for name in ['../Cargo.toml', '/foreign/Cargo.toml', './Cargo.toml']:
            acquired = copy.deepcopy(self.fixture()[1]); acquired['source_files'][name] = {}
            with self.subTest(name=name), self.assertRaises(ValueError):
                workspace.manifest_paths(acquired, self.fixture()[3])
        args = list(self.fixture()); del args[1]['source_files']['src/bootstrap/Cargo.toml']
        args[0]['ancestor_manifests'] = {name: None for name in workspace.manifest_paths(args[1], args[3])}
        with self.assertRaises(ValueError):
            workspace.contract(*args)

    @staticmethod
    def stamp(path):
        s = path.lstat()
        return [s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_nlink]

    @staticmethod
    def sha(path):
        return digest(path.read_bytes())

    def test_current_present_and_absent_paths_are_guarded(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name).resolve(); present = root / 'Cargo.toml'; absent = root / 'nested/Cargo.toml'
            present.write_bytes(b'[workspace]\n')
            rows = {str(present): dict(stamp=self.stamp(present), sha256=self.sha(present)), str(absent): None}
            workspace.guard_manifests(rows, self.stamp, self.sha, True)
            absent.parent.mkdir(); absent.write_bytes(b'[workspace]\n')
            with self.assertRaises(ValueError):
                workspace.guard_manifests(rows, self.stamp, self.sha, False)

    def test_current_route_and_identity_changes_are_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name).resolve(); present = root / 'Cargo.toml'
            present.write_bytes(b'[workspace]\n')
            expected = dict(stamp=self.stamp(present), sha256=self.sha(present))
            present.write_bytes(b'[different]\n')
            with self.assertRaises(ValueError):
                workspace.guard_manifests({str(present): expected}, self.stamp, self.sha, False)
            link = root / 'alias'; link.symlink_to(root, target_is_directory=True)
            with self.assertRaises(ValueError):
                workspace.guard_manifests({str(link / 'absent.toml'): None}, self.stamp, self.sha, False)

    def test_full_guard_rejects_wrong_hash_even_with_current_stamp(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name).resolve() / 'Cargo.toml'; path.write_bytes(b'[workspace]\n')
            with self.assertRaises(ValueError):
                workspace.guard_manifests({str(path): dict(stamp=self.stamp(path), sha256='0' * 64)}, self.stamp, self.sha, True)


if __name__ == '__main__':
    unittest.main()
