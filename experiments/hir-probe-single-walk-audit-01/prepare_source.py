"""Copy the existing real-AST audit onto the held current-base candidate.

This source-only generator never imports a compiler controller or runs a child.
It writes only absent files beside itself and rechecks every input afterward.
"""
from pathlib import Path
import difflib
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PERF = ROOT / 'experiments/hir-probe-single-walk-01'
OLD = ROOT / 'experiments/hir-input-walk-audit/source-01'
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
N = X / '.work/hir-options-hash-compiler-01/source'
INPUT = 'compiler/rustc_ast_lowering/src/body_cache/input.rs'
BODY = 'compiler/rustc_ast_lowering/src/body_cache/mod.rs'
IDENTITY = 'compiler/rustc_ast_lowering/src/body_cache/source_identity.rs'
PERFORMANCE_MANIFEST = '6c7652e7353b9829f3c6e832a85b3162643a3b7cfc572956cd36e6d08e13ed12'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def replace_once(value, old, new):
    assert value.count(old) == 1, old
    return value.replace(old, new)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as output:
        output.write(data)


def main():
    assert sys.dont_write_bytecode and not sys.flags.optimize
    assert not (HERE / 'candidate').exists() and not (HERE / 'fixtures').exists()
    consumed = {}

    def read(path):
        path = Path(path)
        assert not path.is_symlink() and path.is_file()
        data = path.read_bytes()
        assert path not in consumed or consumed[path] == data
        consumed[path] = data
        return data

    manifest_bytes = read(PERF / 'manifest.json')
    assert sha(manifest_bytes) == PERFORMANCE_MANIFEST
    manifest = json.loads(manifest_bytes)
    for name, row in manifest['files'].items():
        data = read(PERF / name)
        assert len(data) == row['bytes'] and sha(data) == row['sha256']
    comparison = json.loads(read(PERF / 'source-comparison.json'))
    inherited = json.loads(read(PERF / 'inherited-options-hash-manifest.json'))
    current = {name: read(N / name) for name in inherited['acyclic_identity_files']}
    assert {name: sha(data) for name, data in current.items()} == inherited['acyclic_identity_files']
    current[IDENTITY] = read(N / IDENTITY)
    assert current[IDENTITY] == read(PERF / 'base' / IDENTITY)
    before = dict(current)
    for name in [INPUT, BODY, IDENTITY]:
        before[name] = read(PERF / 'candidate' / name)
        assert sha(before[name]) == comparison['candidate_hashes'][name]
    old = json.loads(read(OLD / 'manifest.json'))
    oracle = read(OLD / 'old-current-nodes.rs')
    marker = b'pub(super) fn current_nodes'
    assert current[INPUT].count(marker) == 1
    assert current[INPUT][current[INPUT].index(marker):] == oracle
    assert sha(oracle) == old['old_function_sha256']
    # The previous audit input and its performance precursor remain identical
    # to the current constructor design, including every oracle byte.
    assert read(OLD / 'performance-candidate' / INPUT) == before[INPUT]
    audit_input = read(OLD / 'audit-candidate' / INPUT)
    assert sha(audit_input) == old['audit_hashes'][INPUT]
    assert audit_input.endswith(oracle)
    old_body = read(OLD / 'performance-candidate' / BODY).decode()
    old_audit_body = read(OLD / 'audit-candidate' / BODY).decode()
    call = '    let (probe, ast_nodes) = input::probe(tcx, resolver, owner, span, function, role).ok()?.into_parts();\n'
    start = old_audit_body.index('    let probed = match input::probe(')
    end = old_audit_body.index('    let (probe, ast_nodes) = probed.into_parts();\n', start)
    end += len('    let (probe, ast_nodes) = probed.into_parts();\n')
    audit_call = old_audit_body[start:end]
    assert replace_once(old_body, call, audit_call) == old_audit_body
    audit_body = replace_once(before[BODY].decode(), call, audit_call).encode()
    after = dict(before, **{INPUT: audit_input, BODY: audit_body})
    closure = {name: sha(data) for name, data in after.items() if name != IDENTITY}
    identity = sha(json.dumps(closure, sort_keys=True, separators=(',', ':')).encode())
    assert identity != comparison['source_identity'] != inherited['source_identity']
    after[IDENTITY] = f'pub(super) const SOURCE_IDENTITY: &str = "{identity}";\n'.encode()
    patches = []
    for name in [INPUT, BODY, IDENTITY]:
        write(HERE / 'performance' / name, before[name])
        write(HERE / 'candidate' / name, after[name])
        patches.append(f'diff --git a/{name} b/{name}\n')
        patches.extend(difflib.unified_diff(before[name].decode().splitlines(True),
            after[name].decode().splitlines(True), fromfile='a/' + name, tofile='b/' + name, n=5))
    patch = ''.join(patches).encode()
    write(HERE / 'audit.patch', patch)
    write(HERE / 'old-current-nodes.rs', oracle)
    fixtures = {}
    assert len(old['fixtures']) == 13
    for name, row in sorted(old['fixtures'].items()):
        data = read(OLD / 'fixtures' / name)
        assert sha(data) == row['sha256']
        if name in ['fixture.rs', 'inherited-rmake.rs']:
            original = 'rmake.rs' if name == 'inherited-rmake.rs' else name
            assert data == read(N / 'tests/run-make/hir-body-cache-capture' / original)
        write(HERE / 'fixtures' / name, data)
        fixtures[name] = dict(path=str(OLD / 'fixtures' / name), sha256=sha(data), bytes=len(data))
    # Preserve the exact source-derived compiler test-name reader; it is not run.
    reader = X / 'experiments/hir-options-hash/compiler-build-continuation-01/test_source.py'
    write(HERE / 'compiler_test_source.py', read(reader))
    report = dict(status='source-only-uncompiled-unrun', audit_only=True, timing_eligible=False,
        performance_manifest=dict(path=str(PERF / 'manifest.json'), sha256=PERFORMANCE_MANIFEST),
        inherited_identity=inherited['source_identity'], performance_identity=comparison['source_identity'],
        source_identity=identity, acyclic_identity_files=closure,
        performance_hashes={name: sha(before[name]) for name in [INPUT, BODY, IDENTITY]},
        audit_hashes={name: sha(after[name]) for name in [INPUT, BODY, IDENTITY]},
        patch_sha256=sha(patch), oracle_sha256=sha(oracle), fixtures=fixtures,
        exact_old_audit_input=True, exact_old_audit_call_replacement=True,
        current_options_hash_query_preserved=True, original_runner_and_fixtures_byte_exact=True,
        assertions_unconditional_when_original_enable_gate_enters_probe=True,
        compiler_builds=0, tests_run=0, performance_measurements=0,
        full_persistent_key_equal=False,
        key_note='Normalized Input and key recipe remain equal; the separately derived SOURCE_IDENTITY intentionally changes persisted keys.',
        consumed={str(path): dict(sha256=sha(data), bytes=len(data)) for path, data in sorted(consumed.items())},
        generator_sha256=sha(Path(__file__).read_bytes()))
    write(HERE / 'source-comparison.json', encoded(report))
    assert all(path.read_bytes() == data for path, data in consumed.items())
    print(json.dumps(dict(status=report['status'], source_identity=identity,
        audit_patch_sha256=sha(patch), fixtures=len(fixtures), consumed_files=len(consumed)), indent=2))


if __name__ == '__main__':
    main()
