"""Synthetic association controls; no files, providers, subprocesses or writes."""
import copy
import hashlib
from pathlib import Path
import unittest

import snapshot_bindings as b

LIMITS = dict(maximum_files=1024, maximum_file_bytes=64*2**20,
    maximum_logical_bytes=512*2**20, maximum_compressed_bytes=128*2**20,
    maximum_manifest_bytes=4*2**20)


class Fixture:
    def __init__(self, mutations=None):
        self.json = {}; self.files = {}; self.directories = {}; self.predecessors = []; self.inputs = []
        self.inode = 10; self.mutations = mutations or {}
        helper = self.put(Path('/qualified/v1/proof_snapshots.py'), b'original helper')
        for role in ['beta', 'native']:
            source = Path('/qualified')/role/'source'; work = Path('/qualified')/role/'work'
            root = work/'source-snapshots'
            ordinary = [self.put(source/'shared.py', b'shared original source'),
                        self.put(source/'unique.py', role.encode())]
            self.inputs.extend(ordinary)
            old_plan = dict(candidate_revision='candidate',evidence_roots=[str(work)],
                children=[dict(index=i) for i in range(20 if role=='native' else 19)])
            old_plan_row = self.put_json(source/'plan.json',old_plan)
            original_parser = self.put(source/'observations.py',b'original observations')
            freeze = dict(files={row['path']:{key:row[key] for key in ['identity','sha256','size']}
                                  for row in ordinary+[helper,old_plan_row,original_parser]},
                          plan_sha256=old_plan_row['sha256'], snapshot_inputs=sorted(row['path'] for row in ordinary))
            input_row = self.put_json(source/'inputs.json', freeze)
            originals = dict(sorted((row['path'],row) for row in ordinary+[input_row]))
            blobs = {}
            for row in originals.values():
                key = row['sha256']; compressed = b'synthetic blob descriptor '+key.encode()
                physical = self.put(root/(key+'.gz'), compressed)
                blobs[key] = dict(filename=key+'.gz', logical_sha256=key, logical_bytes=row['size'],
                                  sha256=physical['sha256'], compressed_bytes=len(compressed))
            total = sum(row['compressed_bytes'] for row in blobs.values())
            projection = dict(policy='bounded-gzip-proof-snapshots-v1', limits=LIMITS,
                files=originals, blobs=dict(sorted(blobs.items())), logical_bytes=sum(row['size'] for row in originals.values()),
                unique_logical_bytes=sum(row['logical_bytes'] for row in blobs.values()), compressed_bytes=total,
                compressed_allocated_bytes=sum(((row['compressed_bytes']+4095)//4096)*4096 for row in blobs.values()),
                manifest_reservation_bytes=8*2**20)
            self.mutate(role, 'projection', projection)
            snapshot = dict(inputs_sha256=input_row['sha256'], limits=LIMITS, projection=projection,
                            helper=dict(path=helper['path'],sha256=helper['sha256']))
            source_projection = self.put_json(source/'snapshot-plan.json',snapshot)
            self.put_json(work/'snapshot-plan.json',snapshot)
            manifest = dict(policy='bounded-gzip-proof-snapshots-v1', projection_sha256=hashlib.sha256(b.encoded(projection)).hexdigest(),
                files={name:dict(path=str(root/(row['sha256']+'.gz')), sha256=row['sha256'],size=row['size'],encoding='gzip')
                       for name,row in originals.items()}, blobs=dict(sorted(blobs.items())),compressed_bytes=total,
                full_gzip_eof=True,full_logical_readback=True)
            self.mutate(role,'manifest',manifest)
            manifest_row = self.put_json(work/'source-snapshots.json',manifest)
            terminal = dict(status='passed',started_at=1,admitted_at=2,finished_at=3,
                inputs_sha256=input_row['sha256'],snapshot_plan_sha256=source_projection['sha256'],
                source_snapshots_sha256=manifest_row['sha256'])
            if role=='native':terminal.update(status='failed',error=b.NATIVE_FAILURE,source_restored=True,
                candidate_revision='candidate',commands=[dict(path=str(work/'commands'/f'{i:03}'/'receipt.json'),
                    sha256=str(i%10)*64,pid=100+i) for i in range(20)])
            self.mutate(role,'terminal',terminal)
            terminal_row = self.put_json(work/'receipt.json',terminal)
            audit = dict(status='verified',receipt_sha256=terminal_row['sha256'])
            if role=='native':audit.update(status='verified-retained-failure',children=20,historical_failed_children=11,
                total_actual_native_children=31,qualified_native_children=0,source_restored=True,native_roles_and_behavior_qualified=False)
            self.mutate(role,'audit',audit)
            audit_row = self.put_json(Path('/qualified/audits')/(role+'.json'),audit)
            self.directories[str(root)] = dict(identity=self.identity(0,0o40700),children=sorted(key+'.gz' for key in blobs))
            predecessor=dict(role=role,source=str(source),evidence=str(work),audit=dict(path=audit_row['path'],sha256=audit_row['sha256']))
            if role=='native':
                qs=source.parent/'reconciliation-source';qw=work.parent/'reconciliation-work'
                base=dict(path=input_row['path'],sha256=input_row['sha256'])
                commands=dict(source=str(source),evidence=str(work),receipt_sha256=terminal_row['sha256'],
                    inputs_sha256=input_row['sha256'],plan_sha256=old_plan_row['sha256'],snapshot_plan_sha256=source_projection['sha256'],
                    status='failed',error=b.NATIVE_FAILURE,commands=terminal['commands'],failure_audit=predecessor['audit'])
                parser=self.put(qs/'wrong_beta.py',b'corrected observations')
                reconciliation=dict(source=str(qs),base_inputs=base,original_parser=dict(path=original_parser['path'],sha256=original_parser['sha256']),
                    parser=dict(path=parser['path'],sha256=parser['sha256']),parser_controls=dict(controls=1),failure_audit=predecessor['audit'])
                qplan=dict(old_plan,read_only_reconciliation=True,actual_workload_children=0,base_inputs=base,
                    command_evidence=commands,reconciliation=reconciliation,wrong_beta_providers=[],wrong_beta_lib='/qualified/beta/lib',
                    reconciliation_evidence_roots=sorted([str(work),str(qw)]))
                self.mutate(role,'qualification_plan',qplan)
                qplan_row=self.put_json(qs/'plan.json',qplan)
                qfreeze=dict(base_inputs=base,files={qplan_row['path']:{key:qplan_row[key] for key in ['identity','sha256','size']}},
                    links={},absent_paths=[str(work/'native-controls.json')],plan_sha256=qplan_row['sha256'])
                self.mutate(role,'qualification_freeze',qfreeze)
                qfreeze_row=self.put_json(qs/'inputs.json',qfreeze)
                qualified=dict(status='native-roles-and-behavior-qualified',candidate_revision='candidate',qualified_native_children=20,
                    total_actual_native_children=31,history=terminal['commands'][:18],wrong_B3_commands=terminal['commands'][18:],
                    command_evidence=commands,reconciliation=reconciliation)
                self.mutate(role,'qualification_result',qualified)
                result_row=self.put_json(qw/'native-controls.json',qualified)
                qreceipt=dict(status='passed',started_at=4,admitted_at=5,finished_at=6,read_only_reconciliation=True,
                    commands=[],actual_workload_children=0,saved_actual_children=20,historical_failed_children=11,
                    native_roles_and_behavior_qualified=True,inputs_sha256=qfreeze_row['sha256'],plan_sha256=qplan_row['sha256'],
                    result_sha256=result_row['sha256'],command_evidence=commands,reconciliation=reconciliation)
                self.mutate(role,'qualification_terminal',qreceipt)
                qr=self.put_json(qw/'receipt.json',qreceipt)
                qaudit=dict(status='verified',receipt_sha256=qr['sha256'],result_sha256=result_row['sha256'])
                self.mutate(role,'qualification_audit',qaudit)
                qa=self.put_json(Path('/qualified/audits/native-reconciliation.json'),qaudit)
                predecessor['qualification']=dict(source=str(qs),evidence=str(qw),audit=dict(path=qa['path'],sha256=qa['sha256']))
            self.predecessors.append(predecessor)
        self.accounted = sorted([row['evidence'] for row in self.predecessors]
            +[row['qualification']['evidence'] for row in self.predecessors if 'qualification' in row])

    def identity(self,size,mode=0o100600):
        self.inode += 1
        return dict(dev=1,ino=self.inode,mode=mode,size=size,mtime_ns=10,ctime_ns=10,nlink=1)

    def put(self,path,data):
        row=dict(path=str(path),sha256=hashlib.sha256(data).hexdigest(),size=len(data),identity=self.identity(len(data)))
        self.files[str(path)]=row;return row

    def put_json(self,path,value):
        self.json[str(path)]=copy.deepcopy(value);return self.put(path,b.encoded(value))

    def mutate(self,role,kind,value):
        callback=self.mutations.get((role,kind))
        if callback:callback(value)

    def catalog(self):
        return b.catalog(self.predecessors,self.accounted,LIMITS,
            read_json=lambda p:copy.deepcopy(self.json[str(p)]),
            file_record=lambda p:copy.deepcopy(self.files[str(p)]),
            directory_record=lambda p:copy.deepcopy(self.directories[str(p)]))


class AssociationControls(unittest.TestCase):
    def test_complete_catalog_keeps_both_predecessors_and_all_blobs(self):
        f=Fixture();catalog=f.catalog()
        self.assertEqual([p['role'] for p in catalog['predecessors']],['beta','native'])
        self.assertEqual(len(catalog['records']),6)
        self.assertEqual(len(catalog['evidence_roots']),2)
        self.assertEqual([p['audit'] for p in catalog['predecessors']],[p['audit'] for p in f.predecessors])

    def test_same_payload_prefers_beta_without_dropping_logical_aliases(self):
        f=Fixture();catalog=f.catalog();before=copy.deepcopy(f.inputs)
        selected=b.select(f.inputs,catalog)
        shared=f.inputs[0]['sha256']
        row=next(row for row in selected['records'] if row['blob']['logical_sha256']==shared)
        self.assertIn('/beta/work/',row['path'])
        self.assertEqual(len(selected['records']),3)
        self.assertEqual(f.inputs,before)
        self.assertEqual(sum(row['blob']['logical_sha256']==shared for row in catalog['records']),2)

    def test_new_source_retains_selection_and_does_not_receive_reuse_credit(self):
        f=Fixture();new=f.put(Path('/qualified/new.py'),b'new proof input');records=f.inputs+[new]
        before=copy.deepcopy(records);selected=b.select(records,f.catalog())
        self.assertNotIn(new['sha256'],[row['blob']['logical_sha256'] for row in selected['records']])
        self.assertEqual(records,before)

    def test_closed_audit_must_bind_actual_receipt(self):
        f=Fixture({('beta','audit'):lambda row:row.update(receipt_sha256='0'*64)})
        with self.assertRaisesRegex(ValueError,'closed actual'):f.catalog()

    def test_failed_predecessor_cannot_supply_credited_bytes(self):
        f=Fixture({('beta','terminal'):lambda row:row.update(status='failed')})
        with self.assertRaisesRegex(ValueError,'closed actual'):f.catalog()

    def test_evidence_root_must_already_be_in_monitor_total(self):
        f=Fixture();f.accounted.remove(f.predecessors[1]['evidence'])
        with self.assertRaisesRegex(ValueError,'already counted'):f.catalog()

    def test_manifest_path_cannot_escape_fixed_predecessor_snapshot_root(self):
        def change(row):next(iter(row['files'].values()))['path']='/unaccounted/payload.gz'
        f=Fixture({('beta','manifest'):change})
        with self.assertRaisesRegex(ValueError,'path/hash mapping'):f.catalog()

    def test_source_and_retained_projection_are_bound_to_terminal(self):
        f=Fixture({('native','terminal'):lambda row:row.update(snapshot_plan_sha256='f'*64)})
        with self.assertRaisesRegex(ValueError,'receipt hashes'):f.catalog()

    def test_original_logical_input_cannot_disappear(self):
        def change(row):row['files'].pop(next(iter(row['files'])))
        f=Fixture({('beta','projection'):change})
        with self.assertRaisesRegex(ValueError,'logical input set'):f.catalog()

    def test_blob_hardlink_has_no_independent_storage_credit(self):
        f=Fixture();path=next(path for path in f.files if path.endswith('.gz'))
        f.files[path]['identity']['nlink']=2
        with self.assertRaisesRegex(ValueError,'single-link'):f.catalog()

    def test_selected_inodes_cannot_receive_duplicate_credit(self):
        f=Fixture();catalog=f.catalog();eligible=[row for row in catalog['records'] if row['blob']['logical_sha256'] in {r['sha256'] for r in f.inputs}]
        first=eligible[0];other=next(row for row in eligible if row['blob']['logical_sha256']!=first['blob']['logical_sha256'])
        other['identity']['ino']=first['identity']['ino']
        with self.assertRaisesRegex(ValueError,'physical reference'):b.select(f.inputs,catalog)

    def test_complete_snapshot_directory_membership_is_required(self):
        f=Fixture();next(iter(f.directories.values()))['children'].append('unadmitted.gz')
        with self.assertRaisesRegex(ValueError,'snapshot directory'):f.catalog()

    def test_full_gzip_readback_claim_is_required(self):
        f=Fixture({('beta','manifest'):lambda row:row.update(full_gzip_eof=False)})
        with self.assertRaisesRegex(ValueError,'v1 snapshot'):f.catalog()

    def test_equal_digest_cannot_change_logical_size(self):
        f=Fixture();records=copy.deepcopy(f.inputs);records[0]['size']+=1
        with self.assertRaisesRegex(ValueError,'alias size'):b.select(records,f.catalog())

    def test_reservation_counts_only_new_physical_blobs_and_fixed_reserves(self):
        projection=dict(blobs={'new':dict(compressed_bytes=4097),'old':dict(compressed_bytes=1000000)},
            storage={'new':dict(kind='stored'),'old':dict(kind='reused',path='/already/counted.gz')},
            new_compressed_allocated_bytes=8192)
        self.assertEqual(b.reservation(projection,4*2**20,32*2**20),8192+4096+40*2**20)
        projection['new_compressed_allocated_bytes']=4097
        with self.assertRaisesRegex(ValueError,'allocation'):b.reservation(projection,4*2**20,32*2**20)

    def test_native_failed_owner_stays_distinct_from_successful_qualifier(self):
        f=Fixture();native=f.catalog()['predecessors'][1]
        self.assertEqual(f.json[native['receipt']['path']]['status'],'failed')
        self.assertEqual(f.json[native['qualification']['receipt']['path']]['status'],'passed')
        self.assertNotEqual(native['receipt']['path'],native['qualification']['receipt']['path'])
        self.assertIn('/native/work/source-snapshots',native['snapshot_root'])

    def test_native_owner_cannot_be_relabelled_passed(self):
        f=Fixture({('native','terminal'):lambda row:row.update(status='passed')})
        with self.assertRaisesRegex(ValueError,'must remain failed'):f.catalog()

    def test_failed_reconciliation_does_not_qualify_original_snapshots(self):
        f=Fixture({('native','qualification_terminal'):lambda row:row.update(status='failed')})
        with self.assertRaisesRegex(ValueError,'zero-child'):f.catalog()

    def test_reconciliation_cannot_claim_new_workload_children(self):
        f=Fixture({('native','qualification_terminal'):lambda row:row.update(actual_workload_children=1)})
        with self.assertRaisesRegex(ValueError,'zero-child'):f.catalog()

    def test_reconciliation_cannot_change_original_recipe(self):
        f=Fixture({('native','qualification_plan'):lambda row:row.update(children=[])})
        with self.assertRaisesRegex(ValueError,'original command plan'):f.catalog()

    def test_reconciliation_preserves_nested_json_value_types(self):
        for index,replacement in [(0,False),(0,0.0),(1,True),(1,1.0)]:
            with self.subTest(index=index,replacement=repr(replacement)):
                def change(row):
                    children=copy.deepcopy(row['children'])
                    children[index]['index']=replacement
                    row['children']=children
                f=Fixture({('native','qualification_plan'):change})
                with self.assertRaisesRegex(ValueError,'original command plan'):f.catalog()

    def test_original_result_absence_is_part_of_reconciliation_freeze(self):
        f=Fixture({('native','qualification_freeze'):lambda row:row.update(absent_paths=[])})
        with self.assertRaisesRegex(ValueError,'original command plan'):f.catalog()

    def test_qualifier_audit_binds_exact_new_result(self):
        f=Fixture({('native','qualification_audit'):lambda row:row.update(result_sha256='f'*64)})
        with self.assertRaisesRegex(ValueError,'zero-child'):f.catalog()

    def test_qualifier_cannot_predate_original_failure(self):
        f=Fixture({('native','qualification_terminal'):lambda row:row.update(started_at=1)})
        with self.assertRaisesRegex(ValueError,'zero-child'):f.catalog()

    def test_reconciliation_cannot_reset_old_monitor_roots(self):
        f=Fixture({('native','qualification_plan'):lambda row:row.update(reconciliation_evidence_roots=[])})
        with self.assertRaisesRegex(ValueError,'physical accounting'):f.catalog()


if __name__=='__main__':unittest.main()
