from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from suite_reports import validate_shared_templates

def fixture():
    return dict(mode='prepared',workers=2,shared_templates=dict(requested=True,active=True,preparation_ns=10,
        storage=dict(functions=1,charged_bytes=2000,limit_bytes=64*1024*1024)),tests=[
        dict(status='passed',worker=0,shared_templates=dict(hits=0,misses=1,restored_code_bytes=0)),
        dict(status='failed',worker=1,shared_templates=dict(hits=1,misses=0,restored_code_bytes=100))])

class SharedTemplateReceiptTests(unittest.TestCase):
    def test_passed_and_failed_test_counters_are_both_validated(self):
        validate_shared_templates(fixture(),True)
        for key in ['hits','misses','restored_code_bytes']:
            bad=fixture();bad['tests'][1]['shared_templates'][key]=True
            with self.assertRaises(RuntimeError):validate_shared_templates(bad,True)
    def test_default_off_accepts_old_receipts_and_rejects_unrequested_sharing(self):
        validate_shared_templates(dict(tests=[dict(status='passed')]),False)
        with self.assertRaises(RuntimeError):validate_shared_templates(fixture(),False)
        bad=fixture();bad.pop('shared_templates')
        with self.assertRaises(RuntimeError):validate_shared_templates(bad,False)
    def test_one_effective_worker_must_report_ordinary_preparation(self):
        report=fixture();report['workers']=1;report['shared_templates'].update(active=False,storage=None)
        report['tests']=[dict(status='passed',worker=0)];validate_shared_templates(report,True)
        report['shared_templates']['active']=True
        with self.assertRaises(RuntimeError):validate_shared_templates(report,True)
    def test_mode_workers_storage_bounds_and_identity_are_required(self):
        changes=[lambda r:r.update(mode='fresh'),lambda r:r.update(workers=True),lambda r:r.update(workers=0),
            lambda r:r.pop('shared_templates'),lambda r:r['shared_templates'].update(requested=False),
            lambda r:r['shared_templates'].update(storage=None),lambda r:r['shared_templates'].update(preparation_ns=-1),
            lambda r:r['shared_templates']['storage'].update(limit_bytes=True),
            lambda r:r['shared_templates']['storage'].update(charged_bytes=64*1024*1024+1)]
        for change in changes:
            bad=fixture();change(bad)
            with self.assertRaises(RuntimeError):validate_shared_templates(bad,True)
    def test_inconsistent_hits_bytes_or_owner_cannot_claim_reuse(self):
        for change in [lambda r:r['tests'][1].update(worker=2),lambda r:r['tests'][1].pop('shared_templates'),
            lambda r:r['tests'][1]['shared_templates'].update(hits=0),
            lambda r:r['tests'][1]['shared_templates'].update(restored_code_bytes=0),
            lambda r:r['tests'][1]['shared_templates'].update(restored_code_bytes=3)]:
            bad=fixture();change(bad)
            with self.assertRaises(RuntimeError):validate_shared_templates(bad,True)

if __name__=='__main__':unittest.main()
