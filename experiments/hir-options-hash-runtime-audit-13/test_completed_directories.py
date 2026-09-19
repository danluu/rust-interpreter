"""Focused declaration and actual qualified-Access regression fixtures.

All owner documents below are synthetic in-memory callbacks. Physical fixtures
use only a test-owned temporary tree. These are integration regressions, never
claims of actual runtime/failure-owner qualification or additions to old53.
"""
import copy
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import audit

_spec = importlib.util.spec_from_file_location('completed_directory_test_access',
    audit.QUALIFIED_AUDIT/'audit_io.py')
access = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(access)


class DeclarationTests(unittest.TestCase):
    def setUp(self):
        self.work = Path('/owned/completed/failed')
        self.source = audit.HASH.with_name('hir-options-hash-driver-stage-02')
        self.artifacts = Path('/owned/completed/artifacts')
        self.documents = {}; self.files = {}
        def reference(path, document):
            name = str(path); digest = hashlib.sha256(audit.encoded(document)).hexdigest()
            self.documents[name] = document; self.files[name] = dict(sha256=digest)
            return dict(path=name,sha256=digest)
        self.reference = reference
        fixture = self.artifacts/'fixture.rs'
        children = [dict(argv=['rustc','-o',str(self.artifacts/'hash-control-driver')],
                         environment=dict(TMPDIR=str(self.artifacts/'tmp')))]
        children += [dict(argv=['driver','sysroot',str(fixture),str(self.artifacts/name),name],
                          environment=dict(TMPDIR=str(self.artifacts/'tmp'))) for name in ['serial','parallel']]
        original = dict(children=children)
        association = dict(role='failed-hash-driver-01',completion='failed',source=str(self.source),
            evidence=str(self.work),snapshot_root=str(self.work/'source-snapshots'))
        for key,path,doc in [('plan',self.source/'plan.json',original),
             ('receipt',self.work/'receipt.json',dict(status='failed')),
             ('manifest',self.work/'source-snapshots.json',{}),
             ('projection',self.source/'snapshot-plan.json',{}),
             ('retained_projection',self.work/'snapshot-plan.json',{})]:
            association[key] = reference(path,doc)
        fixture_sha = hashlib.sha256(b'fixture').hexdigest()
        self.files[str(fixture)] = dict(sha256=fixture_sha)
        saved = dict(status='verified-retained-failure',source=str(self.source),evidence=str(self.work),
            receipt_sha256=association['receipt']['sha256'],plan_sha256=association['plan']['sha256'],
            source_snapshots_sha256=association['manifest']['sha256'],snapshot_plan_sha256=association['projection']['sha256'],
            actual_compiler_children=1,actual_driver_processes=0,hash_driver_qualified=False,
            complete_failed_raw_history=True,full_snapshot_selection=True,
            artifacts={'fixture.rs':dict(kind='file',sha256=fixture_sha),
                       **{name:dict(kind='directory') for name in ['serial','parallel','tmp']}},
            absent_outputs=list(map(str,[self.work/'result.json',self.work/'serial',self.work/'parallel',
                self.work/'linker-command.json',self.work/'driver-loader-closure.json',self.artifacts/'hash-control-driver'])))
        association['audit'] = reference('/owned/failure-audit.json',saved)
        self.owner = {key:copy.deepcopy(association[key]) for key in ['role','source','evidence','audit']}
        wire = dict(policy='external-json-member-v1',member='metadata_plan',reference={},integrity={},
                    remainder=dict(failed_driver=self.owner))
        reference(audit.HASH_PLAN['path'],wire)
        # The callback boundary supplies externally authenticated byte digests.
        # Synthetic documents never stand in for an actual saved proof.
        self.files[audit.HASH_PLAN['path']]['sha256'] = audit.HASH_PLAN['sha256']
        self.authority = b'synthetic frozen membership source'
        self.authority_sha = hashlib.sha256(self.authority).hexdigest()
        self.files[str(audit.HASH/'failed_driver.py')] = dict(sha256=self.authority_sha)
        for name in ['receipt.json','stdout','stderr']:
            self.files[str(self.work/'compile'/name)] = dict(sha256='1'*64)
        self.plan = dict(evidence_roots=[str(self.work)],snapshot_reuse=dict(
            predecessors=[association],evidence_roots={str(self.work/'source-snapshots'): {}}))

    def derive(self):
        with patch.object(audit,'COMPLETED_READER_SHA',self.authority_sha):
            return audit.completed_directory_declarations(self.plan,self.files,
                read_json=lambda p:copy.deepcopy(self.documents[str(p)]),
                read_bytes=lambda p:self.authority,sha=lambda p:self.files[str(p)]['sha256'])

    def test_exact_six_and_three_explicit_empty_directories(self):
        value = self.derive();dirs=value['directories']
        self.assertEqual(set(dirs),{str(self.work),str(self.work/'compile'),str(self.artifacts),
            *[str(self.artifacts/name) for name in ['serial','parallel','tmp']]})
        self.assertEqual(dirs[str(self.work)],['compile','receipt.json','snapshot-plan.json','source-snapshots','source-snapshots.json'])
        self.assertEqual(dirs[str(self.work/'compile')],['receipt.json','stderr','stdout'])
        self.assertEqual(dirs[str(self.artifacts)],['fixture.rs','parallel','serial','tmp'])
        self.assertEqual([name for name,children in dirs.items() if not children],
            sorted(str(self.artifacts/name) for name in ['serial','parallel','tmp']))
        self.assertEqual(value['owner'],self.owner)

    def test_failed_association_cannot_be_relabelled_success(self):
        self.plan['snapshot_reuse']['predecessors'][0]['completion']='passed'
        with self.assertRaisesRegex(RuntimeError,'accounted completed predecessor'):self.derive()

    def test_unaccounted_owner_rejected(self):
        self.plan['evidence_roots']=[]
        with self.assertRaisesRegex(RuntimeError,'accounted completed predecessor'):self.derive()

    def test_artifact_recipe_cannot_add_unrelated_directory(self):
        self.documents[str(self.source/'plan.json')]['children'][1]['argv'][3]='/unrelated/serial'
        with self.assertRaisesRegex(RuntimeError,'exact original recipe'):self.derive()

    def test_directory_authority_cannot_supply_missing_payload(self):
        del self.files[str(self.work/'compile/stdout')]
        with self.assertRaisesRegex(RuntimeError,'missing payload authorization'):self.derive()

    def test_changed_membership_reader_rejected(self):
        self.authority=b'changed source'
        with self.assertRaisesRegex(RuntimeError,'membership reader required'):self.derive()


class AccessIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='completed-directory-regression-')
        self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name).resolve()
        self.work=self.base/'work';self.artifacts=self.base/'artifacts'
        for name in [self.work,self.work/'compile',self.artifacts,
                     *[self.artifacts/n for n in ['serial','parallel','tmp']]]:
            name.mkdir()
        self.receipt=self.work/'receipt.json';self.receipt.write_bytes(b'{}')
        self.files={str(self.receipt):dict(size=2,sha256=hashlib.sha256(b'{}').hexdigest(),
            identity=access.stamp(self.receipt.stat()))}
        directories={str(self.work):['compile','receipt.json'],str(self.work/'compile'):[],
            str(self.artifacts):['parallel','serial','tmp'],
            **{str(self.artifacts/n):[] for n in ['serial','parallel','tmp']}}
        self.declaration=dict(directories=directories)
        self.entries={name:access.stamp(Path(name).stat()) for name in directories}

    def test_frozen_child_does_not_authorize_parent_but_exact_entry_does(self):
        original=access.Access(self.files)
        with self.assertRaisesRegex(RuntimeError,'undeclared saved-evidence path'):
            original.directory_record(self.work)
        corrected=access.Access(self.files,entries=self.entries)
        observed=audit.completed_directory_readback(self.declaration,corrected)
        self.assertEqual(len(observed),6)
        self.assertEqual(corrected.output_roots,())
        self.assertEqual(corrected.files,self.files)
        self.assertEqual(corrected.read_bytes(self.receipt),b'{}')
        with self.assertRaisesRegex(RuntimeError,'undeclared saved-evidence path'):
            corrected.read_bytes(self.artifacts/'not-frozen')
        corrected.recheck(full=True)

    def test_membership_change_rejected_after_first_observation(self):
        io=access.Access(self.files,entries=self.entries)
        audit.completed_directory_readback(self.declaration,io)
        (self.artifacts/'tmp'/'unexpected').write_bytes(b'x')
        with self.assertRaises(RuntimeError):audit.completed_directory_readback(self.declaration,io)

    def test_symlink_replacement_rejected_without_subtree_access(self):
        io=access.Access(self.files,entries=self.entries)
        audit.completed_directory_readback(self.declaration,io)
        target=self.artifacts/'tmp';target.rmdir();target.symlink_to(self.work,target_is_directory=True)
        with self.assertRaises(RuntimeError):audit.completed_directory_readback(self.declaration,io)


if __name__=='__main__':
    unittest.main()
