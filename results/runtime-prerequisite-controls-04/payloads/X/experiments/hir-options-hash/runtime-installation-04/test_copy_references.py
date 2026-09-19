"""Tiny metadata-only controls for exact copy selection and closed retention.

No real payload, helper, process, archive, compiler or provider is read.
The generic helper's actual40 separately qualifies build/partition semantics.
"""
import copy
from contextlib import ExitStack
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import copies as c
import entry


class Fixture:
    def __init__(self):
        self.stage=SimpleNamespace(RECIPE_WORK=Path('/fixture/recipe-work'),RECIPE_SOURCE=Path('/fixture/recipe-source'))
        self.docs={};self.digests={};self.reads=[]
        self.sha=lambda p:self.digests.get(str(p),'sha:'+str(p))
        self.plan={'source_identity':{'revision':'candidate'},'independent_audits':{'run_make':{'path':'/fixture/audit','sha256':'sha:/fixture/audit'}}}
        selection={f'/fixture/input-{i:03d}':{'sha256':f'input-{i}','stamp':[1,2,3,7,5,6,1]} for i in range(59)}
        original={name:{'sha256':row['sha256'],'size':7,'identity':{'ino':100+i}} for i,(name,row) in enumerate(selection.items())}
        for path in [self.stage.RECIPE_SOURCE/'plan.json',self.stage.RECIPE_SOURCE/'inputs.json']:
            original[str(path)]={'sha256':self.sha(path),'size':9,'identity':{'ino':200+len(original)}}
        rows=[]
        for i,name in enumerate(sorted(original)):
            row=original[name];retained=str(c.COPY_ROOT/(f'{i:04d}-'+Path(name).name))
            rows.append(dict(source=name,retained=retained,sha256=row['sha256'],bytes=row['size']))
        self.retention=dict(status='retained',files=rows)
        self.original=dict(files=copy.deepcopy(original),snapshot_inputs=[])
        for i,row in enumerate(rows):
            self.original['files'][row['retained']]={'sha256':row['sha256'],'size':row['bytes'],'identity':{'ino':300+i}}
        receipt=dict(status='passed',result_sha256=self.sha(self.stage.RECIPE_WORK/'result.json'),native_recipe_qualified=True,
            recipe_compilations=1,recipe_executions=1,nested_commands=230,hash_driver_qualified=False,
            application_qualified=False,performance_measurement=False,commands=[{'fixture':'command'}])
        result=dict(receipt,retained_inputs_sha256=self.sha(self.stage.RECIPE_WORK/'retained-inputs.json'),
            plan_sha256=self.sha(self.stage.RECIPE_SOURCE/'plan.json'),inputs_sha256=self.sha(self.stage.RECIPE_SOURCE/'inputs.json'),
            actual_commands=copy.deepcopy(receipt['commands']),source_identity=copy.deepcopy(self.plan['source_identity']))
        self.docs.update({str(self.stage.RECIPE_WORK/'receipt.json'):receipt,str(self.stage.RECIPE_WORK/'result.json'):result,
            '/fixture/audit':{'status':'verified','receipt_sha256':self.sha(self.stage.RECIPE_WORK/'receipt.json')},
            str(self.stage.RECIPE_WORK/'retained-inputs.json'):self.retention,
            str(self.stage.RECIPE_SOURCE/'plan.json'):{'retained_selection':selection}})
        self.proposal=dict(status='source-only-prospective-retirement-not-prepared',target_root=str(c.COPY_ROOT),selection_count=21,
            selected=[Path(row['retained']).name for row in rows[:21]],
            recovery=[dict(path=row['retained'],original_record=copy.deepcopy(self.original['files'][row['retained']])) for row in rows[:21]])
        self.docs[str(c.PROPOSAL)]=self.proposal;self.digests[str(c.PROPOSAL)]=c.PROPOSAL_SHA256

    def read(self,path):
        self.reads.append(str(path));return copy.deepcopy(self.docs[str(path)])

    def selected(self):
        return c.selection(self.original,read_json=self.read,sha=self.sha)

    def owner(self):
        return c.retained_owner(self.stage,self.plan,self.original,read_json=self.read,sha=self.sha)


class CopyReferenceControls(unittest.TestCase):
    def setUp(self):
        stack=ExitStack();self.addCleanup(stack.close);self.forbidden=[]
        for owner,names in [(subprocess,['Popen','run','call','check_call','check_output']),
                (os,['open','kill','killpg','system']),
                (Path,['open','read_bytes','read_text','write_bytes','write_text','mkdir','unlink','rmdir'])]:
            for name in names:self.forbidden.append(stack.enter_context(patch.object(owner,name,side_effect=AssertionError('forbidden IO'))))

    def tearDown(self):
        for call in self.forbidden:call.assert_not_called()

    def test_full61_owner_mapping_and21_selection_keep_payloads_unread(self):
        f=Fixture();owner,rows=f.owner();names=f.selected()
        self.assertEqual(len(rows['files']),61);self.assertEqual(len(names),21)
        self.assertEqual(owner['source'],str(f.stage.RECIPE_SOURCE))
        self.assertFalse(any(name.startswith(str(c.COPY_ROOT)+'/') for name in f.reads))

    def test_proposal_digest_is_required_before_selection(self):
        f=Fixture();f.digests[str(c.PROPOSAL)]='foreign'
        with self.assertRaisesRegex(RuntimeError,'reviewed copy selection'):f.selected()
        self.assertEqual(f.reads,[])

    def test_recovery_rows_must_be_unique_complete_and_typed(self):
        for mode in ['duplicate','missing','typed']:
            with self.subTest(mode=mode):
                f=Fixture()
                if mode=='duplicate':f.proposal['recovery'][0]=copy.deepcopy(f.proposal['recovery'][1])
                elif mode=='missing':f.proposal['recovery'].pop()
                else:f.proposal['recovery'][0]['original_record']['size']=7.0
                with self.assertRaisesRegex(RuntimeError,'recovery map|historical copy row'):f.selected()

    def test_current_snapshot_selection_cannot_become_historical(self):
        f=Fixture();f.original['snapshot_inputs']=[f.proposal['recovery'][0]['path']]
        with self.assertRaisesRegex(RuntimeError,'selected hash snapshot'):f.selected()

    def test_proposal_root_count_and_order_are_exact(self):
        for key,value in [('target_root','/fixture/other'),('selection_count',21.0),('selected',[])]:
            with self.subTest(key=key):
                f=Fixture();f.proposal[key]=value
                with self.assertRaisesRegex(RuntimeError,'proposal scope|recovery map'):f.selected()

    def test_historical_copy_must_be_directly_inside_reviewed_root(self):
        f=Fixture();old=f.proposal['recovery'][0]['path'];new=str(c.COPY_ROOT/'nested'/'file')
        f.original['files'][new]=f.original['files'].pop(old)
        f.proposal['recovery'][0]['path']=new
        f.proposal['selected'][0]='nested/file';f.proposal['selected'].sort()
        with self.assertRaisesRegex(RuntimeError,'historical copy row'):f.selected()

    def test_retained_owner_rejects_failed_or_wrong_actual_audit(self):
        for mode in ['failed','audit','result','retention']:
            with self.subTest(mode=mode):
                f=Fixture()
                if mode=='failed':f.docs[str(f.stage.RECIPE_WORK/'receipt.json')]['status']='failed'
                elif mode=='audit':f.docs['/fixture/audit']['receipt_sha256']='foreign'
                elif mode=='result':f.docs[str(f.stage.RECIPE_WORK/'receipt.json')]['result_sha256']='foreign'
                else:f.docs[str(f.stage.RECIPE_WORK/'result.json')]['retained_inputs_sha256']='foreign'
                with self.assertRaisesRegex(RuntimeError,'completed run-make retention'):f.owner()

    def test_retained_owner_scope_counters_and_flags_are_typed(self):
        for key,value in [('recipe_compilations',True),('nested_commands',230.0),('performance_measurement',0)]:
            with self.subTest(key=key):
                f=Fixture();f.docs[str(f.stage.RECIPE_WORK/'result.json')][key]=value
                with self.assertRaisesRegex(RuntimeError,'recipe scope'):f.owner()

    def test_complete_mapping_rejects_missing_duplicate_or_numeric_relabel(self):
        for mode in ['missing','duplicate','numeric']:
            with self.subTest(mode=mode):
                f=Fixture()
                if mode=='missing':f.retention['files'].pop()
                elif mode=='duplicate':f.retention['files'][0]=copy.deepcopy(f.retention['files'][1])
                else:f.retention['files'][0]['bytes']=7.0
                with self.assertRaisesRegex(RuntimeError,'61-entry retained selection'):f.owner()

    def test_retained_alias_order_is_bound_to_original_recipe(self):
        f=Fixture();f.retention['files'][0],f.retention['files'][1]=f.retention['files'][1],f.retention['files'][0]
        with self.assertRaisesRegex(RuntimeError,'retained-copy alias/order'):f.owner()

    def test_current_source_identity_and_commands_cannot_relabel_history(self):
        for key in ['source_identity','actual_commands','inputs_sha256','plan_sha256']:
            with self.subTest(key=key):
                f=Fixture();f.docs[str(f.stage.RECIPE_WORK/'result.json')][key]='foreign'
                with self.assertRaisesRegex(RuntimeError,'retention source/commands'):f.owner()

    def test_discovery_add_has_no_historical_fallback_even_if_file_would_exist(self):
        calls=[]
        class Discovery:
            def __init__(self,modules):pass
            def add(self,path,expected=None,*,snapshot=False):calls.append(str(path));return Path(path)
        modules=SimpleNamespace(collector=SimpleNamespace(Discovery=Discovery),hash_modules={})
        d=entry.discovery(modules);d.historical_names={'/fixture/historical'}
        with self.assertRaisesRegex(RuntimeError,'no current-file API'):d.add('/fixture/historical')
        self.assertEqual(calls,[])
        self.assertEqual(d.add('/fixture/current'),Path('/fixture/current'))
        self.assertEqual(calls,['/fixture/current'])

    def retirement_fixture(self):
        reference=dict(path=str(entry.RETIREMENT_AUDIT),sha256='a'*64)
        paths=[str(c.COPY_ROOT/f'{i:04d}-proof') for i in range(21)]
        state=dict(historical_files={name:{} for name in paths})
        audit=dict(status='verified-exact-proof-copy-retirement',proposal_sha256=c.PROPOSAL_SHA256,
            historical_source_stage03_wire_sha256=c.ORIGINAL_INPUTS_SHA256,
            helper40_audit=dict(path=str(c.CONTROL_AUDIT),sha256=c.CONTROL_AUDIT_SHA256),
            original_retained_inputs_sha256='587139f94eeb3d6ccac398f9c12ec65f4eb33b0e79b40e513678826cdd9f2c0d',
            selected_paths=paths,removed_files=21,preserved_files=40,removed_directories=0,chmod_operations=0,
            durable_events=63,current_context_rows=109322,full_ledger_replay=True,
            source_witness_readback=True,preserved40_readback=True,
            recovery=dict(path='/fixture/recovery',sha256='a'*64),runtime_rehearsal=dict(path='/fixture/rehearsal',sha256='a'*64))
        rehearsal=dict(status='verified-strict-callback-rehearsal',bootstrap_policy='continued-catalog-before-reader',
            proposal_sha256=c.PROPOSAL_SHA256,historical_source_stage03_wire_sha256=c.ORIGINAL_INPUTS_SHA256,
            complete_original_rows=109343,current_context_rows=109322,historical_copies=21,
            no_live_api_virtualization=True,runtime_admission=False,retirement_authorized=False)
        docs={str(entry.RETIREMENT_AUDIT):audit,'/fixture/rehearsal':rehearsal}
        def check():
            return entry.retirement_qualification(SimpleNamespace(copies=c),reference,state,
                read_json=lambda path:copy.deepcopy(docs[str(path)]),sha=lambda path:'a'*64)
        return reference,state,audit,rehearsal,check

    def test_production_requires_actual_retirement_and21_real_absences(self):
        ref,state,audit,rehearsal,check=self.retirement_fixture()
        with patch.object(Path,'exists',return_value=False) as exists,patch.object(Path,'is_symlink',return_value=False) as link:
            self.assertEqual(check(),ref)
        self.assertEqual(exists.call_count,21);self.assertEqual(link.call_count,21)
        with patch.object(Path,'exists',return_value=True):
            with self.assertRaisesRegex(RuntimeError,'retired copy is still present'):check()

    def test_rehearsal_or_unbound_digest_cannot_authorize_production(self):
        for mode in ['digest','status','scope']:
            with self.subTest(mode=mode):
                ref,state,audit,rehearsal,check=self.retirement_fixture()
                if mode=='digest':ref['sha256']=None
                elif mode=='status':audit['status']='strict-callback-rehearsal'
                else:rehearsal['runtime_admission']=True
                with patch.object(Path,'exists',side_effect=AssertionError('premature absence read')):
                    with self.assertRaisesRegex(RuntimeError,'retirement audit|retirement proof|reader rehearsal'):check()

    def test_retirement_count_types_and_preservation_flags_are_strict(self):
        for key,value in [('removed_files',21.0),('removed_directories',False),('preserved40_readback',1)]:
            with self.subTest(key=key):
                ref,state,audit,rehearsal,check=self.retirement_fixture();audit[key]=value
                with patch.object(Path,'exists',side_effect=AssertionError('premature absence read')):
                    with self.assertRaisesRegex(RuntimeError,'retirement proof differs'):check()


if __name__=='__main__':unittest.main()
