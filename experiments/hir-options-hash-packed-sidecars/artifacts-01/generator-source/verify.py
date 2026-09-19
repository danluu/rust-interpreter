#!/usr/bin/env python3
"""UNRUN draft: independently verify retained source; never apply/build/import it."""
import json
import os
from pathlib import Path
import stat
import sys
from contract import (HERE, BODY, IDENTITY, CONTEXT, CACHED_CALL, OLD_CALL,
                      CHANGED, COMMIT, document, encoded, load_inputs, make_patch,
                      read_regular, render_identity, sha, source_bytes)

OUTPUT = HERE / 'artifacts-01'
REPORT = HERE / 'source-verification-01.json'


def main():
    assert sys.dont_write_bytecode and not sys.flags.optimize
    assert not os.path.lexists(REPORT)
    bindings, data = load_inputs()
    sources = source_bytes()
    manifest_raw = read_regular(OUTPUT / 'manifest.json')
    manifest = json.loads(manifest_raw)
    assert manifest['status'] == 'source-only-uncompiled-unrun' and manifest['base_commit'] == COMMIT
    assert manifest['bindings_sha256'] == sha(sources['bindings.json'])
    assert manifest['generator_sources'] == {n: sha(b) for n, b in sources.items()}

    # Independent algebraic expectation, not the generator's hunk application.
    before = data['current_files']
    expected = dict(before)
    for name, content in data['packed_candidate_files'].items():
        if name not in (BODY, IDENTITY):
            expected[name] = content
    body = data['packed_candidate_files'][BODY]
    assert body.count(OLD_CALL) == 1 and CACHED_CALL not in body
    expected[BODY] = body.replace(OLD_CALL, CACHED_CALL)
    assert expected[CONTEXT] == before[CONTEXT]
    assert b'input::current_nodes(' in expected[BODY]
    closure = {n: sha(expected[n]) for n in bindings['identity_union']}
    identity = sha(encoded(closure))
    expected[IDENTITY] = render_identity(identity)
    assert len(closure) == 29 and len(expected) == 30
    assert manifest['acyclic_identity_files'] == closure
    assert manifest['source_identity'] == identity
    assert manifest['options_identity'] == bindings['options_identity']
    assert manifest['packed_identity'] == bindings['packed_identity']
    assert manifest['complete_closure_files'] == {n: sha(b) for n, b in expected.items()}
    assert manifest['base_files'] == {n: {'bytes': len(b), 'sha256': sha(b)} for n, b in before.items()}
    assert manifest['changed_files'] == sorted(n for n in expected if before.get(n) != expected[n]) == CHANGED
    wanted = {'base/' + n: b for n, b in before.items()}
    wanted.update({'candidate/' + n: b for n, b in expected.items()})
    wanted.update({'generator-source/' + n: b for n, b in sources.items()})
    for role, content in data['fixed_files'].items():
        suffix = os.path.splitext(bindings['fixed_files'][role]['path'])[1]
        wanted['provenance/' + role + suffix] = content
    wanted['inputs.json'] = sources['bindings.json']
    wanted['candidate.patch'] = make_patch(before, expected)
    wanted['hunks.json'] = document({'packed_hunks': bindings['packed_hunks'],
                                    'skipped_identity_hunk': IDENTITY,
                                    'applied_nonidentity_hunks': 17})
    assert manifest['patch_sha256'] == sha(wanted['candidate.patch'])
    assert manifest['files'] == {n: {'bytes': len(b), 'sha256': sha(b)} for n, b in wanted.items()}
    assert manifest['inherited_test_counts'] == {'lowering': 27, 'interface': 18, 'support': 15}
    assert manifest['proposed_session_tests'] == bindings['new_session_tests']
    assert manifest['compiler_source_modified'] is False and manifest['checkout_created'] is False
    assert manifest['compiler_builds'] == 0 and manifest['rust_controls_run'] is False
    assert manifest['benchmarks_run'] is False and manifest['single_walk_applied'] is False
    assert manifest['options_hash_preserved'] is True

    expected_manifest = dict(
        schema_version=1, status='source-only-uncompiled-unrun', base_commit=COMMIT,
        base_source=bindings['compiler_source'], options_identity=bindings['options_identity'],
        packed_identity=bindings['packed_identity'], source_identity=identity,
        acyclic_identity_files=closure, complete_closure_files={n: sha(b) for n, b in expected.items()},
        base_files={n: {'bytes': len(b), 'sha256': sha(b)} for n, b in before.items()},
        changed_files=CHANGED, patch_sha256=sha(wanted['candidate.patch']),
        bindings_sha256=sha(sources['bindings.json']),
        generator_sources={n: sha(b) for n, b in sources.items()},
        files={n: {'bytes': len(b), 'sha256': sha(b)} for n, b in wanted.items()},
        inherited_test_counts={'lowering': 27, 'interface': 18, 'support': 15},
        proposed_session_tests=bindings['new_session_tests'],
        compiler_source_modified=False, checkout_created=False,
        compiler_builds=0, rust_controls_run=False, benchmarks_run=False,
        options_hash_preserved=True, single_walk_applied=False)
    assert encoded(manifest) == encoded(expected_manifest)

    limits = bindings['limits']
    wanted['manifest.json'] = manifest_raw
    assert len(wanted) <= limits['maximum_output_files']
    assert sum(len(b) for b in wanted.values()) <= limits['maximum_output_bytes']
    observed = set()
    expected_dirs = {'.'}
    for name in wanted:
        expected_dirs.update(str(parent) for parent in Path(name).parents)
    observed_dirs = set()
    assert stat.S_ISDIR(OUTPUT.lstat().st_mode) and OUTPUT.resolve(strict=True) == OUTPUT
    for root, dirs, files in os.walk(OUTPUT, followlinks=False):
        assert len(observed) <= limits['maximum_output_files']
        directory = os.path.relpath(root, OUTPUT)
        assert directory in expected_dirs and directory not in observed_dirs
        observed_dirs.add(directory)
        for name in dirs:
            path = os.path.join(root, name)
            assert stat.S_ISDIR(os.lstat(path).st_mode)
            assert os.path.relpath(path, OUTPUT) in expected_dirs
        for name in files:
            path = os.path.join(root, name)
            relative = os.path.relpath(path, OUTPUT)
            assert relative in wanted and relative not in observed
            assert read_regular(path, limit=limits['maximum_file_bytes']) == wanted[relative]
            observed.add(relative)
    assert observed == set(wanted)
    assert observed_dirs == expected_dirs
    assert load_inputs() == (bindings, data) and source_bytes() == sources
    report = dict(status='source-only-verification-passed', manifest_sha256=sha(manifest_raw),
                  source_identity=identity, complete_closure_files=30, acyclic_identity_files=29,
                  changed_files=CHANGED, files=len(wanted),
                  verification='Independent expected bytes plus exact patch, closure and all retained inputs.',
                  compiler_source_modified=False, compiler_builds=0, rust_controls_run=False,
                  benchmarks_run=False, git_commands_run=False)
    with REPORT.open('xb') as stream:
        stream.write(document(report))
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'report': str(REPORT), 'sha256': sha(document(report))}, sort_keys=True))


if __name__ == '__main__':
    main()
