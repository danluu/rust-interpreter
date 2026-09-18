"""Correct a copied Python count, preserving the original closed report."""
import hashlib, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import write_json as write

with (ROOT / '.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock, 45)
    out = ROOT / 'results/demand-region-build-02'
    summary = json.loads((out / 'summary.json').read_text())
    closed = json.loads((out / 'closure.json').read_text())
    assert closed['status'] == 'closed' and closed['all_hashes_verified']
    assert sha(out / 'summary.json') == closed['summary_sha256']
    raw = ROOT / summary['raw']
    assert sha(raw / 'records.json') == summary['records_sha256']
    record, = [r for r in json.loads((raw / 'records.json').read_text()) if r['label'] == 'python']
    log = raw / 'python.stderr'
    assert record['returncode'] == 0 and sha(log) == record['stderr_sha256']
    text = log.read_text()
    discovered = int(re.search(r'Ran (\d+) tests', text)[1])
    skipped = int(re.search(r'OK \(skipped=(\d+)\)\s*$', text)[1])
    assert summary['python'] == {'discovered': 430, 'passed': 407, 'skipped': 22}
    assert (discovered, skipped) == (430, 22)
    for name in ['summary', 'closure']:
        original = out / (name + '.original.json')
        assert not original.exists()
        original.write_bytes((out / (name + '.json')).read_bytes())
    summary['python']['passed'] = discovered - skipped
    write(out / 'summary.json', summary)
    correction = dict(reason='Copied report literal was 407; verified raw unittest log is 430 discovered minus 22 skips = 408 passes.',
        script=str(Path(__file__).relative_to(ROOT)), script_sha256=sha(Path(__file__)),
        original_summary_sha256=sha(out / 'summary.original.json'), original_closure_sha256=sha(out / 'closure.original.json'),
        corrected_summary_sha256=sha(out / 'summary.json'), raw_log=str(log.relative_to(ROOT)), raw_log_sha256=sha(log),
        repeated_commands=0, runtime_or_artifact_changes=0)
    write(out / 'reporting-correction.json', correction)
    closed.update(summary_sha256=sha(out / 'summary.json'), reporting_correction_sha256=sha(out / 'reporting-correction.json'))
    write(out / 'closure.json', closed)
    print('Corrected Python passes to 408; original closed reports preserved; no commands rerun.')
