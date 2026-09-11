#!/usr/bin/env python3
"""Run an unchanged existing pgrust test natively and in the custom engine."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from interpreter import ROOT, TOOLCHAIN


def main():
    lock=(ROOT/'.work/benchmark.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    source=ROOT/'.work/sources/pgrust'
    revision=json.loads((ROOT/'benchmarks/corpus.json').read_text())['projects']['pgrust']['revision']
    assert (source/'.rust-interp-owned.json').is_file()
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==revision
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source,text=True).strip()
    work=ROOT/'.work'/('interpreter-project-validation-'+str(time.time_ns()))
    work.mkdir()
    records=[]
    manifest=str(source/'Cargo.toml')
    commands=[
        ['cargo','+'+TOOLCHAIN,'test','--manifest-path',manifest,'--package','hashfn','--lib','--locked','--offline','--jobs','4','--target-dir',str(work/'native'),'tests::murmurhash32_inverse_roundtrips','--','--exact'],
        [sys.executable,str(ROOT/'scripts/interpreter.py'),'--manifest-path',manifest,'--package','hashfn','--entry','murmurhash32_inverse_roundtrips','--test-body','--instruction-limit','1000000000'],
    ]
    for mode,command in zip(['native','vm'],commands):
        start=time.perf_counter()
        p=subprocess.run(command,cwd=source,text=True,capture_output=True)
        records.append(dict(mode=mode,command=command,returncode=p.returncode,seconds=time.perf_counter()-start,stdout=p.stdout,stderr=p.stderr))
        (work/'records.json').write_text(json.dumps(records,indent=2)+'\n')
        assert p.returncode==0,p.stderr
        if mode=='native':assert '1 passed' in p.stdout,p.stdout
        else:assert p.stdout.strip()=='0',p.stdout
    (ROOT/'results/interpreter-project-validation.json').write_text(json.dumps(dict(project='pgrust',revision=revision,test='hashfn::tests::murmurhash32_inverse_roundtrips',iterations=100000,modes=['native','vm'],raw=str(work.relative_to(ROOT)),source_unchanged=True),indent=2)+'\n')
    print('existing pgrust test passed in both engines; source unchanged')


if __name__=='__main__':main()
