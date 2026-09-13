#!/usr/bin/env python3
from pathlib import Path
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write
from ledger import reconcile

NAMES = ['scalar-copy-public-cache-retirement-04',
         'scalar-copy-native-dependencies-retirement-01',
         'scalar-copy-fre-cache-retirement-01', 'scalar-copy-fre-cache-retirement-02',
         'checked-address-screen-retirement-01', 'checked-address-nushell-retirement-01',
         'guarded-ranges-nushell-retirement-01']

with (ROOT / '.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock, 45)
    require_space(ROOT, 8)
    raw = ROOT / '.work/cache-retirement-ledger-01'
    raw.mkdir(exist_ok=False)
    summaries = ['results/' + name + '/summary.json' for name in NAMES]
    inputs = [ROOT / name for name in summaries]
    inputs += [ROOT / json.loads(path.read_text())['raw'] / 'plan.json' for path in inputs.copy()]
    inputs += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py', '.md']]
    inputs += [ROOT / 'scripts' / name for name in ['compare_saved_runtime.py', 'workflow_io.py']]
    frozen = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    write(raw / 'plan.json', dict(owner=str(ROOT), frozen=frozen, summaries=summaries, guest_commands=0))
    child, out, err = capture([sys.executable, '-m', 'unittest', 'discover',
        '-s', 'benchmarks/experiments/cache-retirement-ledger', '-p', 'test_*.py'],
        cwd=ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), receipt_path=raw / 'active.json',
        receipt=dict(stage='ledger tests'))
    (raw / 'tests.stdout').write_text(out)
    (raw / 'tests.stderr').write_text(err)
    write(raw / 'tests.json', dict(pid=child.pid, returncode=child.returncode,
        stdout_sha256=sha(raw / 'tests.stdout'), stderr_sha256=sha(raw / 'tests.stderr')))
    assert child.returncode == 0 and 'Ran 7 tests in' in err and '\nOK\n' in err, err
    ledger = reconcile(ROOT, summaries)
    write(raw / 'ledger.json', ledger)
    assert all(sha(ROOT / name) == digest for name, digest in frozen.items())
    destination = ROOT / 'results/cache-retirement-ledger-01'
    destination.mkdir(exist_ok=False)
    write(destination / 'ledger.json', ledger)
    write(destination / 'summary.json', dict(status='passed', tests=7,
        receipts=len(ledger['receipts']), unique_roots=ledger['unique_roots'], empty_rechecks=ledger['empty_rechecks'],
        cache_files_inspected=0, files_deleted=0, guest_commands=0,
        raw=str(raw.relative_to(ROOT)), plan_sha256=sha(raw / 'plan.json'),
        tests_sha256=sha(raw / 'tests.json'), ledger_sha256=sha(raw / 'ledger.json')))
    print(json.dumps(dict(status='passed', unique_roots=ledger['unique_roots'], receipts=len(ledger['receipts']))), flush=True)
