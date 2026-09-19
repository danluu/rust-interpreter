#!/opt/homebrew/bin/python3 -B
"""Existing real-fixture argv adapter pattern: record then exec unchanged rustc."""
import json
import os
from pathlib import Path
import sys
import time

directory = Path(os.environ['HOSTQUAL_TRACE'])
assert directory.is_absolute() and directory.is_dir() and not directory.is_symlink()
assert len(list(directory.iterdir())) < 64
assert len(sys.argv) > 1 and sys.argv[1] == os.environ['RUSTC']
record = dict(pid=os.getpid(), parent_pid=os.getppid(), entered_at=time.time(),
    argv=sys.argv[1:], cwd=os.getcwd(), environment={k:v for k,v in os.environ.items()
    if k.startswith('CARGO_PROFILE_') or k in ['OPT_LEVEL', 'DEBUG', 'CARGO_PKG_NAME',
        'CARGO_MANIFEST_DIR', 'CARGO_MAKEFLAGS', 'MAKEFLAGS', 'MFLAGS']},
    policy='record-then-exec-unchanged-rustc', individual_os_wait_observed=False)
path = directory / (str(os.getpid()) + '-' + str(time.time_ns()) + '.json')
payload = (json.dumps(record, sort_keys=True, indent=2) + '\n').encode()
assert len(payload) < 2**20
with path.open('xb') as stream:
    stream.write(payload)
# exec keeps Cargo's inherited jobserver descriptors and compiler stdin intact.
os.execv(sys.argv[1], sys.argv[1:])
