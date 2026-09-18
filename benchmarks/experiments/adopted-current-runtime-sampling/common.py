"""Shared identities for two fresh adopted-runtime diagnostic windows."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import require_space, write_json as write

RUN = 'adopted-current-runtime-sampling-01'
KEY = 'df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
VM = '6ac4dd9e964e0ebb0a050f8412c8ec8877bd197e8ad7876832db378ed03ca7cf'


def read(path):
    assert path.stat().st_size <= 256 * 1024**2
    return json.loads(path.read_text())


def verify(plan):
    assert all(sha(ROOT / path) == digest for path, digest in plan['frozen'].items())


def terminal(supervisor, expected_command=None):
    assert Path(supervisor).name == supervisor
    outer = ROOT / '.work/experiments' / supervisor
    value = read(outer / 'status.json')
    assert value['status'] == 'finished' and value['returncode'] == 0
    assert value['owner'] == value['cwd'] == str(ROOT)
    assert sha(outer / 'plan.json') == value['plan_sha256']
    assert sha(outer / 'command.log') == value['log_sha256']
    if expected_command is not None:
        assert Path(value['command'][0]).resolve() == Path(expected_command[0]).resolve()
        assert value['command'][1:] == expected_command[1:]
    return outer, value
