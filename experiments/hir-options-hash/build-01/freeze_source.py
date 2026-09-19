#!/usr/bin/env python3
"""Freeze a three-file candidate build patch; never acquire/build a compiler."""
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
OWNER = HERE.parents[2]
PACKET = HERE.parent
COMPILER = Path('/Users/danluu/dev/rustc-hir-capture-check-20260913')
BASE = '7efc0d9484da82cd327deb3b48616f8ec81eaf8d'
IDENTITY = 'compiler/rustc_ast_lowering/src/body_cache/source_identity.rs'
CONTEXT = 'compiler/rustc_middle/src/ty/context.rs'
BODY = 'compiler/rustc_ast_lowering/src/body_cache/mod.rs'
OLD_IDENTITY = 'a6cf8a739f3c7a29707bacb4f12ecb575700f72bc41004260f99951f85ecf13b'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(root, *args):
    return subprocess.check_output(['/usr/bin/git', '--no-optional-locks', '-C', str(root), *args])


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def main():
    assert sys.dont_write_bytecode and not sys.flags.optimize
    output = HERE / 'source-01'
    assert not output.exists() and not output.is_symlink()
    assert git(COMPILER, 'rev-parse', 'HEAD').decode().strip() == BASE
    assert not git(COMPILER, 'diff', 'HEAD', '--')
    prior_bytes = git(OWNER, 'show', 'HEAD:experiments/hir-arena-identity-upgrade/inputs/patch.json')
    prior = json.loads(prior_bytes)
    assert prior['source_identity'] == OLD_IDENTITY and len(prior['files']) == 25
    before = {}
    for name, record in prior['files'].items():
        data = git(COMPILER, 'show', BASE + ':' + name)
        assert digest(data) == record['after_sha256']
        assert (COMPILER / name).read_bytes() == data
        before[name] = data
    original_hashes = {n: digest(b) for n, b in before.items() if n != IDENTITY}
    assert digest(json.dumps(original_hashes, sort_keys=True, separators=(',', ':')).encode()) == OLD_IDENTITY
    before[CONTEXT] = git(COMPILER, 'show', BASE + ':' + CONTEXT)
    original_packet = json.loads((PACKET / 'artifacts-01/manifest.json').read_bytes())
    assert original_packet['base_commit'] == BASE
    after = dict(before)
    for name in [CONTEXT, BODY]:
        assert digest(before[name]) == original_packet['base_files'][name]['sha256']
        after[name] = (PACKET / 'artifacts-01/candidate' / name).read_bytes()
        assert digest(after[name]) == original_packet['candidate_files'][name]['sha256']
    closure = {n: digest(b) for n, b in after.items() if n != IDENTITY}
    identity = digest(json.dumps(closure, sort_keys=True, separators=(',', ':')).encode())
    assert len(closure) == 25
    after[IDENTITY] = f'pub(super) const SOURCE_IDENTITY: &str = "{identity}";\n'.encode()
    changed = sorted(n for n in before if before[n] != after[n])
    assert changed == sorted([CONTEXT, BODY, IDENTITY])
    pieces = []
    for name in changed:
        pieces.append(f'diff --git a/{name} b/{name}\n')
        pieces.extend(difflib.unified_diff(before[name].decode().splitlines(keepends=True),
            after[name].decode().splitlines(keepends=True), fromfile='a/' + name, tofile='b/' + name, n=5))
    patch = ''.join(pieces).encode()
    write(output / 'candidate.patch', patch)
    write(output / 'inherited-manifest.json', prior_bytes)
    for name, data in after.items():
        write(output / 'closure' / name, data)
    for name in changed:
        write(output / 'base' / name, before[name])
    manifest = dict(schema_version=1, status='source-only-uncompiled-unrun', base_commit=BASE,
        old_identity=OLD_IDENTITY, source_identity=identity, acyclic_identity_files=closure,
        complete_closure_files={n: digest(b) for n, b in after.items()}, changed_files=changed,
        before_hashes={n: digest(before[n]) for n in changed}, patch_sha256=digest(patch),
        inherited_manifest_sha256=digest(prior_bytes), original_packet_sha256=digest((PACKET / 'artifacts-01/manifest.json').read_bytes()),
        generator_sha256=digest(Path(__file__).read_bytes()), checkout_created=False,
        compiler_builds=0, qualification_run=False, adopted=False)
    write(output / 'manifest.json', (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode())
    assert git(COMPILER, 'rev-parse', 'HEAD').decode().strip() == BASE
    assert not git(COMPILER, 'diff', 'HEAD', '--')
    print(json.dumps(dict(manifest=str(output / 'manifest.json'), manifest_sha256=digest((output / 'manifest.json').read_bytes()),
        patch_sha256=digest(patch), source_identity=identity, source_only=True), indent=2))


if __name__ == '__main__':
    main()
