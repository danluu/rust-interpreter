"""Lossless parser for the exact saved ld-1266.8 metadata03 provider report.

The six VERSION_TEXT lines are actual stderr from metadata03 child 047,
PID 79778, SHA256 950bfdc12496b487e06869981eb0dd12b45e29a9268804f4fc5c8e79899755a3.
The selected ld provider SHA256 is
40eb2432a67a720717ca1144068d85e0441b038054edda43eb88ba9dc8066bc5.
Its complete private-provider/platform binding remains the caller's obligation.
This does not infer search sections or permit an arbitrary architecture list.

DYLD parsing is unchanged from compiler-metadata-03/linker_parser.py, whose
two-form grammar derives from the qualified embedded-frontend source03/run.py
parse_dyld. Every raw byte, line and offset is retained. System-cache images
remain explicitly distinct from private file-hash proofs. The original failed
metadata03 receipt and raw streams must remain unchanged.
"""
import hashlib
from pathlib import Path
import re


VERSION_TEXT = (
    '@(#)PROGRAM:ld PROJECT:ld-1266.8\n'
    'BUILD 01:30:17 Apr  9 2026\n'
    'configured to support archs: armv6 armv7 armv7s arm64 arm64e arm64_32 i386 '
    'x86_64 x86_64h armv6m armv7k armv7m armv7em armv8m.main armv8.1m.main\n'
    'will use ld-classic for: armv6 armv7 armv7s i386 armv6m armv7k armv7m armv7em\n'
    'LTO support using: LLVM version 21.0.0 (static support for 30, runtime is 30)\n'
    'TAPI support using: Apple TAPI version 21.0.0 (tapi-2100.0.2.6)\n'
)


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
    version_text = ''.join(row['raw'] for row in version_lines)
    require(version_text == VERSION_TEXT, 'linker version report differs from the exact saved six lines')
    return dict(private_paths=sorted(loaded), images=images, delayed=delayed, version_lines=version_lines,
                version_text=version_text, lines=lines, raw_bytes=len(raw),
                raw_sha256=hashlib.sha256(raw).hexdigest(),
                system_assumption='System dyld-cache images are bound to the separately recorded uname platform, not private file hashes.')
