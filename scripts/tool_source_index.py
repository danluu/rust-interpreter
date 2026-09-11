#!/usr/bin/env python3
"""Recompute legacy tool keys from Git objects and verify installed binaries."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
COMMITS = ['32f5e2f', '6b2c61f', 'a2a0e04', '09de2a9', '26833c3']


def index(ref):
    commit = subprocess.check_output(['git', 'rev-parse', ref], cwd=ROOT, text=True).strip()
    data = subprocess.check_output(['git', 'archive', commit, 'Cargo.toml', 'Cargo.lock',
                                   'crates/bytecode', 'crates/mir-export'], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        contents = {m.name: archive.extractfile(m).read() for m in archive if m.isfile()}
    paths = ['Cargo.toml', 'Cargo.lock']
    for crate in ['bytecode', 'mir-export']:
        prefix = 'crates/' + crate + '/'
        # Match sorted(Path.rglob(...)), which orders path components. String
        # ordering differs for e.g. jit.rs versus jit/limit_tests.rs.
        paths += sorted((p for p in contents if p.startswith(prefix) and p.endswith('.rs')), key=Path)
        paths.append(prefix + 'Cargo.toml')
    digest = hashlib.sha256()
    files = {}
    for path in paths:
        digest.update(path.encode() + b'\0' + contents[path])
        files[path] = hashlib.sha256(contents[path]).hexdigest()
    key = digest.hexdigest()
    directory = ROOT / '.work/interpreter-tools' / key
    binaries = None
    if (directory / 'ready.json').exists():
        binaries = json.loads((directory / 'ready.json').read_text())
        if set(binaries) != {'rust-interp-vm', 'rust-interp-mir-export'}:
            raise RuntimeError('unexpected ready schema')
        for name, expected in binaries.items():
            if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
                raise RuntimeError('installed binary hash mismatch: ' + key + '/' + name)
    return dict(commit=commit, tool_key=key, files=files, binaries=binaries)


if __name__ == '__main__':
    result = dict(schema_version=1, key_algorithm='legacy source-only SHA256, with pathlib path ordering',
        toolchain='nightly-2026-09-08', target='aarch64-apple-darwin',
        note='These source keys are reconstructed from Git. Compiler/target are recorded separately; the legacy key itself does not include compiler identity. This is not an audit of all historical keys.',
        builds=[index(ref) for ref in COMMITS])
    (ROOT / 'benchmarks/tool-builds.json').write_text(json.dumps(result, indent=2) + '\n')
    for row in result['builds']:
        print(row['commit'][:8], row['tool_key'], 'binaries verified' if row['binaries'] else 'not installed')
