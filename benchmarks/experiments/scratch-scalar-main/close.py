"""Close the merged Python qualification without repeating guest histories."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import write_json as write
from qualify import RUN


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        raw = ROOT / '.work' / RUN
        result = ROOT / 'results' / RUN
        outer = ROOT / '.work/experiments' / RUN
        summary = json.loads((result / 'summary.json').read_text())
        terminal = json.loads((outer / 'status.json').read_text())
        assert summary['status'] == 'passed' and summary['all_frozen_inputs_verified']
        assert terminal['status'] == 'finished' and terminal['returncode'] == 0
        assert terminal['owner'] == terminal['cwd'] == str(ROOT)
        assert sha(outer / 'command.log') == terminal['log_sha256']
        assert sha(outer / 'plan.json') == terminal['plan_sha256']
        for name in ['plan', 'record']:
            assert sha(raw / (name + '.json')) == summary[name + '_sha256']
        plan = json.loads((raw / 'plan.json').read_text())
        record = json.loads((raw / 'record.json').read_text())
        assert record['returncode'] == 0
        for stream in ['stdout', 'stderr']:
            assert sha(raw / stream) == record[stream + '_sha256']
        for path, digest in {**plan['frozen'], **plan['evidence']}.items():
            assert sha(ROOT / path) == digest, path
        bindings = {}
        for path, digest in plan['frozen'].items():
            original = subprocess.check_output(['git', 'show', plan['source_revision'] + ':' + path], cwd=ROOT)
            assert hashlib.sha256(original).hexdigest() == digest, path
            bindings[path] = dict(revision=plan['source_revision'], sha256=digest)
        write(raw / 'source-bindings.json', bindings)
        assert not (result / 'closure.json').exists()
        (result / 'terminal.json').write_bytes((outer / 'status.json').read_bytes())
        write(result / 'closure.json', dict(status='closed', source_revision=plan['source_revision'],
            summary_sha256=sha(result / 'summary.json'), terminal_sha256=sha(result / 'terminal.json'),
            bindings=str((raw / 'source-bindings.json').relative_to(ROOT)),
            bindings_sha256=sha(raw / 'source-bindings.json'), source_bindings=len(bindings),
            reused_result_manifests_verified=True, all_frozen_inputs_verified=True,
            new_guest_commands=0, performance_measurement=False))
        print('Closed merged Python qualification:', len(bindings), 'Git source bindings', flush=True)


if __name__ == '__main__':
    main()
