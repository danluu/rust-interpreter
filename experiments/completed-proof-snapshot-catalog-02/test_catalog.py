"""Synthetic in-memory contracts. No files, compression, or process fixtures."""
import copy
import hashlib
from pathlib import PurePosixPath as Path
import stat
import unittest

import catalog as c

LIMITS = dict(maximum_files=1024, maximum_file_bytes=64*2**20,
              maximum_logical_bytes=512*2**20, maximum_compressed_bytes=128*2**20,
              maximum_manifest_bytes=4*2**20)


class Fixture:
    def __init__(self, *, compact=False):
        self.rows = {}; self.docs = {}; self.dirs = {}; self.serial = 0
        self.source = Path('/source/current'); self.work = Path('/evidence/current')
        self.oldroot = Path('/evidence/old/source-snapshots'); self.root = self.work/'source-snapshots'
        self.roots = ['/evidence/current', '/evidence/old']
        self.a = self.file('/source/a', b'old logical payload')
        self.alias = self.file('/source/alias', b'old logical payload')
        self.b = self.file('/source/b', b'new logical payload')
        self.helper = self.file('/helpers/snapshots.py', b'qualified helper bytes')
        self.oldblob = self.blob(self.a, self.oldroot)
        oldrow = self.rows[str(self.oldroot/self.oldblob['filename'])]
        self.dirs[str(self.oldroot)] = dict(identity=self.stamp(stat.S_IFDIR|0o700, 0), children=[self.oldblob['filename']])
        self.prior = dict(policy=c.ANCESTOR_POLICY, priority=['ancestor'], predecessors=[dict(role='ancestor')],
            records=[dict(path=oldrow['path'], identity=oldrow['identity'], blob=self.oldblob, evidence_root=str(self.oldroot))],
            evidence_roots={str(self.oldroot):self.dirs[str(self.oldroot)]['identity']})
        self.plan = dict(snapshot_reuse=copy.deepcopy(self.prior), evidence_roots=list(self.roots))
        planrow = self.document(self.source/'plan.json', self.plan)
        self.freeze = dict(files={r['path']:{k:v for k,v in r.items() if k != 'path'}
                                 for r in [self.a,self.alias,self.b,self.helper]},
            links={}, absent_paths=[], snapshot_inputs=[r['path'] for r in [self.alias,self.b,self.a]],
            plan_sha256=planrow['sha256'])
        self.compact = compact
        wire = copy.deepcopy(self.freeze)
        if compact:
            base = self.document('/source/base-inputs.json',dict(files={self.a['path']:self.freeze['files'][self.a['path']]}))
            self.freeze['files'][base['path']]={k:v for k,v in base.items() if k != 'path'}
            wire = copy.deepcopy(self.freeze);del wire['files'][self.a['path']]
            wire['file_table_base']=dict(path=base['path'],sha256=base['sha256'])
            wire['file_table_integrity']=dict(sha256=c.sha(self.freeze['files']),count=len(self.freeze['files']),
                                            total_bytes=sum(v['size'] for v in self.freeze['files'].values()))
        inputrow = self.document(self.source/'inputs.json', wire)
        self.files = {r['path']:copy.deepcopy(r) for r in [self.a,self.alias,self.b,inputrow]}
        fresh = self.blob(self.b, self.root); own = self.blob(inputrow, self.root)
        blobs = {v['logical_sha256']:v for v in [self.oldblob,fresh,own]}
        reuse = {self.a['sha256']:copy.deepcopy(self.prior['records'][0])}
        storage = {k:(dict(kind='reused',path=self.prior['records'][0]['path']) if k in reuse else dict(kind='stored')) for k in blobs}
        newkeys = set(blobs)-set(reuse)
        total = sum(v['compressed_bytes'] for v in blobs.values())
        new = sum(blobs[k]['compressed_bytes'] for k in newkeys)
        self.projection = dict(policy=c.SNAPSHOT_POLICY, limits=copy.deepcopy(LIMITS), files=copy.deepcopy(self.files), blobs=blobs,
            logical_bytes=sum(r['size'] for r in self.files.values()), unique_logical_bytes=sum(v['logical_bytes'] for v in blobs.values()),
            compressed_bytes=total,new_compressed_bytes=new,reused_compressed_bytes=total-new,
            compressed_allocated_bytes=sum(self.round(v['compressed_bytes']) for v in blobs.values()),
            new_compressed_allocated_bytes=sum(self.round(blobs[k]['compressed_bytes']) for k in newkeys),
            storage=storage,reuse=reuse,evidence_roots=copy.deepcopy(self.prior['evidence_roots']),
            manifest_reservation_bytes=2*LIMITS['maximum_manifest_bytes'])
        physical = {k:(dict(storage[k]) if k in reuse else dict(kind='stored',path=str(self.root/blobs[k]['filename']))) for k in blobs}
        self.manifest = dict(policy=c.SNAPSHOT_POLICY,projection_sha256=c.sha(self.projection),
            files={n:dict(path=physical[r['sha256']]['path'],sha256=r['sha256'],size=r['size'],encoding='gzip') for n,r in self.files.items()},
            blobs=copy.deepcopy(blobs),storage=physical,reuse=copy.deepcopy(reuse),evidence_roots=copy.deepcopy(self.prior['evidence_roots']),
            compressed_bytes=total,new_compressed_bytes=new,reused_compressed_bytes=total-new,full_logical_readback=True,full_gzip_eof=True)
        self.dirs[str(self.root)] = dict(identity=self.stamp(stat.S_IFDIR|0o700,0),children=sorted(blobs[k]['filename'] for k in newkeys))
        self.result = dict(status='owner-qualified')
        resultrow = self.document(self.work/'result.json',self.result)
        self.receipt = dict(status='passed-awaiting-independent-audit',started_at=1,admitted_at=2,finished_at=3,
            inputs_sha256=inputrow['sha256'],result_sha256=resultrow['sha256'])
        self.owner = dict(role='current',source=str(self.source),evidence=str(self.work),
            audit=dict(path='/audits/current.json',sha256='0'*64),result_path=str(self.work/'result.json'),result_digest_field='result_sha256')
        self.seal()

    def stamp(self,mode,size):
        self.serial += 1
        return dict(dev=1,ino=self.serial,mode=mode,nlink=1,size=size,mtime_ns=10,ctime_ns=10)

    def file(self,name,data):
        name = str(name)
        old = self.rows.get(name)
        identity = self.stamp(stat.S_IFREG|0o444,len(data)) if old is None else dict(old['identity'],size=len(data))
        row = dict(path=name,size=len(data),sha256=hashlib.sha256(data).hexdigest(),identity=identity)
        self.rows[name] = row
        return row

    def document(self,name,value):
        self.docs[str(name)] = copy.deepcopy(value)
        return self.file(name,c.encoded(value))

    def blob(self,logical,root):
        # Catalog tests only compare frozen descriptors. Qualified helper tests
        # separately cover actual gzip bytes and complete logical/physical EOF.
        payload = b'synthetic compressed descriptor '+logical['sha256'].encode()
        row = self.file(root/(logical['sha256']+'.gz'),payload)
        return dict(filename=logical['sha256']+'.gz',logical_sha256=logical['sha256'],logical_bytes=logical['size'],
                    sha256=row['sha256'],compressed_bytes=row['size'])

    @staticmethod
    def round(size):return (size+4095)//4096*4096

    def seal(self):
        snapshot = dict(inputs_sha256=self.receipt['inputs_sha256'],helper=dict(path=self.helper['path'],sha256=self.helper['sha256']),
                        limits=copy.deepcopy(LIMITS),projection=copy.deepcopy(self.projection))
        row = self.document(self.source/'snapshot-plan.json',snapshot)
        self.document(self.work/'snapshot-plan.json',snapshot)
        self.manifest['projection_sha256'] = c.sha(self.projection)
        manifestrow = self.document(self.work/'source-snapshots.json',self.manifest)
        self.receipt.update(snapshot_plan_sha256=row['sha256'],source_snapshots_sha256=manifestrow['sha256'])
        receiptrow = self.document(self.work/'receipt.json',self.receipt)
        audit = dict(status='verified',receipt_sha256=receiptrow['sha256'],result_sha256=self.receipt[self.owner['result_digest_field']])
        self.owner['audit']['sha256'] = self.document(self.owner['audit']['path'],audit)['sha256']

    def extend(self,**overrides):
        callbacks = dict(read_json=lambda p:copy.deepcopy(self.docs[str(p)]),
                         file_record=lambda p:copy.deepcopy(self.rows[str(p)]),
                         directory_record=lambda p:copy.deepcopy(self.dirs[str(p)]),
                         expand_inputs=lambda raw,row:copy.deepcopy(self.freeze if self.compact else raw),
                         validate_owner=lambda owner,receipt,result,audit:result['status']=='owner-qualified')
        callbacks.update(overrides)
        return c.extend(self.prior,self.owner,self.roots,LIMITS,**callbacks)


class CatalogTests(unittest.TestCase):
    def test_complete_aliases_and_physical_roots(self):
        f=Fixture();out=f.extend()
        self.assertEqual(out['priority'],['ancestor','current'])
        self.assertEqual(len(out['records']),3)
        self.assertEqual(set(out['evidence_roots']),{str(f.oldroot),str(f.root)})
        self.assertEqual(out['predecessors'][-1]['inherited_catalog_sha256'],c.sha(f.prior))
        self.assertEqual(len(c.select(list(f.files.values()),out)['records']),3)
        self.assertEqual(len(f.files),4)

    def test_historical_order_does_not_drop_alias(self):
        f=Fixture();self.assertNotEqual(f.freeze['snapshot_inputs'],sorted(f.freeze['snapshot_inputs']))
        self.assertEqual(len(f.extend()['records']),3)

    def test_compact_raw_digest_and_expanded_selection(self):
        f=Fixture(compact=True);out=f.extend()
        self.assertEqual(out['predecessors'][-1]['inputs']['sha256'],f.receipt['inputs_sha256'])
        self.assertEqual(len(out['records']),3)

    def test_compact_full_integrity_cannot_be_changed(self):
        f=Fixture(compact=True)
        def bad(raw,row):
            value=copy.deepcopy(f.freeze);value['files'][f.a['path']]['size']+=1;return value
        with self.assertRaisesRegex(ValueError,'base/delta|input integrity'):f.extend(expand_inputs=bad)

    def test_failed_owner_never_gets_reuse_credit(self):
        f=Fixture();f.receipt['status']='failed';f.seal()
        with self.assertRaisesRegex(ValueError,'closed passed'):f.extend()

    def test_role_specific_recipe_must_pass(self):
        with self.assertRaisesRegex(ValueError,'owner-specific'):Fixture().extend(validate_owner=lambda *a:False)
        f=Fixture();before=copy.deepcopy(f.owner)
        def mutation(owner,receipt,result,audit):
            owner['result_path']='/outside/result.json';receipt['inputs_sha256']='0'*64
            result.clear();audit.clear();return True
        self.assertEqual(len(f.extend(validate_owner=mutation)['records']),3)
        self.assertEqual(f.owner,before)

    def test_audit_result_digest_must_match(self):
        f=Fixture();doc=f.docs[f.owner['audit']['path']];doc['result_sha256']='9'*64
        f.owner['audit']['sha256']=f.document(f.owner['audit']['path'],doc)['sha256']
        with self.assertRaisesRegex(ValueError,'closed passed'):f.extend()

    def test_retained_projection_must_be_exact(self):
        f=Fixture();p=f.work/'snapshot-plan.json';doc=f.docs[str(p)];doc['inputs_sha256']='8'*64;f.document(p,doc)
        with self.assertRaisesRegex(ValueError,'source/snapshot'):f.extend()

    def test_missing_logical_alias_rejected(self):
        f=Fixture();del f.projection['files'][f.alias['path']];f.seal()
        with self.assertRaisesRegex(ValueError,'logical catalog'):f.extend()

    def test_original_source_still_required(self):
        f=Fixture();del f.rows[f.a['path']]
        with self.assertRaises(KeyError):f.extend()

    def test_new_blob_cannot_claim_ancestor_role(self):
        f=Fixture();key=f.b['sha256'];f.projection['storage'][key]=dict(kind='reused',path=str(f.root/(key+'.gz')));f.seal()
        with self.assertRaisesRegex(ValueError,'incorrectly receives reuse'):f.extend()

    def test_reused_descriptor_cannot_be_relabelled(self):
        f=Fixture();key=f.a['sha256'];f.projection['reuse'][key]['blob']['sha256']='9'*64;f.seal()
        with self.assertRaisesRegex(ValueError,'authenticated predecessor'):f.extend()

    def test_reused_storage_path_is_exact(self):
        f=Fixture();f.projection['storage'][f.a['sha256']]['path']='/elsewhere/blob.gz';f.seal()
        with self.assertRaisesRegex(ValueError,'descriptor/path'):f.extend()

    def test_manifest_mapping_covers_all_aliases(self):
        f=Fixture();del f.manifest['files'][f.alias['path']];f.seal()
        with self.assertRaisesRegex(ValueError,'storage/mapping'):f.extend()

    def test_extra_stored_file_rejected(self):
        f=Fixture();f.dirs[str(f.root)]['children'].append('extra.gz')
        with self.assertRaisesRegex(ValueError,'storage/mapping'):f.extend()

    def test_missing_ancestor_membership_rejected(self):
        f=Fixture();f.dirs[str(f.oldroot)]['children']=[]
        with self.assertRaisesRegex(ValueError,'ancestor directory'):f.extend()

    def test_all_reused_roots_stay_accounted(self):
        f=Fixture();f.roots.remove('/evidence/old')
        with self.assertRaisesRegex(ValueError,'outside counted'):f.extend()

    def test_changed_ancestor_identity_rejected(self):
        f=Fixture();f.rows[f.prior['records'][0]['path']]['identity']=dict(f.prior['records'][0]['identity'],ctime_ns=99)
        with self.assertRaisesRegex(ValueError,'physical file changed'):f.extend()

    def test_hardlink_does_not_gain_credit(self):
        f=Fixture();p=f.prior['records'][0]['path'];f.rows[p]['identity']=dict(f.rows[p]['identity'],nlink=2)
        with self.assertRaisesRegex(ValueError,'single-link'):f.extend()

    def test_new_and_old_inode_collision_rejected(self):
        f=Fixture();key=f.b['sha256'];p=str(f.root/(key+'.gz'))
        f.rows[p]['identity']['ino']=f.prior['records'][0]['identity']['ino']
        with self.assertRaisesRegex(ValueError,'duplicate physical'):f.extend()

    def test_new_rounded_allocation_checked(self):
        f=Fixture();f.projection['new_compressed_allocated_bytes']-=4096;f.seal()
        with self.assertRaisesRegex(ValueError,'physical accounting'):f.extend()

    def test_float_counter_is_not_equivalent(self):
        f=Fixture();f.projection['new_compressed_allocated_bytes']=float(f.projection['new_compressed_allocated_bytes']);f.seal()
        with self.assertRaisesRegex(ValueError,'physical accounting'):f.extend()

    def test_negative_or_zero_identity_is_rejected(self):
        for key,value in [('ino',0),('nlink',0),('dev',-1),('size',-1),('mtime_ns',-1),('ctime_ns',-1)]:
            with self.subTest(key=key):
                f=Fixture();p=f.prior['records'][0]['path'];f.rows[p]['identity']=dict(f.rows[p]['identity'],**{key:value})
                with self.assertRaisesRegex(ValueError,'typed ordinary'):f.extend()

    def test_full_eof_attestation_is_required(self):
        f=Fixture();f.manifest['full_gzip_eof']=False;f.seal()
        with self.assertRaisesRegex(ValueError,'complete qualified'):f.extend()

    def test_unqualified_helper_cannot_replace_frozen_source(self):
        f=Fixture();p=f.source/'snapshot-plan.json';doc=f.docs[str(p)];doc['helper']['sha256']='f'*64
        row=f.document(p,doc);f.document(f.work/'snapshot-plan.json',doc)
        f.receipt['snapshot_plan_sha256']=row['sha256'];rr=f.document(f.work/'receipt.json',f.receipt)
        audit=f.docs[f.owner['audit']['path']];audit['receipt_sha256']=rr['sha256'];f.owner['audit']['sha256']=f.document(f.owner['audit']['path'],audit)['sha256']
        with self.assertRaisesRegex(ValueError,'helper not frozen'):f.extend()

    def test_expansion_cannot_change_snapshot_selection(self):
        def bad(raw,row):raw['snapshot_inputs']=[];return raw
        with self.assertRaisesRegex(ValueError,'non-file metadata'):Fixture().extend(expand_inputs=bad)

    def test_flat_freeze_cannot_be_rewritten_by_expander(self):
        def bad(raw,row):raw['files'].pop('/source/a');return raw
        with self.assertRaisesRegex(ValueError,'flat input'):Fixture().extend(expand_inputs=bad)
        f=Fixture();before=copy.deepcopy(f.rows[str(f.source/'inputs.json')])
        def record_mutation(raw,row):
            row['sha256']='0'*64;row['identity']['ino']=0;return raw
        self.assertEqual(len(f.extend(expand_inputs=record_mutation)['records']),3)
        self.assertEqual(f.rows[str(f.source/'inputs.json')],before)

    def test_explicit_result_field_and_path(self):
        f=Fixture();p=f.work/'source-probe/result.json';r=f.document(p,f.result)
        f.owner.update(result_path=str(p),result_digest_field='source_preflight_sha256')
        f.receipt['source_preflight_sha256']=r['sha256'];del f.receipt['result_sha256'];f.seal()
        self.assertEqual(f.extend()['predecessors'][-1]['result']['path'],str(p))

    def test_result_cannot_escape_owner(self):
        f=Fixture();f.owner['result_path']='/elsewhere/result.json'
        with self.assertRaisesRegex(ValueError,'owned result'):f.extend()

    def test_reservation_only_counts_new_physical_blobs(self):
        f=Fixture();p=f.projection
        self.assertEqual(c.reservation(p,4*2**20,32*2**20),40*2**20+2*4096+2*4096)
        p['new_compressed_allocated_bytes']=0
        with self.assertRaisesRegex(ValueError,'allocation'):c.reservation(p,4*2**20,32*2**20)

    def test_zero_new_allocation_rejects_boolean_and_float(self):
        f=Fixture();key=f.a['sha256'];b=f.oldblob
        p=dict(blobs={key:b},storage={key:dict(kind='reused',path=f.prior['records'][0]['path'])},
               new_compressed_allocated_bytes=0,new_compressed_bytes=0,compressed_bytes=b['compressed_bytes'],
               reused_compressed_bytes=b['compressed_bytes'],compressed_allocated_bytes=f.round(b['compressed_bytes']))
        self.assertEqual(c.reservation(p,4*2**20,32*2**20),40*2**20)
        for field in ['new_compressed_allocated_bytes','new_compressed_bytes']:
            for value in [False,0.0]:
                with self.subTest(field=field,value=repr(value)):
                    bad=copy.deepcopy(p);bad[field]=value
                    with self.assertRaisesRegex(ValueError,'accounting'):c.reservation(bad,4*2**20,32*2**20)

    def test_reservation_parameter_types_and_bounds(self):
        for a,b in [(False,32*2**20),(4*2**20,False),(4.0,32*2**20),(-1,32*2**20),(4*2**20,-1),(4*2**20+1,32*2**20),(4*2**20,32*2**20+1)]:
            with self.subTest(parameters=(a,b)):
                with self.assertRaisesRegex(ValueError,'reservation parameters'):c.reservation(Fixture().projection,a,b)

    def test_reservation_rejects_unbounded_or_extra_storage_keys(self):
        f=Fixture();p=f.projection;p['storage'][f.b['sha256']]['path']='/unneeded/path'
        with self.assertRaisesRegex(ValueError,'storage fields'):c.reservation(p,4*2**20,32*2**20)
        p=dict(blobs={},storage={},new_compressed_allocated_bytes=0)
        with self.assertRaisesRegex(ValueError,'bounded storage'):c.reservation(p,4*2**20,32*2**20)


if __name__ == '__main__':
    unittest.main(verbosity=2)
