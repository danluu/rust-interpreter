"""Verify terminal offline reconstruction evidence and all source/artifact hashes."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import write_json as write


def read(p):
    return json.loads(p.read_text())


def main():
    run = sys.argv[1]
    assert re.fullmatch(r'scalar-memory-parts-\d{2}', run)
    raw, out = ROOT / '.work' / run, ROOT / 'results' / run
    outer = ROOT / '.work/experiments' / run
    terminal = read(outer / 'status.json')
    assert terminal['owner'] == str(ROOT) and terminal['status'] == 'finished'
    assert sha(outer / 'command.log') == terminal['log_sha256']
    plan = read(raw / 'plan.json')
    assert plan['owner'] == str(ROOT)
    bindings = {}
    for p, h in plan['frozen'].items():
        if p.startswith(('.work/', 'results/')):
            assert sha(ROOT / p) == h
            bindings[p] = dict(kind='retained', sha256=h)
        else:
            payload = subprocess.check_output(['git', 'show', plan['source_revision'] + ':' + p], cwd=ROOT)
            assert hashlib.sha256(payload).hexdigest() == h
            bindings[p] = dict(kind='git', revision=plan['source_revision'], sha256=h)
    records = read(raw / 'records.json')
    artifacts = {}
    for r in records:
        for stream in ['stdout', 'stderr']:
            p = raw / (r['label'] + '.' + stream)
            assert sha(p) == r[stream + '_sha256']
            artifacts[str(p.relative_to(ROOT))] = sha(p)
    out.mkdir(exist_ok=True)
    assert not (out / 'closure.json').exists()
    if terminal['returncode'] == 0:
        summary = read(out / 'summary.json')
        assert summary['status'] == 'passed' and summary['commands'] == len(records) == 5
        assert all(r['returncode'] == 0 for r in records)
        assert summary['plan_sha256'] == sha(raw / 'plan.json')
        assert summary['records_sha256'] == sha(raw / 'records.json')
        assert summary['attribution_sha256'] == sha(out / 'attribution.json')
        for label, h in summary['census_sha256'].items():
            p = raw / (label + '.json')
            assert sha(p) == h
            census = read(p)
            assert census['status'] == 'passed' and census['guest_commands'] == census['executable_code_publications'] == 0
            artifacts[str(p.relative_to(ROOT))] = h
        for p, h in read(out / 'attribution.json')['evidence'].items():
            assert sha(ROOT / p) == h
            artifacts[p] = h
    else:
        assert not (out / 'summary.json').exists()
        write(out / 'summary.json', dict(status='failed', raw=str(raw.relative_to(ROOT)), source_revision=plan['source_revision'],
            commands=len(records), command_returncodes=[r['returncode'] for r in records],
            plan_sha256=sha(raw / 'plan.json'), records_sha256=sha(raw / 'records.json'), performance_measurement=False))
    write(raw / 'bindings.json', dict(source=bindings, artifacts=artifacts))
    (out / 'terminal.json').write_bytes((outer / 'status.json').read_bytes())
    write(out / 'closure.json', dict(status='closed', source_revision=plan['source_revision'],
        frozen_input_count=len(bindings), artifact_count=len(artifacts), all_hashes_verified=True,
        bindings=str((raw / 'bindings.json').relative_to(ROOT)), bindings_sha256=sha(raw / 'bindings.json'),
        terminal_sha256=sha(out / 'terminal.json'), summary_sha256=sha(out / 'summary.json')))
    print(run, terminal['returncode'], len(bindings), 'source bindings;', len(artifacts), 'artifacts verified')


if __name__ == '__main__':
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        main()
