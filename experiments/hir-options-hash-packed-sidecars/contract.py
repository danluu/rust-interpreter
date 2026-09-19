#!/usr/bin/env python3
"""Fixed source inputs and bounded, read-only checks; no compiler/Git invocation."""
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import stat

HERE = Path(__file__).resolve().parent
BINDINGS_SHA256 = '8afec96917ef1a22aeb9fcc4df9e0ff111878c2ac05b0f7d04a9de526bc24757'
COMMIT = '4de35bdacef0e3cd18a66bc30b5459c19e09b118'
BODY = 'compiler/rustc_ast_lowering/src/body_cache/mod.rs'
IDENTITY = 'compiler/rustc_ast_lowering/src/body_cache/source_identity.rs'
CONTEXT = 'compiler/rustc_middle/src/ty/context.rs'
PACK = 'compiler/rustc_session/src/hir_body_cache.rs'
OLD_CALL = b'tcx.sess.opts.dep_tracking_hash(false).as_u64().encode(&mut encoder);'
CACHED_CALL = b'tcx.incremental_options_hash().as_u64().encode(&mut encoder);'
CHANGED = sorted([
    BODY, IDENTITY, PACK,
    'compiler/rustc_ast_lowering/src/body_cache/prepared_replay.rs',
    'compiler/rustc_ast_lowering/src/body_cache/storage.rs',
    'compiler/rustc_incremental/src/persist/fs.rs',
    'compiler/rustc_session/src/lib.rs',
    'compiler/rustc_session/src/session.rs',
    'tests/run-make/hir-body-cache-capture/rmake.rs',
])
SOURCE_FILES = ['bindings.json', 'contract.py', 'generate.py', 'verify.py',
                'README.md', 'QUALIFICATION.md']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def document(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def identity(s):
    return [s.st_dev, s.st_ino, s.st_mode, s.st_size,
            s.st_mtime_ns, s.st_ctime_ns, s.st_nlink]


def relative(name):
    path = Path(name)
    assert name and not path.is_absolute() and '..' not in path.parts
    assert str(path) == name
    return path


def read_regular(path, row=None, limit=4 * 1024 * 1024):
    path = Path(path)
    assert path.is_absolute() and path.resolve(strict=True) == path
    before = path.lstat()
    assert stat.S_ISREG(before.st_mode) and before.st_size <= limit
    if row is not None:
        assert str(path) == row['path'] and identity(before) == row['identity']
        assert before.st_size == row['size']
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        assert identity(os.fstat(fd)) == identity(before)
        parts = []
        remaining = before.st_size + 1
        while remaining:
            part = os.read(fd, min(remaining, 1024 * 1024))
            if not part:
                break
            parts.append(part)
            remaining -= len(part)
        data = b''.join(parts)
        assert len(data) == before.st_size
        assert identity(os.fstat(fd)) == identity(before)
    finally:
        os.close(fd)
    assert identity(path.lstat()) == identity(before)
    if row is not None:
        assert sha(data) == row['sha256']
    return data


def render_identity(value):
    return f'pub(super) const SOURCE_IDENTITY: &str = "{value}";\n'.encode()


def load_inputs():
    raw = read_regular(HERE / 'bindings.json')
    assert sha(raw) == BINDINGS_SHA256
    bindings = json.loads(raw)
    assert bindings['schema_version'] == 1 and bindings['compiler_commit'] == COMMIT
    limits = bindings['limits']
    groups = ['fixed_files', 'current_files', 'packed_base_files', 'packed_candidate_files']
    rows = [row for group in groups for row in bindings[group].values()]
    assert len(rows) <= limits['maximum_input_files'] == 96
    assert sum(row['size'] for row in rows) <= limits['maximum_input_bytes'] == 16 * 1024 * 1024
    data = {group: {key: read_regular(row['path'], row, limits['maximum_file_bytes'])
                    for key, row in bindings[group].items()} for group in groups}
    source = Path(bindings['compiler_source'])
    assert source.resolve(strict=True) == source
    assert bindings['absent_paths'] == [str(source / PACK)]
    assert not os.path.lexists(source / PACK)
    for name, row in bindings['current_files'].items():
        assert row['path'] == str(source / relative(name))

    fixed = data['fixed_files']
    options = json.loads(fixed['options_manifest'])
    packed = json.loads(fixed['packed_manifest'])
    current, base, proposed = (data[g] for g in groups[1:])
    assert len(current) == 29 and len(options['complete_closure_files']) == 26
    assert set(current) == set(options['complete_closure_files']) | set(packed['base_files'])
    assert {n: sha(current[n]) for n in options['complete_closure_files']} == options['complete_closure_files']
    old_closure = {n: sha(current[n]) for n in options['acyclic_identity_files']}
    assert len(old_closure) == 25 and old_closure == options['acyclic_identity_files']
    assert sha(encoded(old_closure)) == options['source_identity'] == bindings['options_identity']
    assert current[IDENTITY] == render_identity(options['source_identity'])
    assert sorted(proposed) == packed['changed_files'] == CHANGED
    for mapping, records in [(base, packed['base_files']), (proposed, packed['candidate_files'])]:
        assert set(mapping) == set(records)
        for name, content in mapping.items():
            relative(name)
            assert sha(content) == records[name]['sha256'] and len(content) == records[name]['bytes']
    old_packed = dict(base)
    old_packed.update(proposed)
    old_packed_closure = {n: sha(b) for n, b in old_packed.items() if n != IDENTITY}
    assert old_packed_closure == packed['complete_closure_files']
    assert sha(encoded(old_packed_closure)) == packed['source_identity'] == bindings['packed_identity']
    assert proposed[IDENTITY] == render_identity(packed['source_identity'])
    assert sha(fixed['packed_patch']) == packed['patch_sha256']
    assert sorted(n for n in base if current[n] != base[n]) == sorted([BODY, IDENTITY])
    assert base[BODY].count(OLD_CALL) == 1 and current[BODY] == base[BODY].replace(OLD_CALL, CACHED_CALL)
    assert current[CONTEXT] == read_regular(bindings['current_files'][CONTEXT]['path'], bindings['current_files'][CONTEXT])
    assert sha(current[CONTEXT]) == 'ea9494306f859cfb9e579d8f3131fe2fd5d4b3b451ccdae480edecd7d1564fa1'
    union = sorted(set(options['acyclic_identity_files']) | set(packed['complete_closure_files']))
    assert union == bindings['identity_union'] and len(union) == 29 and IDENTITY not in union

    compiled = json.loads(fixed['compiled'])
    terminal = json.loads(fixed['compiler_terminal'])
    audit = json.loads(fixed['compiler_audit'])
    assert compiled['candidate_revision'] == terminal['candidate_revision'] == COMMIT
    assert compiled['source_identity'] == terminal['source_identity'] == options['source_identity']
    assert compiled['status'] == 'compiled-awaiting-native-recipe-and-B3-qualification'
    assert terminal['status'] == 'passed' and audit['status'] == 'verified'
    assert terminal['compiled_sha256'] == audit['compiled_sha256'] == sha(fixed['compiled'])
    assert audit['receipt_sha256'] == sha(fixed['compiler_terminal'])
    assert [compiled['all_lowering_tests'], compiled['all_interface_tests'], compiled['all_support_tests']] == [27, 18, 15]
    tests = re.findall(rb'#\[test\]\s+fn ([a-zA-Z0-9_]+)', proposed[PACK])
    assert [name.decode() for name in tests] == bindings['new_session_tests'] and len(tests) == 9
    return bindings, data


def parse_hunks(patch, bindings):
    """Decode only the pinned strict unified diff; no offsets, fuzz or Git."""
    lines = patch.splitlines(keepends=True)
    index = 0
    hunks = []
    names = []
    while index < len(lines):
        match = re.fullmatch(rb'diff --git a/(\S+) b/(\S+)\n', lines[index])
        assert match and match[1] == match[2]
        name = match[1].decode()
        relative(name)
        names.append(name)
        index += 1
        new_file = name == PACK
        if new_file:
            assert lines[index] == b'new file mode 100644\n'
            index += 1
        assert lines[index] == ('--- ' + ('/dev/null' if new_file else 'a/' + name) + '\n').encode()
        assert lines[index + 1] == ('+++ b/' + name + '\n').encode()
        index += 2
        while index < len(lines) and not lines[index].startswith(b'diff --git '):
            header = lines[index]
            match = re.fullmatch(rb'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@\n', header)
            assert match
            start, count, new_start, new_count = [int(match[1]), int(match[2] or 1), int(match[3]), int(match[4] or 1)]
            index += 1
            body = []
            while index < len(lines) and not lines[index].startswith((b'@@ ', b'diff --git ')):
                assert lines[index][:1] in (b' ', b'+', b'-')
                body.append(lines[index])
                index += 1
            old = [line[1:] for line in body if line[:1] in (b' ', b'-')]
            new = [line[1:] for line in body if line[:1] in (b' ', b'+')]
            assert len(old) == count and len(new) == new_count
            record = dict(path=name, old_start=start, old_lines=count,
                          new_start=new_start, new_lines=new_count,
                          sha256=sha(header + b''.join(body)),
                          old_sha256=sha(b''.join(old)), new_sha256=sha(b''.join(new)))
            hunks.append((record, old, new))
    assert names == CHANGED and len(hunks) == 18
    assert [row for row, _, _ in hunks] == bindings['packed_hunks']
    return hunks


def make_patch(before, after):
    changed = sorted(n for n in after if before.get(n) != after[n])
    assert changed == CHANGED
    parts = []
    for name in changed:
        parts.append(f'diff --git a/{name} b/{name}\n')
        if name not in before:
            parts.append('new file mode 100644\n')
        parts.extend(difflib.unified_diff(
            before.get(name, b'').decode().splitlines(keepends=True),
            after[name].decode().splitlines(keepends=True),
            fromfile='a/' + name if name in before else '/dev/null', tofile='b/' + name, n=5))
    return ''.join(parts).encode()


def source_bytes():
    return {name: read_regular(HERE / name) for name in SOURCE_FILES}
