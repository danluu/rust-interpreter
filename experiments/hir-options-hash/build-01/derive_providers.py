#!/usr/bin/env python3
"""Read-only provider derivation; writes only a new proposal in this packet."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tomllib

HERE = Path(__file__).resolve().parent
SOURCE = Path('/Users/danluu/dev/rustc-hir-capture-check-20260913')
BASE = '7efc0d9484da82cd327deb3b48616f8ec81eaf8d'
REGISTRY = Path('/Users/danluu/.cargo/registry')
REGISTRY_KEY = 'index.crates.io-1949cf8c6b5b557f'
LOCKS = ['Cargo.lock', 'src/bootstrap/Cargo.lock', 'library/Cargo.lock']
PATTERN = re.compile(rb'/Users/danluu/\.cargo/registry/src/index\.crates\.io-1949cf8c6b5b557f/([A-Za-z0-9_.+\-]+)/')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def ordinary(path):
    s = path.lstat()
    assert stat.S_ISREG(s.st_mode) and path.resolve(strict=True) == path
    data = path.read_bytes()
    after = path.lstat()
    assert (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns) == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
    return data, dict(path=str(path), bytes=len(data), sha256=sha(data),
        stamp=[s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_nlink])


def index_relative(name):
    if len(name) == 1:
        return '1/' + name
    if len(name) == 2:
        return '2/' + name
    if len(name) == 3:
        return '3/' + name[0] + '/' + name
    return name[:2] + '/' + name[2:4] + '/' + name


def main():
    assert sys.dont_write_bytecode and not sys.flags.optimize
    output = HERE / 'provider-proposal-01.json'
    assert not output.exists() and not output.is_symlink()
    locks, packages = {}, {}
    for name in LOCKS:
        data, locks[name] = ordinary(SOURCE / name)
        blob = subprocess.check_output(['/usr/bin/git', '--no-optional-locks', '-C', str(SOURCE), 'show', BASE + ':' + name])
        assert data == blob
        for p in tomllib.loads(data.decode())['package']:
            if 'source' not in p:
                continue
            assert p['source'] == 'registry+https://github.com/rust-lang/crates.io-index'
            key = p['name'] + '-' + p['version']
            value = dict(name=p['name'], version=p['version'], checksum=p['checksum'])
            assert key not in packages or packages[key] == value
            packages[key] = value
    index, archives = {}, {}
    for name in sorted({p['name'] for p in packages.values()}):
        path = REGISTRY / 'index' / REGISTRY_KEY / '.cache' / index_relative(name)
        data, record = ordinary(path)
        entries = {}
        for part in data.split(b'\0'):
            if part.startswith(b'{'):
                row = json.loads(part)
                assert row['name'] == name and row['vers'] not in entries
                entries[row['vers']] = row['cksum']
        for package in packages.values():
            if package['name'] == name:
                assert entries.get(package['version']) == package['checksum']
        index[name] = record
    for key, package in sorted(packages.items()):
        path = REGISTRY / 'cache' / REGISTRY_KEY / (key + '.crate')
        if path.exists() or path.is_symlink():
            data, record = ordinary(path)
            assert record['sha256'] == package['checksum']
            archives[key] = record
    config_data, config = ordinary(REGISTRY / 'index' / REGISTRY_KEY / 'config.json')
    assert json.loads(config_data)['dl'] == 'https://static.crates.io/crates'
    historical, referenced = {}, set()
    for root, dirs, files in os.walk(SOURCE / 'build', followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(root) / d).is_symlink())
        for name in sorted(files):
            if not name.endswith('.d'):
                continue
            path = Path(root) / name
            data, record = ordinary(path)
            found = {v.decode('ascii') for v in PATTERN.findall(data)}
            if found:
                historical[str(path)] = dict(**record, packages=sorted(found))
                referenced.update(found)
    required = sorted(referenced & packages.keys())
    unknown = sorted(referenced - packages.keys())
    missing = sorted(set(required) - archives.keys())
    result = dict(schema_version=1, status='source-only-provider-proposal', compiler_source=str(SOURCE),
        base_commit=BASE, locks=locks, packages=packages, sparse_index=index, sparse_index_config=config,
        archives=archives, absent_locked_archives=sorted(packages.keys() - archives.keys()),
        historical_depinfo=historical, historical_locked_packages=required,
        historical_packages_outside_current_locks=unknown, historical_required_archives_missing=missing,
        archive_bytes=sum(r['bytes'] for r in archives.values()),
        index_bytes=sum(r['bytes'] for r in index.values()) + config['bytes'],
        depinfo_bytes=sum(r['bytes'] for r in historical.values()),
        limitation='Historical dep-info is evidence of prior consumed packages, not proof every future target dependency is present. All495 locked package-name index records and every available checksum-matching locked archive are proposed; missing archive demand must fail offline.',
        source_acquired=False, provider_files_copied=0, compiler_builds=0,
        generator_sha256=sha(Path(__file__).read_bytes()))
    with output.open('x') as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print(json.dumps(dict(path=str(output), sha256=sha(output.read_bytes()), packages=len(packages),
        indexes=len(index), archives=len(archives), historical_packages=len(required),
        historical_outside=unknown, required_missing=missing, archive_bytes=result['archive_bytes'],
        index_bytes=result['index_bytes'], depinfo_files=len(historical)), indent=2))


if __name__ == '__main__':
    main()
