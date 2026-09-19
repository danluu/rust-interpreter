#!/usr/bin/env python3
"""Retain the completed removal evidence and all exact frozen inputs."""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import tarfile
import time

from assess import OWNER, ASSESSMENT

HERE = Path(__file__).resolve().parent
WORK = OWNER/'.work/ruff-diagnostic-target-cleanup-01'
OUTER = OWNER/'.work/experiments/ruff-diagnostic-target-cleanup-supervisor-01'
RESULT = OWNER/'results/ruff-diagnostic-target-cleanup-01'


def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()


def write(path,value):
    with path.open('x') as output:
        json.dump(value,output,sort_keys=True,indent=2); output.write('\n')


def space():
    assert shutil.disk_usage(OWNER).free >= 9*2**30


def main():
    assert Path.cwd() == OWNER and not RESULT.exists()
    space()
    receipt = json.loads((WORK/'receipt.json').read_text())
    outer = json.loads((OUTER/'status.json').read_text())
    assert receipt['status']=='passed' and outer['status']=='finished' and outer['returncode']==0
    packet=HERE/'plan-01'; frozen=json.loads((packet/'inputs.json').read_text())
    paths={Path(name) for name in frozen['files']}
    for name,digest in frozen['files'].items(): assert sha(Path(name))==digest
    for directory in [WORK,OUTER,packet]:
        for path in directory.rglob('*'):
            if path.is_file(): paths.add(path)
    paths.update([OWNER/'.work/ruff-diagnostic-target-cleanup-independent-verification-01.json',
                  ASSESSMENT,Path(__file__).resolve()])
    manifest={}
    for path in sorted(paths):
        space(); value=path.lstat()
        assert stat.S_ISREG(value.st_mode) and path.resolve(strict=True)==path
        assert value.st_size<=96*2**20
        manifest[str(path).lstrip('/')]=dict(source=str(path),bytes=value.st_size,sha256=sha(path))
    RESULT.mkdir(parents=True)
    write(RESULT/'manifest.json',manifest)
    started=time.time()
    with (RESULT/'evidence.tar.gz').open('xb') as raw, gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as zipped, tarfile.open(fileobj=zipped,mode='w') as archive:
        for name,proof in manifest.items():
            space(); path=Path(proof['source']); before=path.stat(); data=path.read_bytes()
            assert path.stat()==before and len(data)==proof['bytes'] and hashlib.sha256(data).hexdigest()==proof['sha256']
            member=tarfile.TarInfo(name);member.size=len(data);member.mode=0o644;member.mtime=0
            archive.addfile(member,io.BytesIO(data))
    with tarfile.open(RESULT/'evidence.tar.gz','r:gz') as archive:
        members=archive.getmembers()
        assert len(members)==len(manifest) and {m.name for m in members}==set(manifest)
        for member in members:
            space();proof=manifest[member.name]
            assert member.isfile() and member.size==proof['bytes']
            assert hashlib.sha256(archive.extractfile(member).read()).hexdigest()==proof['sha256']
        while archive.fileobj.read(2**20): space()
    result=dict(status='passed',started_at=started,finished_at=time.time(),members=len(manifest),
        logical_bytes=sum(x['bytes'] for x in manifest.values()),archive_bytes=(RESULT/'evidence.tar.gz').stat().st_size,
        archive_sha256=sha(RESULT/'evidence.tar.gz'),manifest_sha256=sha(RESULT/'manifest.json'),
        receipt_sha256=sha(WORK/'receipt.json'),full_gzip_eof_verified=True,free_bytes_after=shutil.disk_usage(OWNER).free)
    write(RESULT/'archive-execution.json',result)
    write(RESULT/'summary.json',dict(status='passed',benchmark=False,deleted_entries=receipt['deleted_entries'],
        roots=receipt['roots'],free_bytes_before=receipt['free_bytes_before'],free_bytes_after=receipt['free_bytes_after'],
        observed_free_increase_bytes=receipt['free_bytes_after']-receipt['free_bytes_before'],
        all_three_targets_absent=True,source_and_evidence_preserved=True,read_only_probe_children=4,
        receipt_sha256=sha(WORK/'receipt.json'),archive_sha256=result['archive_sha256'],
        scope='Only three completed Ruff diagnostic targets; allocation/free deltas are observations, not exclusive attribution.',
        artifact_retention='results/ruff-diagnostic-final-artifacts-01',
        limitation='Earlier overwritten native executable bytes were unavailable. Final native and both complete guest outputs retained; no performance qualification implied.'))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
