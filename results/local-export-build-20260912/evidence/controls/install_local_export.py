from pathlib import Path
import hashlib,json,os,shutil,subprocess,time
root=Path(__file__).resolve().parents[2]
b=Path(__file__).resolve().parent
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,obj): path.write_text(json.dumps(obj,indent=2)+'\n')
freeze=json.loads((b/'local-export-input-freeze.json').read_text())
assert freeze['status']=='passed' and freeze['returncode']==0 and freeze['finished_at']<=time.time()
for name,digest in freeze['outputs_sha256'].items():assert sha(b/name)==digest,name
controls=json.loads((b/'local-export-prebuild-controls.json').read_text())
for name,digest in controls['qualification_input_hashes'].items():assert sha(b/name)==digest,name
commands=json.loads((b/'local-export-qualification-commands.json').read_text())
assert sha(b/'local-export-qualification-commands.json')==freeze['commands_sha256']
build_receipt=json.loads((b/'local-export-tools-build.json').read_text())
assert build_receipt['returncode']==0 and build_receipt['command']==commands['qualification']['local-export-tools-build']['command']
assert build_receipt['cwd']==str(root) and freeze['finished_at']<=build_receipt['started_at']<=build_receipt['finished_at']<=time.time()
inputs=[root/'Cargo.toml',root/'Cargo.lock']
for folder in ['bytecode','mir-export']:
 inputs+=sorted((root/'crates'/folder).rglob('*.rs'))
 inputs.append(root/'crates'/folder/'Cargo.toml')
h=hashlib.sha256()
snapshot=b/'local-export-source';snapshot.mkdir(exist_ok=False)
files={}
for p in inputs:
 name=str(p.relative_to(root));data=p.read_bytes();h.update(name.encode()+b'\0'+data)
 files[name]=hashlib.sha256(data).hexdigest();out=snapshot/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
key=h.hexdigest();assert key==json.loads((b/'local-export-composition-manifest.json').read_text())['compiler_source_key'], key;directory=root/'.work/interpreter-tools'/key;directory.mkdir(parents=True,exist_ok=False)
manifest={}
built={}
selected={}
baseline=json.loads((b/'owned-analysis-tools.json').read_text())
assert baseline['tool_key']=='eb91912d5eb6d06fde8e873404b7235a62ad4527a4dfef9e84de093a917e974d'
for name in ['rust-interp-vm','rust-interp-mir-export','rust-interp-rustc-wrapper']:
 src=root/'.work/perf-general-20260912/target/release'/name;dst=directory/name
 built[name]={'path':str(src),'sha256':sha(src)}
 if name != 'rust-interp-mir-export': src=Path(baseline['directory'])/name
 selected[name]={'path':str(src),'sha256':sha(src)}
 shutil.copy2(src,dst);manifest[name]=sha(dst)
assert len(manifest)==3
baseline=json.loads((b/'owned-analysis-tools.json').read_text())
for name in ['rust-interp-vm','rust-interp-rustc-wrapper']:
 assert manifest[name]==baseline['binaries'][name], (name, 'baseline/candidate drift')
command=[str(directory/'rust-interp-mir-export'),'--rust-interp-capabilities']
started=time.time();child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,stdin=subprocess.DEVNULL)
receipt={'command':command,'cwd':str(root),'child_pid':child.pid,'controller_pid':os.getpid(),'started_at':started}
stdout,stderr=child.communicate();receipt.update(returncode=child.returncode,stdout=stdout,stderr=stderr,finished_at=time.time());write(b/'local-export-capabilities.json',receipt)
assert child.returncode==0
capabilities=json.loads(stdout);assert capabilities['schema_version']==1
capabilities.update(tool_key=key,exporter_sha256=manifest['rust-interp-mir-export'])
write(directory/'capabilities.json',capabilities);write(directory/'ready.json',manifest)
write(snapshot/'source.json',{'compiler_source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'files':files,'tool_key':key,'binaries':manifest})
write(b/'local-export-tools.json',{'tool_key':key,'directory':str(directory),'binaries':manifest,'source_snapshot':str(snapshot),'build_receipt':str(b/'local-export-tools-build.json'),'built_binaries':built,'selected_binaries':selected,'frozen_baseline_runtime':True})
print(json.dumps({'candidate_tool_key':key,'binaries':manifest,'free_gib':shutil.disk_usage(root).free/2**30},indent=2))
