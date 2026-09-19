#!/usr/bin/env python3
"""Run exactly four filesystem controls under canonical supervision."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time

import acquire as a


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs-sha256', required=True)
    args = parser.parse_args()
    assert sys.dont_write_bytecode and not sys.flags.optimize
    assert a.owned.sha(a.HERE/'control-inputs.json') == args.inputs_sha256
    frozen = a.read(a.HERE/'control-inputs.json')
    work = a.OWNER/'.work/hir-options-hash-acquisition-controls-01'
    work.mkdir(exist_ok=False)
    receipt = dict(status='waiting', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(), commands=[])
    a.owned.write(work/'receipt.json', receipt)
    try:
        a.guard_inputs(frozen)
        with a.owned.workload_lock(a.owned.CANONICAL_LOCK, 600):
            receipt.update(status='running', admitted_at=time.time(), free_bytes_before=a.owned.disk(a.OWNER,16))
            a.owned.write(work/'receipt.json', receipt)
            a.guard_inputs(frozen)
            (work/'tmp').mkdir()
            env = dict(frozen['environment'], TMPDIR=str(work/'tmp'))
            try:
                a.owned.run(frozen['command'], cwd=a.HERE, env=env, out=work/'command', capacity_root=a.OWNER)
            finally:
                path = work/'command/receipt.json'
                if path.is_file():
                    receipt['commands'] = [dict(path=str(path), sha256=a.owned.sha(path), pid=a.read(path).get('pid'))]
            stderr = (work/'command/stderr').read_text()
            assert re.search(r'^Ran 4 tests in [0-9.]+s\n\nOK\n$', stderr, re.M)
            assert len(re.findall(r'^test_.* \.\.\. ok$', stderr, re.M)) == 4
            assert not (work/'command/stdout').read_bytes()
            a.guard_inputs(frozen)
            receipt.update(status='passed', controls_passed=4, free_bytes_after=a.owned.disk(a.OWNER,8))
    except BaseException as error:
        receipt.update(status='failed', error=repr(error))
        raise
    finally:
        receipt['finished_at'] = time.time()
        a.owned.write(work/'receipt.json', receipt)


if __name__ == '__main__':
    main()
