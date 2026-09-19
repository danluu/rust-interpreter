"""Synthetic reader/factory controls; no provider, process or output activity.

The Stage boundary is a fake definitions-only object. Its constructor fails if
called. Real Reader and factory wiring are exercised against in-memory records;
the original 21 Mach-O/cwd/allocation and 11 adapter controls remain separate.
The file-table loader is a fake boundary; these tests neither load the helper
nor claim real catalog/gzip qualification.
"""
import copy
from contextlib import ExitStack
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import prerequisites as p
import imports as factory


class Fixture:
    def __init__(self, *, runtime_selection=True):
        self.events = []
        fixture = self
        class Stage:
            def __init__(self):
                raise AssertionError('real Stage constructor is forbidden')
            def file_table_qualification(self):
                fixture.events.append(('file-table-qualified', 29))
                if fixture.table_control_error:
                    raise RuntimeError('actual29 file-table qualification rejected')
                return copy.deepcopy(fixture.table_proof)
            def snapshot_qualification(self):
                fixture.events.append(('snapshot-qualified', 22))
                if fixture.snapshot_control_error:
                    raise RuntimeError('actual22 snapshot qualification rejected')
            def frozen(self, path):
                fixture.events.append(('frozen', str(path)))
                if str(path) not in self.freeze['files']:
                    raise RuntimeError('missing frozen projection')
                return path
            def bind_snapshot_plan(self, digest):
                fixture.events.append(('bind', digest, copy.deepcopy(self.freeze['snapshot_inputs'])))
            def retained_snapshot_proof(self, source, work, receipt):
                fixture.events.append(('retained', str(source), str(work), receipt['snapshot_plan_sha256']))
            def guard(self, full):
                fixture.events.append(('guard', full))
            def read_json(self, path):
                return fixture.read(path)
            def read_bytes(self, path):
                return fixture.raw[str(path)]
            def closure(self, path):
                return copy.deepcopy(fixture.closure)
            def prerequisites(self):
                fixture.events.append(('original-commands', fixture.docs[str(fixture.stage.NATIVE_WORK/'receipt.json')]['status']))
                if fixture.command_error:
                    raise RuntimeError('saved original command proof rejected')
                return {'saved_native_children': 20, 'reconciliation_workload_children': 0}
        self.stage = SimpleNamespace(Stage=Stage, HERE=Path('/fixture/hash-source'), WORK=Path('/fixture/hash-work'),
            BETA_WORK=Path('/fixture/beta-work'), NATIVE_WORK=Path('/fixture/native-failed-work'),
            NATIVE_QUALIFICATION_WORK=Path('/fixture/native-reconciliation-work'), RECIPE_WORK=Path('/fixture/run-make-work'),
            REVISION='candidate', ROOT=Path('/fixture/hash-owner'),
            FILE_TABLE_SOURCE=Path('/fixture/file-table/file_table.py'),
            PLAN_REFERENCE_SOURCE=Path('/fixture/hash-source/plan_reference.py'),
            FAILED_WORK=Path('/fixture/hash-failed-work'),
            METADATA_PLAN_REFERENCE=dict(path='/fixture/metadata/plan.json',sha256='metadata'))
        self.continuation_error = self.partition_error = False
        self.continuation = dict(controls=70, audit={'path':'/fixture/control70','sha256':'actual70'})
        self.failed_owner = dict(role='failed-hash-driver-01',source='/fixture/old-source',evidence='/fixture/old-work',audit={})
        self.stage.failed_owner = lambda:copy.deepcopy(self.failed_owner)
        def continuation(**kwargs):
            self.events.append(('continuation-qualified',70))
            if self.continuation_error:raise RuntimeError('actual70 continuation rejected')
            return copy.deepcopy(self.continuation)
        self.stage.continuation_qualification = continuation
        self.command_error = self.table_control_error = self.snapshot_control_error = False
        self.table_proof = dict(controls=29,helper=dict(path=str(self.stage.FILE_TABLE_SOURCE),sha256='helper'))
        self.docs = {}; self.raw = {}; self.reads = []
        self.digests = {}
        self.sha = lambda path: self.digests.get(str(path), 'sha256:'+str(path))
        self.roles = {'beta':self.stage.BETA_WORK, 'native':self.stage.NATIVE_QUALIFICATION_WORK,
                      'run_make':self.stage.RECIPE_WORK, 'hash':self.stage.WORK}
        self.references = {role:dict(path='/fixture/audits/'+role+'.json',
            sha256=self.sha('/fixture/audits/'+role+'.json')) for role in self.roles}
        for role, work in self.roles.items():
            self.docs[str(work/'receipt.json')] = dict(status='passed')
            self.docs[self.references[role]['path']] = dict(status='verified',receipt_sha256=self.sha(work/'receipt.json'))
        self.docs[str(self.stage.NATIVE_WORK/'receipt.json')] = dict(status='failed',commands=['twenty saved commands'])
        source = '/fixture/original-hash-source.py'
        self.original = dict(files={source:dict(sha256='source',identity={'ino':1},size=1)},links={},absent_paths=[],
            snapshot_inputs=[source],plan_sha256=self.sha(self.stage.HERE/'plan.json'))
        self.original['files'][str(self.stage.FILE_TABLE_SOURCE)] = dict(sha256='helper',identity={'ino':4},size=1)
        self.original['files'][str(self.stage.PLAN_REFERENCE_SOURCE)] = dict(sha256='plan-helper',identity={'ino':7},size=1)
        self.base = dict(path='/fixture/native03/inputs.json',sha256='base')
        self.original['files'][self.base['path']] = dict(sha256='base',identity={'ino':5},size=1)
        self.compact = copy.deepcopy(self.original)
        self.compact['files'] = {n:copy.deepcopy(r) for n,r in self.original['files'].items() if n != source}
        self.compact['file_table_base'] = copy.deepcopy(self.base)
        self.compact['file_table_integrity'] = dict(sha256='table',count=4,total_bytes=4)
        self.combined = copy.deepcopy(self.original)
        self.combined['files'][str(self.stage.HERE/'inputs.json')] = dict(
            sha256=self.sha(self.stage.HERE/'inputs.json'),identity={'ino':6},size=1)
        def load_table(wire, comp):
            self.events.append(('table-import',))
            if not p.same(wire, self.compact):
                raise RuntimeError('fixture load unexpected compact table')
            return 'fixture-qualified-table'
        def expand_table(wire, table, guard):
            self.events.append(('table-expand',))
            if table != 'fixture-qualified-table' or not p.same(wire['file_table_base'],self.base):
                raise RuntimeError('exact fixture base required')
            guard()
            return copy.deepcopy(self.original)
        self.stage.load_file_table = load_table
        self.stage.expand_file_table = expand_table
        extra = '/fixture/new-runtime-source.py'
        self.combined['files'][extra] = dict(sha256='new',identity={'ino':2},size=1)
        if runtime_selection:
            self.combined['snapshot_inputs'] = [extra]
        else:
            del self.combined['snapshot_inputs']
        for path in [self.stage.HERE/'snapshot-plan.json',self.stage.WORK/'snapshot-plan.json',
                     self.stage.WORK/'source-snapshots.json']:
            self.combined['files'][str(path)] = dict(sha256=self.sha(path),identity={'ino':3},size=1)
        children = [dict(argv=['compile'],environment={}),
                    *[dict(argv=['driver',mode],environment={}) for mode in ['serial','parallel']]]
        self.plan = dict(source_identity={'revision':'candidate'},children=children,
            independent_audits={role:ref for role,ref in self.references.items() if role!='hash'})
        self.docs[str(self.stage.HERE/'inputs.json')] = self.compact
        self.plan.update(continuation_controls=copy.deepcopy(self.continuation),failed_driver=copy.deepcopy(self.failed_owner))
        self.wire = dict(member='metadata_plan',reference=copy.deepcopy(self.stage.METADATA_PLAN_REFERENCE),fixture='wire')
        self.docs[str(self.stage.HERE/'plan.json')] = self.wire
        self.combined['files'][str(self.stage.HERE/'plan.json')] = dict(sha256=self.sha(self.stage.HERE/'plan.json'),identity={'ino':8},size=1)
        def load_plan(freeze, comp):
            self.events.append(('plan-import',))
            return 'fixture-plan-helper'
        def expand_plan(wire, helper, read_bytes):
            self.events.append(('plan-expand',))
            if helper!='fixture-plan-helper' or not p.same(wire,self.wire):raise RuntimeError('fixture plan envelope changed')
            return copy.deepcopy(self.plan)
        self.stage.load_plan_reference=load_plan
        self.stage.expand_plan=expand_plan
        self.docs[str(self.stage.WORK/'receipt.json')] = dict(status='passed-awaiting-independent-audit',
            inputs_sha256=self.sha(self.stage.HERE/'inputs.json'),snapshot_plan_sha256='snapshot-digest',
            result_sha256=self.sha(self.stage.WORK/'result.json'))
        self.closure = {'files':{'/fixture/provider':{}}}
        self.docs[str(self.stage.WORK/'driver-loader-closure.json')] = self.closure
        artifact = Path('/fixture/artifacts')
        result = dict(status='hash-driver-observations-passed-awaiting-independent-audit',candidate_revision='candidate',
            source_identity=self.plan['source_identity'],compilation_count=1,driver_process_count=2,contexts_per_process=8,
            application_qualified=False,performance_measurement=False,closure_sha256=self.sha(self.stage.WORK/'driver-loader-closure.json'),
            binary_sha256=self.sha(artifact/'hash-control-driver'),processes=[])
        for i, mode in enumerate(['serial','parallel']):
            work = self.stage.WORK/mode
            result['processes'].append(dict(mode=mode,pid=100+i,receipt_sha256=self.sha(work/'receipt.json'),
                readback_sha256=self.sha(work/'validated-readback.json')))
            self.docs[str(work/'receipt.json')] = dict(pid=100+i,mode=mode)
            self.docs[str(work/'validated-readback.json')] = dict(observed=mode)
            self.raw[str(work/'stdout')] = b'saved stdout'; self.raw[str(work/'stderr')] = b'saved stderr'
        self.docs[str(self.stage.WORK/'result.json')] = result
        for item in [self.docs[str(self.stage.WORK/'receipt.json')],result]:
            item.update(continuation_controls=copy.deepcopy(self.continuation),failed_driver=copy.deepcopy(self.failed_owner))
        self.docs[self.references['hash']['path']].update(result_sha256=self.sha(self.stage.WORK/'result.json'),
            inputs_sha256=self.sha(self.stage.HERE/'inputs.json'),snapshot_plan_sha256='snapshot-digest',
            launch_sha256=self.sha(self.stage.HERE/'launch.json'),metadata_plan_reference=copy.deepcopy(self.stage.METADATA_PLAN_REFERENCE),
            continuation_controls=copy.deepcopy(self.continuation),
            failed_predecessor=dict(owner=copy.deepcopy(self.failed_owner),receipt_sha256=self.sha(self.stage.FAILED_WORK/'receipt.json'),
                actual_children=1,qualified_children=0),actual_children=3,compilation_count=1,driver_process_count=2,contexts_per_process=8,
            historical_failed_compiler_children=1,total_actual_hash_children=4,hash_driver_qualified=True,
            application_qualified=False,performance_measurement=False,runtime_installation=False)
        self.historical = {}
        self.partition_override = None
        self.modules = dict(core=SimpleNamespace(S=Path('/fixture/compiler-source'),ARTIFACTS=artifact,
                desired_commands=lambda plan:copy.deepcopy(plan['children'])),
            monitor=SimpleNamespace(owned=SimpleNamespace(disk=lambda root,floor:self.events.append(('disk',str(root),floor)),sha=self.sha)),comp=SimpleNamespace(),
            snapshot_bindings=SimpleNamespace(__file__=str(self.stage.HERE/'snapshot_bindings.py')),
            trace=SimpleNamespace(process=lambda child,*args,**kwargs:dict(observed=child['mode'])))

    def read(self, path):
        self.reads.append(str(path))
        return copy.deepcopy(self.docs[str(path)])

    def partition(self, reader):
        self.events.append(('copy-bootstrap',))
        if self.partition_error:raise RuntimeError('copy bootstrap rejected')
        if self.partition_override is not None:return self.partition_override(reader)
        return dict(references={'fixture':'reference'}, historical_files=copy.deepcopy(self.historical),
            current_context_files=len(reader.original['files'])-len(self.historical),prior_catalog={'fixture':'prior'},
            bootstrap_policy='continued-catalog-before-reader',runtime_admitted=False,retirement_authorized=False)

    def reader(self):
        return p.Reader(self.stage,self.modules,combined_freeze=self.combined,references=self.references,
                        read_json=self.read,sha=self.sha,copy_partition=self.partition)


class SuccessorControls(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.forbidden = []
        for owner,names in [(subprocess,['Popen','run','call','check_call','check_output']),
                            (os,['open','kill','killpg','system']),
                            (Path,['open','read_bytes','read_text','write_bytes','write_text','mkdir','unlink','rmdir'])]:
            for name in names:
                self.forbidden.append(self.stack.enter_context(patch.object(owner,name,
                    side_effect=AssertionError('forbidden process/file operation: '+name))))

    def tearDown(self):
        for mocked in self.forbidden:
            mocked.assert_not_called()

    def test_early_union_binds_original_snapshot_selection_without_constructor(self):
        f=Fixture(runtime_selection=False); before=copy.deepcopy(f.combined); reader=f.reader()
        self.assertEqual(reader.reader.freeze['snapshot_inputs'],f.original['snapshot_inputs'])
        self.assertEqual(f.combined,before)
        self.assertIn(('bind','snapshot-digest',f.original['snapshot_inputs']),f.events)

    def test_final_runtime_selection_remains_distinct_and_unchanged(self):
        f=Fixture(); before=copy.deepcopy(f.combined); old=copy.deepcopy(f.original); reader=f.reader()
        self.assertNotEqual(reader.reader.freeze['snapshot_inputs'],f.combined['snapshot_inputs'])
        self.assertEqual(reader.reader.freeze['files'],f.combined['files'])
        self.assertEqual(f.combined,before); self.assertEqual(f.original,old)

    def test_missing_or_foreign_binding_module_rejects_before_stage_state(self):
        for foreign in [None,SimpleNamespace(__file__='/fixture/unrelated/snapshot_bindings.py')]:
            with self.subTest(foreign=foreign):
                f=Fixture()
                if foreign is None:del f.modules['snapshot_bindings']
                else:f.modules['snapshot_bindings']=foreign
                with self.assertRaisesRegex(RuntimeError,'exact hash v2'):f.reader()
                self.assertEqual(f.events,[])

    def test_incomplete_historical_selection_rejects(self):
        f=Fixture(); f.original['snapshot_inputs']=['/fixture/not-in-original-freeze.py']
        with self.assertRaisesRegex(RuntimeError,'historical hash snapshot selection'):f.reader()

    def test_failed_native_command_owner_and_passed_qualifier_remain_distinct(self):
        f=Fixture(); result=f.reader().check()
        self.assertEqual(result['earlier_qualifications']['saved_native_children'],20)
        self.assertEqual(result['earlier_qualifications']['reconciliation_workload_children'],0)
        self.assertIn(str(f.stage.NATIVE_QUALIFICATION_WORK/'receipt.json'),f.reads)
        self.assertIn(('original-commands','failed'),f.events)
        self.assertEqual(f.docs[str(f.stage.NATIVE_WORK/'receipt.json')]['status'],'failed')

    def test_original_failure_audit_cannot_replace_qualifier_audit(self):
        f=Fixture(); f.docs[f.references['native']['path']]['receipt_sha256']=f.sha(f.stage.NATIVE_WORK/'receipt.json')
        with self.assertRaisesRegex(RuntimeError,'actual independent audit differs: native'):f.reader().check()

    def test_absent_or_failed_qualifier_does_not_use_original_history_as_success(self):
        for absent in [True,False]:
            with self.subTest(absent=absent):
                f=Fixture(); path=str(f.stage.NATIVE_QUALIFICATION_WORK/'receipt.json')
                if absent:del f.docs[path]
                else:f.docs[path]['status']='failed'
                with self.assertRaises((KeyError,RuntimeError)):f.reader().check()
                self.assertNotIn(('original-commands','failed'),f.events)

    def test_saved_original_command_rejection_still_blocks_runtime(self):
        f=Fixture(); f.command_error=True
        with self.assertRaisesRegex(RuntimeError,'saved original command proof rejected'):f.reader().check()

    def test_qualifier_reference_must_equal_actual_hash_plan(self):
        f=Fixture(); f.references=copy.deepcopy(f.references)
        f.references['native']=dict(path='/fixture/new-audit',sha256=f.sha('/fixture/new-audit'))
        f.docs['/fixture/new-audit']=dict(status='verified',receipt_sha256=f.sha(f.stage.NATIVE_QUALIFICATION_WORK/'receipt.json'))
        with self.assertRaisesRegex(RuntimeError,'hash predecessor audit association'):f.reader().check()

    def test_compact_terminal_digest_refuses_before_helper_import(self):
        f=Fixture(); f.docs[str(f.stage.WORK/'receipt.json')]['inputs_sha256']='foreign'
        with self.assertRaisesRegex(RuntimeError,'completed compact hash input'):f.reader()
        self.assertNotIn(('table-import',),f.events)

    def test_actual_hash_audit_refuses_before_helper_qualification_or_import(self):
        for field,value in [('status','failed'),('receipt_sha256','foreign')]:
            with self.subTest(field=field):
                f=Fixture();f.docs[f.references['hash']['path']][field]=value
                with self.assertRaisesRegex(RuntimeError,'actual independent audit differs: hash'):f.reader()
                self.assertEqual(f.events,[])

    def test_compact_input_must_be_in_authenticated_union(self):
        for missing in [True,False]:
            with self.subTest(missing=missing):
                f=Fixture();key=str(f.stage.HERE/'inputs.json')
                if missing:del f.combined['files'][key]
                else:f.combined['files'][key]['sha256']='foreign'
                with self.assertRaisesRegex(RuntimeError,'compact hash inputs missing'):f.reader()
                self.assertEqual(f.events,[])

    def test_actual29_and_exact_helper_row_precede_import(self):
        f=Fixture();f.table_control_error=True
        with self.assertRaisesRegex(RuntimeError,'actual29'):f.reader()
        self.assertNotIn(('table-import',),f.events)
        f=Fixture();f.compact['files'][str(f.stage.FILE_TABLE_SOURCE)]['size']=True
        with self.assertRaisesRegex(RuntimeError,'helper differs'):f.reader()
        self.assertNotIn(('table-import',),f.events)
        f=Fixture();f.reader()
        self.assertLess(f.events.index(('file-table-qualified',29)),f.events.index(('table-import',)))
        self.assertLess(f.events.index(('table-import',)),f.events.index(('table-expand',)))

    def test_wrong_base_and_typed_inherited_row_refuse(self):
        f=Fixture();f.compact['file_table_base']['sha256']='foreign'
        with self.assertRaisesRegex(RuntimeError,'exact fixture base'):f.reader()
        f=Fixture();f.combined['files']['/fixture/original-hash-source.py']['size']=True
        with self.assertRaisesRegex(RuntimeError,'historical hash freeze'):f.reader()

    def test_actual22_snapshot_qualification_before_history(self):
        f=Fixture();f.snapshot_control_error=True
        with self.assertRaisesRegex(RuntimeError,'actual22'):f.reader()
        self.assertFalse(any(event[0]=='original-commands' for event in f.events))
        f=Fixture();reader=f.reader();reader.check()
        self.assertLess(f.events.index(('snapshot-qualified',22)),f.events.index(('original-commands','failed')))
        self.assertEqual(reader.inputs_sha256, f.sha(f.stage.HERE/'inputs.json'))
        self.assertEqual(reader.reader.inputs_sha256, reader.inputs_sha256)

    def owner_args(self, f):
        owner=dict(role='hash',source=str(f.stage.HERE),evidence=str(f.stage.WORK),audit=f.references['hash'],
            result_path=str(f.stage.WORK/'result.json'),result_digest_field='result_sha256')
        return [owner,f.read(f.stage.WORK/'receipt.json'),f.read(f.stage.WORK/'result.json'),
                f.read(f.references['hash']['path'])]

    def test_snapshot_owner_requires_successful_full_check_and_never_recurses(self):
        f=Fixture();reader=f.reader();args=self.owner_args(f)
        with self.assertRaisesRegex(RuntimeError,'complete hash recipe check'):reader.snapshot_owner(*args)
        reader.check(full=False)
        with self.assertRaisesRegex(RuntimeError,'complete hash recipe check'):reader.snapshot_owner(*args)
        summary=reader.check(full=True)
        self.assertEqual(summary['file_table_qualification'],f.table_proof)
        with patch.object(reader,'check',side_effect=AssertionError('recursive recipe check')):
            self.assertIs(reader.snapshot_owner(*args),True)

    def test_snapshot_owner_binds_all_exact_owner_fields(self):
        f=Fixture();reader=f.reader();reader.check()
        for field in ['role','source','evidence','audit','result_path','result_digest_field']:
            with self.subTest(field=field):
                args=self.owner_args(f);args[0][field]='foreign'
                with self.assertRaisesRegex(RuntimeError,'snapshot owner differs'):reader.snapshot_owner(*args)
        args=self.owner_args(f)
        f.references['hash']['path']='/fixture/changed-audit-declaration'
        with self.assertRaisesRegex(RuntimeError,'snapshot owner differs'):reader.snapshot_owner(*args)

    def test_snapshot_owner_rejects_readback_type_and_current_byte_changes(self):
        f=Fixture();reader=f.reader();reader.check()
        for index in [1,2,3]:
            with self.subTest(index=index):
                args=self.owner_args(f);args[index]['added']=1
                with self.assertRaisesRegex(RuntimeError,'owner readback differs'):reader.snapshot_owner(*args)
        args=self.owner_args(f);args[2]['compilation_count']=True
        with self.assertRaisesRegex(RuntimeError,'owner readback differs'):reader.snapshot_owner(*args)
        f.digests[str(f.stage.HERE/'inputs.json')]='changed'
        with self.assertRaisesRegex(RuntimeError,'owner changed after'):reader.snapshot_owner(*self.owner_args(f))

    def test_failed_later_full_check_invalidates_snapshot_owner_marker(self):
        f=Fixture();reader=f.reader();reader.check();f.command_error=True
        with self.assertRaisesRegex(RuntimeError,'saved original command proof'):reader.check()
        with self.assertRaisesRegex(RuntimeError,'complete hash recipe check'):reader.snapshot_owner(*self.owner_args(f))

    def factory_fixture(self, *, foreign=False):
        source=Path('/fixture/hash-source'); calls=[]; checked=[]
        binding=SimpleNamespace(__file__=str(source/('foreign.py' if foreign else 'snapshot_bindings.py')))
        historical_monitor=SimpleNamespace(owned=SimpleNamespace())
        stage=SimpleNamespace(dependencies=Mock(return_value={'snapshot_bindings':binding,'monitor':historical_monitor}))
        def load(name,path,check_source,dependencies=None):
            calls.append((name,Path(path))); check_source(Path(path))
            return stage if name=='hash_stage' else SimpleNamespace(__file__=str(path))
        return source,calls,checked,stage,load

    def test_factory_keeps_qualified_original_module_routes_and_loads_no_snapshot_helper(self):
        source,calls,checked,stage,load=self.factory_fixture()
        with patch.object(factory,'load',side_effect=load),patch.object(Path,'resolve',lambda self,**kwargs:self):
            modules=factory.definitions(source,checked.append)
        self.assertEqual(stage.dependencies.call_count,1)
        for name in ['recipe','discovery','controller']:
            self.assertIn((name,factory.QUALIFIED/(name+'.py')),calls)
        self.assertIn(('private_monitor',factory.QUALIFIED/'monitor.py'),calls)
        self.assertIn(('prerequisites',factory.HERE/'prerequisites.py'),calls)
        self.assertIn(('preflight_history',factory.HERE/'preflight_history.py'),calls)
        self.assertEqual(checked.count(source/'snapshot_bindings.py'),2)
        self.assertIs(modules.hash_modules['snapshot_bindings'],stage.dependencies.return_value['snapshot_bindings'])
        self.assertFalse(any(path.name=='proof_snapshots.py' for _,path in calls))

    def test_factory_rejects_wrong_binding_module_before_loading_installer(self):
        source,calls,checked,stage,load=self.factory_fixture(foreign=True)
        with patch.object(factory,'load',side_effect=load),patch.object(Path,'resolve',lambda self,**kwargs:self):
            with self.assertRaisesRegex(RuntimeError,'snapshot binding module route'):factory.definitions(source,checked.append)
        self.assertEqual(calls,[('hash_stage',source/'stage.py')])

    def test_raw_plan_digest_is_preserved_after_expansion(self):
        f=Fixture();reader=f.reader()
        self.assertEqual(reader.plan,f.plan)
        self.assertNotEqual(reader.plan,f.wire)
        self.assertEqual(reader.plan_wire_sha256,f.sha(f.stage.HERE/'plan.json'))
        f.digests[str(f.stage.HERE/'plan.json')]='changed-wire'
        with self.assertRaisesRegex(RuntimeError,'completed raw hash plan changed'):reader.read_hash_plan()

    def test_actual70_precedes_plan_helper_import_and_partition(self):
        f=Fixture();reader=f.reader()
        self.assertLess(f.events.index(('continuation-qualified',70)),f.events.index(('plan-import',)))
        self.assertLess(f.events.index(('plan-expand',)),f.events.index(('copy-bootstrap',)))
        self.assertLess(f.events.index(('snapshot-qualified',22)),f.events.index(('copy-bootstrap',)))
        self.assertIsNone(reader._checked)
        f=Fixture();f.continuation_error=True
        with self.assertRaisesRegex(RuntimeError,'actual70'):f.reader()
        self.assertNotIn(('plan-import',),f.events)
        self.assertNotIn(('copy-bootstrap',),f.events)

    def test_plan_helper_current_row_is_typed_and_exact(self):
        f=Fixture();f.combined['files'][str(f.stage.PLAN_REFERENCE_SOURCE)]['size']=True
        with self.assertRaisesRegex(RuntimeError,'plan-reference helper differs'):f.reader()
        self.assertNotIn(('plan-import',),f.events)

    def test_continuation_and_failed_owner_cannot_be_relabelled(self):
        for key in ['continuation_controls','failed_driver']:
            with self.subTest(key=key):
                f=Fixture();f.plan[key]['foreign']=True
                with self.assertRaisesRegex(RuntimeError,'continuation and failed-owner'):f.reader()

    def test_failed_hash_owner_is_kept_distinct_from_passed_hash02(self):
        f=Fixture();summary=f.reader().check()
        old=summary['failed_hash_predecessor']
        self.assertEqual(old['actual_children'],1)
        self.assertEqual(old['qualified_children'],0)
        self.assertEqual(old['owner'],f.failed_owner)
        for key in ['failed_predecessor','metadata_plan_reference','continuation_controls']:
            with self.subTest(key=key):
                g=Fixture();g.docs[g.references['hash']['path']][key]={'foreign':True}
                with self.assertRaisesRegex(RuntimeError,'successful continuation audit'):g.reader().check()

    def test_actual_driver_count_types_and_scope_are_exact(self):
        for key,value in [('compilation_count',True),('total_actual_hash_children',4.0),
                          ('application_qualified',True),('runtime_installation',True)]:
            with self.subTest(key=key):
                f=Fixture();f.docs[f.references['hash']['path']][key]=value
                with self.assertRaisesRegex(RuntimeError,'successful continuation audit'):f.reader().check()

    def test_bootstrap_rejection_precedes_original_command_qualification(self):
        f=Fixture();f.partition_error=True
        with self.assertRaisesRegex(RuntimeError,'copy bootstrap rejected'):f.reader()
        self.assertFalse(any(e[0]=='original-commands' for e in f.events))

    def historical_fixture(self):
        f=Fixture();name='/fixture/retained-proof-copy'
        row=dict(sha256='copy',size=3,identity={'ino':11})
        f.original['files'][name]=copy.deepcopy(row)
        f.historical[name]=copy.deepcopy(row)
        return f,name,row

    def test_explicit_historical_copy_is_not_inserted_in_physical_union(self):
        f,name,row=self.historical_fixture();before=copy.deepcopy(f.combined);reader=f.reader()
        self.assertEqual(reader.original['files'][name],row)
        self.assertNotIn(name,reader.reader.freeze['files'])
        with self.assertRaisesRegex(RuntimeError,'missing frozen projection'):reader.reader.frozen(name)
        self.assertEqual(f.combined,before)
        self.assertEqual(reader.check()['historical_copy_references'],{'fixture':'reference'})

    def test_saved_copy_mapping_cannot_omit_or_modify_original_row(self):
        for missing in [True,False]:
            with self.subTest(missing=missing):
                f,name,row=self.historical_fixture()
                if missing:del f.historical[name]
                else:f.historical[name]['size']=True
                with self.assertRaisesRegex(RuntimeError,'historical hash freeze omitted or changed'):f.reader()

    def test_historical_copy_cannot_overlap_current_or_selected(self):
        for current in [True,False]:
            with self.subTest(current=current):
                f,name,row=self.historical_fixture()
                if current:f.combined['files'][name]=copy.deepcopy(row)
                else:f.original['snapshot_inputs'].append(name)
                with self.assertRaisesRegex(RuntimeError,'historical copy overlaps'):f.reader()

    def test_bootstrap_cannot_mutate_original_or_grant_admission(self):
        for mode in ['mutation','admission','retirement','count']:
            with self.subTest(mode=mode):
                f=Fixture();state=f.partition(SimpleNamespace(original=f.original))
                def altered(reader):
                    if mode=='mutation':reader.original['added']='foreign'
                    elif mode=='admission':state['runtime_admitted']=True
                    elif mode=='retirement':state['retirement_authorized']=True
                    else:state['current_context_files']=True
                    return state
                f.partition_override=altered
                with self.assertRaisesRegex(RuntimeError,'partition changed|cannot grant|partition counts'):f.reader()

    def test_full_check_rebuilds_partition_and_invalidates_owner_after_failure(self):
        f=Fixture();reader=f.reader();reader.check()
        self.assertEqual(f.events.count(('copy-bootstrap',)),2)
        f.partition_error=True
        with self.assertRaisesRegex(RuntimeError,'copy bootstrap rejected'):reader.check()
        with self.assertRaisesRegex(RuntimeError,'complete hash recipe check'):reader.snapshot_owner(*self.owner_args(f))

    def test_partition_runs_without_successful_owner_callback(self):
        f=Fixture();reader=f.reader()
        with patch.object(reader,'snapshot_owner',side_effect=AssertionError('circular successful owner')):
            reader.partition()
        self.assertIsNone(reader._checked)

    def test_later_partition_cannot_change_saved_witnesses(self):
        f=Fixture();reader=f.reader();state=copy.deepcopy(reader.copy_state)
        state['prior_catalog']['foreign']=True
        f.partition_override=lambda ignored:state
        with self.assertRaisesRegex(RuntimeError,'historical-copy bootstrap changed'):reader.check()

    def test_original_physical_input_omission_still_rejects(self):
        f=Fixture();del f.combined['files']['/fixture/original-hash-source.py']
        with self.assertRaisesRegex(RuntimeError,'historical hash freeze omitted or changed'):f.reader()

    def test_factory_loads_own_copy_adapter_without_reference_or_snapshot_helper(self):
        source,calls,checked,stage,load=self.factory_fixture()
        with patch.object(factory,'load',side_effect=load),patch.object(Path,'resolve',lambda self,**kwargs:self):
            factory.definitions(source,checked.append)
        self.assertIn(('copies',factory.HERE/'copies.py'),calls)
        self.assertFalse(any(path.name in ['references.py','proof_snapshots.py'] for _,path in calls))


if __name__=='__main__':unittest.main()
