"""Narrow, lossless ld-1266.8 metadata-probe parser (not yet probe-qualified).

DYLD grammar derives from the previously qualified parse_dyld at
/Users/danluu/dev/rust-interp-embedded-frontend-bootstrap-20260913/
.work/embedded-frontend-compatibility-source-03/run.py:70-97.
Version labels derive from ARM64 strings in the exact selected Xcode ld
SHA256 40eb2432a67a720717ca1144068d85e0441b038054edda43eb88ba9dc8066bc5:
PROGRAM ld-1266.8, BUILD 01:30:17 Apr  9 2026, configured archs, LTO/TAPI
support, and library/framework search paths. The loader probe must still run;
unknown output fails instead of extending this grammar during a launch.

Every input byte occurs in one retained line. System images use the separately
recorded uname/dyld-cache assumption; they are not attributed to private files.
Only the five exact private ld/provider paths supplied by the plan may load.
"""
import hashlib
from pathlib import Path
import re


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def canonical(path):
    return path.startswith('/') and str(Path(path)) == path and '..' not in Path(path).parts


def system(path):
    return path.startswith(('/usr/lib/', '/System/Library/'))


def parse(raw, pid, expected):
    require(isinstance(raw, bytes) and 0 < len(raw) <= 8 * 2**20, 'invalid bounded linker stderr')
    require(isinstance(pid, int) and not isinstance(pid, bool) and pid > 0, 'actual linker PID required')
    require(isinstance(expected, list) and len(expected) == len(set(expected)) == 5
            and all(canonical(path) and not system(path) for path in expected), 'exact five private providers required')
    require(raw.endswith(b'\n'), 'incomplete linker stderr line')
    text = raw.decode('utf-8')
    require('\r' not in text and '\x00' not in text, 'noncanonical linker text')
    prefix = rf'dyld\[{pid}\]: '
    images, delayed, version_lines, lines = [], [], [], []
    basenames, loaded = {}, set()
    cursor = 0
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        encoded = line.encode('utf-8')
        require(encoded.endswith(b'\n'), 'unsupported line separator')
        value = line[:-1]
        row = dict(line=number, start=cursor, end=cursor + len(encoded), raw=line, raw_hex=encoded.hex())
        cursor += len(encoded)
        image = re.fullmatch(prefix + r'(?:<[0-9A-Fa-f-]{36}>\s+)?(/.+)', value)
        move = re.fullmatch(prefix + r'move loaded to delayed: ([^/\r\n]+)', value)
        if image:
            path = image[1]
            require(canonical(path), 'noncanonical DYLD image path')
            row.update(kind='image', path=path, system=system(path))
            images.append(row)
            basenames.setdefault(Path(path).name, set()).add(path)
            if not system(path):
                require(path in expected, 'foreign private linker image: ' + path)
                loaded.add(path)
        elif move:
            matches = basenames.get(move[1], set())
            require(len(matches) == 1 and all(system(path) for path in matches),
                    'delayed notice is not one previously observed system image')
            row.update(kind='delayed-system-image', basename=move[1], image=next(iter(matches)))
            delayed.append(row)
        else:
            require(not value.startswith('dyld['), 'unknown DYLD line or wrong child PID')
            row.update(kind='version')
            version_lines.append(row)
        lines.append(row)
    require(cursor == len(raw) and b''.join(bytes.fromhex(row['raw_hex']) for row in lines) == raw,
            'linker line partition lost bytes')
    require(loaded == set(expected), 'actual private linker images differ from the exact frozen set')
    values = [row['raw'][:-1] for row in version_lines]
    require(values and values[0] == '@(#)PROGRAM:ld PROJECT:ld-1266.8', 'unexpected linker version')
    seen = {'version'}
    section = None
    paths = {'libraries': [], 'frameworks': []}
    details = {}
    architecture_names = {'armv6', 'armv7', 'armv7s', 'armv7k', 'arm64', 'arm64e',
                          'arm64_32', 'i386', 'x86_64', 'x86_64h'}
    for value in values[1:]:
        if value == 'BUILD 01:30:17 Apr  9 2026':
            require(section is None and 'build' not in seen, 'duplicate or misplaced linker build')
            seen.add('build')
        elif value.startswith('configured to support archs: '):
            require(section is None and 'architectures' not in seen, 'duplicate or misplaced architecture line')
            architectures = value.removeprefix('configured to support archs: ').split()
            require(architectures and len(architectures) == len(set(architectures))
                    and set(architectures) <= architecture_names, 'unknown linker architecture grammar')
            seen.add('architectures')
            details['architectures'] = architectures
        elif match := re.fullmatch(r'LTO support using: ((?:Apple )?LLVM version 21\.0\.0(?: \([A-Za-z0-9 ._-]{1,160}\))?) '
                                  r'\(static support for ([0-9]{1,4}), runtime is ([0-9]{1,4})\)', value):
            require(section is None and 'lto' not in seen, 'duplicate or misplaced LTO line')
            seen.add('lto')
            details['lto'] = dict(version=match[1], static=int(match[2]), runtime=int(match[3]))
        elif match := re.fullmatch(r'TAPI support using: ((?:Apple )?TAPI version 21\.0\.0 \(tapi-2100\.0\.2\.6\))', value):
            require(section is None and 'tapi' not in seen, 'duplicate or misplaced TAPI line')
            seen.add('tapi')
            details['tapi'] = match[1]
        elif value == 'Library search paths:':
            require(section is None and 'library-section' not in seen, 'duplicate or misplaced library header')
            seen.add('library-section')
            section = 'libraries'
        elif value == 'Framework search paths:':
            require(section == 'libraries' and 'framework-section' not in seen, 'duplicate or misplaced framework header')
            seen.add('framework-section')
            section = 'frameworks'
        elif match := re.fullmatch(r'[\t ]+(/[^\r\n]*)', value):
            require(section is not None, 'search path outside its section')
            path = match[1]
            # ld prints framework directories with a trailing slash. Preserve
            # the actual spelling while rejecting dot components/other edits.
            require(canonical(path.rstrip('/') or '/'), 'noncanonical linker search path')
            paths[section].append(path)
        else:
            raise RuntimeError('unknown linker version diagnostic: ' + repr(value))
    require({'version', 'build', 'architectures', 'library-section', 'framework-section'} <= seen,
            'incomplete ld -v version/search report')
    return dict(private_paths=sorted(loaded), images=images, delayed=delayed, version_lines=version_lines,
                version_text=''.join(row['raw'] for row in version_lines), version_details=details,
                search_paths=paths, lines=lines, raw_bytes=len(raw), raw_sha256=hashlib.sha256(raw).hexdigest(),
                system_assumption='System dyld-cache images are bound to the separately recorded uname platform, not private file hashes.')
