import copy,hashlib,json
from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from template_session_receipt import read_receipt,validate_selection
from types import SimpleNamespace

class TemplateSessionReceipts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.artifact=self.root/'program.rbc';self.artifact.write_bytes(b'current artifact')
        self.catalog=self.root/'catalog.json';self.write(self.catalog,dict(artifact_sha256=self.sha(self.artifact),entries=[dict(name='one'),dict(name='two')]))
        self.ready=self.root/'ready.json';self.write(self.ready,dict(pid=123,executable_sha256='a'*64,auth='never-publish-this-token',
            history_bytes_per_worker=67108864,verify_hits=False,cpu_at_ready=dict(user_us=10,system_us=5)))
        self.report=self.root/'report.json';self.write(self.report,dict(schema_version=1,request_id=1,mode='prepared',workers=2,
            poisoned=False,status='passed',passed=2,failed=0,artifact_sha256=self.sha(self.artifact),catalog_sha256=self.sha(self.catalog),
            tests=[dict(name='one',status='passed'),dict(name='two',status='passed')]))
        self.path=Path(str(self.report)+'.session.json')
        self.receipt=dict(schema_version=1,transport='private-unix-socket',request_id=1,server_pid=123,server_executable_sha256='a'*64,
            readiness_sha256=self.sha(self.ready),history_bytes_per_worker=67108864,verify_hits=False,report=str(self.report),
            artifact_sha256=self.sha(self.artifact),catalog_sha256=self.sha(self.catalog),status='completed',report_sha256=self.sha(self.report),
            response=dict(kind='result',poisoned=False,id=1,pid=123,executable_sha256='a'*64,report=str(self.report),
                report_sha256=self.sha(self.report),status='passed',cpu_before=dict(user_us=11,system_us=6),cpu_after=dict(user_us=25,system_us=8)))
        self.write(self.path,self.receipt)
    def write(self,path,value):path.write_text(json.dumps(value))
    def sha(self,path):return hashlib.sha256(path.read_bytes()).hexdigest()
    def read(self,code=0):return read_receipt(self.ready,self.report,self.artifact,self.catalog,code)
    def test_complete_receipt_binds_actual_server_and_does_not_publish_credentials(self):
        result=self.read();self.assertEqual(result['server_pid'],123);self.assertEqual(result['receipt_sha256'],self.sha(self.path))
        self.assertNotIn('never-publish-this-token',json.dumps(result))
        with self.assertRaisesRegex(RuntimeError,'outcome differs'):self.read(1)
    def test_identity_artifacts_and_cpu_must_match(self):
        for change in [lambda r:r.update(server_pid=124),lambda r:r.update(server_executable_sha256='b'*64),
                lambda r:r.update(readiness_sha256='c'*64),lambda r:r.update(artifact_sha256='d'*64),
                lambda r:r.update(catalog_sha256='e'*64),lambda r:r.update(report_sha256='f'*64),
                lambda r:r['response']['cpu_after'].update(user_us=0),lambda r:r['response']['cpu_before'].update(system_us=True)]:
            bad=copy.deepcopy(self.receipt);change(bad);self.write(self.path,bad)
            with self.assertRaises(RuntimeError):self.read()
    def test_changed_result_and_catalog_coverage_cannot_pass_by_hash_only(self):
        report=json.loads(self.report.read_text());report['tests'].reverse();self.write(self.report,report)
        self.receipt['report_sha256']=self.receipt['response']['report_sha256']=self.sha(self.report);self.write(self.path,self.receipt)
        with self.assertRaisesRegex(RuntimeError,'names/order'):self.read()
    def test_unknown_or_missing_outcomes_are_only_accepted_with_client_failure(self):
        self.receipt.update(status='unknown-or-error');self.receipt.pop('response');self.write(self.path,self.receipt)
        self.assertEqual(self.read(1)['status'],'unknown-or-error')
        with self.assertRaisesRegex(RuntimeError,'uncertain outcome'):self.read()
        self.path.unlink();self.assertIsNone(self.read(1))
        with self.assertRaisesRegex(RuntimeError,'omitted its receipt'):self.read()

    def test_receipt_describes_executed_bytes_and_requires_prelaunch_digest_when_supplied(self):
        original=self.sha(self.artifact)
        self.artifact.write_bytes(b'later bytes, never executed')
        result=read_receipt(self.ready,self.report,self.artifact,self.catalog,0,expected_artifact_sha256=original)
        self.assertEqual(result['artifact_sha256'],original)
        with self.assertRaisesRegex(RuntimeError,'pre-execution artifact digest differs'):
            read_receipt(self.ready,self.report,self.artifact,self.catalog,0,expected_artifact_sha256=self.sha(self.artifact))
        for value in ['',None,'x'*64,4]:
            self.write(self.catalog,dict(artifact_sha256=value,entries=[]))
            with self.assertRaisesRegex(RuntimeError,'invalid catalog artifact digest'):self.read()

    def capable_report(self,options):
        ready=json.loads(self.ready.read_text());ready['indirect_calls']=True;self.write(self.ready,ready)
        report=json.loads(self.report.read_text());report['jit_options']=options;self.write(self.report,report)
        self.receipt['readiness_sha256']=self.sha(self.ready)
        self.receipt['report_sha256']=self.receipt['response']['report_sha256']=self.sha(self.report)
        self.write(self.path,self.receipt)

    def test_session_composition_options_are_boolean_exact_and_match_the_request(self):
        options=dict(persistent_registers=True,scalar_calls=True,indirect_calls=True)
        self.capable_report(options)
        self.assertIsNotNone(read_receipt(self.ready,self.report,self.artifact,self.catalog,0,expected_jit_options=options))
        with self.assertRaisesRegex(RuntimeError,'requested JIT options differ'):
            read_receipt(self.ready,self.report,self.artifact,self.catalog,0,expected_jit_options=dict(options,indirect_calls=False))
        for bad in [None,{},dict(options,indirect_calls=1),dict(options,indirect_calls='true'),dict(options,extra=False)]:
            self.capable_report(bad)
            with self.assertRaisesRegex(RuntimeError,'invalid JIT options'):self.read()

    def test_session_composition_old_server_cannot_claim_enabled_indirect_calls(self):
        disabled=dict(persistent_registers=True,scalar_calls=True,indirect_calls=False)
        self.assertIsNotNone(read_receipt(self.ready,self.report,self.artifact,self.catalog,0,expected_jit_options=disabled))
        with self.assertRaisesRegex(RuntimeError,'server lacks indirect calls'):
            read_receipt(self.ready,self.report,self.artifact,self.catalog,0,expected_jit_options=dict(disabled,indirect_calls=True))

    def test_session_composition_selection_requires_explicit_server_capability(self):
        args=SimpleNamespace(tool_key='a'*64,engine='jit',jit_resumable_calls=True,isolated_batch='prepared',suite_workers=2,
            jit_shared_templates=False,jit_indirect_calls=True,allocation_trace=False,audit_entries=None,list_tests=False,
            jit_template_session=self.ready.resolve(),suite_report=self.root/'new.json')
        for capability in [None,False,1,'true']:
            ready=json.loads(self.ready.read_text());ready['indirect_calls']=capability;self.write(self.ready,ready)
            with self.assertRaisesRegex(ValueError,'does not support indirect'):validate_selection(args)
        ready['indirect_calls']=True;self.write(self.ready,ready);validate_selection(args)
        args.jit_shared_templates=True
        with self.assertRaisesRegex(ValueError,'prepared two-worker'):validate_selection(args)

if __name__=='__main__':unittest.main()
