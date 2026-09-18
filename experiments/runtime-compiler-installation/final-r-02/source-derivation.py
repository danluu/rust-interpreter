"""Source-only R02 derivation from the actual passed current readmission."""
import ast,hashlib,json,sys
from pathlib import Path
OWNER=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
HERE=OWNER/'experiments/runtime-compiler-installation/final-r-02'
OLD=OWNER/'experiments/runtime-compiler-installation/final-r-01'
CURRENT=Path('/Users/danluu/dev/rust-interp-runtime-readmission-20260918')
READMISSION=CURRENT/'.work/runtime-readmission-01'
WORK=OWNER/'.work/runtime-installation-r-02'
sys.path.insert(0,str(OWNER/'scripts'))
import runtime_compiler as runtime

def read(p):return json.loads(Path(p).read_bytes())
def sha(p):
 p=Path(p);assert p.resolve(strict=True)==p and p.is_file() and not p.is_symlink()
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def ref(p):return dict(path=str(p),sha256=sha(p))
def write(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
plan=read(OLD/'plan.json');terminal=read(READMISSION/'receipt.json')
assert sha(READMISSION/'receipt.json')=='5812037c34c633f5ec7bfeec1b6036e63e2cd6c988b3b51b0ba90668e3643129'
assert terminal['status']=='passed' and terminal['full_current_guard_passed'] and len(terminal['children'])==28
refs=plan['evidence']
refs.update(candidate=ref(READMISSION/'candidate-specification.json'),components=ref(READMISSION/'components-and-stamps.json'),
 metadata=ref(READMISSION/'metadata.json'),source_preflight=ref(READMISSION/'receipt.json'),
 metadata_outer=ref(CURRENT/'.work/experiments/runtime-readmission-supervisor-01/status.json'),
 source_preflight_outer=ref(CURRENT/'.work/experiments/runtime-readmission-supervisor-01/status.json'),
 readmission_plan=ref(CURRENT/'experiments/runtime-compiler-installation/readmission-01/plan.json'),
 readmission_inputs=ref(CURRENT/'experiments/runtime-compiler-installation/readmission-01/inputs.json'),
 readmission_launch=ref(CURRENT/'experiments/runtime-compiler-installation/readmission-01/launch.json'),
 readmission_verification=ref(CURRENT/'.work/runtime-readmission-independent-verification-01.json'))
candidate=read(refs['candidate']['path']);assert sha(refs['candidate']['path'])=='1c0ec4abd1432baa8ba5fe24498af99dd8ae1975a0b3ceece4124409d235de33'
spec=read(OLD/'specification.json');spec['provenance']['source_preflight_sha256']=refs['source_preflight']['sha256']
assert spec['components']==candidate['components'];write(HERE/'specification.json',spec)
identity=runtime.identity_for(spec);key=runtime.digest(identity);root=OWNER/'.work/runtime-compilers'/key/'sysroot'
plan.update(work=str(WORK),runtime_key=key,sysroot=str(root),evidence=refs,
 compiler_environment=runtime.RuntimeCompiler(key,root,identity).environment(plan['environment']))
old_work=OWNER/'.work/runtime-installation-r-01';old_root=Path(read(OLD/'plan.json')['sysroot'])
for row in plan['children']:
 row['argv']=[arg.replace(str(old_root),str(root)).replace(str(old_work),str(WORK)) for arg in row['argv']]
 row['cwd']=row['cwd'].replace(str(old_work),str(WORK));row['out']=row['out'].replace(str(old_work),str(WORK))
write(HERE/'plan.json',plan)
print(json.dumps(dict(runtime_key=key,sysroot=str(root),specification_sha256=sha(HERE/'specification.json'),plan_sha256=sha(HERE/'plan.json')),indent=2))
