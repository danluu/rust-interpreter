import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); sys.modules[name] = value; spec.loader.exec_module(value)
    return value
m = load('hir_arena_native', ROOT / 'experiments/hir-arena-native/check.py')
base = load('hir_arena_native_base_controls', ROOT / 'tests/test_hir_native_correctness.py')


class ArenaNativeTests(unittest.TestCase):
    def test_native_context_preserves_original_defaults_and_requires_actual_archive(self):
        original = m.native.default_context()
        with patch.object(m, 'CURRENT_ARCHIVE_SHA', 'a' * 64):
            context = m.context()
        self.assertEqual(m.native.default_context(), original)
        self.assertEqual(original.revision, m.native.CHECKPOINT)
        self.assertEqual(original.read_history, m.native.history)
        self.assertEqual(context.revision, m.upgrade.CHECKPOINT)
        self.assertEqual(context.read_history, m.history)
        self.assertEqual(context.work, m.WORK)
        self.assertNotEqual(context.work, original.work)
        with patch.object(m, 'CURRENT_ARCHIVE_SHA', None):
            with self.assertRaisesRegex(RuntimeError, 'archive has not been pinned'): m.context()

    def test_reviewed_plan_requires_all27_full_native_sequence_and_correct_current_archive(self):
        frozen, names = {'helper': 'a' * 64}, m.checkpoint()[1]
        with patch.object(m, 'CURRENT_ARCHIVE_SHA', 'a' * 64): context = m.context()
        plan = dict(owner=str(context.root), source=str(m.engine.SOURCE), checkpoint=context.revision,
            inputs=frozen, required_units=names, commands=copy.deepcopy(m.native.COMMANDS),
            probes=m.native.PROBES, capacity=m.native.CAPACITY, canonical_lock=str(m.engine.CANONICAL_LOCK),
            archive_paths={'archive': '/new-success.tar.gz'}, archive_hashes={'/new-success.tar.gz': 'a' * 64})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp).resolve() / 'plan.json'; path.write_text(json.dumps(plan)); reviewed = m.sha(path)
            self.assertEqual(m.native.load_plan(path, reviewed, frozen, names, context=context), plan)
            commands = copy.deepcopy(m.native.COMMANDS); commands['native'].remove('--no-capture')
            for field, value in [('required_units', names[:-1]), ('commands', commands), ('probes', []),
                    ('capacity', dict(m.native.CAPACITY, initial_free_gib=8)),
                    ('archive_hashes', {'/new-success.tar.gz': m.upgrade.ARCHIVE_HASHES['archive']})]:
                changed = dict(plan, **{field: value}); path.write_text(json.dumps(changed))
                for digest in [reviewed, m.sha(path)]:
                    with self.subTest(field=field), self.assertRaises(RuntimeError):
                        m.native.load_plan(path, digest, frozen, names, context=context)

    def fixture(self, root):
        owner, work, plan_path, _, manifest, _, old_plan = base.NativeCorrectnessTests().fixture(root)
        names = m.checkpoint()[1]
        def save(path, value):
            path.write_text(json.dumps(value)); return m.sha(path)
        plan = json.loads(plan_path.read_bytes())
        refs = []
        for i, expected in enumerate(m.ARCHIVE_CHAIN):
            paths = {key: str(root / f'archive-{i}-{key}') for key in ['archive', 'manifest', 'summary']}
            for path in paths.values(): Path(path).write_text('separately retained proof')
            refs.append(dict(paths=paths, hashes={p: expected if k == 'archive' else m.sha(p) for k,p in paths.items()},
                             required=dict(plan['archive_required'])))
        plan.update(checkpoint=m.upgrade.CHECKPOINT, old_tests=[n for n in names if n != m.upgrade.NEW_TEST],
                    added_tests=[m.upgrade.NEW_TEST], archive_paths=refs[0]['paths'],
                    archive_hashes=refs[0]['hashes'], archive_required=refs[0]['required'])
        plan['previous']['source']['revision'] = m.upgrade.diagnostic.SOURCE_REVISION
        plan['previous']['historical_archives'] = refs[1:]
        plan['inputs'] = {p: h for ref in refs[1:] for p,h in ref['hashes'].items()}
        plan_hash = save(plan_path, plan)
        state_path = work / 'source.json'; state = json.loads(state_path.read_bytes())
        state.update(revision=m.SOURCE_REVISION, parent=m.upgrade.diagnostic.SOURCE_REVISION, plan_sha256=plan_hash)
        state_hash = save(state_path, state)
        completed = json.loads((work / 'completed.json').read_bytes())
        for i, phase in enumerate(['plan', 'apply', 'check', 'unit']):
            path = work / 'stages' / (phase + '-01') / 'receipt.json'; row = json.loads(path.read_bytes())
            row.update(plan_sha256=plan_hash, source_record_sha256=state_hash, parent_pid=200+i)
            if phase == 'unit':
                child_path = Path(row['commands'][0]['path']); child = json.loads(child_path.read_bytes())
                output = child_path.parent / 'stdout'
                output.write_text(''.join(f'test body_cache::{n} ... ok\n' for n in names) + base.result(27))
                child['stdout_sha256'] = m.sha(output)
                row['commands'][0]['sha256'] = save(child_path, child)
            digest = save(path, row)
            if phase != 'plan': completed[phase]['sha256'] = digest
            outer = owner / '.work/experiments' / ('hir-ready-hit-upgrade-' + phase + '-supervisor-01')
            status = json.loads((outer / 'status.json').read_bytes()); status['supervisor_pid'] = 200+i
            save(outer / 'status.json', status)
            outer.rename(outer.with_name('hir-arena-identity-upgrade-' + phase + '-supervisor-01'))
        save(work / 'completed.json', completed)
        return owner, work, plan_path, plan_hash, state_hash, manifest, names, old_plan, refs

    def read_fixture(self, parts):
        owner, work, plan_path, plan_hash, state_hash, manifest, names, old_plan, _ = parts
        with patch.multiple(m, UPGRADE=owner, UPGRADE_WORK=work, UPGRADE_PLAN=plan_path,
                            PLAN_SHA=plan_hash, SOURCE_RECORD_SHA=state_hash), \
             patch.object(m, 'checkpoint', return_value=(manifest, names)), \
             patch.object(m.engine.old, 'frozen_plan', return_value=old_plan):
            return m.history(plan_hash, work / 'stages/unit-01/receipt.json')

    def test_current_history_keeps_all_six_older_tar_payloads_as_verified_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            parts = self.fixture(Path(tmp).resolve()); value = self.read_fixture(parts)
            self.assertEqual(len(value['historical_archives']), 6)
            self.assertEqual(value['source']['revision'], m.SOURCE_REVISION)
            self.assertIn(str(parts[1] / 'source.json'), value['files'])
            for ref in parts[-1]: self.assertNotIn(ref['paths']['archive'], value['files'])
            for ref in parts[-1][1:]: self.assertIn(ref['paths']['manifest'], value['files'])
            with patch.object(m.native.engine, 'verify_archive') as verify, \
                 patch.object(m.native, 'sha', side_effect=lambda p: next(
                     ref['hashes'][str(p)] for ref in parts[-1] if str(p) in ref['hashes'])):
                m.native.verify_references(value)
                self.assertEqual(verify.call_count, 6)

    def test_missing_check_and_rehashed_old26_cannot_qualify_the_new_compiler(self):
        with tempfile.TemporaryDirectory() as tmp:
            parts = self.fixture(Path(tmp).resolve()); completed = parts[1] / 'completed.json'
            saved = completed.read_bytes(); data = json.loads(saved); del data['check']; completed.write_text(json.dumps(data))
            with self.assertRaisesRegex(RuntimeError, 'incomplete'): self.read_fixture(parts)
            completed.write_bytes(saved)
            stage = parts[1] / 'stages/unit-01/receipt.json'; row = json.loads(stage.read_bytes())
            child_path = Path(row['commands'][0]['path']); child = json.loads(child_path.read_bytes())
            output = child_path.parent / 'stdout'
            old_names = [n for n in parts[6] if n != m.upgrade.NEW_TEST]
            output.write_text(''.join(f'test body_cache::{n} ... ok\n' for n in old_names) + base.result(26))
            child['stdout_sha256'] = m.sha(output); child_path.write_text(json.dumps(child))
            row['commands'][0]['sha256'] = m.sha(child_path); stage.write_text(json.dumps(row))
            data = json.loads(saved); data['unit']['sha256'] = m.sha(stage); completed.write_text(json.dumps(data))
            with self.assertRaisesRegex(RuntimeError, 'required actual unit test missing'): self.read_fixture(parts)

    def test_source_identity_and_raw_unit_output_cannot_be_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            parts = self.fixture(Path(tmp).resolve())
            with patch.object(m, 'SOURCE_REVISION', m.upgrade.diagnostic.SOURCE_REVISION):
                with self.assertRaisesRegex(RuntimeError, 'compiler source'): self.read_fixture(parts)
            (parts[1] / 'stages/unit-01/commands/000/stdout').write_text(base.result(27))
            with self.assertRaisesRegex(RuntimeError, 'raw output changed'): self.read_fixture(parts)


if __name__ == '__main__': unittest.main()
