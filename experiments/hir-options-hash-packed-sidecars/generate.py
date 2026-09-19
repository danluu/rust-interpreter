#!/usr/bin/env python3
"""UNRUN draft: derive source artifacts only, preserving the current compiler."""
import json
import os
from pathlib import Path
import sys
from contract import (HERE, BODY, IDENTITY, CONTEXT, PACK, CACHED_CALL, OLD_CALL,
                      CHANGED, COMMIT, document, encoded, load_inputs, make_patch,
                      parse_hunks, read_regular, relative, render_identity, sha,
                      source_bytes)

OUTPUT = HERE / 'artifacts-01'


def derive(bindings, data):
    before = data['current_files']
    after = dict(before)
    hunks = parse_hunks(data['fixed_files']['packed_patch'], bindings)
    for name in CHANGED:
        if name == IDENTITY:
            continue  # The old packed-only identity is never applied.
        original = before.get(name, b'').splitlines(keepends=True)
        result = []
        cursor = 0
        for row, old, new in hunks:
            if row['path'] != name:
                continue
            start = max(row['old_start'] - 1, 0)
            assert cursor <= start <= len(original)
            assert original[start:start + len(old)] == old
            result.extend(original[cursor:start])
            result.extend(new)
            cursor = start + len(old)
        result.extend(original[cursor:])
        after[name] = b''.join(result)
    assert after[CONTEXT] == before[CONTEXT]
    assert after[BODY].count(CACHED_CALL) == 1 and OLD_CALL not in after[BODY]
    assert b'input::current_nodes(' in after[BODY]  # Single-Walk remains separate.
    closure = {name: sha(after[name]) for name in bindings['identity_union']}
    assert len(closure) == 29
    identity = sha(encoded(closure))
    assert identity not in (bindings['options_identity'], bindings['packed_identity'])
    after[IDENTITY] = render_identity(identity)
    assert len(after) == 30
    assert sorted(n for n in after if before.get(n) != after[n]) == CHANGED
    return before, after, closure, identity


def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    assert path.parent.resolve(strict=True) == path.parent
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    assert read_regular(path, limit=16 * 1024 * 1024) == data


def main():
    assert sys.dont_write_bytecode and not sys.flags.optimize
    assert not os.path.lexists(OUTPUT)
    bindings, data = load_inputs()
    sources = source_bytes()
    before, after, closure, identity = derive(bindings, data)
    output = {'base/' + n: b for n, b in before.items()}
    output.update({'candidate/' + n: b for n, b in after.items()})
    output.update({'generator-source/' + n: b for n, b in sources.items()})
    for role, content in data['fixed_files'].items():
        suffix = Path(bindings['fixed_files'][role]['path']).suffix
        output['provenance/' + role + suffix] = content
    output['inputs.json'] = sources['bindings.json']
    output['candidate.patch'] = make_patch(before, after)
    output['hunks.json'] = document({'packed_hunks': bindings['packed_hunks'],
                                    'skipped_identity_hunk': IDENTITY,
                                    'applied_nonidentity_hunks': 17})
    manifest = dict(
        schema_version=1, status='source-only-uncompiled-unrun', base_commit=COMMIT,
        base_source=bindings['compiler_source'], options_identity=bindings['options_identity'],
        packed_identity=bindings['packed_identity'], source_identity=identity,
        acyclic_identity_files=closure, complete_closure_files={n: sha(b) for n, b in after.items()},
        base_files={n: {'bytes': len(b), 'sha256': sha(b)} for n, b in before.items()},
        changed_files=CHANGED, patch_sha256=sha(output['candidate.patch']),
        bindings_sha256=sha(sources['bindings.json']),
        generator_sources={n: sha(b) for n, b in sources.items()},
        files={n: {'bytes': len(b), 'sha256': sha(b)} for n, b in output.items()},
        inherited_test_counts={'lowering': 27, 'interface': 18, 'support': 15},
        proposed_session_tests=bindings['new_session_tests'],
        compiler_source_modified=False, checkout_created=False,
        compiler_builds=0, rust_controls_run=False, benchmarks_run=False,
        options_hash_preserved=True, single_walk_applied=False)
    output['manifest.json'] = document(manifest)
    limits = bindings['limits']
    assert len(output) <= limits['maximum_output_files']
    assert sum(len(b) for b in output.values()) <= limits['maximum_output_bytes']
    assert all(len(b) <= limits['maximum_file_bytes'] for b in output.values())
    for name in output:
        relative(name)
    assert load_inputs() == (bindings, data) and source_bytes() == sources
    OUTPUT.mkdir()
    # Manifest comes last. Any failure leaves its exact prefix for review.
    for name, content in sorted(output.items()):
        if name != 'manifest.json':
            write_new(OUTPUT / name, content)
    assert load_inputs() == (bindings, data) and source_bytes() == sources
    write_new(OUTPUT / 'manifest.json', output['manifest.json'])
    print(json.dumps({'status': manifest['status'], 'output': str(OUTPUT),
                      'manifest_sha256': sha(output['manifest.json']),
                      'source_identity': identity, 'files': len(output),
                      'bytes': sum(len(b) for b in output.values())}, sort_keys=True))


if __name__ == '__main__':
    main()
