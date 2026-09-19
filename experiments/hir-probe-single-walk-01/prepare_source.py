"""Materialize three isolated source files; never import or execute the compiler."""
from pathlib import Path
import difflib
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
N = X / '.work/hir-options-hash-compiler-01/source'
OLD = ROOT / 'experiments/hir-input-walk/source-01'
MANIFEST = X / 'experiments/hir-options-hash/build-01/source-01/manifest.json'
INPUT = 'compiler/rustc_ast_lowering/src/body_cache/input.rs'
BODY = 'compiler/rustc_ast_lowering/src/body_cache/mod.rs'
IDENTITY = 'compiler/rustc_ast_lowering/src/body_cache/source_identity.rs'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    assert sys.dont_write_bytecode and not sys.flags.optimize
    assert not (HERE / 'base').exists() and not (HERE / 'candidate').exists()
    inherited_bytes = MANIFEST.read_bytes()
    inherited = json.loads(inherited_bytes)
    before = {name: (N / name).read_bytes() for name in inherited['acyclic_identity_files']}
    assert {name: sha(data) for name, data in before.items()} == inherited['acyclic_identity_files']
    encode = lambda rows: json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()
    assert sha(encode(inherited['acyclic_identity_files'])) == inherited['source_identity']
    before[IDENTITY] = (N / IDENTITY).read_bytes()
    assert before[IDENTITY] == ('pub(super) const SOURCE_IDENTITY: &str = "' + inherited['source_identity'] + '";\n').encode()
    # Reuse the existing unqualified constructor design, against exact current bytes.
    old = json.loads((OLD / 'manifest.json').read_bytes())
    assert before[INPUT] == (OLD / 'base' / INPUT).read_bytes()
    new_input = (OLD / 'candidate' / INPUT).read_bytes()
    assert sha(new_input) == old['candidate_hashes'][INPUT]
    old_call = ('    let probe = input::probe(tcx, resolver, owner, span, function, role).ok()?;\n'
                '    let ast_nodes = input::current_nodes(tcx, resolver, owner, span, function, &probe).ok()?;\n')
    new_call = '    let (probe, ast_nodes) = input::probe(tcx, resolver, owner, span, function, role).ok()?.into_parts();\n'
    text = before[BODY].decode()
    assert text.count(old_call) == 1
    after = dict(before)
    after[INPUT] = new_input
    after[BODY] = text.replace(old_call, new_call).encode()
    closure = {name: sha(data) for name, data in after.items() if name != IDENTITY}
    identity = sha(encode(closure))
    after[IDENTITY] = ('pub(super) const SOURCE_IDENTITY: &str = "' + identity + '";\n').encode()
    assert sorted(name for name in before if before[name] != after[name]) == sorted([INPUT, BODY, IDENTITY])
    # The complete walker and original first-pass gate stay byte-identical.
    a, b = before[INPUT].decode(), new_input.decode()
    walk_start = "struct Walk<'a,'tcx> {"
    gate_start = '/// Caller enumerates Fn owners directly from expanded AST;'
    assert a[a.index(walk_start):a.index(gate_start)] == b[b.index(walk_start):b.index(gate_start)]
    assert a[a.index('pub(super) const POLICY:'):a.index(walk_start)] == b[b.index('pub(super) const POLICY:'):b.index('/// The normalized input')]
    gate_a = a[a.index('    if tcx.incr_comp_session'):a.index('    Ok(Probe{')]
    gate_b = b[b.index('    if tcx.incr_comp_session'):b.index('    Ok(ProbedInput {')]
    assert gate_a == gate_b
    assert after[BODY].decode().replace(new_call, old_call) == text
    patch = []
    for name in [INPUT, BODY, IDENTITY]:
        for directory, data in [('base', before[name]), ('candidate', after[name])]:
            path = HERE / directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(data)
        patch.append(f'diff --git a/{name} b/{name}\n')
        patch.extend(difflib.unified_diff(before[name].decode().splitlines(True), after[name].decode().splitlines(True), fromfile='a/'+name, tofile='b/'+name, n=5))
    patch_bytes = ''.join(patch).encode()
    (HERE / 'candidate.patch').write_bytes(patch_bytes)
    (HERE / 'inherited-options-hash-manifest.json').write_bytes(inherited_bytes)
    report = dict(status='source-only-uncompiled-unqualified-unmeasured', source_root=str(N),
        inherited_manifest=dict(path=str(MANIFEST), sha256=sha(inherited_bytes)),
        inherited_identity=inherited['source_identity'], source_identity=identity,
        changed_files=[INPUT, BODY, IDENTITY], before_hashes={n: sha(before[n]) for n in [INPUT, BODY, IDENTITY]},
        candidate_hashes={n: sha(after[n]) for n in [INPUT, BODY, IDENTITY]},
        acyclic_identity_files=closure, patch_sha256=sha(patch_bytes),
        same_entire_walk=True, same_first_gate=True, same_input_encoding_definitions=True,
        body_module_only_call_pair_replaced=True, held_options_hash_query_unchanged=True,
        original_current_nodes_only_production_caller='body_cache::prepare',
        semantic_key_bytes='Same normalized Input and key recipe; SOURCE_IDENTITY intentionally changes, so full persisted keys differ.',
        reused_constructor=dict(path=str(OLD/'candidate'/INPUT),sha256=sha(new_input)),
        compiler_builds=0, tests_run=0, performance_measurements=0, adopted=False,
        generator_sha256=sha(Path(__file__).read_bytes()))
    (HERE / 'source-comparison.json').write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
    assert all((N / name).read_bytes() == data for name, data in before.items())
    print(json.dumps(dict(source_identity=identity, patch_sha256=sha(patch_bytes), source_comparison_sha256=sha((HERE/'source-comparison.json').read_bytes())), indent=2))


if __name__ == '__main__':
    main()
