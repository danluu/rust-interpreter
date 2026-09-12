from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys,time
root=Path(__file__).resolve().parents[2];work=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
build=json.loads((work/'local-analysis-tools.json').read_text())
for name,digest in build['binaries'].items():assert sha(Path(build['directory'])/name)==digest
source=root/'scripts/validate_interpreter.py'
sys.path.insert(0,str(root/'scripts'))
spec=importlib.util.spec_from_file_location('local_analysis_validation',source)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.BUILD=Path(build['directory'])
receipt={'tool_key':build['tool_key'],'source_sha256':sha(source),'fixture_sha256':sha(root/'tests/local_layout_fixture.rs'),'controller_pid':os.getpid(),'started_at':time.time(),'fixture_native_seed_count':111,'fixture_engines':['interpreter','jit']}
path=work/'local-analysis-fixture-validation-02.json'
with path.open('x') as f:json.dump(receipt,f,indent=2)
try:
 module.main()
 receipt.update(status='passed',finished_at=time.time())
except BaseException as error:
 receipt.update(status='failed',error=repr(error),finished_at=time.time());raise
finally:
 path.write_text(json.dumps(receipt,indent=2)+'\n')
