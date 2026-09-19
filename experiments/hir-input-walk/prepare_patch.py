#!/usr/bin/env python3
"""Prepare an independent source-only candidate from exact compiler Git blobs."""
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
COMPILER = Path('/Users/danluu/dev/rustc-hir-capture-check-20260913')
BASE = '7efc0d9484da82cd327deb3b48616f8ec81eaf8d'
INPUT = 'compiler/rustc_ast_lowering/src/body_cache/input.rs'
BODY = 'compiler/rustc_ast_lowering/src/body_cache/mod.rs'
IDENTITY = 'compiler/rustc_ast_lowering/src/body_cache/source_identity.rs'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(root, *args):
    return subprocess.check_output(['/usr/bin/git', '--no-optional-locks', '-C', str(root), *args])


def replace_once(source, old, new):
    assert source.count(old) == 1, old
    return source.replace(old, new)


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
    inherited_bytes = git(ROOT, 'show', 'HEAD:experiments/hir-arena-identity-upgrade/inputs/patch.json')
    inherited = json.loads(inherited_bytes)
    before = {}
    for name, row in inherited['files'].items():
        data = git(COMPILER, 'show', BASE + ':' + name)
        assert sha(data) == row['after_sha256'] and (COMPILER / name).read_bytes() == data
        before[name] = data
    prior_hashes = {n: sha(data) for n, data in before.items() if n != IDENTITY}
    assert sha(json.dumps(prior_hashes, sort_keys=True, separators=(',', ':')).encode()) == inherited['source_identity']

    source = before[INPUT].decode()
    source = replace_once(source,
        '//! Closed structural/resolved body gate. No lowering, queries, arena writes or cache.\n',
        '//! Closed structural/resolved body gate. No lowering or persistent-cache access.\n'
        '//! Literal validation can intern decoded strings in the current session.\n')
    source = replace_once(source, "struct Walk<'a,'tcx> {", """/// The normalized input and node order originate in the same completed Walk.
/// Private fields prevent callers from pairing independently generated values.
pub(super) struct ProbedInput {
    probe: Probe,
    ordered: Vec<(ast::NodeId, bool)>,
}
impl ProbedInput {
    pub(super) fn into_parts(self) -> (Probe, Vec<(ast::NodeId, bool)>) {
        (self.probe, self.ordered)
    }
}
struct Walk<'a,'tcx> {""")
    source = replace_once(source,
        "span:Span,f:&ast::Fn,role:&'static str)->Outcome<Probe> {",
        "span:Span,f:&ast::Fn,role:&'static str)->Outcome<ProbedInput> {")
    source = replace_once(source,
        '    Ok(Probe{input:Input{owner:tcx.def_path_hash(current.def_id.to_def_id()),file:file.stable_id,\n',
        '    Ok(ProbedInput { probe: Probe{input:Input{owner:tcx.def_path_hash(current.def_id.to_def_id()),file:file.stable_id,\n')
    source = replace_once(source,
        '        trait_entries:w.trait_entries,trait_candidates:w.trait_candidates,external_resolutions:w.external_resolutions})\n',
        '        trait_entries:w.trait_entries,trait_candidates:w.trait_candidates,external_resolutions:w.external_resolutions},\n'
        '        ordered: w.ordered })\n')
    marker = '\n// Appended after the exact qualified gate bytes by prepare_patch.py.'
    assert source.count(marker) == 1
    removed = source[source.index(marker):]
    assert removed.count('pub(super) fn current_nodes') == 1 and source.endswith('    Ok(w.ordered)\n}\n')
    source = source[:source.index(marker)]
    body = replace_once(before[BODY].decode(),
        '    let probe = input::probe(tcx, resolver, owner, span, function, role).ok()?;\n'
        '    let ast_nodes = input::current_nodes(tcx, resolver, owner, span, function, &probe).ok()?;\n',
        '    let (probe, ast_nodes) = input::probe(tcx, resolver, owner, span, function, role).ok()?.into_parts();\n')
    after = dict(before)
    after[INPUT] = source.encode()
    after[BODY] = body.encode()
    closure = {n: sha(data) for n, data in after.items() if n != IDENTITY}
    identity = sha(json.dumps(closure, sort_keys=True, separators=(',', ':')).encode())
    after[IDENTITY] = f'pub(super) const SOURCE_IDENTITY: &str = "{identity}";\n'.encode()
    changed = sorted(n for n in before if before[n] != after[n])
    assert changed == sorted([INPUT, BODY, IDENTITY])
    pieces = []
    for name in changed:
        pieces.append(f'diff --git a/{name} b/{name}\n')
        pieces.extend(difflib.unified_diff(before[name].decode().splitlines(keepends=True),
            after[name].decode().splitlines(keepends=True), fromfile='a/' + name, tofile='b/' + name, n=5))
        write(output / 'base' / name, before[name])
        write(output / 'candidate' / name, after[name])
    patch = ''.join(pieces).encode()
    write(output / 'candidate.patch', patch)
    write(output / 'inherited-manifest.json', inherited_bytes)
    proof_files = {}
    for name in [INPUT, BODY, 'compiler/rustc_ast/src/util/literal.rs',
                 'compiler/rustc_span/src/symbol.rs', 'compiler/rustc_span/src/span_encoding.rs',
                 'compiler/rustc_span/src/lib.rs', 'compiler/rustc_middle/src/middle/resolve.rs',
                 'compiler/rustc_middle/src/ty/context.rs', 'compiler/rustc_hir_id/src/definitions.rs',
                 'compiler/rustc_metadata/src/rmeta/decoder.rs']:
        data = git(COMPILER, 'show', BASE + ':' + name)
        assert (COMPILER / name).read_bytes() == data
        write(output / 'proof' / name, data)
        proof_files[name] = sha(data)
    manifest = dict(schema_version=1, status='source-only-uncompiled-unrun', base_commit=BASE,
        source_identity=identity, inherited_identity=inherited['source_identity'],
        changed_files=changed, patch_sha256=sha(patch),
        before_hashes={n: sha(before[n]) for n in changed},
        candidate_hashes={n: sha(after[n]) for n in changed},
        acyclic_identity_files=closure, source_references=proof_files,
        generator_sha256=sha(Path(__file__).read_bytes()), compiler_builds=0,
        qualification_run=False, performance_measurements=0, adopted=False)
    write(output / 'manifest.json', (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode())
    assert git(COMPILER, 'rev-parse', 'HEAD').decode().strip() == BASE
    assert not git(COMPILER, 'diff', 'HEAD', '--')
    print(json.dumps(dict(status=manifest['status'], source_identity=identity,
        patch_sha256=sha(patch), manifest_sha256=sha((output/'manifest.json').read_bytes())), indent=2))


if __name__ == '__main__':
    main()
