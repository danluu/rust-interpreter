#!/usr/bin/env python3
"""Check retained source bytes and apply the patch only to a fresh two-file copy."""
import json
from pathlib import Path
import subprocess
import sys

from prepare import BASE, BODY, CONTEXT, EXPECTED, HERE, ROOT, patch_bytes, require, sha, transform


def main():
    require(sys.dont_write_bytecode and not sys.flags.optimize, 'use Python -B without -O')
    artifacts = HERE / 'artifacts-01'
    manifest = json.loads((artifacts / 'manifest.json').read_bytes())
    require(manifest['base_commit'] == BASE and manifest['production_code_files_changed'] == 2,
            'candidate scope differs')
    original = {}
    for name, expected in manifest['base_files'].items():
        data = (artifacts / 'base' / name).read_bytes()
        require(len(data) == expected['bytes'] and sha(data) == expected['sha256'], 'base differs: ' + name)
        original[name] = data
    for name, digest in EXPECTED.items():
        require(sha(original[name]) == digest, 'unadmitted base')
    for name, expected in manifest['experiment_sources'].items():
        require(sha((HERE / name).read_bytes()) == expected, 'experiment source differs: ' + name)
    updated = transform(original)
    require(set(manifest['candidate_files']) == {CONTEXT, BODY}, 'unexpected candidate file')
    for name, data in updated.items():
        require((artifacts / 'candidate' / name).read_bytes() == data, 'candidate transformation differs')
        require(manifest['candidate_files'][name] == dict(bytes=len(data), sha256=sha(data)), 'candidate digest')
    patch = (artifacts / 'candidate.patch').read_bytes()
    require(patch == patch_bytes(original, updated) and manifest['patch'] == dict(bytes=len(patch), sha256=sha(patch)), 'patch differs')
    scratch = ROOT / '.work/hir-options-hash-patch-check-01'
    require(not scratch.exists() and not scratch.is_symlink(), 'preserve prior verification')
    scratch.mkdir(parents=True)
    for name in updated:
        target = scratch / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(original[name])
    command = ['git', 'apply', '--directory=' + str(scratch.relative_to(ROOT))]
    check = subprocess.run([*command, '--check', str(artifacts / 'candidate.patch')],
                           cwd=ROOT, capture_output=True, check=True)
    applied = subprocess.run([*command, str(artifacts / 'candidate.patch')],
                             cwd=ROOT, capture_output=True, check=True)
    for name, data in updated.items():
        require((scratch / name).read_bytes() == data, 'Git-applied source differs')
    result = dict(status='passed-source-only', base_commit=BASE,
        manifest_sha256=sha((artifacts / 'manifest.json').read_bytes()), patch_sha256=sha(patch),
        retained_base_files=len(original), changed_code_files=2,
        git_check_stdout=check.stdout.decode(), git_check_stderr=check.stderr.decode(),
        git_apply_stdout=applied.stdout.decode(), git_apply_stderr=applied.stderr.decode(),
        scratch=str(scratch), shared_compiler_checkout_modified=False,
        compiler_commands=0, rust_test_commands=0, benchmark_commands=0,
        rust_controls_status='uncompiled-unrun', source_identity_update_required_before_build=True)
    target = artifacts / 'source-verification.json'
    with target.open('x') as stream:
        stream.write(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
