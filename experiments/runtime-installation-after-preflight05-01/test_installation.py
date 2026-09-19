"""Pure installation routing/prerequisite controls, with no provider imports.

The history callback records exact routing or deliberately refuses admission;
these fixtures do not model or claim qualification of the two compiler probes.
The immutable preflight reader performs that full validation in production.
"""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import entry
import controller
import audit_owner

CURRENT=json.loads(Path(__file__).with_name('routes.json').read_bytes())
PRIOR=json.loads(entry.PREFLIGHT_ROUTES.read_bytes())


def encoded(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def require(ok,message):
    if not ok:raise RuntimeError(message)


class Fixture:
    def __init__(self):
        self.data={str(entry.ROUTES):copy.deepcopy(CURRENT),str(entry.PREFLIGHT_ROUTES):copy.deepcopy(PRIOR)}
        self.pins={str(entry.ROUTES):entry.ROUTES_SHA256,str(entry.PREFLIGHT_ROUTES):entry.PREFLIGHT_ROUTES_SHA256}
        self.packet=Path(PRIOR['packet']);self.work=Path(PRIOR['work'])
        self.audit_ref=dict(path=PRIOR['report'],sha256='a'*64)
        self.expected=dict(source_preflight_audit=copy.deepcopy(self.audit_ref))
        self.terminal=dict(status='passed',phase='preflight',source_preflight_sha256='b'*64)
        self.data[str(self.work/'receipt.json')]=self.terminal
        self.result=dict(path=str(self.work/'source-probe/result.json'),sha256='b'*64)
        self.audit=dict(status='verified',phase='preflight',actual_children=2,
            attempt=dict(path=str(entry.PREFLIGHT_ROUTES),sha256=entry.PREFLIGHT_ROUTES_SHA256),
            receipt_sha256='c'*64,result_sha256='b'*64,inputs_sha256='d'*64,plan_sha256='e'*64,
            outer_sha256='f'*64,launcher_record_sha256='1'*64)
        self.data[self.audit_ref['path']]=self.audit
        self.pins.update({self.audit_ref['path']:'a'*64,str(self.work/'receipt.json'):'c'*64,
            str(self.work/'source-probe/result.json'):'b'*64,str(self.packet/'inputs.json'):'d'*64,
            str(self.packet/'plan.json'):'e'*64,str(Path(PRIOR['supervisor'])/'status.json'):'f'*64,
            str(Path(PRIOR['launcher_execution'])/'record.json'):'1'*64})
        self.plan=dict(phase='installation',owner=str(entry.R),work=CURRENT['work'],supervisor_work=CURRENT['supervisor'],
            attempt=dict(path=str(entry.ROUTES),sha256=entry.ROUTES_SHA256),capacity=copy.deepcopy(CURRENT['capacity']),
            retry_qualification=dict(kind='actual-old33'),installation_qualification=dict(kind='separate-new-controls'),
            source_preflight=copy.deepcopy(self.result),source_preflight_readback=dict(audit=copy.deepcopy(self.audit_ref),reference=copy.deepcopy(self.result)))
        self.original=SimpleNamespace(require=require,same=lambda x,y:encoded(x)==encoded(y),R=entry.R)
        self.history=Mock(return_value={'history':'returned only after full real validator in production'})
        self.modules=SimpleNamespace(q=object(),recipe=object(),preflight_history=SimpleNamespace(validate=self.history))

    def sha(self,path):return self.pins[str(path)]
    def read(self,path):return copy.deepcopy(self.data[str(path)])
    def owner_routes(self,**callbacks):
        return audit_owner.attempt_routes(self.plan,phase='installation',sha=self.sha,read_json=self.read,
            original=self.original,validate_retry_qualification=callbacks.get('old',lambda x:x=={'kind':'actual-old33'}),
            validate_installation_qualification=callbacks.get('new',lambda x:x=={'kind':'separate-new-controls'}))
    def preflight(self):
        return entry.completed_preflight(self.modules,candidate={'candidate':'current'},audit_reference=self.audit_ref,
            read_json=self.read,read_bytes=lambda path:(_ for _ in ()).throw(AssertionError('fixture has no provider bytes')),sha=self.sha)
    def admission(self):
        return audit_owner.preflight_admission(self.plan,expected=self.expected,sha=self.sha,read_json=self.read,original=self.original)


class Routes(unittest.TestCase):
    def test_current_installation_uses_exact_preflight05(self):
        f=Fixture();self.assertEqual(entry.attempt_routes(read_json=f.read,sha=f.sha),CURRENT)
        self.assertEqual(entry.preflight_routes(read_json=f.read,sha=f.sha),CURRENT['preflight'])

    def test_current_descriptor_bytes_are_authenticated(self):
        f=Fixture();f.pins[str(entry.ROUTES)]='0'*64
        with self.assertRaises(RuntimeError):entry.attempt_routes(read_json=f.read,sha=f.sha)

    def test_preflight_phase_cannot_reuse_installation_attempt(self):
        f=Fixture();f.data[str(entry.ROUTES)]['phase']='preflight'
        with self.assertRaises(RuntimeError):entry.attempt_routes(read_json=f.read,sha=f.sha)

    def test_qualified_factory_source_cannot_change(self):
        f=Fixture();f.data[str(entry.ROUTES)]['qualified_source']='/fixture/different-factory'
        with self.assertRaises(RuntimeError):entry.attempt_routes(read_json=f.read,sha=f.sha)

    def test_old_preflight_descriptor_bytes_are_authenticated(self):
        f=Fixture();f.pins[str(entry.PREFLIGHT_ROUTES)]='0'*64
        with self.assertRaises(RuntimeError):entry.preflight_routes(read_json=f.read,sha=f.sha)

    def test_old04_packet_cannot_replace_completed05(self):
        f=Fixture();f.data[str(entry.ROUTES)]['preflight']['packet']=PRIOR['failed_predecessor']['packet']
        with self.assertRaises(RuntimeError):entry.preflight_routes(read_json=f.read,sha=f.sha)

    def test_predecessor_owner_is_not_installation(self):
        f=Fixture();f.data[str(entry.PREFLIGHT_ROUTES)]['phase']='installation'
        with self.assertRaises(RuntimeError):entry.preflight_routes(read_json=f.read,sha=f.sha)


class Phase(unittest.TestCase):
    def test_installation24_is_accepted_without_provider_access(self):
        f=Fixture();self.assertEqual(controller.phase_admission(f.plan,sha=f.sha,read_json=f.read),CURRENT)

    def test_preflight16_is_rejected(self):
        f=Fixture();f.plan['capacity']['entry_gib']=16
        with self.assertRaises(RuntimeError):controller.phase_admission(f.plan,sha=f.sha,read_json=f.read)

    def test_phase_and_old_work_routes_are_rejected(self):
        for field,value in [('phase','preflight'),('work',PRIOR['work']),('supervisor_work',PRIOR['supervisor']),('owner','/fixture/owner')]:
            f=Fixture();f.plan[field]=value
            with self.subTest(field=field),self.assertRaises(RuntimeError):controller.phase_admission(f.plan,sha=f.sha,read_json=f.read)

    def test_attempt_identity_cannot_be_replaced(self):
        f=Fixture();f.plan['attempt']['path']=str(entry.PREFLIGHT_ROUTES)
        with self.assertRaises(RuntimeError):controller.phase_admission(f.plan,sha=f.sha,read_json=f.read)

    def test_both_old_and_new_source_qualifications_are_required(self):
        f=Fixture();self.assertEqual(f.owner_routes(),CURRENT)
        for which in ['old','new']:
            with self.subTest(which=which),self.assertRaises(RuntimeError):f.owner_routes(**{which:lambda p:False})

    def test_new_qualification_is_exact_true_not_truthy(self):
        with self.assertRaises(RuntimeError):Fixture().owner_routes(new=lambda p:1)

    def test_qualification_callbacks_cannot_mutate_plan(self):
        f=Fixture();before=copy.deepcopy(f.plan)
        def mutate(proof):proof['changed']=True;return True
        f.owner_routes(old=mutate,new=mutate);self.assertEqual(f.plan,before)


class Preflight(unittest.TestCase):
    def test_completed05_routes_into_unchanged_history_validator(self):
        f=Fixture();self.assertEqual(f.preflight(),f.history.return_value)
        f.history.assert_called_once();args,kw=f.history.call_args
        self.assertEqual(args,(f.modules.q,f.modules.recipe))
        self.assertEqual(kw['packet'],f.packet);self.assertEqual(kw['work'],f.work)
        self.assertEqual(kw['candidate'],{'candidate':'current'});self.assertEqual(kw['audit_reference'],f.audit_ref)

    def test_history_validation_failure_is_not_bypassed(self):
        f=Fixture();f.history.side_effect=RuntimeError('actual raw history rejected')
        with self.assertRaisesRegex(RuntimeError,'actual raw history rejected'):f.preflight()

    def test_explicit_future_audit_pin_is_required(self):
        for value in [None,'','0'*63,'not-a-digest']:
            f=Fixture();f.audit_ref['sha256']=value
            with self.subTest(value=value),self.assertRaises(RuntimeError):f.preflight()
            f.history.assert_not_called()

    def test_old04_audit_path_is_rejected(self):
        f=Fixture();f.audit_ref['path']=f.audit_ref['path'].replace('-05.json','-04.json')
        with self.assertRaises(RuntimeError):f.preflight()
        f.history.assert_not_called()

    def test_exact_two_typed_children_required(self):
        for value in [True,1,3]:
            f=Fixture();f.audit['actual_children']=value
            with self.subTest(value=value),self.assertRaises(RuntimeError):f.preflight()

    def test_all_actual_owner_digests_remain_bound(self):
        for field in ['receipt_sha256','result_sha256','inputs_sha256','plan_sha256','outer_sha256','launcher_record_sha256']:
            f=Fixture();f.audit[field]='0'*64
            with self.subTest(field=field),self.assertRaises(RuntimeError):f.preflight()
            f.history.assert_not_called()

    def test_failed_or_different_phase_audit_is_rejected(self):
        for field,value in [('status','failed'),('phase','installation'),('attempt',{})]:
            f=Fixture();f.audit[field]=value
            with self.subTest(field=field),self.assertRaises(RuntimeError):f.preflight()

    def test_saved_owner_accepts_exact_closed05_prerequisite(self):
        f=Fixture();answer=f.admission();self.assertEqual(answer,f.audit_ref)
        answer['path']='/fixture/mutated';self.assertEqual(f.expected['source_preflight_audit'],f.audit_ref)

    def test_saved_owner_refuses_failed_terminal(self):
        f=Fixture();f.terminal['status']='failed'
        with self.assertRaises(RuntimeError):f.admission()

    def test_saved_owner_refuses_substituted_result_reference(self):
        f=Fixture();f.plan['source_preflight']['path']='/fixture/different-result'
        with self.assertRaises(RuntimeError):f.admission()

    def test_saved_owner_requires_external_audit_reference(self):
        f=Fixture();f.expected['source_preflight_audit']['sha256']='0'*64
        with self.assertRaises(RuntimeError):f.admission()
