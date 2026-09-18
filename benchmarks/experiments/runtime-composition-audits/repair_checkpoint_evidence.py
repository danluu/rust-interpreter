"""Resolve recovered-prefix ledger references to their original immutable copies."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import require_space, write_json as write


def read(path):
    return json.loads(path.read_text())


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        script = str(Path(__file__).relative_to(ROOT))
        assert hashlib.sha256(subprocess.check_output(['git', 'show', revision + ':' + script])).hexdigest() == sha(Path(__file__))
        campaign = ROOT / '.work/runtime-composition-full-02'
        repairs = []
        for count, case in [(2, 'folded'), (3, 'pgrust')]:
            result = ROOT / 'results' / ('runtime-composition-edit-' + case + '-02')
            closed = read(result / 'closure.json')
            assert closed['status'] == 'closed' and closed['performance_gate_passed']
            for name in ['summary', 'terminal']:
                assert sha(result / (name + '.json')) == closed[name + '_sha256']
            snapshot = ROOT / closed['snapshot']
            assert snapshot == campaign / f'closed-checkpoint-{count}'
            assert sha(snapshot / 'evidence.json') == closed['evidence_sha256']
            assert sha(snapshot / 'sources.json') == closed['sources_sha256']
            evidence = read(snapshot / 'evidence.json')
            corrected = {}
            aliases = []
            for path, digest in evidence.items():
                if path == str((campaign / 'records.json').relative_to(ROOT)):
                    archive = str((snapshot / 'records.json').relative_to(ROOT))
                    assert evidence[archive] == digest and sha(ROOT / archive) == digest
                    assert len(read(ROOT / archive)) == count
                    assert sha(ROOT / path) != digest, 'expected an already advanced live ledger'
                    aliases.append(dict(original_path=path, sha256=digest, archived_path=archive))
                    corrected[archive] = digest
                else:
                    assert sha(ROOT / path) == digest, path
                    corrected[path] = digest
            assert len(aliases) == 1
            for path, binding in read(snapshot / 'sources.json').items():
                contents = subprocess.check_output(['git', 'show', binding['revision'] + ':' + path])
                assert hashlib.sha256(contents).hexdigest() == binding['sha256']
            target = snapshot / 'archived-evidence.json'
            assert not target.exists()
            write(target, corrected)
            receipt = dict(status='passed', original_closure_sha256=sha(result / 'closure.json'),
                original_evidence_sha256=closed['evidence_sha256'], aliases=aliases,
                evidence=str(target.relative_to(ROOT)), evidence_sha256=sha(target),
                verified_files=len(corrected), all_archived_hashes_verified=True,
                original_receipts_unchanged=True, new_guest_commands=0, measurements_changed=False)
            assert not (result / 'checkpoint-evidence-repair.json').exists()
            write(result / 'checkpoint-evidence-repair.json', receipt)
            repairs.append(dict(case=case, **receipt))
        out = ROOT / 'results/runtime-composition-checkpoint-evidence-repair-01'
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', dict(status='passed', source_revision=revision,
            script=script, script_sha256=sha(Path(__file__)), repairs=repairs,
            new_guest_commands=0, measurements_changed=False, performance_measurement=False))
        print('Verified immutable ledger snapshots for two recovered checkpoints; no measurements changed', flush=True)


if __name__ == '__main__':
    main()
