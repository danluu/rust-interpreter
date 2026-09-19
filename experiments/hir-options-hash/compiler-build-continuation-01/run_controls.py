#!/usr/bin/env python3
"""One supervised synthetic allocation-control invocation; no compiler process."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time

import bounded_command_v2 as b

HERE=Path(__file__).resolve().parent
WORK=b.OWNER/'.work/hir-options-hash-build-continuation-controls-01'


def read(path):
    return json.loads(path.read_bytes())


def guard(frozen):
    for name,row in frozen['files'].items():
        path=Path(name)
        assert path.resolve(strict=True)==path and path.is_file() and not path.is_symlink()
        assert b.owned.sha(path)==row['sha256']


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--inputs-sha256',required=True)
    args=parser.parse_args()
    assert sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd()==b.OWNER
    assert b.owned.sha(HERE/'control-inputs.json')==args.inputs_sha256
    frozen=read(HERE/'control-inputs.json');guard(frozen)
    assert str(Path(sys.executable).resolve(strict=True))==frozen['python']
    assert dict(os.environ)==frozen['environment']
    WORK.mkdir(exist_ok=False)
    receipt=dict(status='waiting',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),commands=[])
    b.owned.write(WORK/'receipt.json',receipt)
    try:
        with b.owned.workload_lock(b.owned.CANONICAL_LOCK,600):
            receipt.update(status='running',admitted_at=time.time(),free_bytes_before=b.owned.disk(b.OWNER,16))
            b.owned.write(WORK/'receipt.json',receipt);guard(frozen)
            (WORK/'tmp').mkdir()
            environment=dict(frozen['environment'],TMPDIR=str(WORK/'tmp'))
            try:
                b.owned.run(frozen['command'],cwd=HERE,env=environment,out=WORK/'command',capacity_root=b.OWNER)
            finally:
                child=WORK/'command/receipt.json'
                if child.is_file():
                    receipt['commands']=[dict(path=str(child),sha256=b.owned.sha(child),pid=read(child).get('pid'))]
            stderr=(WORK/'command/stderr').read_text()
            assert re.search(r'^Ran 13 tests in [0-9.]+s\n\nOK\n$',stderr,re.M)
            assert len(re.findall(r'^test_.* \.\.\. ok$',stderr,re.M))==13
            assert not (WORK/'command/stdout').read_bytes()
            guard(frozen)
            receipt.update(status='passed',controls_passed=13,free_bytes_after=b.owned.disk(b.OWNER,9))
    except BaseException as error:
        receipt.update(status='failed',error=repr(error));raise
    finally:
        receipt['finished_at']=time.time();b.owned.write(WORK/'receipt.json',receipt)


if __name__=='__main__':
    main()
