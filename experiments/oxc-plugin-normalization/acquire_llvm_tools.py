#!/usr/bin/env python3
"""Acquire/inspect one official matching component; do not install or extract it."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tarfile
import time
import tomllib

OWNER = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PLAN = HERE / 'llvm-tools-acquisition-plan-01.json'
FROZEN = OWNER / '.work/oxc-llvm-tools-acquisition-source-01/inputs.json'
WORK = OWNER / '.work/oxc-llvm-tools-acquisition-01'


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            result.update(block)
    return result.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def main(expected):
    require(sha(FROZEN) == expected, 'LLVM component freeze differs')
    frozen, plan = read(FROZEN), read(PLAN)
    require(frozen['owner'] == plan['owner'] == str(OWNER), 'foreign LLVM component stage')
    def guard():
        require(sha(FROZEN) == expected, 'LLVM component freeze changed')
        for path, checksum in frozen['files'].items():
            require(sha(path) == checksum, 'LLVM component input changed: ' + path)
        require(str(Path(sys.executable).resolve()) == frozen['python']['path'] and
                sha(sys.executable) == frozen['python']['sha256'], 'LLVM component Python changed')
    guard()
    spec = importlib.util.spec_from_file_location('oxc_llvm_owned', OWNER / 'experiments/stable-cgu/owned_stage.py')
    owned = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owned)
    require(not WORK.exists() and not WORK.is_symlink(), 'LLVM component output must be fresh')
    WORK.mkdir()
    record = dict(schema_version=1, owner=str(OWNER), pid=os.getpid(), parent_pid=os.getppid(),
                  status='waiting', started_at=time.time(), freeze_sha256=expected, children=[],
                  installed=False, extracted=False, native_compilation=False, benchmark=False)
    def save():
        owned.write(WORK / 'receipt.json', record)
    def capacity():
        return owned.disk(OWNER, 9)
    save()
    try:
        with owned.workload_lock(plan['canonical_lock'], 600):
            record.update(status='running', admitted_at=time.time(), free_bytes_before=owned.disk(OWNER, 16))
            save()
            manifest = tomllib.loads(Path(plan['distribution_manifest']).read_text())
            component = manifest['pkg']['llvm-tools-preview']['target']['aarch64-apple-darwin']
            require(manifest['date'] == '2026-09-03' and
                    manifest['pkg']['rustc']['version'] == '1.98.1 (48a229cea 2026-09-01)' and
                    component['available'] and component['xz_url'] == plan['url'] and
                    component['xz_hash'] == plan['archive_sha256'], 'official component identity differs')
            require(sum(Path(p).stat().st_size for p in frozen['files']) <= 16*2**20, 'component evidence input bound')
            for path, checksum in frozen['files'].items():
                destination = WORK / 'inputs' / path.lstrip('/')
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open('xb') as output:
                    output.write(Path(path).read_bytes())
                require(sha(destination) == checksum, 'component frozen copy differs')
            for label in ['curl-identity', 'download']:
                guard()
                capacity()
                command = plan['commands'][label]
                out = WORK / 'commands' / label
                try:
                    owned.run(command, cwd=WORK, env=plan['environment'], out=out, capacity_root=OWNER)
                finally:
                    if (out / 'receipt.json').exists():
                        record['children'].append(dict(label=label, path=str(out), receipt=read(out/'receipt.json')))
                        save()
                guard()
                capacity()
            archive = WORK / 'llvm-tools.tar.xz'
            require(archive.resolve(strict=True) == archive and archive.is_file() and not archive.is_symlink()
                    and archive.stat().st_size <= plan['archive_max_bytes'] and sha(archive) == plan['archive_sha256'],
                    'downloaded official component archive differs')
            prefix = 'llvm-tools-1.98.1-aarch64-apple-darwin'
            members, folded, text_files, total = {}, set(), {}, 0
            with tarfile.open(archive, 'r:xz') as stream:
                for member in stream:
                    capacity()
                    name = member.name.rstrip('/') if member.isdir() else member.name
                    parts = name.split('/')
                    require(parts[0] == prefix and all(p not in ['', '.', '..'] for p in parts)
                            and '\\' not in name and '\x00' not in name, 'invalid LLVM component archive path')
                    require(name not in members and name.casefold() not in folded, 'duplicate LLVM component member')
                    folded.add(name.casefold())
                    require(member.isfile() or member.isdir(), 'LLVM component links/special entries unsupported')
                    require(0 <= member.size <= 256*2**20 and len(members) < 10000, 'LLVM component member bound')
                    total += member.size
                    require(total <= plan['unpacked_max_bytes'], 'LLVM component unpacked byte bound')
                    proof = dict(kind='directory' if member.isdir() else 'file', bytes=member.size, mode=member.mode)
                    if member.isfile():
                        digest = hashlib.sha256()
                        retain = parts[-1] in ['components', 'manifest.in', 'rust-installer-version']
                        require(not retain or member.size <= 64*1024, 'LLVM component metadata bound')
                        payload = bytearray()
                        with stream.extractfile(member) as source:
                            for block in iter(lambda: source.read(1024**2), b''):
                                digest.update(block)
                                if retain:
                                    payload.extend(block)
                        proof['sha256'] = digest.hexdigest()
                        if retain:
                            text_files[name] = payload.decode()
                    members[name] = proof
                tail = 0
                while block := stream.fileobj.read(1024**2):
                    tail += len(block)
                    require(tail <= 16*2**20, 'LLVM component trailing data bound')
            components = text_files[prefix + '/components'].splitlines()
            require(len(components) == 1 and re.fullmatch(r'[a-zA-Z0-9_-]+', components[0]), 'unexpected component list')
            component_root = prefix + '/' + components[0] + '/'
            declared = text_files[component_root + 'manifest.in'].splitlines()
            provider = 'lib/rustlib/aarch64-apple-darwin/lib/libLLVM.dylib'
            require('file:' + provider in declared and members[component_root + provider]['kind'] == 'file',
                    'official LLVM component does not declare the missing host-library provider')
            require(all(line.startswith('file:') for line in declared), 'unexpected component installation operation')
            declared_names = [line.removeprefix('file:') for line in declared]
            require(len(declared_names) == len(set(declared_names)) and
                    {name.removeprefix(component_root) for name, row in members.items()
                     if name.startswith(component_root) and row['kind'] == 'file'} == set(declared_names) | {'manifest.in'},
                    'component payload membership differs from installation manifest')
            owned.write(WORK / 'component-proof.json', dict(archive_sha256=sha(archive), members=members,
                metadata=text_files, provider=provider, provider_record=members[component_root + provider],
                component=components[0], declared_files=declared_names, unpacked_bytes=total))
            allocated = sum(path.lstat().st_blocks*512 for path in WORK.rglob('*'))
            require(allocated <= plan['allocation_budget_bytes'], 'LLVM component allocation bound')
            guard()
            record.update(status='passed', component=components[0], members=len(members),
                          allocated_bytes=allocated, archive_bytes=archive.stat().st_size,
                          provider_record=members[component_root+provider], free_bytes_after=capacity())
    except BaseException as error:
        record.update(status='failed', error=repr(error))
        raise
    finally:
        record['finished_at'] = time.time()
        save()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--frozen-sha256', required=True)
    main(parser.parse_args().frozen_sha256)
