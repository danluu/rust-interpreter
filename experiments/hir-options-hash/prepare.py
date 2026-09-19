#!/usr/bin/env python3
"""Produce an uncompiled patch from immutable compiler Git blobs only."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = '7efc0d9484da82cd327deb3b48616f8ec81eaf8d'
CONTEXT = 'compiler/rustc_middle/src/ty/context.rs'
BODY = 'compiler/rustc_ast_lowering/src/body_cache/mod.rs'
EXPECTED = {
    CONTEXT: '54b34717e12bb2af80ab0a0a6dabc0e4b841fbf9588c619ceb60c94b8314519d',
    BODY: '08fa352bcb32db37baf01e0428d3c3bc6beb68ba5007c2b2528dd051cba82198',
}
REFERENCES = [CONTEXT, BODY,
    'compiler/rustc_session/src/options.rs', 'compiler/rustc_session/src/config.rs',
    'compiler/rustc_session/src/session.rs', 'compiler/rustc_interface/src/interface.rs',
    'compiler/rustc_driver_impl/src/lib.rs', 'compiler/rustc_data_structures/src/sync.rs',
    'compiler/rustc_data_structures/src/sync/parallel.rs',
    'compiler/rustc_middle/src/query/caches.rs', 'compiler/rustc_hashes/src/lib.rs',
    'compiler/rustc_ast_lowering/src/body_cache/source_identity.rs',
    'tests/run-make/hir-body-cache-capture/rmake.rs',
    'tests/run-make/hir-body-cache-capture/fixture.rs',
    'compiler/rustc_interface/src/tests.rs']


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def replace_once(text, old, new):
    require(text.count(old) == 1, 'missing or repeated source anchor: ' + old[:80])
    return text.replace(old, new)


def transform(base):
    text = base[CONTEXT].decode()
    text = replace_once(text, 'use rustc_hir::attrs::lang_items::LangItem;\n',
        'use rustc_hashes::Hash64;\nuse rustc_hir::attrs::lang_items::LangItem;\n')
    text = replace_once(text, "pub struct GlobalCaches<'tcx> {\n",
        "pub struct GlobalCaches<'tcx> {\n"
        '    /// Options are immutable for the lifetime of the owning GlobalCtxt.\n'
        '    /// Keep this cache local to that context, including in multi-run drivers.\n'
        '    incremental_options_hash: OnceLock<Hash64>,\n\n')
    text = replace_once(text,
        "impl<'tcx> TyCtxt<'tcx> {\n    pub fn has_typeck_results(self, def_id: LocalDefId) -> bool {\n",
        "impl<'tcx> TyCtxt<'tcx> {\n"
        '    /// The complete incremental option hash for this immutable context.\n'
        '    /// Unlike the crate hash, this includes TRACKED_NO_CRATE_HASH options.\n'
        '    pub fn incremental_options_hash(self) -> Hash64 {\n'
        '        *self.caches.incremental_options_hash.get_or_init(|| {\n'
        '            self.sess.opts.dep_tracking_hash(false)\n'
        '        })\n'
        '    }\n\n'
        '    pub fn has_typeck_results(self, def_id: LocalDefId) -> bool {\n')
    body = replace_once(base[BODY].decode(),
        '    tcx.sess.opts.dep_tracking_hash(false).as_u64().encode(&mut encoder);\n',
        '    tcx.incremental_options_hash().as_u64().encode(&mut encoder);\n')
    return {CONTEXT: text.encode(), BODY: body.encode()}


def patch_bytes(before, after):
    pieces = []
    for name in sorted(after):
        pieces.append(f'diff --git a/{name} b/{name}\n')
        pieces.extend(difflib.unified_diff(before[name].decode().splitlines(keepends=True),
            after[name].decode().splitlines(keepends=True), fromfile='a/' + name,
            tofile='b/' + name, n=5))
    return ''.join(pieces).encode()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler-git', type=Path, required=True)
    args = parser.parse_args()
    require(sys.dont_write_bytecode and not sys.flags.optimize, 'use Python -B without -O')
    compiler = args.compiler_git.resolve(strict=True)
    def git(*argv):
        return subprocess.check_output(['git', '--no-optional-locks', '-C', str(compiler), *argv])
    require(git('rev-parse', BASE + '^{commit}').decode().strip() == BASE, 'wrong compiler base')
    original = {name: git('show', BASE + ':' + name) for name in REFERENCES}
    require(sum(map(len, original.values())) < 2 * 2**20, 'source proof bound')
    for name, expected in EXPECTED.items():
        require(sha(original[name]) == expected, 'base source differs: ' + name)
    updated = transform(original)
    patch = patch_bytes(original, updated)
    destination = HERE / 'artifacts-01'
    require(not destination.exists() and not destination.is_symlink(), 'preserve previous artifact')
    destination.mkdir()
    base_records = {}
    for name, data in original.items():
        write(destination / 'base' / name, data)
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        require(git('rev-parse', BASE + ':' + name).decode().strip() == blob, 'Git blob mismatch')
        base_records[name] = dict(bytes=len(data), sha256=sha(data), git_blob=blob)
    for name, data in updated.items():
        write(destination / 'candidate' / name, data)
    write(destination / 'candidate.patch', patch)
    sources = [HERE / name for name in ['prepare.py', 'verify.py', 'README.md', 'QUALIFICATION.md',
        'controls/driver.rs', 'controls/fixture.rs']]
    manifest = dict(schema_version=1, status='source-only-uncompiled-unrun',
        base_commit=BASE, compiler_git_read_only=str(compiler),
        integration_checkpoint=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
        base_files=base_records, candidate_files={name: dict(bytes=len(data), sha256=sha(data))
            for name, data in updated.items()}, patch=dict(bytes=len(patch), sha256=sha(patch)),
        experiment_sources={str(p.relative_to(HERE)): sha(p.read_bytes()) for p in sources},
        production_code_files_changed=2, compiler_checkout_modified=False,
        builds_run=False, rust_controls_run=False, benchmarks_run=False, adopted=False,
        expected_benefit='Eliminate repeated session-option hashing; cost and end-to-end benefit unmeasured.',
        unchanged_contracts=['exact false option hash', 'as_u64 varint key encoding',
            'eligibility gate', 'JSON decode/checksum', 'Current/tree/journal validation',
            'hit recapture and poststate verification', 'strict compiler diagnostics'],
        source_identity_update_required_before_build=True,
        historical_source_identity='a6cf8a739f3c7a29707bacb4f12ecb575700f72bc41004260f99951f85ecf13b')
    data = (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode()
    write(destination / 'manifest.json', data)
    print(json.dumps(dict(manifest=str(destination / 'manifest.json'), manifest_sha256=sha(data),
                         patch_sha256=sha(patch), source_only=True)))


if __name__ == '__main__':
    main()
