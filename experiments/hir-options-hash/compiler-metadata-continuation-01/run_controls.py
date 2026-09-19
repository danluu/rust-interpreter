#!/usr/bin/env python3
"""One saved-output parser control child; no toolchain or compiler probes."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time

HERE = Path(__file__).resolve().parent
OWNER = HERE.parents[2]
sys.path.insert(0,str(OWNER/'experiments/stable-cgu'))
import owned_stage as owned
WORK = OWNER/'.work/hir-options-hash-metadata-parser-controls-01'

def read(path):return json.loads(path.read_bytes())
def guard(frozen):
    for name,row in frozen['files'].items():
        p=Path(name)
        assert p.resolve(strict=True)==p and p.is_file() and owned.sha(p)==row['sha256']

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--inputs-sha256',required=True)
    args=parser.parse_args()
    assert sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd()==OWNER
    assert owned.sha(HERE/'control-inputs.json')==args.inputs_sha256
    frozen=read(HERE/'control-inputs.json');guard(frozen)
    WORK.mkdir(exist_ok=False)
    receipt=dict(status='waiting',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),commands=[])
    owned.write(WORK/'receipt.json',receipt)
    try:
        with owned.workload_lock(owned.CANONICAL_LOCK,600):
            receipt.update(status='running',admitted_at=time.time(),free_bytes_before=owned.disk(OWNER,16))
            owned.write(WORK/'receipt.json',receipt);guard(frozen)
            (WORK/'tmp').mkdir()
            environment=dict(frozen['environment'],TMPDIR=str(WORK/'tmp'))
            try:
                owned.run(frozen['command'],cwd=HERE,env=environment,out=WORK/'command',capacity_root=OWNER)
            finally:
                child=WORK/'command/receipt.json'
                if child.is_file():receipt['commands']=[dict(path=str(child),sha256=owned.sha(child),pid=read(child).get('pid'))]
            stderr=(WORK/'command/stderr').read_text()
            names=re.findall(r'^(test_[A-Za-z0-9_]+) .* \.\.\. ok$',stderr,re.M)
            assert sorted(names)==frozen['expected_names']
            assert re.search(r'^Ran '+str(len(names))+r' tests in [0-9.]+s\n\nOK\n$',stderr,re.M)
            assert not (WORK/'command/stdout').read_bytes()
            guard(frozen)
            receipt.update(status='passed',controls_passed=len(names),free_bytes_after=owned.disk(OWNER,9))
    except BaseException as error:
        receipt.update(status='failed',error=repr(error));raise
    finally:
        receipt['finished_at']=time.time();owned.write(WORK/'receipt.json',receipt)

if __name__=='__main__':main()
