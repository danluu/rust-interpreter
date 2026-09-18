"""Read all physical archive bytes and verify every logical backward hardlink."""
import gzip
import hashlib
import json
from pathlib import Path
import tarfile
import time

ROOT = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
OUT = ROOT / 'results/runtime-exporter-publication-01'
WORK = ROOT / '.work/runtime-exporter-evidence-archive-01'
FREEZE = ROOT / '.work/runtime-exporter-evidence-freeze-01.json'
OUTER = ROOT / '.work/experiments/runtime-exporter-evidence-supervisor-01'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def main():
    terminal = read(WORK / 'summary.json'); outer = read(OUTER / 'status.json')
    summary = read(OUT / 'summary.json'); manifest = read(OUT / 'manifest.json'); frozen = read(FREEZE)
    assert terminal['status'] == summary['status'] == 'passed' and outer['status'] == 'finished' and outer['returncode'] == 0
    assert terminal['parent_pid'] == outer['supervisor_pid'] and terminal['pid'] == outer['child_pid']
    assert sha(OUTER / 'command.log') == outer['log_sha256']
    assert terminal['summary_sha256'] == sha(OUT / 'summary.json')
    assert terminal['freeze_sha256'] == sha(FREEZE) == '8f6983b137cd1012f1ed6a1dc49c52cb8443ad2ed55ddbfb819285983cc9c934'
    assert outer['started_at'] <= terminal['started_at'] <= terminal['admitted_at'] <= terminal['finished_at'] <= outer['finished_at']
    assert summary['manifest_sha256'] == sha(OUT / 'manifest.json')
    archive = OUT / 'evidence.tar.gz'
    archive_hash = sha(archive)
    assert archive_hash == summary['archive']['sha256'] == terminal['archive']['sha256']
    assert archive.stat().st_size == summary['archive']['bytes'] <= 96 * 2**20
    expected = {path.lstrip('/'):dict(source=path, sha256=row['sha256'], bytes=row['bytes']) for path,row in frozen['files'].items()}
    expected[str(FREEZE).lstrip('/')] = dict(source=str(FREEZE), sha256=sha(FREEZE), bytes=FREEZE.stat().st_size)
    assert manifest == expected and len(manifest) == summary['source_and_proof_files'] == summary['archive']['members']
    seen = {}; physical = 0; logical_bytes = 0
    with tarfile.open(archive, 'r|gz') as tar:
        for member in tar:
            assert member.name in manifest and member.name not in seen
            row = manifest[member.name]
            if member.isfile():
                data = tar.extractfile(member).read()
                proof = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
                physical += 1
            else:
                assert member.islnk() and member.linkname in seen and member.size == 0
                proof = seen[member.linkname]
            assert proof['bytes'] == row['bytes'] and proof['sha256'] == row['sha256']
            seen[member.name] = proof
            logical_bytes += row['bytes']
    assert set(seen) == set(manifest) and physical == summary['archive']['physical_members']
    assert logical_bytes == frozen['input_bytes'] + FREEZE.stat().st_size
    total = 0
    with gzip.open(archive, 'rb') as stream:
        while block := stream.read(2**20):
            total += len(block)
            assert total <= 160 * 2**20
    assert total == summary['archive']['uncompressed_bytes'] and sha(archive) == archive_hash
    counts = {'metadata-01':(53,'passed'), 'build-01':(19,'passed'), 'frontend-01':(32,'failed'),
              'frontend-continue-01':(8,'passed'), 'publication-01':(0,'failed'),
              'publication-02':(0,'failed'), 'publication-03':(23,'passed')}
    assert set(summary['stages']) == set(counts)
    for stage, (count,status) in counts.items():
        assert summary['stages'][stage]['children'] == count and summary['stages'][stage]['status'] == status
        assert summary['stages'][stage]['receipt_sha256'] == frozen['stages'][stage]['receipt']['sha256']
    assert summary['frontend_qualified'] and summary['prior_failed_frontend_preserved'] and summary['prior_failed_publication_admission_preserved']
    assert not any(summary[name] for name in ('application_qualified','guest_execution','benchmark','performance_target_met','actual_commands_rerun','live_compiler_or_tool_payload_read_by_archive'))
    result = dict(status='passed', time=time.time(), terminal_sha256=sha(WORK / 'summary.json'),
        outer_sha256=sha(OUTER / 'status.json'), summary_sha256=sha(OUT / 'summary.json'),
        manifest_sha256=sha(OUT / 'manifest.json'), archive_sha256=archive_hash,
        archive_bytes=archive.stat().st_size, logical_members=len(seen), physical_members=physical,
        logical_bytes=logical_bytes, gzip_uncompressed_bytes=total, all_physical_bytes_and_backward_links_verified=True,
        full_gzip_eof_crc_verified=True, historical_failures_preserved=True, application_performance_qualified=False)
    path = ROOT / '.work/runtime-exporter-retention-independent-verification-01.json'
    with path.open('x') as stream: json.dump(result,stream,indent=2,sort_keys=True); stream.write('\n')
    print(json.dumps(result,indent=2)); print('independent retention',sha(path))


if __name__ == '__main__':
    main()
