#!/usr/bin/env python3
"""Retain references for the static purity review, without compiler execution."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

from prepare import BASE, HERE, require, sha

COMPILER = Path('/Users/danluu/dev/rustc-hir-capture-check-20260913')
REGISTRY = Path('/Users/danluu/.cargo/registry')
PACKAGE = 'rustc-stable-hash-0.1.2'
PACKAGE_SHA = '781442f29170c5c93b7185ad559492601acdc71d5bb0706f5868094f45cfcd08'
GIT_PATHS = [
    'Cargo.lock', 'compiler/rustc_session/src/options.rs',
    'compiler/rustc_session/src/config.rs', 'compiler/rustc_session/src/utils.rs',
    'compiler/rustc_target/src/spec/mod.rs', 'compiler/rustc_target/src/spec/tuple.rs',
    'compiler/rustc_span/src/lib.rs', 'compiler/rustc_span/src/edition.rs',
    'compiler/rustc_lint_defs/src/lib.rs', 'compiler/rustc_abi/src/lib.rs',
    'compiler/rustc_ast/src/attr/version.rs', 'compiler/rustc_feature/src/lib.rs',
    'compiler/rustc_structures/src/crate_type.rs',
    'compiler/rustc_structures/src/native_lib_kind.rs',
    'compiler/rustc_structures/src/sanitizer_set.rs',
    'compiler/rustc_structures/src/collapse_macro_debug_info.rs',
    'compiler/rustc_data_structures/src/stable_hash.rs',
    'compiler/rustc_hashes/src/lib.rs',
    'library/std/src/path.rs', 'library/std/src/ffi/os_str.rs',
]


def main():
    require(sys.dont_write_bytecode and not sys.flags.optimize, 'Python -B required')
    destination = HERE / 'purity-01'
    require(not destination.exists(), 'preserve existing purity proof')
    files = {}
    for name in GIT_PATHS:
        data = subprocess.check_output(['git', '--no-optional-locks', '-C', str(COMPILER),
                                        'show', BASE + ':' + name])
        files[name] = dict(bytes=len(data), sha256=sha(data),
            git_blob=hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest())
        if name == 'Cargo.lock':
            require(PACKAGE_SHA.encode() in data, 'hasher checksum not present in pinned lock')
    archive = REGISTRY / 'cache/index.crates.io-1949cf8c6b5b557f' / (PACKAGE + '.crate')
    packed = archive.read_bytes()
    require(len(packed) < 128 * 1024 and sha(packed) == PACKAGE_SHA, 'qualified package differs')
    # Full gzip read also verifies its trailer. No extraction into the registry.
    unpacked = gzip.decompress(packed)
    require(len(unpacked) < 1024 * 1024, 'hasher archive bound')
    saved = {}
    with tarfile.open(fileobj=io.BytesIO(unpacked), mode='r:') as source:
        for name in ['src/lib.rs', 'src/stable_hasher.rs', 'src/sip128.rs', 'src/int_overflow.rs']:
            member = source.getmember(PACKAGE + '/' + name)
            require(member.isfile(), 'hasher source must be ordinary')
            data = source.extractfile(member).read()
            path = REGISTRY / 'src/index.crates.io-1949cf8c6b5b557f' / PACKAGE / name
            require(path.read_bytes() == data, 'inspected hasher differs from package')
            saved[name] = data
    destination.mkdir()
    for name, data in saved.items():
        path = destination / PACKAGE / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as output:
            output.write(data)
    result = dict(status='static-source-reviewed-rust-controls-unrun', base_commit=BASE,
        review_sha256=sha((HERE / 'HASH-PURITY.md').read_bytes()),
        review_producer_sha256=sha(Path(__file__).read_bytes()),
        candidate_manifest_sha256=sha((HERE / 'artifacts-01/manifest.json').read_bytes()),
        git_sources=files, hasher_package=dict(name=PACKAGE, archive=str(archive),
            bytes=len(packed), sha256=PACKAGE_SHA, gzip_full_eof_checked=True),
        retained_hasher_sources={name: dict(bytes=len(data), sha256=sha(data))
                                 for name, data in saved.items()},
        conclusion='Audited hash path reads immutable stored values and local deterministic hasher state.',
        compiler_commands=0, rust_test_commands=0, benchmark_commands=0)
    data = (json.dumps(result, sort_keys=True, indent=2) + '\n').encode()
    with (destination / 'source-references.json').open('xb') as output:
        output.write(data)
    print(json.dumps(dict(proof=str(destination / 'source-references.json'), sha256=sha(data))))


if __name__ == '__main__':
    main()
