"""Shared identities for two fresh candidate-runtime diagnostic windows."""
import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import require_space, write_json as write

RUN = 'session-fre-runtime-sampling-01'
KEY = '60bc004658a1db09e1c905eed50e25062f1ff8ae27811331aed9ad51b206a5a5'
VM = '784aef73f3bac42d3eec002008318932ececc4ef95a677070fcd08c6ebe20f01'


def run_name(value):
    if not re.fullmatch(r'session-fre-runtime-sampling-[0-9]{2}', value):
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
