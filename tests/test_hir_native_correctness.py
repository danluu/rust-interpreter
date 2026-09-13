import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('hir_native_correctness', ROOT / 'experiments/hir-native-correctness/check.py')
native = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = native
spec.loader.exec_module(native)


def result(count, filtered=0):
    return f'test result: ok. {count} passed; 0 failed; 0 ignored; 0 measured; {filtered} filtered out; finished in 1s\n'


class NativeCorrectnessTests(unittest.TestCase):
    def test_checkpoint_requires_all_twenty_six_and_actual_reuse_source(self):
        manifest, names = native.checkpoint()
        self.assertEqual(len(names), 26)
        self.assertTrue(manifest['actual_cache_hit_path'])
        self.assertTrue(manifest['cached_body_materialization'])
        self.assertEqual(manifest['replay_verification'], 'always-on-tree-journal-poststate')
        text = ''.join(f'test body_cache::{n} ... ok\n' for n in names) + result(26)
        native.engine.checked_tests(text, names, [])
        native.checked_result(text, 26, unfiltered=True)
        with self.assertRaises(RuntimeError):
            native.engine.checked_tests(text.replace(f'test body_cache::{names[-1]} ... ok\n', ''), names, [])
        with self.assertRaises(RuntimeError):
            native.checked_result(text.replace('0 filtered out', '1 filtered out'), 26, unfiltered=True)

    def test_reviewed_plan_and_fixed_commands_capacity_cannot_be_rehashed_away(self):
        frozen, names = {'source': 'a' * 64}, ['unit']
        plan = dict(owner=str(native.ROOT), source=str(native.SOURCE), checkpoint=native.CHECKPOINT,
                    inputs=frozen, required_units=names, commands=copy.deepcopy(native.COMMANDS),
                    probes=copy.deepcopy(native.PROBES), capacity=copy.deepcopy(native.CAPACITY),
                    canonical_lock=str(native.engine.CANONICAL_LOCK))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp).resolve() / 'plan.json'
            path.write_text(json.dumps(plan))
            reviewed = native.sha(path)
            self.assertEqual(native.load_plan(path, reviewed, frozen, names), plan)
            changes = []
            wrong = copy.deepcopy(plan); wrong['commands']['native'].remove('--no-capture'); changes.append(wrong)
            wrong = copy.deepcopy(plan); wrong['capacity']['running_floor_gib'] = 1; changes.append(wrong)
            wrong = copy.deepcopy(plan); wrong['required_units'] = []; changes.append(wrong)
            wrong = copy.deepcopy(plan); wrong['probes'] = []; changes.append(wrong)
            for wrong in changes:
                path.write_text(json.dumps(wrong))
                for digest in [reviewed, native.sha(path)]:
                    with self.assertRaises(RuntimeError):
                        native.load_plan(path, digest, frozen, names)

    def test_native_requires_success_and_visible_verified_hit_with_split_libtest_line(self):
        start = 'test [run-make] tests/run-make/hir-body-cache-capture ... '
        hit = '[hir-body-reuse] anchor hit cache_hits=1 verify_tree=1 verify_journal=1 verify_poststate=1\n'
        text = start + '\n------rmake stderr------\n' + hit + 'ok\n' + result(1, 530)
        native.checked_native(text)
        for wrong in [text.replace(hit, ''), text.replace('verify_poststate=1', 'verify_poststate=0'),
                      text.replace(result(1, 530), result(0, 531)), text.replace('0 ignored', '1 ignored'),
                      text.replace('test [run-make]', 'test [ignored]')]:
            with self.assertRaises(RuntimeError):
                native.checked_native(wrong)

    def test_option_requires_actual_one_named_pass_and_ignores_command_line_text(self):
        text = 'running: cargo test --test-args test_unstable_options_tracking_hash\n'
        passed = 'test tests::test_unstable_options_tracking_hash ... ok\n'
        native.checked_option(text + passed + result(1, 17) + result(0))
        for wrong in [text + result(1, 17), text + passed + result(0),
                      text + passed + passed + result(1, 17)]:
            with self.assertRaises(RuntimeError):
                native.checked_option(wrong)

    def fixture(self, root):
        ready = root / 'ready'; work = ready / '.work/hir-ready-hit-upgrade-01'
        plan_path = ready / 'plan.json'
        def save(path, value):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value))
            return native.sha(path)
        def raw(path, data=''):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(data)
            return native.sha(path)
        names = native.checkpoint()[1]
        manifest = {'files': {'compiler/example.rs': {'after_sha256': 'a' * 64}}}
        cold_files = {str(root / 'old-cold-payload'): 'b' * 64}
        old_plan = {'environment': {'CARGO_NET_OFFLINE': 'true'}}
        refs = []
        for label, digest in [('cold', native.COLD_ARCHIVE_SHA), ('failed', native.FAILED_ARCHIVE_SHA)]:
            paths = {k: str(root / (label + '-' + k)) for k in ['archive', 'manifest', 'summary']}
            for path in paths.values(): raw(Path(path), 'retained archive placeholder')
            refs.append(dict(paths=paths, hashes={p: digest if k == 'archive' else 'c' * 64 for k,p in paths.items()},
                             required=cold_files))
        delta = work / 'stages/plan-01/source.delta'
        delta_hash = raw(delta, 'delta')
        plan = dict(owner=str(ready), source=str(native.SOURCE), checkpoint=native.CHECKPOINT,
            commands=native.old.COMMANDS, stages=['apply','check','unit'], old_tests=names[:22], added_tests=names[22:],
            delta=str(delta), delta_sha256=delta_hash, inputs={},
            archive_paths=refs[0]['paths'], archive_hashes=refs[0]['hashes'], archive_required=cold_files,
            previous=dict(source={'revision':'old'}, files=cold_files, historical_source={},
                          historical_archives=[refs[1]], old_plan=old_plan, old_plan_path='/original/plan.json'))
        plan_hash = save(plan_path, plan)
        state = dict(revision='new', parent='old', plan_sha256=plan_hash, config_sha256=native.CONFIG_SHA,
                     files={'compiler/example.rs': dict(kind='file', sha256='a' * 64)})
        source_hash = save(work / 'source.json', state)
        completed = {}
        for i, phase in enumerate(['plan','apply','check','unit']):
            folder = work / 'stages' / (phase + '-01')
            cmd = native.old.COMMANDS.get(phase, ['git','diff'])
            text = ''.join(f'test body_cache::{n} ... ok\n' for n in names) + result(26) if phase == 'unit' else ''
            child = folder / 'commands/000/receipt.json'
            row = dict(status='finished', returncode=0, command=cmd, cwd=str(native.SOURCE), environment=old_plan['environment'],
                       stdout_sha256=raw(child.parent/'stdout', text), stderr_sha256=raw(child.parent/'stderr'))
            child_hash = save(child, row)
            receipt = dict(owner=str(ready), stage=phase, status='passed', plan_sha256=plan_hash,
                           source_record_sha256=source_hash, started_at=i*3, admitted_at=i*3+1, finished_at=i*3+2,
                           pid=100+i, commands=[dict(path=str(child),sha256=child_hash,command=cmd)])
            receipt_path = folder/'receipt.json'
            receipt_hash = save(receipt_path, receipt)
            if phase != 'plan': completed[phase] = dict(path=str(receipt_path),sha256=receipt_hash)
            supervisor = ready/'.work/experiments'/('hir-ready-hit-upgrade-'+phase+'-supervisor-01')
            sp = raw(supervisor/'plan.json','{}'); log=raw(supervisor/'command.log')
            raw(supervisor/'supervisor.log')
            save(supervisor/'status.json', dict(status='finished',returncode=0,child_pid=100+i,plan_sha256=sp,log_sha256=log))
        save(work/'completed.json',completed)
        return ready, work, plan_path, plan_hash, manifest, names, old_plan

    def read_fixture(self, parts):
        ready, work, plan_path, digest, manifest, names, old_plan = parts
        with patch.multiple(native, READY=ready, READY_WORK=work, READY_PLAN=plan_path), \
             patch.object(native, 'checkpoint', return_value=(manifest,names)), \
             patch.object(native.old, 'frozen_plan', return_value=old_plan):
            return native.history(digest, work/'stages/unit-01/receipt.json')

    def test_completed_history_keeps_old_payloads_as_separate_verified_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            parts = self.fixture(Path(tmp).resolve())
            checked = self.read_fixture(parts)
            self.assertEqual(len(checked['historical_archives']),2)
            self.assertNotIn(str(Path(tmp).resolve()/'old-cold-payload'), checked['files'])
            self.assertIn(str(parts[1]/'source.json'), checked['files'])
            with patch.object(native,'sha',return_value='changed'):
                with self.assertRaisesRegex(RuntimeError, 'referenced historical archive changed'):
                    native.verify_references(checked)

    def test_missing_successful_stage_or_raw_child_tamper_rejects_before_any_native_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            parts = self.fixture(Path(tmp).resolve())
            completed = parts[1]/'completed.json'
            saved = completed.read_bytes(); data=json.loads(saved); del data['check']
            completed.write_text(json.dumps(data))
            with self.assertRaises(RuntimeError): self.read_fixture(parts)
            completed.write_bytes(saved)
            (parts[1]/'stages/unit-01/commands/000/stdout').write_text(result(26))
            with self.assertRaises(RuntimeError): self.read_fixture(parts)


if __name__ == '__main__':
    unittest.main()
