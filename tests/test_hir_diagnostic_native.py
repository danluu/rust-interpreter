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
m = load('hir_diagnostic_native', ROOT / 'experiments/hir-diagnostic-native/check.py')
base = load('hir_diagnostic_native_base_controls', ROOT / 'tests/test_hir_native_correctness.py')


def report(state, suffix='S=1 E=4'):
    return (f'[hir-body-capture] child {state} {suffix} events=3 cache_hits=0 body_codec=1 '
        'prepared_values=1 cold_materialization_audit=1 hit_materializer=0 '
        'body_bytes=5 body_ast=3 param_ast=0 trait_entries=0 trait_candidates=0 external_refs=0\n')


class DiagnosticNativeTests(unittest.TestCase):
    def test_actual_phase_messages_and_empty_output_never_qualify_native_hits(self):
        text = ''.join(report('rejected-body-tree-' + phase) for phase in m.BODY_PHASES)
        value = m.observations(text)
        self.assertEqual(value['records'], 6)
        self.assertEqual(value['raw_records'], text.splitlines())
        self.assertFalse(value['native_qualified']); self.assertFalse(value['executed_native_binary'])
        self.assertTrue(m.observations('ordinary diagnostic only\n')['no_records'])
        self.assertEqual(m.observations(report('cold-tree-and-journal-after-stock-lowering'))['records'], 1)
        self.assertEqual(m.observations(report('rejected-entry', 'S=0 E=0'))['records'], 1)

    def test_old_aggregate_malformed_ranges_or_unexpected_reuse_cannot_mask_diagnostics(self):
        valid = report('rejected-body-tree-validation')
        for bad in [report('rejected-body-tree'), report('unknown-phase'),
                    report('rejected-body-tree-current', 'S=4 E=1'),
                    report('rejected-body-tree-current', 'S=1 E=4294967041'),
                    report('rejected-body-tree-current', 'S=01 E=4'),
                    '[hir-body-reuse] child hit cache_hits=1\n', valid.replace('body_codec=1', 'body_codec=0')]:
            with self.subTest(bad=bad), self.assertRaises(RuntimeError): m.observations(valid + bad)

    def test_reviewed_plan_keeps_one_build_three_probes_and_capture_only_with_capacity(self):
        frozen, names = {'fixture': 'a' * 64}, m.upgrade.checkpoint()[1]
        self.assertEqual(len(names), 26)
        self.assertEqual(m.BUILD, ['./x', 'build', '--stage', '1', 'compiler/rustc', 'library', '--jobs', '2', '-vv'])
        command = m.compile_command(m.WORK / 'fixture')
        self.assertEqual(command.count('-Zincremental-info'), 1)
        self.assertEqual(command.count('-Zhir-body-cache-capture=true'), 1)
        self.assertFalse(any('hir-body-cache-reuse' in arg for arg in command))
        plan = dict(owner=str(m.ROOT), source=str(m.SOURCE), checkpoint=m.CHECKPOINT, inputs=frozen,
            required_units=names, build=m.BUILD, probes=m.PROBES, compile_command=command, capacity=m.CAPACITY,
            canonical_lock=str(m.engine.CANONICAL_LOCK), diagnostic_only=True, native_qualified=False,
            executed_native_binary=False)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp).resolve() / 'plan.json'; path.write_text(json.dumps(plan)); reviewed = m.sha(path)
            self.assertEqual(m.load_plan(path, reviewed, frozen, names), plan)
            for field, value in [('compile_command', command + ['-Zhir-body-cache-reuse=true']), ('build', []),
                                 ('required_units', names[:-1]), ('native_qualified', True), ('executed_native_binary', True),
                                 ('capacity', dict(m.CAPACITY, initial_free_gib=8))]:
                bad = dict(plan, **{field: value}); path.write_text(json.dumps(bad))
                for digest in [reviewed, m.sha(path)]:
                    with self.assertRaises(RuntimeError): m.load_plan(path, digest, frozen, names)

    def fixture(self, root):
        parts = base.NativeCorrectnessTests().fixture(root)
        owner, work, plan_path, _, manifest, names, old_plan = parts
        def save(path, value):
            path.write_text(json.dumps(value)); return m.sha(path)
        plan = json.loads(plan_path.read_bytes())
        refs = []
        for i, expected in enumerate(m.ARCHIVE_CHAIN):
            paths = {key: str(root / f'archive-{i}-{key}') for key in ['archive', 'manifest', 'summary']}
            for path in paths.values(): Path(path).write_text('separately retained proof')
            refs.append(dict(paths=paths, hashes={p: expected if k == 'archive' else m.sha(p) for k,p in paths.items()},
                             required=dict(plan['archive_required'])))
        plan.update(checkpoint=m.CHECKPOINT, old_tests=names, added_tests=[], archive_paths=refs[0]['paths'],
                    archive_hashes=refs[0]['hashes'], archive_required=refs[0]['required'])
        plan['previous']['source']['revision'] = m.upgrade.PREVIOUS_REVISION
        plan['previous']['historical_archives'] = refs[1:]
        # Historical tar files are explicit references, never nested current payloads.
        plan['inputs'] = {p: h for ref in refs[1:] for p,h in ref['hashes'].items()}
        plan_hash = save(plan_path, plan)
        state_path = work / 'source.json'; state = json.loads(state_path.read_bytes())
        state.update(revision=m.SOURCE_REVISION, parent=m.upgrade.PREVIOUS_REVISION, plan_sha256=plan_hash)
        state_hash = save(state_path, state)
        completed = json.loads((work / 'completed.json').read_bytes())
        for phase in ['plan', 'apply', 'check', 'unit']:
            path = work / 'stages' / (phase + '-01') / 'receipt.json'; row = json.loads(path.read_bytes())
            row.update(plan_sha256=plan_hash, source_record_sha256=state_hash)
            digest = save(path, row)
            if phase != 'plan': completed[phase]['sha256'] = digest
            outer = owner / '.work/experiments' / ('hir-ready-hit-upgrade-' + phase + '-supervisor-01')
            outer.rename(outer.with_name('hir-fixture-env-upgrade-' + phase + '-supervisor-01'))
        save(work / 'completed.json', completed)
        return owner, work, plan_path, plan_hash, state_hash, manifest, names, old_plan, refs

    def read_fixture(self, parts):
        owner, work, plan_path, plan_hash, state_hash, manifest, names, old_plan, _ = parts
        with patch.multiple(m, UPGRADE=owner, UPGRADE_WORK=work, UPGRADE_PLAN=plan_path,
                            UPGRADE_PLAN_SHA=plan_hash, SOURCE_RECORD_SHA=state_hash), \
             patch.object(m.upgrade, 'checkpoint', return_value=(manifest, names)), \
             patch.object(m.old, 'frozen_plan', return_value=old_plan):
            return m.history(work / 'stages/unit-01/receipt.json')

    def test_actual_current_history_separates_all_four_predecessor_tar_payloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            parts = self.fixture(Path(tmp).resolve()); value = self.read_fixture(parts)
            self.assertEqual(len(value['historical_archives']), 4)
            self.assertIn(str(parts[1] / 'source.json'), value['files'])
            for ref in parts[-1]: self.assertNotIn(ref['paths']['archive'], value['files'])
            for ref in parts[-1][1:]: self.assertIn(ref['paths']['manifest'], value['files'])

    def test_missing_selected_check_or_tampered_unit_raw_output_rejects_prerequisite(self):
        with tempfile.TemporaryDirectory() as tmp:
            parts = self.fixture(Path(tmp).resolve()); completed = parts[1] / 'completed.json'
            saved = completed.read_bytes(); value = json.loads(saved); del value['check']; completed.write_text(json.dumps(value))
            with self.assertRaises(RuntimeError): self.read_fixture(parts)
            completed.write_bytes(saved)
            (parts[1] / 'stages/unit-01/commands/000/stdout').write_text(base.result(26))
            with self.assertRaises(RuntimeError): self.read_fixture(parts)

if __name__ == '__main__': unittest.main()
