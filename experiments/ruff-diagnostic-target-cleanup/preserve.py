#!/usr/bin/env python3
"""Preserve final artifacts and verify existing diagnostic archive; no removal."""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tarfile

from assess import OWNER, A, R, RUN, ROOTS, ASSESSMENT, digest, identity

HERE = Path(__file__).resolve().parent
DEST = OWNER/'.work/ruff-diagnostic-preservation-01'
RESULT = OWNER/'results/ruff-diagnostic-final-artifacts-01'
REVISION = 'bdb42f49'
NATIVE = ROOTS['native']/'debug/build/ruff_linter/c92b0847448cb8f8/out/ruff_linter-c92b0847448cb8f8'
NATIVE_SHA = '449bf2d2bebe5df27e0f4ac148a0031a7835b8dd9e44e0c6e7feadd9cf972472'


def space():
    assert shutil.disk_usage(OWNER).free >= 9*2**30


def write(path, value):
    with path.open('x') as output:
        json.dump(value, output, indent=2, sort_keys=True)
        output.write('\n')


def main():
    assert Path.cwd() == OWNER and not DEST.exists() and not RESULT.exists()
    space()
    DEST.mkdir()
    original = DEST/'original-archive'
    original.mkdir()
    git_records = []
    for name in ['manifest.json', 'evidence.tar.gz']:
        argv = ['/usr/bin/git', 'show', REVISION+':results/runtime-ruff-hir-diagnostic-01/'+name]
        result = subprocess.run(argv, cwd=A, capture_output=True, check=True)
        assert not result.stderr and len(result.stdout) < 96*2**20
        path = original/name
        with path.open('xb') as output:
            output.write(result.stdout)
        git_records.append(dict(command=argv, cwd=str(A), returncode=result.returncode,
                                bytes=len(result.stdout), sha256=digest(path), path=str(path)))
    manifest = json.loads((original/'manifest.json').read_bytes())
    assert len(manifest) == 263
    with tarfile.open(original/'evidence.tar.gz', 'r:gz') as archive:
        members = archive.getmembers()
        assert len(members) == 263 and {x.name for x in members} == set(manifest)
        seen = {}
        for member in members:
            space()
            proof = manifest[member.name]
            assert proof['source'] == '/'+member.name
            if member.islnk():
                assert member.linkname in seen and seen[member.linkname] == proof['sha256'] and member.size == 0
            else:
                assert member.isfile() and member.size == proof['bytes']
            stream = archive.extractfile(member)
            data = stream.read()
            assert len(data) == proof['bytes'] and hashlib.sha256(data).hexdigest() == proof['sha256']
            seen[member.name] = proof['sha256']
        while archive.fileobj.read(2**20):
            space()
    records = json.loads((RUN/'records.json').read_bytes())
    assert len(records) == 24
    final = {row['mode']:row for row in records if row['state'] == -2}
    assert set(final) == set(ROOTS)
    assert str(NATIVE) in final['native']['calls'][0]['stderr']
    assert NATIVE.stat().st_size == 36683808 and digest(NATIVE) == NATIVE_SHA
    sources = {'native/'+NATIVE.name:NATIVE, 'native/'+NATIVE.name+'.d':Path(str(NATIVE)+'.d')}
    directory_sets = {}
    for mode in ['baseline', 'candidate']:
        launch = final[mode]['calls'][0]['launch']
        artifact = Path(launch['artifact_path'])
        assert artifact.is_relative_to(ROOTS[mode]) and digest(artifact) == launch['artifact_sha256']
        paths = sorted(artifact.parent.iterdir())
        assert len(paths) == 5
        expected = {artifact.name, artifact.name+'.entries.json', artifact.name+'.calls.json',
                    artifact.name.removesuffix('.rbc'), artifact.name.removeprefix('lib').removesuffix('.rmeta.rbc')+'.d'}
        assert {path.name for path in paths} == expected
        directory_sets[mode] = dict(path=str(artifact.parent), names=sorted(expected))
        sources.update({mode+'/'+path.name:path for path in paths})
    assert len(sources) == 12
    retained = {}
    for name, source in sources.items():
        space()
        before = identity(source)
        assert source.resolve(strict=True) == source and stat.S_ISREG(before['mode']) and before['size'] <= 64*2**20
        payload = source.read_bytes()
        assert identity(source) == before
        target = DEST/'artifacts'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as output:
            output.write(payload)
        assert target.stat().st_nlink == 1 and target.stat().st_ino != source.stat().st_ino
        assert digest(target) == digest(source)
        retained[name] = dict(source=str(source), source_identity=before, retained=str(target),
                              bytes=len(payload), sha256=digest(target))
    live = {}
    fingerprints = {}
    for name, proof in manifest.items():
        path = Path(proof['source'])
        deleting = any(path.is_relative_to(root) for root in ROOTS.values())
        if deleting:
            assert path.is_relative_to(ROOTS['candidate']) and 'fingerprint' in str(path)
            assert digest(path) == proof['sha256']
            fingerprints[str(path)] = proof
        elif path.is_relative_to(RUN) or path.is_relative_to(A/'.work/ruff-hir-diagnostic-supervision-01') or path.is_relative_to(A/'.work/experiments/ruff-hir-diagnostic-supervisor-01'):
            assert path.resolve(strict=True) == path and digest(path) == proof['sha256']
            live[str(path)] = proof
    assert len(fingerprints) == 19
    assert sum(path.endswith('.rbc') for path in live) == 16
    assert sum('/cargo-timings/' in path and path.endswith('.html') for path in live) == 24
    # Preserve existing workspace identities outside the exact target subtrees.
    workspaces = {}
    for mode in ['baseline', 'candidate']:
        parent = ROOTS[mode].parent
        names = sorted(path.name for path in parent.iterdir())
        files = {}
        for path in parent.iterdir():
            if path == ROOTS[mode]:
                continue
            assert path.resolve(strict=True) == path and path.is_file()
            files[path.name] = dict(identity=identity(path), sha256=digest(path))
        workspaces[mode] = dict(path=str(parent), initial_names=names, files=files)
    receipt = dict(status='preserved', original_archive=git_records, archive_members_verified=263,
                   archive_full_gzip_eof_verified=True, final_artifacts=retained,
                   guest_output_directories=directory_sets, original_replay_fingerprints=fingerprints,
                   live_evidence=live, workspaces=workspaces,
                   assessment=dict(path=str(ASSESSMENT), sha256=digest(ASSESSMENT)),
                   limitation='Only the final native executable was still available; earlier overwritten native bytes are not claimed. All 24 original call records/raw output and 16 bytecode artifacts remain preserved.')
    write(DEST/'receipt.json', receipt)
    paths = {str(path.relative_to(DEST)):path for path in (DEST/'artifacts').rglob('*') if path.is_file()}
    paths['receipt.json'] = DEST/'receipt.json'
    members = {name:dict(bytes=path.stat().st_size, sha256=digest(path)) for name,path in paths.items()}
    RESULT.mkdir(parents=True)
    write(RESULT/'manifest.json', dict(schema_version=1, members=members,
          scope='Final native executable/dep-info and both complete five-file guest artifact directories; original 263-member archive remains referenced by exact committed bytes.'))
    with (RESULT/'evidence.tar.gz').open('xb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as zipped, tarfile.open(fileobj=zipped, mode='w') as archive:
        for name, path in sorted(paths.items()):
            space()
            payload = path.read_bytes()
            assert hashlib.sha256(payload).hexdigest() == members[name]['sha256']
            item = tarfile.TarInfo(name)
            item.size, item.mode, item.mtime = len(payload), 0o644, 0
            archive.addfile(item, io.BytesIO(payload))
    with tarfile.open(RESULT/'evidence.tar.gz', 'r:gz') as archive:
        rows = archive.getmembers()
        assert len(rows) == 13 and {row.name for row in rows} == set(members)
        for row in rows:
            assert row.isfile() and row.size == members[row.name]['bytes']
            assert hashlib.sha256(archive.extractfile(row).read()).hexdigest() == members[row.name]['sha256']
        while archive.fileobj.read(2**20):
            space()
    print(json.dumps(dict(retained_files=12, original_archive_members=263, fingerprints=19,
                         preservation_sha256=digest(DEST/'receipt.json'),
                         supplement_members=13, supplement_archive_bytes=(RESULT/'evidence.tar.gz').stat().st_size,
                         supplement_archive_sha256=digest(RESULT/'evidence.tar.gz'),
                         supplement_manifest_sha256=digest(RESULT/'manifest.json')), indent=2))


if __name__ == '__main__':
    main()
