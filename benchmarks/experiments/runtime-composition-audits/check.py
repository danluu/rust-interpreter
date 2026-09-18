"""Record terminal-decision controls without executing a guest benchmark."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write

NAME = 'runtime-composition-audit-controls-01'


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        directory = Path(__file__).parent
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        paths = [directory / n for n in ['check.py', 'close_campaign.py',
                                        'parser_decision.py', 'test_parser_decision.py']]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        for path, digest in frozen.items():
            content = subprocess.check_output(['git', 'show', revision + ':' + path], cwd=ROOT)
            assert hashlib.sha256(content).hexdigest() == digest
        raw = ROOT / '.work' / NAME
        raw.mkdir(exist_ok=False)
        command = [sys.executable, '-m', 'unittest', 'test_parser_decision', '-v']
        write(raw / 'plan.json', dict(owner=str(ROOT), source_revision=revision,
                                      frozen=frozen, command=command, guest_commands=0))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        child, out, err = capture(command, cwd=directory, env=env,
            receipt_path=raw / 'active.json', receipt=dict(stage='terminal parser decision controls'))
        for stream, payload in [('stdout', out), ('stderr', err)]:
            (raw / stream).write_text(payload)
        write(raw / 'record.json', dict(command=command, pid=child.pid, returncode=child.returncode,
            stdout_sha256=sha(raw / 'stdout'), stderr_sha256=sha(raw / 'stderr')))
        assert child.returncode == 0 and 'Ran 3 tests' in err and err.rstrip().endswith('OK'), err
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        result = ROOT / 'results' / NAME
        result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', commands=1, tests=3, guest_commands=0,
            source_revision=revision, all_frozen_inputs_verified=True, raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw / 'plan.json'), record_sha256=sha(raw / 'record.json'),
            performance_measurement=False))
        print('PASS: 3 terminal parser-decision controls; no guest executions', flush=True)


if __name__ == '__main__':
    main()
