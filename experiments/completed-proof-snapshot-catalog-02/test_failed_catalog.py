"""Tiny dictionary-only failed-owner tests; descriptors are not actual gzip proof."""
import copy
import stat
import unittest
from pathlib import PurePosixPath as Path

import catalog as c
from test_catalog import Fixture, LIMITS


class FailedFixture(Fixture):
    def __init__(self, *, compact=False):
        super().__init__(compact=compact)
        for table in [self.docs, self.rows]:
            del table[str(self.work/'result.json')]
        self.receipt.pop('result_sha256')
        self.receipt.update(status='failed', error="RuntimeError('expected fixture failure')")
        self.owner = {key:value for key,value in self.owner.items()
                      if key not in ['result_path', 'result_digest_field']}
        self.reads = []
        self.seal_failed()

    def seal_failed(self):
        snapshot = dict(inputs_sha256=self.receipt['inputs_sha256'],
            helper=dict(path=self.helper['path'], sha256=self.helper['sha256']),
            limits=copy.deepcopy(LIMITS), projection=copy.deepcopy(self.projection))
        row = self.document(self.source/'snapshot-plan.json', snapshot)
        self.document(self.work/'snapshot-plan.json', snapshot)
        self.manifest['projection_sha256'] = c.sha(self.projection)
        manifest = self.document(self.work/'source-snapshots.json', self.manifest)
        self.receipt.update(snapshot_plan_sha256=row['sha256'], source_snapshots_sha256=manifest['sha256'])
        receipt = self.document(self.work/'receipt.json', self.receipt)
        self.audit = dict(status='verified-retained-failure', receipt_sha256=receipt['sha256'],
            inputs_sha256=self.receipt['inputs_sha256'],
            plan_sha256=self.rows[str(self.source/'plan.json')]['sha256'],
            snapshot_plan_sha256=row['sha256'], source_snapshots_sha256=manifest['sha256'],
            actual_compiler_children=1, actual_driver_processes=0, qualified_hash_driver_processes=0,
            fixture_outer_closed=True, fixture_raw_complete=True)
        self.reseal_audit()

    def reseal_audit(self):
        self.owner['audit']['sha256'] = self.document(self.owner['audit']['path'], self.audit)['sha256']

    def read(self, name):
        self.reads.append(str(name))
        return copy.deepcopy(self.docs[str(name)])

    @staticmethod
    def closed(owner, receipt, audit):
        # Synthetic owner-specific closure only; these controls do not claim
        # that dictionary booleans prove any real process or gzip completion.
        return (receipt['status'] == 'failed' and audit['fixture_outer_closed'] is True
                and audit['fixture_raw_complete'] is True and audit['actual_compiler_children'] == 1
                and audit['actual_driver_processes'] == audit['qualified_hash_driver_processes'] == 0)

    def extend_failed(self, **overrides):
        callbacks = dict(read_json=self.read, file_record=lambda p:copy.deepcopy(self.rows[str(p)]),
            directory_record=lambda p:copy.deepcopy(self.dirs[str(p)]),
            expand_inputs=lambda raw,row:copy.deepcopy(self.freeze if self.compact else raw),
            validate_failure=self.closed)
        callbacks.update(overrides)
        return c.extend_failed(self.prior, self.owner, self.roots, LIMITS, **callbacks)

    def successful_successor(self):
        """A second tiny owner really succeeds; the prior failed owner stays failed."""
        later = Fixture()
        later.rows, later.docs, later.dirs = [copy.deepcopy(value) for value in [self.rows, self.docs, self.dirs]]
        later.serial = self.serial
        later.source, later.work = Path('/source/later'), Path('/evidence/later')
        later.root = later.work/'source-snapshots'
        later.prior = self.extend_failed(); later.roots = sorted(self.roots+['/evidence/later'])
        later.plan = dict(snapshot_reuse=copy.deepcopy(later.prior), evidence_roots=list(later.roots))
        plan = later.document(later.source/'plan.json', later.plan)
        later.freeze = copy.deepcopy(self.freeze); later.freeze['plan_sha256'] = plan['sha256']
        later.compact = False
        own = later.document(later.source/'inputs.json', later.freeze)
        later.files = {row['path']:copy.deepcopy(row) for row in [later.a,later.alias,later.b,own]}
        selection = c.select(list(later.files.values()), later.prior)
        reuse = {row['blob']['logical_sha256']:row for row in selection['records']}
        fresh = later.blob(own, later.root)
        blobs = {key:row['blob'] for key,row in reuse.items()}; blobs[fresh['logical_sha256']] = fresh
        storage = {key:dict(kind='reused', path=row['path']) for key,row in reuse.items()}
        storage[fresh['logical_sha256']] = dict(kind='stored')
        total = sum(row['compressed_bytes'] for row in blobs.values()); new = fresh['compressed_bytes']
        later.projection = dict(policy=c.SNAPSHOT_POLICY, limits=copy.deepcopy(LIMITS), files=copy.deepcopy(later.files),
            blobs=blobs, logical_bytes=sum(row['size'] for row in later.files.values()),
            unique_logical_bytes=sum(row['logical_bytes'] for row in blobs.values()),
            compressed_bytes=total, new_compressed_bytes=new, reused_compressed_bytes=total-new,
            compressed_allocated_bytes=sum(later.round(row['compressed_bytes']) for row in blobs.values()),
            new_compressed_allocated_bytes=later.round(new), storage=storage, reuse=copy.deepcopy(reuse),
            evidence_roots=copy.deepcopy(selection['evidence_roots']), manifest_reservation_bytes=2*LIMITS['maximum_manifest_bytes'])
        physical = {key:(dict(value) if value['kind'] == 'reused'
                         else dict(kind='stored', path=str(later.root/blobs[key]['filename']))) for key,value in storage.items()}
        later.manifest = dict(policy=c.SNAPSHOT_POLICY, projection_sha256=c.sha(later.projection),
            files={name:dict(path=physical[row['sha256']]['path'], sha256=row['sha256'], size=row['size'], encoding='gzip')
                   for name,row in later.files.items()}, blobs=copy.deepcopy(blobs), storage=physical,
            reuse=copy.deepcopy(reuse), evidence_roots=copy.deepcopy(selection['evidence_roots']),
            compressed_bytes=total, new_compressed_bytes=new, reused_compressed_bytes=total-new,
            full_logical_readback=True, full_gzip_eof=True)
        later.dirs[str(later.root)] = dict(identity=later.stamp(stat.S_IFDIR|0o700, 0), children=[fresh['filename']])
        result = later.document(later.work/'result.json', later.result)
        later.receipt = dict(status='passed', started_at=4, admitted_at=5, finished_at=6,
            inputs_sha256=own['sha256'], result_sha256=result['sha256'])
        later.owner = dict(role='later', source=str(later.source), evidence=str(later.work),
            audit=dict(path='/audits/later.json', sha256='0'*64), result_path=str(later.work/'result.json'),
            result_digest_field='result_sha256')
        later.seal()
        return later


class FailedCatalogTests(unittest.TestCase):
    def test_closed_failed_owner_preserves_all_aliases_without_result_read(self):
        fixture = FailedFixture(); result = fixture.extend_failed()
        self.assertEqual(result['policy'], c.FAILED_POLICY)
        self.assertEqual(result['predecessors'][-1]['completion'], 'failed')
        self.assertNotIn('result', result['predecessors'][-1])
        self.assertNotIn(str(fixture.work/'result.json'), fixture.reads)
        self.assertEqual(len(result['records']), 3)
        self.assertEqual(len(c.select(list(fixture.files.values()), result)['records']), 3)
        self.assertEqual(fixture.receipt['status'], 'failed')

    def test_compact_failed_owner_preserves_raw_input_digest(self):
        fixture = FailedFixture(compact=True); result = fixture.extend_failed()
        self.assertEqual(result['predecessors'][-1]['inputs']['sha256'], fixture.receipt['inputs_sha256'])
        self.assertIn('file_table_base', result['predecessors'][-1])

    def test_successful_successor_keeps_failed_predecessor_distinct(self):
        later = FailedFixture().successful_successor(); result = later.extend()
        self.assertEqual(result['policy'], c.FAILED_POLICY)
        self.assertEqual(result['priority'], ['ancestor','current','later'])
        self.assertEqual(result['predecessors'][1]['completion'], 'failed')
        self.assertNotIn('completion', result['predecessors'][2])
        self.assertIn('result', result['predecessors'][2])
        self.assertEqual(len(result['records']), 4)

    def test_unchanged_successful_api_refuses_failed_owner(self):
        fixture = Fixture(); fixture.receipt['status'] = 'failed'; fixture.seal()
        with self.assertRaisesRegex(ValueError, 'closed passed'): fixture.extend()

    def test_result_fields_cannot_be_smuggled_into_failed_owner(self):
        fixture = FailedFixture(); fixture.owner['result_path'] = '/evidence/current/result.json'
        with self.assertRaisesRegex(ValueError, 'without result'): fixture.extend_failed()

    def test_success_or_unfinished_terminal_is_not_a_closed_failure(self):
        for status in ['passed', 'running', 'waiting', 'passed-awaiting-independent-audit']:
            with self.subTest(status=status):
                fixture = FailedFixture(); fixture.receipt['status'] = status; fixture.seal_failed()
                with self.assertRaisesRegex(ValueError, 'closed failed'): fixture.extend_failed()

    def test_original_failure_error_and_typed_times_are_required(self):
        for field, value in [('error',''), ('error',False), ('admitted_at',True),
                             ('admitted_at',float('inf')), ('finished_at',1)]:
            with self.subTest(field=field, value=repr(value)):
                fixture = FailedFixture(); fixture.receipt[field] = value
                if value == float('inf'):
                    # The strict callback JSON copy refuses nonfinite evidence.
                    fixture.docs[str(fixture.work/'receipt.json')][field] = value
                else:
                    fixture.seal_failed()
                with self.assertRaises(ValueError): fixture.extend_failed()

    def test_passed_audit_cannot_relabel_failed_terminal(self):
        fixture = FailedFixture(); fixture.audit['status'] = 'verified'; fixture.reseal_audit()
        with self.assertRaisesRegex(ValueError, 'closed failed'): fixture.extend_failed()

    def test_each_failure_audit_document_digest_is_bound(self):
        for field in ['receipt_sha256','inputs_sha256','plan_sha256','snapshot_plan_sha256','source_snapshots_sha256']:
            with self.subTest(field=field):
                fixture = FailedFixture(); fixture.audit[field] = 'f'*64; fixture.reseal_audit()
                with self.assertRaisesRegex(ValueError, 'audit source/snapshot'): fixture.extend_failed()

    def test_missing_independent_failure_audit_refuses(self):
        fixture = FailedFixture(); del fixture.docs[fixture.owner['audit']['path']]
        with self.assertRaises(KeyError): fixture.extend_failed()

    def test_full_owner_specific_raw_and_outer_closure_are_required(self):
        for field in ['fixture_outer_closed','fixture_raw_complete']:
            with self.subTest(field=field):
                fixture = FailedFixture(); fixture.audit[field] = False; fixture.reseal_audit()
                with self.assertRaisesRegex(ValueError, 'history and closure'): fixture.extend_failed()

    def test_callback_must_return_literal_true(self):
        for value in [False, 1, 'verified']:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'history and closure'):
                    FailedFixture().extend_failed(validate_failure=lambda *args:value)

    def test_callback_argument_mutation_has_no_alias_authority(self):
        fixture = FailedFixture(); before = copy.deepcopy([fixture.owner,fixture.receipt,fixture.audit])
        def mutation(owner, receipt, audit):
            owner.clear(); receipt['status'] = 'passed'; audit.clear(); return True
        result = fixture.extend_failed(validate_failure=mutation)
        self.assertEqual([fixture.owner,fixture.receipt,fixture.audit], before)
        self.assertEqual(result['predecessors'][-1]['completion'], 'failed')

    def test_callback_external_document_mutation_is_detected(self):
        fixture = FailedFixture()
        def mutation(*args):
            fixture.docs[str(fixture.work/'receipt.json')]['error'] = 'changed after initial read'; return True
        with self.assertRaisesRegex(ValueError, 'changed during catalog'):
            fixture.extend_failed(validate_failure=mutation)

    def test_callback_external_file_identity_mutation_is_detected(self):
        fixture = FailedFixture()
        def mutation(*args):
            fixture.rows[str(fixture.work/'receipt.json')]['identity']['ctime_ns'] += 1; return True
        with self.assertRaisesRegex(ValueError, 'changed during catalog'):
            fixture.extend_failed(validate_failure=mutation)

    def test_alias_omission_is_rejected_for_failed_owner(self):
        fixture = FailedFixture(); del fixture.manifest['files'][fixture.alias['path']]; fixture.seal_failed()
        with self.assertRaisesRegex(ValueError, 'storage/mapping'): fixture.extend_failed()

    def test_failed_owner_still_needs_every_original_selected_byte(self):
        fixture = FailedFixture(); del fixture.rows[fixture.b['path']]
        with self.assertRaises(KeyError): fixture.extend_failed()

    def test_failed_snapshot_eof_attestation_cannot_be_omitted(self):
        fixture = FailedFixture(); fixture.manifest['full_gzip_eof'] = False; fixture.seal_failed()
        with self.assertRaisesRegex(ValueError, 'complete qualified'): fixture.extend_failed()

    def test_failed_owner_cannot_escape_aggregate_accounting(self):
        fixture = FailedFixture(); fixture.roots.remove('/evidence/current')
        with self.assertRaisesRegex(ValueError, 'outside counted evidence'): fixture.extend_failed()

    def test_failed_owner_cannot_double_credit_an_ancestor_inode(self):
        fixture = FailedFixture(); key = fixture.b['sha256']
        fixture.rows[str(fixture.root/(key+'.gz'))]['identity']['ino'] = fixture.prior['records'][0]['identity']['ino']
        with self.assertRaisesRegex(ValueError, 'duplicate physical'): fixture.extend_failed()

    def test_reused_blob_cannot_be_reattributed_to_failure(self):
        fixture = FailedFixture(); key = fixture.a['sha256']
        fixture.projection['storage'][key] = dict(kind='stored'); fixture.seal_failed()
        with self.assertRaisesRegex(ValueError, 'descriptor/path'): fixture.extend_failed()

    def test_failed_policy_cannot_be_downgraded(self):
        fixture = FailedFixture(); result = fixture.extend_failed(); result['policy'] = c.POLICY
        with self.assertRaisesRegex(ValueError, 'lineage policy'): c.select(list(fixture.files.values()), result)

    def test_failed_association_cannot_acquire_a_success_result(self):
        fixture = FailedFixture(); result = fixture.extend_failed()
        result['predecessors'][-1]['result'] = dict(path='/invented/result.json', sha256='1'*64)
        with self.assertRaisesRegex(ValueError, 'failed-owner association'): c.select(list(fixture.files.values()), result)

    def test_failed_association_route_must_stay_with_original_owner(self):
        fixture = FailedFixture(); result = fixture.extend_failed()
        result['predecessors'][-1]['receipt']['path'] = '/evidence/other/receipt.json'
        with self.assertRaisesRegex(ValueError, 'document route'): c.select(list(fixture.files.values()), result)

    def test_failed_reservation_uses_only_new_physical_allocation(self):
        fixture = FailedFixture(); fixture.extend_failed()
        self.assertEqual(c.reservation(fixture.projection,4*2**20,32*2**20), 40*2**20+4*4096)
        fixture.projection['new_compressed_allocated_bytes'] = 0
        fixture.seal_failed()
        with self.assertRaisesRegex(ValueError, 'physical accounting'): fixture.extend_failed()


if __name__ == '__main__':
    unittest.main(verbosity=2)
