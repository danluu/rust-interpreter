import copy,hashlib,json
from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from template_session_receipt import read_receipt

class TemplateSessionReceipts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.artifact=self.root/'program.rbc';self.artifact.write_bytes(b'current artifact')
        self.catalog=self.root/'catalog.json';self.write(self.catalog,dict(entries=[dict(name='one'),dict(name='two')]))
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

if __name__=='__main__':unittest.main()
