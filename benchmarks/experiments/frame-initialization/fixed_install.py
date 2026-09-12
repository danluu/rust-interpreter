#!/usr/bin/env python3
"""Compose screened VMs with the same immutable exporter and Cargo wrapper."""
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from interpreter import installed_tools

CONTROL = '9637b0acb1d208524c3c8b446af64cfd5e2d0d3be75e1412a8df76750ce36223'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    work = ROOT / '.work/fixed-frame-clear-01'
    summary_path = ROOT / 'results/fixed-frame-clear-screen-01/summary.json'
    screen = json.loads(summary_path.read_text())
    assert screen['status'] == 'passed' and screen['screen_target_met']
    qualification = screen['qualification']
    for p, h in screen['evidence'].items() | qualification['evidence'].items():
        assert sha(ROOT / p) == h
    retained, _ = installed_tools(CONTROL)
    original = json.loads((retained / 'ready.json').read_text())
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        deadline = time.monotonic() + 45
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(1)
        tools = {}
        with (ROOT / '.work/interpreter-tools.lock').open('a') as publication:
            fcntl.flock(publication, fcntl.LOCK_EX | fcntl.LOCK_NB)
            for mode in ['baseline', 'candidate']:
                vm = work / (mode + '-vm')
                assert sha(vm) == qualification[mode + '_vm_sha256']
                binaries = original | {'rust-interp-vm': sha(vm)}
                composition = dict(kind='qualified-runtime-composition', schema_version=1,
                    exporter_wrapper_source_key=CONTROL, runtime_source_mode=mode,
                    runtime_source_manifest='.work/fixed-frame-clear-01/plan.json',
                    runtime_source_manifest_sha256=sha(work / 'plan.json'), binaries=binaries)
                key = hashlib.sha256(json.dumps(composition, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
                destination = ROOT / '.work/interpreter-tools' / key
                destination.mkdir(exist_ok=False)
                for name in binaries:
                    shutil.copy2(vm if name == 'rust-interp-vm' else retained / name, destination / name)
                    assert sha(destination / name) == binaries[name]
                caps = json.loads((retained / 'capabilities.json').read_text())
                caps.update(tool_key=key, exporter_sha256=binaries['rust-interp-mir-export'])
                (destination / 'capabilities.json').write_text(json.dumps(caps, indent=2) + '\n')
                source = dict(tool_key=key, composition=composition, qualification=str(summary_path.relative_to(ROOT)),
                    qualification_sha256=sha(summary_path), key_algorithm='SHA256 canonical sorted compact composition JSON')
                (destination / 'source.json').write_text(json.dumps(source, indent=2) + '\n')
                (destination / 'ready.json').write_text(json.dumps(binaries, indent=2) + '\n')
                installed_tools(key)
                tools[mode] = dict(tool_key=key, binaries=binaries, source=source)
        output = work / 'installed-tools.json'
        with output.open('x') as out:
            out.write(json.dumps(tools, indent=2) + '\n')
        print(json.dumps({mode: row['tool_key'] for mode, row in tools.items()}))


if __name__ == '__main__':
    main()
