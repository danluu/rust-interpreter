#!/usr/bin/env python3
"""Compare execution of the unchanged pgrust hash test, including its full loop."""
import fcntl
import hashlib
import json
import os
import re
import statistics
import subprocess
import time
from interpreter import ROOT, checked_tools


def main():
    lock=(ROOT/'.work/benchmark.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    proof=json.loads((ROOT/'results/interpreter-project-validation.json').read_text())
    raw=json.loads((ROOT/proof['raw']/'records.json').read_text())
    native=re.search(r'Running unittests .* \(([^\n]+)\)',raw[0]['stderr']).group(1)
    tools,key=checked_tools()
    manifest=ROOT/'.work/sources/pgrust/Cargo.toml'
    identity=hashlib.sha256((str(manifest)+'\0hashfn\0murmurhash32_inverse_roundtrips\0True').encode()).hexdigest()[:24]
    artifacts=list((ROOT/'.work/interpreter-workspaces'/key/identity).rglob('*.rmeta.rbc'))
    assert len(artifacts)==1,'run validate_interpreter_project.py with the current tools first'
    commands={
        'native':[native,'tests::murmurhash32_inverse_roundtrips','--exact'],
        'vm':[str(tools/'rust-interp-vm'),'--instruction-limit','1000000000',str(artifacts[0])],
    }
    work=ROOT/'.work'/('interpreter-project-runtime-'+str(time.time_ns()))
    work.mkdir()
    records=[]
    for rep in range(-1,5):
        for mode in (['native','vm'] if rep%2==0 else ['vm','native']):
            env=os.environ.copy();env['RUST_INTERP_VM_STATS']='1'
            start=time.perf_counter()
            p=subprocess.Popen(commands[mode],cwd=ROOT,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            stdout,stderr=p.communicate()
            records.append(dict(rep=rep,mode=mode,pid=p.pid,seconds=time.perf_counter()-start,returncode=p.returncode,stdout=stdout,stderr=stderr))
            (work/'records.json').write_text(json.dumps(records,indent=2)+'\n')
            assert p.returncode==0,stderr
            assert ('1 passed' in stdout) if mode=='native' else stdout.strip()=='0',stdout
    med={mode:statistics.median(r['seconds'] for r in records if r['mode']==mode and r['rep']>=0) for mode in commands}
    result=dict(test=proof['test'],revision=proof['revision'],iterations=proof['iterations'],raw=str(work.relative_to(ROOT)),
                native_sha256=hashlib.sha256(open(native,'rb').read()).hexdigest(),
                vm_sha256=hashlib.sha256((tools/'rust-interp-vm').read_bytes()).hexdigest(),
                bytecode_sha256=hashlib.sha256(artifacts[0].read_bytes()).hexdigest(),
                warmup_per_mode=1,samples_per_mode=5,median_seconds=med,
                samples=[{k:v for k,v in r.items() if k not in ['stdout','stderr','pid']} for r in records if r['rep']>=0])
    (ROOT/'results/interpreter-project-runtime.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(med,indent=2))


if __name__=='__main__':main()
