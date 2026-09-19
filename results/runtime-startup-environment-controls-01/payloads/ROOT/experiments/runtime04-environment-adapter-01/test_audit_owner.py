"""Complete saved phase-owner fixtures for the explicit startup successor.

All records and identities are in memory. The original53 fixture source and
reader definitions are imported from their exact immutable source routes.
"""
import copy
import importlib.util
from pathlib import Path
import unittest
import audit_owner as owner
import environment

ORIGINAL = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/hir-options-hash-runtime-audit-05/test_reader.py')


def fixture(phase='preflight', value='0x1F5:0x0:0x52'):
    spec=importlib.util.spec_from_file_location('_startup_original_owner_fixture',ORIGINAL)
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    return Fixture(old.OwnerFixture(phase),value)


class Fixture:
    def __init__(self, base, value):
        self.base=base;self.s=base.saved;self.phase=base.phase
        self.workload=dict(base.plan['environment'],TMPDIR=str(base.paths['work']/'tmp'))
        self.passed={'PATH':'/fixture/python','HOME':'/fixture/home'}
        observed=dict(self.passed)
        if value is not None:observed[environment.CF]=value
        observations={name:dict(observed) for name in environment.OBSERVATIONS}
        derivation=environment.derive(self.workload,self.passed,observations,platform='darwin',uid=501)
        policy=dict(path=str(owner.ADAPTER/'environment.py'),sha256=self.s.bytes(owner.ADAPTER/'environment.py',b'policy'))
        preparer=dict(path=str(owner.ADAPTER/'prepare.py'),sha256=self.s.bytes(owner.ADAPTER/'prepare.py',b'preparer'))
        qualification=dict(controls=1,audit=dict(path='/fixture/startup-audit.json',sha256=self.s.json('/fixture/startup-audit.json',{'status':'verified'})))
        self.qualification=copy.deepcopy(qualification)
        manifest_value=dict(status='reviewed-runtime04-startup-source-closure',files={
            row['path']:dict(sha256=row['sha256'],size=self.s.identity(row['path'])['size'],identity=self.s.identity(row['path']))
            for row in [policy,preparer]})
        manifest=dict(path='/fixture/adapter-sources.json',sha256=self.s.json('/fixture/adapter-sources.json',manifest_value))
        self.record_path=base.reader.R/'.work'/('hir-options-hash-runtime-'+self.phase+'-preparation-execution-04')/'record.json'
        self.proof=dict(derivation=derivation,policy=policy,preparer=preparer,qualification=qualification,
                       preparation_record=str(self.record_path),source_manifest=manifest)
        base.plan.update(environment=dict(self.workload),launch_environment=dict(derivation['launch_environment']),
                         startup_environment=self.proof)
        base.launch['environment']=dict(derivation['launch_environment'])
        self.observation=dict(status='returned',pid=12,parent_pid=11,blocked_events=[],started_at=3,finished_at=4,
            environments=dict(passed=dict(self.passed),before_validation=dict(observed),
                              before_producer_imports=dict(observed),at_return_or_failure=dict(observed)))
        wrapper=Path('/fixture/prepare_once.py');wrapper_sha=self.s.bytes(wrapper,b'wrapper')
        self.s.bytes(self.record_path.parent/'launcher.py',b'wrapper')
        base.expected['preparation_launcher']=dict(path=str(wrapper),sha256=wrapper_sha)
        invocation=dict(adapter=dict(preparer=preparer,source_manifest=manifest,startup_controls=qualification['audit']))
        self.invocation=dict(path='/fixture/invocation.json',sha256=self.s.json('/fixture/invocation.json',invocation))
        command=['/fixture/python','-B',preparer['path'],'--phase',self.phase,
            '--preparation-record',str(self.record_path),'--preparation-passed-environment-json',environment.encoded(self.passed).decode(),
            '--startup-audit-sha256',qualification['audit']['sha256'],
            '--startup-source-manifest',manifest['path'],'--startup-source-manifest-sha256',manifest['sha256']]
        self.observation['command']=command
        self.record=dict(status='finished',returncode=0,preparation_passed=True,phase=self.phase,cwd=str(base.reader.R),
            canonical_owner='producer-child',signals=[],runtime_admission=False,compiler_calls=0,provider_probes=0,
            environment=dict(self.passed),producer_command=command,command=['/fixture/python','-B',str(wrapper)],
            source_sha256=wrapper_sha,pid=12,parent_pid=11,started_at=1,child_started_at=2,finished_at=5,
            readback_finished_at=6,invocation=self.invocation)
        self.refresh()

    def refresh(self):
        b,s=self.base,self.s;packet=b.paths['packet']
        b.launch['plan_sha256']=s.json(packet/'plan.json',b.plan)
        b.terminal['plan_sha256']=b.launch['plan_sha256']
        b.expected['launch']=s.json(packet/'launch.json',b.launch)
        b.expected['receipt']=s.json(b.paths['work']/'receipt.json',b.terminal)
        b.launcher['environment']=dict(b.launch['environment']);b.launcher['launch_sha256']=b.expected['launch']
        b.expected['launcher_record_sha256']=s.json(b.expected['launcher_record'],b.launcher)
        self.record['outputs']={name:dict(sha256=s.sha(packet/name)) for name in ['plan.json','inputs.json','launch.json']}
        self.record['child_observation_sha256']=s.json(self.record_path.parent/'child-observation.json',self.observation)
        b.expected['preparation']=dict(path=str(self.record_path),sha256=s.json(self.record_path,self.record))

    def check(self, validation=None):
        b=self.base
        return owner.owner(b.plan,b.launch,b.terminal,b.outer,b.launcher,phase=b.phase,expected=b.expected,
            sha=self.s.sha,read_json=self.s.read,original=b.reader,workload_environment=self.workload,
            validate_qualification=validation or (lambda proof:proof==self.qualification))


class Owner(unittest.TestCase):
    def test_both_full_phase_shapes_keep_raw_plan(self):
        for phase in ['preflight','installation']:
            f=fixture(phase);before=copy.deepcopy(f.base.plan)
            self.assertEqual(f.check(),f.base.paths);self.assertEqual(f.base.plan,before)

    def test_plain_exact_launch_without_cf_remains_valid(self):
        f=fixture(value=None);self.assertEqual(f.check(),f.base.paths)

    def test_changed_recipe_environment_is_rejected(self):
        f=fixture();f.base.plan['environment']['PATH']='/foreign';f.refresh()
        with self.assertRaisesRegex(RuntimeError,'workload environment'):f.check()

    def test_foreign_launcher_environment_is_rejected(self):
        for which in ['plan','launch','launcher']:
            f=fixture()
            if which=='plan':f.base.plan['launch_environment']['FOREIGN']='x'
            elif which=='launch':f.base.launch['environment']['FOREIGN']='x'
            else:f.base.launcher['environment']['FOREIGN']='x'
            with self.assertRaises(RuntimeError):f.check()

    def test_forged_cf_observation_is_rejected(self):
        f=fixture()
        for value in f.proof['derivation']['observations'].values():value[environment.CF]='501:0:83'
        f.proof['derivation']['launch_environment'][environment.CF]='501:0:83'
        f.base.plan['launch_environment'][environment.CF]='501:0:83';f.base.launch['environment'][environment.CF]='501:0:83';f.refresh()
        with self.assertRaisesRegex(RuntimeError,'raw preparation'):f.check()

    def test_unqualified_or_mutated_control_proof_is_rejected(self):
        f=fixture()
        with self.assertRaisesRegex(RuntimeError,'actual startup controls'):f.check(lambda proof:False)
        with self.assertRaisesRegex(RuntimeError,'actual startup controls'):f.check(lambda proof:1)
        before=copy.deepcopy(f.proof)
        def mutate(proof):proof['controls']=999;return False
        with self.assertRaises(RuntimeError):f.check(mutate)
        self.assertEqual(f.proof,before)

    def test_preparation_reference_and_observation_hash_are_required(self):
        f=fixture();f.base.expected['preparation']['sha256']='f'*64
        with self.assertRaises(RuntimeError):f.check()
        f=fixture();f.s.json(f.record_path.parent/'child-observation.json',dict(f.observation,status='failed'))
        with self.assertRaisesRegex(RuntimeError,'observation digest'):f.check()

    def test_closed_preparation_and_typed_counters_are_required(self):
        for key,value in [('status','running'),('returncode',1),('returncode',False),('preparation_passed',False),
                          ('signals',[9]),('compiler_calls',True),('compiler_calls',False),('runtime_admission',True)]:
            f=fixture();f.record[key]=value;f.refresh()
            with self.subTest(key=key,value=value),self.assertRaises(RuntimeError):f.check()

    def test_preparation_child_parent_time_and_command_are_bound(self):
        for key,value in [('pid',999),('parent_pid',999),('finished_at',7),('command',['foreign']),('blocked_events',['open'])]:
            f=fixture();f.observation[key]=value;f.refresh()
            with self.subTest(key=key),self.assertRaises(RuntimeError):f.check()

    def test_preparation_must_finish_before_runtime_owner_starts(self):
        f=fixture()
        for key in ['started_at','child_started_at','finished_at','readback_finished_at']:
            f.record[key]+=100
        for key in ['started_at','finished_at']:f.observation[key]+=100
        f.refresh()
        with self.assertRaisesRegex(RuntimeError,'preparation chronology'):f.check()

    def test_source_manifest_invocation_and_source_bytes_are_bound(self):
        for path in [owner.ADAPTER/'environment.py',owner.ADAPTER/'prepare.py',Path('/fixture/adapter-sources.json'),
                     Path('/fixture/invocation.json'),Path('/fixture/prepare_once.py')]:
            f=fixture();f.s.bytes(path,b'changed')
            with self.subTest(path=str(path)),self.assertRaises((RuntimeError,ValueError)):f.check()

    def test_original_terminal_and_packet_predicates_are_retained(self):
        for key,value in [('status','failed'),('pid',0),('application_qualified',True),('free_bytes_before',0)]:
            f=fixture();f.base.terminal[key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):f.check()
        for key in ['launch','inputs','snapshot_plan','receipt','launcher_record_sha256']:
            f=fixture();f.base.expected[key]='f'*64
            with self.subTest(key=key),self.assertRaises(RuntimeError):f.check()

    def test_original_supervisor_predicates_are_retained(self):
        for key,value in [('child_pid',999),('supervisor_pid',999),('command',['foreign']),('cwd','/foreign'),
                          ('returncode',1),('child_started_at',99),('log_sha256','f'*64)]:
            f=fixture();f.base.outer[key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):f.check()

    def test_original_launcher_predicates_are_retained(self):
        for key,value in [('status','finished'),('returncode',1),('controller_pid',999),('supervisor_pid',999),
                          ('terminal_observed_at',0),('command',['foreign']),('stdout_sha256','f'*64)]:
            f=fixture();f.base.launcher[key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):f.check()

    def test_original_handoff_and_raw_predicates_are_retained(self):
        for name in ['stdout','stderr']:
            f=fixture();path=Path(f.base.expected['launcher_record']).parent/name
            f.s.bytes(path,b'changed')
            with self.subTest(name=name),self.assertRaises(RuntimeError):f.check()
