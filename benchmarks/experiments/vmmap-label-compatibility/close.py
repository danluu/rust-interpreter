"""Close Python contracts and retained-map checks with exact source bindings."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import require_space, write_json as write
RUN = 'vmmap-label-compatibility-01'


def read(path):
    return json.loads(path.read_text())


def main():
    supervisor = sys.argv[1] if len(sys.argv) > 1 else RUN
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        raw, out = ROOT / '.work' / RUN, ROOT / 'results' / RUN
        outer = ROOT / '.work/experiments' / supervisor
        summary, plan, terminal = read(out / 'summary.json'), read(raw / 'plan.json'), read(outer / 'status.json')
        assert summary['status'] == 'passed' and summary['commands'] == 3 and summary['guest_commands'] == 0
        assert summary['attribution_tests'] == 9 and summary['retained_reports'] == 14
        assert terminal['status'] == 'finished' and terminal['returncode'] == 0
        assert terminal['owner'] == terminal['cwd'] == str(ROOT)
        assert sha(outer / 'plan.json') == terminal['plan_sha256'] and sha(outer / 'command.log') == terminal['log_sha256']
        assert sha(raw / 'plan.json') == summary['plan_sha256'] and sha(raw / 'records.json') == summary['records_sha256']
        bindings, evidence = {}, {}
        for path, digest in plan['frozen'].items():
            assert sha(ROOT / path) == digest
            if path.startswith(('.work/', 'results/')):
                evidence[path] = digest
            else:
                blob = subprocess.check_output(['git', 'show', plan['source_revision'] + ':' + path], cwd=ROOT)
                assert hashlib.sha256(blob).hexdigest() == digest
                bindings[path] = dict(revision=plan['source_revision'], sha256=digest)
        for row in read(raw / 'records.json'):
            assert row['returncode'] == 0
            for stream in ['stdout', 'stderr']:
                path = raw / (row['label'] + '.' + stream)
                assert sha(path) == row[stream + '_sha256']
                evidence[str(path.relative_to(ROOT))] = sha(path)
        replay = read(raw / 'retained-maps.stdout')
        assert replay['every_original_emitted_arena_contained'] and replay['reports'] == 14
        evidence.update(replay['evidence'])
        assert all(sha(ROOT / p) == h for p, h in evidence.items())
        assert not (out / 'closure.json').exists()
        write(raw / 'closed-sources.json', bindings)
        write(raw / 'closed-evidence.json', evidence)
        (out / 'terminal.json').write_bytes((outer / 'status.json').read_bytes())
        write(out / 'closure.json', dict(status='closed', source_revision=plan['source_revision'],
            all_hashes_verified=True, source_bindings=str((raw / 'closed-sources.json').relative_to(ROOT)),
            source_bindings_sha256=sha(raw / 'closed-sources.json'),
            evidence=str((raw / 'closed-evidence.json').relative_to(ROOT)),
            evidence_sha256=sha(raw / 'closed-evidence.json'),
            summary_sha256=sha(out / 'summary.json'), terminal_sha256=sha(out / 'terminal.json'),
            source_files=len(bindings), evidence_files=len(evidence), new_guest_commands=0))
        print('Closed vmmap compatibility:', len(bindings), 'source files;', len(evidence), 'evidence files', flush=True)


if __name__ == '__main__':
    main()
