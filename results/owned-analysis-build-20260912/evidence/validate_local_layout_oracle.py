from pathlib import Path
import hashlib,json,os,subprocess,time
root=Path(__file__).resolve().parents[2];work=Path(__file__).resolve().parent
source=root/'tests/local_layout_fixture.rs';binary=work/'local-layout-native-tests'
assert not binary.exists()
commands=[['rustc','+nightly-2026-09-08','--edition=2024','--test',str(source),'-o',str(binary)],[str(binary),'--test-threads=1']]
receipt={'fixture_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'oracle_inputs':261,'controller_pid':os.getpid(),'calls':[]}
p=work/'local-layout-oracle-validation.json'
with p.open('x') as f:json.dump(receipt,f,indent=2)
for command in commands:
 child=subprocess.Popen(command,cwd=root,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 row={'command':command,'child_pid':child.pid,'started_at':time.time()};receipt['calls'].append(row)
 p.write_text(json.dumps(receipt,indent=2)+'\n')
 stdout,stderr=child.communicate();row.update(returncode=child.returncode,stdout=stdout,stderr=stderr,finished_at=time.time());p.write_text(json.dumps(receipt,indent=2)+'\n')
 print(stdout,stderr)
 assert child.returncode==0
receipt['status']='passed';receipt['binary_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest();p.write_text(json.dumps(receipt,indent=2)+'\n')
