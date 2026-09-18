"""Close completed sampling evidence with source and retained artifact bindings."""
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


def read(path):
    return json.loads(path.read_text())


def main():
    run = sys.argv[1]
    assert re.fullmatch(r'scratch-scalar-runtime-sampling-\d{2}', run)
    raw, out = ROOT / '.work' / run, ROOT / 'results' / run
    outer = ROOT / '.work/experiments' / run
    terminal = read(outer / 'status.json')
    assert terminal['status'] == 'finished' and terminal['owner'] == str(ROOT)
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
    for row in records:
        for stream in ['stdout', 'stderr']:
            assert sha(raw / (row['label'] + '.' + stream)) == row[stream + '_sha256']
    out.mkdir(exist_ok=True)
    assert not (out / 'closure.json').exists()
    artifacts = {}
    if terminal['returncode'] == 0:
        summary = read(out / 'summary.json')
        assert summary['status'] == 'passed' and summary['guest_commands'] == 2 and len(records) == 4
        assert all(r['returncode'] == 0 for r in records)
        assert sha(raw / 'plan.json') == summary['plan_sha256']
        assert sha(raw / 'records.json') == summary['records_sha256']
        for case in summary['cases']:
            report_path = ROOT / case['report']
            assert sha(report_path) == case['report_sha256']
            report = read(report_path)
            for p, h in report['evidence'].items():
                assert sha(ROOT / p) == h
                artifacts[p] = h
            folder = ROOT / '.work' / case['run_id']
            record = read(folder / '0/record.json')
            assert record['identity']['status'] == 'finished' and record['identity']['returncode'] == 0
            for p, h in record['files'].items():
                path = folder / '0' / p
                assert sha(path) == h
                artifacts[str(path.relative_to(ROOT))] = h
            for p in [report_path, folder / 'plan.json', folder / 'summary.json', folder / 'records.json']:
                artifacts[str(p.relative_to(ROOT))] = sha(p)
    else:
        assert not (out / 'summary.json').exists()
        write(out / 'summary.json', dict(status='failed', raw=str(raw.relative_to(ROOT)),
            source_revision=plan['source_revision'], commands=len(records),
            command_returncodes=[r['returncode'] for r in records],
            plan_sha256=sha(raw / 'plan.json'), records_sha256=sha(raw / 'records.json'),
            performance_measurement=False))
    write(raw / 'source-bindings.json', bindings)
    write(raw / 'artifact-bindings.json', artifacts)
    (out / 'terminal.json').write_bytes((outer / 'status.json').read_bytes())
    write(out / 'closure.json', dict(status='closed', source_revision=plan['source_revision'],
        frozen_input_count=len(bindings), artifact_count=len(artifacts), all_hashes_verified=True,
        source_bindings=str((raw / 'source-bindings.json').relative_to(ROOT)),
        source_bindings_sha256=sha(raw / 'source-bindings.json'),
        artifact_bindings=str((raw / 'artifact-bindings.json').relative_to(ROOT)),
        artifact_bindings_sha256=sha(raw / 'artifact-bindings.json'),
        terminal_sha256=sha(out / 'terminal.json'), summary_sha256=sha(out / 'summary.json')))
    print(run, terminal['returncode'], len(bindings), 'source bindings,', len(artifacts), 'artifact bindings verified')


if __name__ == '__main__':
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        main()
