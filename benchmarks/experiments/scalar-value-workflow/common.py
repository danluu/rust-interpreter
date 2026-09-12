"""Immutable scalar candidate and completed qualification prerequisites."""
import hashlib
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from interpreter import installed_tools
CONTROL='9637b0acb1d208524c3c8b446af64cfd5e2d0d3be75e1412a8df76750ce36223'
SOURCE_TOOL='aa56492e192ef2e87f69ed417b34c8f717b28c31a0fa67f5d63fbb92f313c9cd'
CANDIDATE='ba4ad407e70d887c7872dd85efaaff05fe3efb8e01808767f649ba135803f5c7'
LAUNCHER=HERE.parent/'scalar-value-cargo-controlled/launcher.py'
def require(ok,message):
    if not ok:raise RuntimeError(message)
def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(path)
def qualifications():
    names=['scalar-value-compiler-build-02','scalar-value-frontend-02','scalar-value-cargo-02','scalar-value-real-01']
    paths=[ROOT/'results'/n/'summary.json' for n in names];reports=[read(p) for p in paths]
    require(all(r['status']=='passed' for r in reports),'scalar prerequisite failed')
    b,f,c,r=reports
    require(all(x['tool_key']==SOURCE_TOOL for x in [b,f,r]) and c['tool_key']==CANDIDATE and c['source_tool_key']==SOURCE_TOOL,'qualification component identity differs')
    require(all(c['binaries'][n]==f['binaries'][n] for n in ['rust-interp-vm','rust-interp-mir-export']),'composed compiler/runtime changed')
    require(c['composition']['wrapper_source_key']==CONTROL,'composition wrapper differs')
    require(hashlib.sha256(json.dumps(c['composition'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==CANDIDATE,'composition key differs')
    require(b['tests']['debug']['passed']==b['tests']['release']['passed']==334 and f['vm_executions']==360 and f['strict_rejections']==3,'compiler/frontend qualification differs')
    require(len(c['commands'])==19 and c['fixture_restored'] and c['cargo_flag_states']==[5,6,6,5,6],'Cargo qualification differs')
    require(len(r['commands'])==4 and len(r['cases'])==2 and all(x['original_assertions_pass'] for x in r['cases']),'original assertions not qualified')
    require(sha(LAUNCHER)==c['frozen'][str(LAUNCHER.relative_to(ROOT))],'qualified launcher changed')
    for p in list(paths):
        receipt_path=p.with_name('execution.json');receipt=read(receipt_path)
        require(receipt['all_processes_terminal'] and all(sha(ROOT/q)==h for q,h in receipt['evidence'].items()),'prerequisite process/evidence changed')
        paths.append(receipt_path)
    source=read(ROOT/b['provenance'])
    require(sha(ROOT/b['provenance'])==b['provenance_sha256'] and all(sha(ROOT/source['source']/p)==h for p,h in source['copied_inputs'].items()),'qualified source changed')
    paths+=[ROOT/b['provenance'],LAUNCHER]
    return paths

def tools_for(phase):
    require(phase in ['aa','e2e'],'unknown scalar phase');result={}
    for mode,key in [('baseline',CONTROL),('candidate',CONTROL if phase=='aa' else CANDIDATE)]:
        directory,actual=installed_tools(key);manifest=read(directory/'ready.json');require(actual==key,'tool key differs')
        require(manifest==read(HERE/'identities.json')[key],'qualified component hashes differ')
        result[mode]=dict(tool_key=key,vm_sha256=manifest['rust-interp-vm'],exporter_sha256=manifest['rust-interp-mir-export'],wrapper_sha256=manifest['rust-interp-rustc-wrapper'])
    require(result['baseline']['wrapper_sha256']==result['candidate']['wrapper_sha256'],'wrapper unexpectedly changed')
    return result
