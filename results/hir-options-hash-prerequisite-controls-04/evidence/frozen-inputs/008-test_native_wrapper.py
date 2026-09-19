"""Synthetic successor associations with immutable source and failed history.

These controls do not assert that native03 has executed or qualified.
"""
import copy
import json
from pathlib import Path
import unittest

import prerequisites as p

A = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
N = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/.work/hir-options-hash-compiler-01')
INPUTS = [N/'source/compiler/rustc/src/main.rs', A/'.work/native-controls-failure-verification-01.json',
          A/'.work/hir-options-hash-native-controls-01/receipt.json',
          A/'.work/native-controls-failure-verification-02.json',
          A/'.work/hir-options-hash-native-controls-02/receipt.json']


class NativeWrapper(unittest.TestCase):
    def setUp(self):
        self.files = {path: path.read_bytes() for path in INPUTS}
        self.paths = dict(source=N/'source', stock_source=N/'native-controls-03/stock-main.rs')
        lines = self.files[INPUTS[0]].splitlines(keepends=True)
        derived = b''.join(lines[:3] + lines[4:])
        self.files[self.paths['stock_source']] = derived
        derivation = dict(source=str(INPUTS[0]), original_sha256=p.digest(self.files[INPUTS[0]]), original_size=2128,
            destination=str(self.paths['stock_source']), derived_sha256=p.digest(derived), derived_size=len(derived),
            removed_line=4, removed_bytes=lines[3].decode(), policy='remove-exact-cargo-unused-crate-expectation-v1')
        priors = [dict(source=str(A/('experiments/hir-options-hash-native-controls-' + suffix)),
            evidence=str(INPUTS[receipt].parent), audit=dict(path=str(INPUTS[audit]), sha256=p.digest(self.files[INPUTS[audit]])),
            receipt_sha256=p.digest(self.files[INPUTS[receipt]]), status='verified-retained-failure',
            actual_children=count, qualified_children=0, fixture_never_created=True)
            for suffix, audit, receipt, count in [('01', 1, 2, 5), ('02', 3, 4, 6)]]
        self.plan = dict(namespace=str(N), stock_source_derivation=copy.deepcopy(derivation), prior_failed_attempts=copy.deepcopy(priors))
        source = dict(path=str(self.paths['stock_source']), sha256=p.digest(derived), size=len(derived))
        self.terminal = dict(stock_source_derivation=copy.deepcopy(derivation), stock_source=copy.deepcopy(source))
        self.result = dict(stock_source_derivation=copy.deepcopy(derivation), stock_source=copy.deepcopy(source),
                           prior_failed_attempts=copy.deepcopy(priors), qualified_native_children=20, total_actual_native_children=31)

    def check(self):
        return p.native_wrapper(self.plan, self.terminal, self.result, paths=self.paths,
            read_json=lambda path: json.loads(self.files[Path(path)]), read_bytes=lambda path: self.files[Path(path)])

    def test_exact_private_copy_and_separate_failed_history(self):
        self.assertEqual(self.check(), dict(derived_sha256=p.digest(self.files[self.paths['stock_source']]),
            prior_failed_children=11, qualified_children=20, total_actual_children=31))

    def test_extra_private_source_edit_rejects(self):
        self.files[self.paths['stock_source']] += b'\n'
        with self.assertRaises(ValueError): self.check()

    def test_changed_original_source_rejects(self):
        self.files[INPUTS[0]] += b'\n'
        with self.assertRaises(ValueError): self.check()

    def test_old_artifact_namespace_rejects(self):
        self.paths['stock_source'] = N/'native-controls/stock-main.rs'
        with self.assertRaises(ValueError): self.check()

    def test_consistently_relabelled_derivation_rejects(self):
        for record in [self.plan, self.terminal, self.result]: record['stock_source_derivation']['removed_line'] = 5
        with self.assertRaises(ValueError): self.check()

    def test_consistently_relabelled_stock_digest_rejects(self):
        for record in [self.terminal, self.result]: record['stock_source']['sha256'] = '0'*64
        with self.assertRaises(ValueError): self.check()

    def test_failed_history_cannot_become_qualified(self):
        for record in [self.plan, self.result]: record['prior_failed_attempts'][0]['qualified_children'] = 5
        with self.assertRaises(ValueError): self.check()

    def test_eleven_historical_children_cannot_be_omitted(self):
        self.result['total_actual_native_children'] = 20
        with self.assertRaises(ValueError): self.check()

    def test_second_failure_cannot_be_omitted(self):
        for record in [self.plan, self.result]: record['prior_failed_attempts'].pop()
        with self.assertRaises(ValueError): self.check()

    def test_failed_attempts_cannot_be_reordered(self):
        for record in [self.plan, self.result]: record['prior_failed_attempts'].reverse()
        with self.assertRaises(ValueError): self.check()

    def test_second_failure_cannot_use_first_audit(self):
        for record in [self.plan, self.result]:
            record['prior_failed_attempts'][1]['audit'] = copy.deepcopy(record['prior_failed_attempts'][0]['audit'])
        with self.assertRaises(ValueError): self.check()

    def test_second_failed_history_cannot_become_qualified(self):
        for record in [self.plan, self.result]: record['prior_failed_attempts'][1]['qualified_children'] = 6
        with self.assertRaises(ValueError): self.check()


class NativeReconciliation(unittest.TestCase):
    """Tiny in-memory contracts, not synthetic claims about an actual run.

    The production outer reader separately checks fixed real file hashes,
    complete base/delta freezes, parser controls, and the independent audits.
    These fixtures target dishonest record combinations and saved raw history.
    """
    def setUp(self):
        self.files = {}
        self.original = dict(children=[], evidence_roots=[str(p.NATIVE_EVIDENCE)],
                             environment={'PATH': '/bin'}, marker='unchanged original value',
                             policy=dict(readonly=True, count=20))
        self.terminal = dict(status='failed', error=p.NATIVE_ERROR, pid=41, parent_pid=40,
            admitted_at=10, finished_at=100, commands=[], inputs_sha256=p.NATIVE_HASHES['inputs'],
            snapshot_plan_sha256=p.NATIVE_HASHES['snapshot_plan'])
        for index in range(20):
            declaration = dict(argv=['/fixture/compiler', str(index)], cwd='/fixture/source',
                environment={'PATH': '/bin'}, expected=[1 if index in [13, 14, 15, 18, 19] else 0],
                role='wrong-B3' if index >= 18 else 'native-history')
            self.original['children'].append(declaration)
            directory = p.NATIVE_EVIDENCE/'commands'/f'{index:03}'
            self.files[directory/'stdout'] = b'fixture output\n'
            self.files[directory/'stderr'] = b'fixture diagnostic\n'
            pid = 50 if index == 19 else 50 + index
            child = dict(status='finished', pid=pid, supervisor_pid=41, parent_pid=40,
                started_at=11+index*3, finished_at=12+index*3, command=declaration['argv'],
                environment=declaration['environment'], cwd=declaration['cwd'],
                expected=declaration['expected'], returncode=declaration['expected'][0],
                identity=dict(ps=f'{pid} 41 {pid} Fri Sep 18 12:00:{index:02} 2026 ?? '+
                              ' '.join(declaration['argv']), ps_returncode=0,
                              cwd=f'p{pid}\nfcwd\nn/fixture/source\n', cwd_returncode=0),
                stdout_sha256=p.digest(self.files[directory/'stdout']),
                stderr_sha256=p.digest(self.files[directory/'stderr']))
            self.files[directory/'receipt.json'] = self.encode(child)
            self.terminal['commands'].append(dict(path=str(directory/'receipt.json'),
                sha256=p.digest(self.files[directory/'receipt.json']), pid=pid,
                command=declaration['argv'], role=declaration['role']))
        command_evidence = dict(source=str(p.NATIVE_SOURCE), evidence=str(p.NATIVE_EVIDENCE),
            receipt_sha256=p.NATIVE_HASHES['receipt'], inputs_sha256=p.NATIVE_HASHES['inputs'],
            plan_sha256=p.NATIVE_HASHES['plan'], snapshot_plan_sha256=p.NATIVE_HASHES['snapshot_plan'],
            status='failed', error=p.NATIVE_ERROR, commands=copy.deepcopy(self.terminal['commands']),
            failure_audit=copy.deepcopy(p.NATIVE_FAILURE_AUDIT))
        reconciliation = dict(source=str(p.RECON_SOURCE), base_inputs=copy.deepcopy(p.NATIVE_BASE),
            original_parser=dict(path=str(p.NATIVE_SOURCE/'observations.py'), sha256=p.NATIVE_HASHES['parser']),
            parser=dict(path=str(p.RECON_SOURCE/'wrong_beta.py'), sha256='1'*64),
            parser_controls=dict(source=str(A/'experiments/native-wrong-beta-controls-01'),
                evidence=str(A/'.work/native-wrong-beta-controls-01'), controls=11,
                receipt_sha256='2'*64, result_sha256='3'*64,
                audit=copy.deepcopy(p.PARSER_CONTROL_AUDIT)),
            failure_audit=copy.deepcopy(p.NATIVE_FAILURE_AUDIT))
        provenance = dict(command_evidence=command_evidence, reconciliation=reconciliation)
        self.plan = copy.deepcopy(self.original) | copy.deepcopy(provenance) | dict(
            read_only_reconciliation=True, actual_workload_children=0, base_inputs=copy.deepcopy(p.NATIVE_BASE),
            wrong_beta_providers=[], wrong_beta_lib='/fixture/beta/lib',
            reconciliation_evidence_roots=sorted([str(p.NATIVE_EVIDENCE), str(p.RECON_EVIDENCE)]))
        self.qualification = copy.deepcopy(provenance) | dict(status='passed', pid=101, parent_pid=100,
            started_at=110, admitted_at=111, finished_at=120, commands=[],
            read_only_reconciliation=True, actual_workload_children=0, saved_actual_children=20,
            historical_failed_children=11, native_roles_and_behavior_qualified=True)
        self.result = copy.deepcopy(provenance) | dict(qualified_native_children=20,
            total_actual_native_children=31, history=copy.deepcopy(self.terminal['commands'][:18]),
            wrong_B3_commands=copy.deepcopy(self.terminal['commands'][18:]))

    @staticmethod
    def encode(value):
        return (json.dumps(value, sort_keys=True)+'\n').encode()

    def check(self):
        p._reconciliation_records(self.plan, self.original, self.terminal, self.qualification, self.result)
        return p._command_history(self.terminal, self.plan['children'], evidence=p.NATIVE_EVIDENCE,
            read_json=lambda path: json.loads(self.files[Path(path)]), read_bytes=lambda path: self.files[Path(path)])

    def test_two_real_owners_and_pid_reuse_remain_explicit(self):
        proof = self.check()
        self.assertEqual(len(proof['rows']), 20)
        self.assertEqual(self.terminal['status'], 'failed')
        self.assertEqual(self.qualification['commands'], [])
        self.assertEqual(proof['rows'][0]['receipt']['pid'], proof['rows'][19]['receipt']['pid'])
        self.assertEqual(proof['unavailable_contemporaneous_cwd_children'], [])

    def test_default_history_still_rejects_this_completed_failure(self):
        with self.assertRaises(ValueError):
            p.command_history(self.terminal, self.plan['children'], evidence=p.NATIVE_EVIDENCE,
                read_json=lambda path: json.loads(self.files[Path(path)]), read_bytes=lambda path: self.files[Path(path)])

    def test_forged_original_success_or_different_failure_rejects(self):
        for change in [dict(status='passed'), dict(error='some other failure'),
                       dict(result_sha256='5'*64), dict(wrong_B3={}), dict(native_roles_and_behavior_qualified=True)]:
            before = copy.deepcopy(self.terminal)
            self.terminal.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError): self.check()
            self.terminal = before

    def test_missing_or_failed_reconciliation_rejects(self):
        for change in [dict(status='failed'), dict(error='failure'), dict(read_only_reconciliation=False),
                       dict(native_roles_and_behavior_qualified=False)]:
            before = copy.deepcopy(self.qualification)
            self.qualification.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError): self.check()
            self.qualification = before

    def test_new_workload_or_boolean_counters_reject(self):
        for key, value in [('commands', [{}]), ('actual_workload_children', 1),
                           ('actual_workload_children', False), ('saved_actual_children', 19),
                           ('historical_failed_children', 0)]:
            before = copy.deepcopy(self.qualification)
            self.qualification[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError): self.check()
            self.qualification = before

    def test_omitted_or_changed_original_plan_rejects(self):
        for key, value in [('marker', 'changed'), ('children', self.plan['children'][:19]),
                           ('environment', {'PATH': '/other'})]:
            before = copy.deepcopy(self.plan)
            self.plan[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): self.check()
            self.plan = before
        self.plan.pop('marker')
        with self.assertRaises(ValueError): self.check()

    def test_omitted_base_or_changed_exact_reference_rejects(self):
        for key, value in [('base_inputs', {}), ('base_inputs', dict(p.NATIVE_BASE, sha256='0'*64))]:
            before = copy.deepcopy(self.plan)
            self.plan[key] = value
            with self.subTest(value=value), self.assertRaises(ValueError): self.check()
            self.plan = before
        for record in [self.plan, self.qualification, self.result]:
            record['command_evidence']['receipt_sha256'] = '0'*64
        with self.assertRaises(ValueError): self.check()

    def test_original_nested_boolean_cannot_become_integer(self):
        self.plan['policy']['readonly'] = 1
        with self.assertRaises(ValueError): self.check()

    def test_relabelled_failure_audit_rejects(self):
        for record in [self.plan, self.qualification, self.result]:
            record['command_evidence']['failure_audit']['sha256'] = '0'*64
            record['reconciliation']['failure_audit']['sha256'] = '0'*64
        with self.assertRaises(ValueError): self.check()

    def test_missing_parser_qualification_rejects(self):
        for record in [self.plan, self.qualification, self.result]:
            record['reconciliation']['parser_controls'] = {}
        with self.assertRaises(ValueError): self.check()

    def test_new_result_cannot_omit_or_reorder_saved_history(self):
        for key, value in [('history', self.result['history'][:17]),
                           ('wrong_B3_commands', self.result['wrong_B3_commands'][::-1]),
                           ('total_actual_native_children', 20), ('qualified_native_children', 31)]:
            before = copy.deepcopy(self.result)
            self.result[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): self.check()
            self.result = before

    def test_changed_raw_bytes_fail_even_after_record_contract_passes(self):
        self.files[p.NATIVE_EVIDENCE/'commands/019/stderr'] += b'changed\n'
        with self.assertRaises(ValueError): self.check()

    def test_saved_receipt_changed_without_reference_update_rejects(self):
        self.files[p.NATIVE_EVIDENCE/'commands/019/receipt.json'] += b' '
        with self.assertRaises(ValueError): self.check()

    def test_same_numeric_pid_requires_distinct_observed_start(self):
        path = p.NATIVE_EVIDENCE/'commands/019/receipt.json'
        child = json.loads(self.files[path])
        child['identity']['ps'] = child['identity']['ps'].replace('12:00:19', '12:00:00')
        self.files[path] = self.encode(child)
        ref = self.terminal['commands'][19]
        ref['sha256'] = p.digest(self.files[path])
        for record in [self.plan, self.qualification, self.result]:
            record['command_evidence']['commands'][19] = copy.deepcopy(ref)
        self.result['wrong_B3_commands'][1] = copy.deepcopy(ref)
        with self.assertRaises(ValueError): self.check()

    def test_saved_missing_cwd_remains_explicit_after_reconciliation(self):
        path = p.NATIVE_EVIDENCE/'commands/019/receipt.json'
        child = json.loads(self.files[path])
        child['identity'].update(cwd='', cwd_returncode=1)
        self.files[path] = self.encode(child)
        ref = self.terminal['commands'][19]
        ref['sha256'] = p.digest(self.files[path])
        for record in [self.plan, self.qualification, self.result]:
            record['command_evidence']['commands'][19] = copy.deepcopy(ref)
        self.result['wrong_B3_commands'][1] = copy.deepcopy(ref)
        self.assertEqual(self.check()['unavailable_contemporaneous_cwd_children'], [19])

    def test_reconciliation_cannot_precede_original_completion(self):
        self.qualification['started_at'] = 99
        with self.assertRaises(ValueError): self.check()

    def test_missing_original_or_fresh_evidence_root_rejects(self):
        for root in [p.NATIVE_EVIDENCE, p.RECON_EVIDENCE]:
            self.plan['reconciliation_evidence_roots'] = [str(root)]
            with self.subTest(root=root), self.assertRaises(ValueError): self.check()
        self.plan['reconciliation_evidence_roots'] = sorted([str(p.NATIVE_EVIDENCE), str(p.RECON_EVIDENCE),
                                                            str(A/'.work/hir-options-hash-native-controls-unknown')])
        with self.assertRaises(ValueError): self.check()


if __name__ == '__main__': unittest.main()
