from pathlib import Path
import hashlib,json,os,shutil,subprocess,time
root=Path(__file__).resolve().parents[2]
b=Path(__file__).resolve().parent
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,obj): path.write_text(json.dumps(obj,indent=2)+'\n')
inputs=[root/'Cargo.toml',root/'Cargo.lock']
for folder in ['bytecode','mir-export']:
 inputs+=sorted((root/'crates'/folder).rglob('*.rs'))
 inputs.append(root/'crates'/folder/'Cargo.toml')
h=hashlib.sha256()
snapshot=b/'owned-analysis-source';snapshot.mkdir(exist_ok=False)
files={}
for p in inputs:
 name=str(p.relative_to(root));data=p.read_bytes();h.update(name.encode()+b'\0'+data)
 files[name]=hashlib.sha256(data).hexdigest();out=snapshot/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
key=h.hexdigest();directory=root/'.work/interpreter-tools'/key;directory.mkdir(parents=True,exist_ok=False)
manifest={}
built={}
selected={}
baseline=json.loads((b/'current-baseline-tools.json').read_text())
for name in ['rust-interp-vm','rust-interp-mir-export','rust-interp-rustc-wrapper']:
 src=root/'.work/perf-general-20260912/target/release'/name;dst=directory/name
 built[name]={'path':str(src),'sha256':sha(src)}
 if name != 'rust-interp-mir-export': src=Path(baseline['directory'])/name
 selected[name]={'path':str(src),'sha256':sha(src)}
 shutil.copy2(src,dst);manifest[name]=sha(dst)
assert len(manifest)==3
baseline=json.loads((b/'current-baseline-tools.json').read_text())
for name in ['rust-interp-vm','rust-interp-rustc-wrapper']:
 assert manifest[name]==baseline['binaries'][name], (name, 'baseline/candidate drift')
command=[str(directory/'rust-interp-mir-export'),'--rust-interp-capabilities']
started=time.time();child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,stdin=subprocess.DEVNULL)
receipt={'command':command,'cwd':str(root),'child_pid':child.pid,'controller_pid':os.getpid(),'started_at':started}
stdout,stderr=child.communicate();receipt.update(returncode=child.returncode,stdout=stdout,stderr=stderr,finished_at=time.time());write(b/'owned-analysis-capabilities.json',receipt)
assert child.returncode==0
capabilities=json.loads(stdout);assert capabilities['schema_version']==1
capabilities.update(tool_key=key,exporter_sha256=manifest['rust-interp-mir-export'])
write(directory/'capabilities.json',capabilities);write(directory/'ready.json',manifest)
write(snapshot/'source.json',{'compiler_source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'files':files,'tool_key':key,'binaries':manifest})
write(b/'owned-analysis-tools.json',{'tool_key':key,'directory':str(directory),'binaries':manifest,'source_snapshot':str(snapshot),'build_receipt':str(b/'owned-analysis-tools-build.json'),'built_binaries':built,'selected_binaries':selected,'frozen_baseline_runtime':True})
print(json.dumps({'candidate_tool_key':key,'binaries':manifest,'free_gib':shutil.disk_usage(root).free/2**30},indent=2))
