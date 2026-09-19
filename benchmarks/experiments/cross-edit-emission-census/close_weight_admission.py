"""Preserve the association closer lock timeout without rerunning the passed analysis."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import require_space, write_json

with (ROOT / '.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock, 45)
    require_space(ROOT, 8)
    for name in ['cross-edit-emission-weight-close-01']:
        outer = ROOT / '.work/experiments' / name
        terminal = json.loads((outer / 'status.json').read_text())
        assert terminal['status'] == 'finished' and terminal['returncode'] == 1
        assert terminal['owner'] == terminal['cwd'] == str(ROOT)
        assert sha(outer / 'plan.json') == terminal['plan_sha256']
        assert sha(outer / 'command.log') == terminal['log_sha256']
        assert (outer / 'command.log').read_text().endswith(
            'TimeoutError: timed out after 45s waiting for benchmark lock ' +
            str(ROOT / '.work/benchmark.lock') + '\n')
        if name.startswith('closed-composition'):
            assert not (ROOT / '.work' / name).exists()
        else:
            assert not (ROOT / 'results/cross-edit-emission-weight-01/closure.json').exists()
        result = ROOT / 'results' / name
        result.mkdir(exist_ok=False)
        for filename in ['plan.json', 'status.json', 'command.log']:
            (result / filename).write_bytes((outer / filename).read_bytes())
        write_json(result / 'closure.json', dict(
            status='closed', outcome='admission-timeout', work_started=False,
            raw=str(outer.relative_to(ROOT)),
            terminal_sha256=sha(result / 'status.json'),
            plan_sha256=sha(result / 'plan.json'),
            log_sha256=sha(result / 'command.log')))
        print(name, 'closed: lock admission only; no work started', flush=True)
