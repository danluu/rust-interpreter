"""Read-only test/module derivation for a separately bound single-walk compiler.

This is a validator for the reviewed pinned Rust source shape, not a general Rust
parser. Whole-file hashes are checked before interpreting exact cfg/module/test
lines. The returned catalog differs only in the three effects module names.
No compiler, test, subprocess, network or source mutation is performed.
"""
import copy
import hashlib
import re
import stat
from pathlib import Path

ROOT_LIBS = {
    'compiler/rustc_ast_lowering/src/lib.rs': '218226f84b3b7acc3474be6213740fc4a4f3c13557ae4d4b96b2e0754c3e1970',
    'compiler/rustc_interface/src/lib.rs': '1c22a5920a528d52c4e8a8ffab0cab72f0bc3d4a4d24a6d7ae32350db144ffeb',
}
BASE = 'compiler/rustc_ast_lowering/src/'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def stamp(path):
    s = path.lstat()
    require(stat.S_ISREG(s.st_mode), f'nonordinary source: {path}')
    return {k: getattr(s, 'st_' + k) for k in ('dev', 'ino', 'mode', 'size', 'mtime_ns', 'ctime_ns', 'nlink')}


def derive(source_root, original_expectations, source_revision):
    source = Path(source_root)
    require(source.is_absolute() and source.resolve() == source, 'source must be absolute ordinary resolved route')
    original = copy.deepcopy(original_expectations)
    require(isinstance(source_revision, str) and re.fullmatch(r'[0-9a-f]{40}', source_revision), 'actual built source revision required')
    require(original['source_revision'] == source_revision, 'unexpected source revision')
    expected = dict(original['source_files'])
    for relative, digest in ROOT_LIBS.items():
        path = str(source / relative)
        require(path not in expected or expected[path] == digest, 'root library hash conflict')
        expected[path] = digest
    texts, files, snapshots = {}, [], {}
    total = 0
    for spelling, digest in sorted(expected.items()):
        path = Path(spelling)
        require(path.is_relative_to(source) and path.resolve() == path, 'source binding escapes or aliases root')
        before = stamp(path)
        require(before['size'] <= 4 * 1024 * 1024, 'source file exceeds bound')
        raw = path.read_bytes()
        total += len(raw)
        require(total <= 16 * 1024 * 1024, 'source closure exceeds bound')
        require(hashlib.sha256(raw).hexdigest() == digest and stamp(path) == before, 'source hash/stamp changed')
        relative = path.relative_to(source).as_posix()
        texts[relative] = raw.decode('utf-8')
        snapshots[path] = (before, digest)
        files.append(dict(path=str(path), relative=relative, sha256=digest, size=len(raw)))
    routes = []

    def route(relative, snippet, module):
        text = texts[relative]
        require(text.count(snippet) == 1, f'nonunique/missing module declaration: {relative}: {module}')
        offset = text.index(snippet)
        require(offset == 0 or text[offset - 1] == '\n', 'module declaration not at line start')
        routes.append(dict(path=str(source / relative), module=module,
                           line=text.count('\n', 0, offset) + 1, text=snippet))
        return offset + len(snippet)

    route(BASE + 'lib.rs', 'mod body_cache;\n', 'body_cache')
    for child in ('effects', 'entry', 'journal', 'prepared', 'storage', 'validate', 'wire'):
        route(BASE + 'body_cache/mod.rs', f'mod {child};\n', f'body_cache::{child}')
    route(BASE + 'body_cache/prepared.rs', '#[path = "prepared_audit.rs"]\nmod cold;\n', 'body_cache::prepared::cold')
    route('compiler/rustc_interface/src/lib.rs', '#[cfg(test)]\nmod tests;\n', 'tests')
    names, definitions = [], []
    for filename, prefix, visibility in (
        ('mod.rs', 'body_cache::tests', ''),
        ('effects.rs', 'body_cache::effects::replay_tests', ''),
        ('entry.rs', 'body_cache::entry::tests', ''),
        ('journal.rs', 'body_cache::journal::tests', ''),
        ('prepared.rs', 'body_cache::prepared::tests', ''),
        ('prepared_audit.rs', 'body_cache::prepared::cold::tests', ''),
        ('storage.rs', 'body_cache::storage::tests', ''),
        ('validate.rs', 'body_cache::validate::tests', 'pub(super) '),
        ('wire.rs', 'body_cache::wire::tests', ''),
    ):
        relative = BASE + 'body_cache/' + filename
        text = texts[relative]
        module = prefix.rsplit('::', 1)[1]
        start = route(relative, f'#[cfg(test)]\n{visibility}mod {module} {{\n', prefix)
        # These exact pinned sources indent all members; the first column-zero
        # closing brace is the cfg(test) module boundary, including nested funcs.
        end = text.index('\n}', start) + 1
        body = text[start:end]
        hits = list(re.finditer(r'^    #\[test\]\n    fn ([A-Za-z_][A-Za-z0-9_]*)\(\) \{', body, re.M))
        require(len(hits) == text.count('#[test]') and hits, 'unaccounted or absent test attributes')
        for hit in hits:
            name = prefix + '::' + hit.group(1)
            names.append(name)
            definitions.append(dict(name=name, path=str(source / relative), line=text.count('\n', 0, start + hit.start()) + 1))
    interface_relative = 'compiler/rustc_interface/src/tests.rs'
    text = texts[interface_relative]
    hits = list(re.finditer(r'^#\[test\]\nfn ([A-Za-z_][A-Za-z0-9_]*)\(\) \{', text, re.M))
    require(len(hits) == text.count('#[test]'), 'unaccounted interface test attributes')
    interface = []
    for hit in hits:
        name = 'tests::' + hit.group(1)
        interface.append(name)
        definitions.append(dict(name=name, path=str(source / interface_relative), line=text.count('\n', 0, hit.start()) + 1))
    require(len(names) == len(set(names)) == original['lowering']['count'] == 27, 'lowering count mismatch')
    require(len(interface) == len(set(interface)) == original['interface']['count'] == 18, 'interface count mismatch')
    require(sorted(interface) == original['interface']['names'], 'interface catalog changed')
    old_names = original['lowering']['names']
    corrected = [name.replace('body_cache::effects::tests::', 'body_cache::effects::replay_tests::', 1) for name in old_names]
    changes = [dict(before=a, after=b) for a, b in zip(old_names, corrected) if a != b]
    require(len(changes) == 3 and sorted(names) == corrected, 'change is not exact three effects module corrections')
    result = copy.deepcopy(original)
    result['lowering']['names'] = corrected
    for path, (before, digest) in snapshots.items():
        require(stamp(path) == before and hashlib.sha256(path.read_bytes()).hexdigest() == digest and stamp(path) == before, 'source changed after derivation')
    return dict(tests=result, proof=dict(kind='pinned-source-cfg-module-test-names-v1', source_root=str(source), source_revision=source_revision,
                                        files=files, routes=routes, definitions=sorted(definitions, key=lambda row: row['name']), changes=changes,
                                        note='Whole-file source hashes and exact module routes; not a substitute for actual named successful test output.'))
