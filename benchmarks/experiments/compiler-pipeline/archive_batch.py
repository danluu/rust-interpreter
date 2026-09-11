#!/usr/bin/env python3
"""Run a fixed, hash-bound list of completed-cache preparations or applications.

Inventories are reviewed between these two separate invocations. Every child
uses the qualified single-target helper, including its locks and provenance.
Any failure stops the batch; a partly applied batch cannot be blindly retried.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from reclaim_workflow_objects import identifier
from verify_repeated_workflow import require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--action', choices=['prepare', 'apply'], required=True)
    args = parser.parse_args()
    payload = args.plan.read_bytes()
    require(hashlib.sha256(payload).hexdigest() == args.plan_sha256, 'batch plan changed')
    plan = json.loads(payload)
    require(plan['owner'] == str(ROOT) and plan['schema_version'] == 1, 'batch owner/schema differs')
    entries = plan['entries']
    require(isinstance(entries, list) and 1 <= len(entries) <= 32, 'invalid batch size')
    fields = {'archive', 'workflow', 'mode'}
    require(all(isinstance(e, dict) and set(e) in [fields, fields | {'corpus'}] for e in entries),
            'invalid batch entry')
    require(len({e['archive'] for e in entries}) == len(entries) and
            len({(e['workflow'], e['mode']) for e in entries}) == len(entries), 'duplicate batch target')
    commands = []
    for entry in entries:
        identifier(entry['archive'])
        identifier(entry['workflow'])
        corpus = identifier(entry['corpus']) if 'corpus' in entry else None
        require(entry['mode'] in ['native', 'check', 'baseline', 'candidate'], 'unknown cache mode')
        work = ROOT / '.work/workflow-cache-archives' / entry['archive']
        command = [sys.executable, str(ROOT / 'scripts/archive_workflow_cache.py')]
        if args.action == 'prepare':
            require(not work.exists(), 'batch preparation identity already exists')
            command += ['--prepare', entry['archive'], '--workflow', entry['workflow'], '--mode', entry['mode']]
            if corpus is not None:
                command += ['--corpus', corpus]
        else:
            prepared = json.loads((work / 'plan.json').read_text())
            status = json.loads((work / 'status.json').read_text())
            require(status['status'] == 'prepared' and prepared['workflow'] == entry['workflow'] and
                    prepared.get('mode', 'native') == entry['mode'] and prepared['corpus'] == corpus,
                    'batch does not match untouched inventories; audit any partial application')
            command += ['--apply', entry['archive']]
        commands.append(command)
    for entry, command in zip(entries, commands):
        child = subprocess.Popen(command, cwd=ROOT)
        try:
            print(json.dumps(dict(archive=entry['archive'], action=args.action,
                                  pid=child.pid, command=command)), flush=True)
        finally:
            code = child.wait()
        require(code == 0, 'batch child failed: ' + entry['archive'])
    print(json.dumps(dict(status='completed', action=args.action, targets=len(entries),
                          plan_sha256=args.plan_sha256)), flush=True)


if __name__ == '__main__':
    main()
