#!/opt/homebrew/bin/python3 -B
"""Record Cargo's original argv, then exec the real std-only wrapper."""
import json
import os
from pathlib import Path
import sys
import time

directory = Path(os.environ['HOSTQUAL_TRACE'])
wrapper = Path(os.environ['HOSTQUAL_WRAPPER'])
assert directory.is_absolute() and directory.is_dir() and not directory.is_symlink()
assert wrapper.is_absolute() and wrapper.is_file() and not wrapper.is_symlink()
assert len(list(directory.iterdir())) < 64
assert len(sys.argv) > 1 and sys.argv[1] == os.environ['RUSTC']
record = dict(pid=os.getpid(), parent_pid=os.getppid(), entered_at=time.time(),
    argv=sys.argv[1:], cwd=os.getcwd(), environment={k:v for k,v in os.environ.items()
    if k.startswith('CARGO_PROFILE_') or k in ['OPT_LEVEL', 'DEBUG', 'CARGO_PKG_NAME',
        'CARGO_MANIFEST_DIR', 'CARGO_MAKEFLAGS', 'MAKEFLAGS', 'MFLAGS',
        'RUST_INTERP_HOST_CODEGEN_OPT']},
    policy='record-then-exec-bound-wrapper', individual_os_wait_observed=False)
payload = (json.dumps(record, sort_keys=True, indent=2) + '\n').encode()
assert len(payload) < 2**20
with (directory / (str(os.getpid()) + '.json')).open('xb') as stream:
    stream.write(payload)
os.execv(str(wrapper), [str(wrapper), *sys.argv[1:]])
