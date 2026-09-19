"""Shared identities for two fresh candidate-runtime diagnostic windows."""
import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import require_space, write_json as write

RUN = 'composed-fre-runtime-sampling-01'
KEY = '3ebea1cdc1a521169df8bba1ca139df97759aaf200798c2bcb91bef4cba3c5ad'
VM = '78378e47c23ea937598285e2e0c4a73a2bd10787e4afa1cf21d9c0189152182a'


def run_name(value):
    if not re.fullmatch(r'composed-fre-runtime-sampling-[0-9]{2}', value):
        raise ValueError('invalid candidate-runtime diagnostic run name')
    return value


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
