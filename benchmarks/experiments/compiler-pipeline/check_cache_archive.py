#!/usr/bin/env python3
"""Qualify archive preservation and interruption handling using only owned fixtures."""
import argparse
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import archive_workflow_cache as coordinator
import cache_archive as archive
from reclaim_workflow_objects import no_open_files, sha
from verify_repeated_workflow import require
from workflow_io import write_json

ROOT_ATTRIBUTES = {
    'com.apple.fileprovider.ignore#P': '31',
    'com.apple.metadata:com_apple_backup_excludeItem':
        '62706c69737430305f1011636f6d2e6170706c652e6261636b75706408000000000000010100000000000000010000000000000000000000000000001c',
}
DIRECTORY_ATTRIBUTES = dict(ROOT_ATTRIBUTES, **{'com.apple.fileprovider.ignore#P': '30'})


def fixture(target, many=False):
    target.mkdir(parents=True, mode=0o700)
    (target / 'directory with spaces').mkdir()
    (target / 'empty/deep').mkdir(parents=True)
    (target / 'library.rlib').write_bytes(bytes(range(256)) * 400)
    os.link(target / 'library.rlib', target / 'directory with spaces/linked.bin')
    (target / 'native program').write_bytes(b'owned executable fixture\n')
    (target / 'native program').chmod(0o755)
    (target / '.cargo-lock').write_bytes(b'')
    (target / 'metadata.json').write_bytes(b'{"owned":true}\n')
    if many:
        for index in range(1001):
            (target / f'object-{index:04d}.o').write_bytes(str(index).encode())
    if sys.platform == 'darwin':
        archive.set_root_xattrs(target, ROOT_ATTRIBUTES)
        (target / 'aarch64-apple-darwin').mkdir()
        archive.set_root_xattrs(target / 'aarch64-apple-darwin', DIRECTORY_ATTRIBUTES)
    timestamp = 1_700_000_000_123456789
    for path in sorted(target.rglob('*'), key=lambda p: len(p.parts), reverse=True):
        os.utime(path, ns=(timestamp - 100, timestamp))
    os.utime(target, ns=(timestamp - 100, timestamp))
    return archive.snapshot(target)


@contextmanager
def replace(module, name, value):
    original = getattr(module, name)
    setattr(module, name, value)
    try:
        yield
    finally:
        setattr(module, name, original)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    coordinator.identifier(args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        raw = ROOT / '.work/runs' / args.run_id
        output = ROOT / 'results' / args.run_id
        require(not raw.exists() and not output.exists(), 'qualification identity already exists')
        raw.mkdir(mode=0o700)
        rejected = []

        def rejects(label, operation):
            try:
                operation()
            except (RuntimeError, OSError, zipfile.BadZipFile) as error:
                rejected.append(dict(label=label, error=str(error)))
            else:
                raise RuntimeError('invalid archive operation succeeded: ' + label)

        original = raw / 'original'
        manifest = fixture(original)
        packed = raw / 'cache.zip'
        archive.write_archive(original, manifest, packed)
        archive.verify_archive(packed, manifest)
        archive.unchanged(original, manifest)
        restored = raw / 'restored'
        archive.restore(packed, manifest, restored)
        require(manifest.get('root_xattrs') == (ROOT_ATTRIBUTES if sys.platform == 'darwin' else {}),
                'root attributes were not captured')
        require(manifest.get('directory_xattrs', {}) ==
                ({'aarch64-apple-darwin': DIRECTORY_ATTRIBUTES} if sys.platform == 'darwin' else {}),
                'architecture directory attributes were not captured separately')
        for group in manifest['groups']:
            restored_info = archive.information(restored / group['paths'][0])
            require(restored_info['atime_ns'] == group['atime_ns'] and
                    restored_info['mtime_ns'] == group['mtime_ns'], 'restored file timestamps differ')
        for directory in manifest['directories']:
            restored_info = archive.information(restored / directory['path'], True)
            require(restored_info['atime_ns'] == directory['atime_ns'] and
                    restored_info['mtime_ns'] == directory['mtime_ns'], 'restored directory timestamps differ')
        require((restored / 'library.rlib').stat().st_ino ==
                (restored / 'directory with spaces/linked.bin').stat().st_ino, 'restored hardlink was copied')
        require((restored / 'native program').stat().st_mode & 0o777 == 0o755, 'executable mode lost')
        require((restored / 'empty/deep').is_dir(), 'empty directory lost')
        require(archive.read_file(packed, manifest, 'metadata.json', 1024) == b'{"owned":true}\n', 'inspection differs')
        require(archive.read_file(packed, manifest, '.cargo-lock', 0) == b'', 'empty-file inspection differs')
        rejects('populated restore destination', lambda: archive.restore(packed, manifest, restored))
        alias = raw / 'destination-alias'
        alias.symlink_to(restored, target_is_directory=True)
        rejects('symlink restore destination', lambda: archive.restore(packed, manifest, alias))
        rejects('symlink restore parent', lambda: archive.restore(packed, manifest, alias / 'new'))
        rejects('inspection too large', lambda: archive.read_file(packed, manifest, 'library.rlib', 4))
        rejects('missing inspection member', lambda: archive.read_file(packed, manifest, 'missing', 1024))
        rejects('invalid inspection path', lambda: archive.read_file(packed, manifest, '../outside', 1024))
        for label, name in [('absolute path', '/outside'), ('parent traversal', '../outside'),
                            ('dot path', '.'), ('normalized path', 'a/../b'), ('empty file path', '')]:
            altered = deepcopy(manifest)
            altered['groups'][0]['paths'] = [name]
            altered['groups'][0]['links'] = 1
            rejects(label, lambda: archive.validate(altered))
        altered = deepcopy(manifest)
        altered['groups'][1]['paths'].append(altered['groups'][0]['paths'][0])
        altered['groups'][1]['paths'].sort()
        altered['groups'][1]['links'] += 1
        rejects('duplicate manifest path', lambda: archive.validate(altered))
        altered = deepcopy(manifest)
        altered['groups'][0]['bytes'] = archive.LIMIT_BYTES + 1
        rejects('oversized declared payload', lambda: archive.validate(altered))
        altered = deepcopy(manifest)
        altered['root_xattrs'] = {'com.apple.quarantine': '00'}
        rejects('unsupported root attribute', lambda: archive.validate(altered))
        altered = deepcopy(manifest)
        altered['root_xattrs'] = {'com.apple.fileprovider.ignore#P': 'not-hex'}
        rejects('invalid root attribute encoding', lambda: archive.validate(altered))
        for label, values in [
            ('unsupported attribute directory', {'empty': ROOT_ATTRIBUTES}),
            ('unsupported nested attribute', {'aarch64-apple-darwin': {'com.apple.quarantine': '00'}}),
            ('malformed nested attribute', {'aarch64-apple-darwin': {'com.apple.fileprovider.ignore#P': 'not-hex'}}),
        ]:
            altered = deepcopy(manifest)
            altered['directory_xattrs'] = values
            rejects(label, lambda: archive.validate(altered))
        altered = deepcopy(manifest)
        altered['directory_xattrs'] = {'aarch64-apple-darwin': ROOT_ATTRIBUTES}
        altered['directories'] = [d for d in altered['directories'] if d['path'] != 'aarch64-apple-darwin']
        rejects('attributes on absent directory', lambda: archive.validate(altered))

        with zipfile.ZipFile(packed) as source:
            entries = [(name, source.read(name)) for name in source.namelist()]
        variants = {
            'missing ZIP member': entries[:-1],
            'extra ZIP member': entries + [('outside', b'no')],
            'duplicate ZIP member': entries + [entries[-1]],
            'changed manifest': [(entries[0][0], b'{}')] + entries[1:],
            'changed payload': entries[:-1] + [(entries[-1][0], b'x' * len(entries[-1][1]))],
        }
        for index, (label, contents) in enumerate(variants.items()):
            path = raw / f'invalid-{index}.zip'
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_DEFLATED) as target:
                    for name, data in contents:
                        target.writestr(name, data)
            rejects(label, lambda: archive.verify_archive(path, manifest))
        truncated = raw / 'truncated.zip'
        truncated.write_bytes(packed.read_bytes()[:-17])
        rejects('truncated archive', lambda: archive.verify_archive(truncated, manifest))

        with (original / 'library.rlib').open('rb'):
            rejects('open original file', lambda: no_open_files(original))
        external = raw / 'external-hardlink'
        os.link(original / 'library.rlib', external)
        rejects('external hardlink', lambda: archive.snapshot(original))
        external.unlink()
        special = raw / 'special-files'
        fixture(special)
        (special / 'alias').symlink_to(original, target_is_directory=True)
        rejects('symlink directory in source', lambda: archive.snapshot(special))
        (special / 'alias').unlink()
        (special / 'alias').symlink_to(original / 'metadata.json')
        rejects('symlink file in source', lambda: archive.snapshot(special))
        (special / 'alias').unlink()
        os.mkfifo(special / 'pipe')
        rejects('special file in source', lambda: archive.snapshot(special))
        (special / 'pipe').unlink()
        if hasattr(os, 'setxattr'):
            os.setxattr(special / 'metadata.json', 'user.rust_interp_archive_fixture', b'present')
        else:
            subprocess.run(['/usr/bin/xattr', '-w', 'rust_interp.archive_fixture', 'present',
                            str(special / 'metadata.json')], check=True)
        rejects('extended attributes in source', lambda: archive.snapshot(special))
        if hasattr(os, 'removexattr'):
            os.removexattr(special / 'metadata.json', 'user.rust_interp_archive_fixture')
        else:
            subprocess.run(['/usr/bin/xattr', '-d', 'rust_interp.archive_fixture',
                            str(special / 'metadata.json')], check=True)
        if sys.platform == 'darwin':
            archive.set_root_xattrs(special / 'empty', ROOT_ATTRIBUTES)
            rejects('root marker below the root', lambda: archive.snapshot(special))
        added = raw / 'added-source'
        before_added = fixture(added)
        (added / 'late.bin').write_bytes(b'new file after inventory')
        rejects('new original file after inventory', lambda: archive.unchanged(added, before_added))
        changed = raw / 'changed-source'
        before = fixture(changed)
        (changed / 'metadata.json').write_bytes(b'changed')
        rejects('changed original before archival', lambda: archive.unchanged(changed, before))
        rejects('changed original while opening payload', lambda: archive.write_archive(changed, before, raw / 'changed.zip'))
        require((changed / 'metadata.json').read_bytes() == b'changed', 'failed archive changed original')

        coordination = []
        for scenario in ['success', 'write-failure', 'verification-failure', 'retirement-interruption']:
            root = raw / ('coordinator-' + scenario)
            target = root / '.work/runs/fixture/native'
            before = fixture(target, many=scenario == 'retirement-interruption')
            (root / 'results').mkdir()
            outside = root / 'evidence.json'
            outside.write_bytes(b'preserved outside target\n')
            outside_sha = sha(outside)
            proof = lambda run_id, corpus: (target, {'evidence.json': sha(outside)}, {'fixture': True})
            with replace(coordinator, 'ROOT', root), replace(coordinator, 'BASE', root / '.work/workflow-cache-archives'), \
                 replace(coordinator, 'workflow', proof), replace(coordinator, 'sources', lambda: {'fixture': 'fixed'}):
                coordinator.owned_root()
                coordinator.prepare('archive', 'fixture', None)
                prepared = json.loads((coordinator.BASE / 'archive/plan.json').read_text())['manifest']
                require(archive.stable(prepared) == archive.stable(before), 'preparation changed fixture contents')
                if scenario == 'success':
                    coordinator.apply('archive')
                    require(not list(target.iterdir()), 'successful retirement left files')
                elif scenario == 'write-failure':
                    original_write = archive.write_archive

                    def fail_write(*args):
                        original_write(*args)
                        raise OSError('injected failure after partial archive publication')

                    with replace(archive, 'write_archive', fail_write):
                        rejects(scenario, lambda: coordinator.apply('archive'))
                    archive.unchanged(target, before)
                elif scenario == 'verification-failure':
                    def fail_verification(*args):
                        raise RuntimeError('injected archive verification failure')

                    with replace(archive, 'verify_archive', fail_verification):
                        rejects(scenario, lambda: coordinator.apply('archive'))
                    archive.unchanged(target, before)
                else:
                    original_write = coordinator.write_json

                    def fail_journal(path, record):
                        if record.get('status') == 'verified archive; retiring originals' and record.get('retired_files', 0) >= 1000:
                            raise OSError('injected retirement journal failure')
                        original_write(path, record)

                    with replace(coordinator, 'write_json', fail_journal):
                        rejects(scenario, lambda: coordinator.apply('archive'))
                    require(len(list(target.rglob('*'))) > 0, 'interruption did not preserve partial state')
                    archive_path = coordinator.BASE / 'archive/cache.zip'
                    archive.verify_archive(archive_path, prepared)
                    archive.restore(archive_path, prepared, root / 'recovered')
                    archive.unchanged(root / 'recovered', before, restored=True)
                if scenario != 'success':
                    rejects(scenario + ' automatic retry', lambda: coordinator.apply('archive'))
                    rejects(scenario + ' new identity retry', lambda: coordinator.prepare('retry', 'fixture', None))
                require(sha(outside) == outside_sha, 'outside evidence changed')
                coordination.append(dict(scenario=scenario,
                    status=json.loads((coordinator.BASE / 'archive/status.json').read_text())['status'],
                    evidence_preserved=True))
        legacy = ROOT / '.work/runs/cache-archive-qualification-03/cache.zip'
        with zipfile.ZipFile(legacy) as prior:
            legacy_manifest = json.loads(prior.read('manifest.json'))
        require('root_xattrs' not in legacy_manifest, 'expected the earlier archive layout')
        archive.verify_archive(legacy, legacy_manifest)
        archive.restore(legacy, legacy_manifest, raw / 'legacy-restored')
        root_only = ROOT / '.work/runs/cache-archive-qualification-05/cache.zip'
        with zipfile.ZipFile(root_only) as prior:
            root_only_manifest = json.loads(prior.read('manifest.json'))
        require('directory_xattrs' not in root_only_manifest, 'expected the root-only archive layout')
        archive.restore(root_only, root_only_manifest, raw / 'root-only-restored')
        require(len(rejected) == (44 if sys.platform == 'darwin' else 43),
                f'unexpected rejection count: {len(rejected)}')
        output.mkdir()
        write_json(output / 'summary.json', dict(status='passed', rejected=rejected, coordinator_cases=coordination,
            restored_payloads=len(manifest['groups']), restored_paths=sum(len(g['paths']) for g in manifest['groups']),
            hardlinks_verified=True, timestamps_and_modes_verified=True, outside_evidence_preserved=True,
            root_attributes_verified=manifest.get('root_xattrs'), legacy_archive_verified=True,
            directory_attributes_verified=manifest.get('directory_xattrs'), root_only_archive_verified=True,
            real_compiler_cache_modified=False, raw=str(raw.relative_to(ROOT)),
            sources={str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), *coordinator.SOURCES]}))
        print(json.dumps(dict(status='passed', rejections=len(rejected), coordinator_cases=len(coordination))))


if __name__ == '__main__':
    main()
