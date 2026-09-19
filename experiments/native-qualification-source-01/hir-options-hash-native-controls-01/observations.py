"""Bounded native-control readback; no executions or permissive log filtering."""
import hashlib
import json
from pathlib import Path
import re
import shlex
import struct


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def clean(raw):
    require(type(raw) is bytes and len(raw) <= 8*2**20, 'bounded compiler stderr required')
    require(re.search(rb'(?mi)internal compiler error|^warning(?:\[|:)|dyld\[|Library not loaded:|failed to execute rust-objcopy', raw) is None,
            'compiler/loader/strip warning or failure')


def hit(raw, *, cold=False):
    clean(raw)
    if cold:
        grammar = (r'\[hir-body-capture\] anchor cold-tree-and-journal-after-stock-lowering '
                   r'S=(\d+) E=(\d+) events=(\d+) cache_hits=0 body_codec=1 prepared_values=1 '
                   r'cold_materialization_audit=1 hit_materializer=0 body_bytes=(\d+) body_ast=(\d+) '
                   r'param_ast=(\d+) trait_entries=(\d+) trait_candidates=(\d+) external_refs=(\d+)')
        prefix = '[hir-body-capture] anchor '
    else:
        grammar = (r'\[hir-body-reuse\] anchor hit cache_hits=1 verify_tree=1 verify_journal=1 '
                   r'verify_poststate=1 S=(\d+) E=(\d+)')
        prefix = '[hir-body-reuse] anchor '
    lines = raw.decode('utf-8', errors='strict').splitlines()
    selected = [(i, line) for i, line in enumerate(lines, 1) if line.startswith(prefix)]
    require(len(selected) == 1, 'one complete anchor event required')
    number, text = selected[0]
    match = re.fullmatch(grammar, text)
    require(match is not None and all(len(x) <= 20 for x in match.groups()), 'anchor event grammar differs')
    values = list(map(int, match.groups()))
    require(0 < values[0] < values[1] <= 0xFFFF_FF00, 'invalid NodeId interval')
    require(all(x <= 2**64-1 for x in values), 'counter exceeds u64')
    return dict(line=number, raw=text, values=values, cold=cold, stderr_sha256=digest(raw))


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        require(key not in obj, 'duplicate diagnostic JSON key')
        obj[key] = value
    return obj


def error_pair(ordinary, candidate, code):
    aout, aerr = ordinary[:2]
    bout, berr = candidate[:2]
    require(not aout and not bout and aerr == berr and aerr.endswith(b'\n'), 'raw diagnostic parity differs')
    clean(aerr)
    records = []
    for line in aerr.splitlines():
        obj = json.loads(line, object_pairs_hook=unique_object,
                         parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        require(type(obj) is dict and obj.get('$message_type') == 'diagnostic', 'unknown diagnostic stream record')
        require(obj.get('level') in ['error', 'failure-note'], 'unexpected diagnostic level')
        records.append(obj)
    errors = [row for row in records if row['level'] == 'error' and row.get('code') is not None]
    require(errors and all(row['code']['code'] == code for row in errors), 'wrong compiler error kind')
    return dict(raw_sha256=digest(aerr), code=code, errors=errors, records=len(records))


def wrong_pair(ordinary, candidate, beta_std_paths):
    result = error_pair(ordinary, candidate, 'E0514')
    require(beta_std_paths and all(Path(p).is_absolute() for p in beta_std_paths), 'actual beta std paths required')
    matched = []
    for row in result['errors']:
        require(re.fullmatch(r'found crate `(std|core)` compiled by an incompatible version of rustc.*', row['message']),
                'wrong-B3 failure is not compiler metadata incompatibility')
        notes = [child.get('message', '') for child in row.get('children', []) if child.get('level') == 'note']
        paths = [p for p in beta_std_paths if any(note.startswith('the following crate versions were found:')
                                                 and any(line.endswith(': '+p) for line in note.splitlines())
                                                 for note in notes)]
        require(paths, 'wrong-B3 diagnostic lacks an actual qualified beta std provider')
        matched.extend(paths)
    result['beta_std_paths'] = sorted(set(matched))
    return result


def link_command(raw, *, clang, output, runtime_lib):
    require(type(raw) is bytes and 0 < len(raw) <= 2**20 and raw.endswith(b'\n'), 'bounded linker command required')
    lines = raw.decode('utf-8', errors='strict').splitlines()
    require(len(lines) == 1, 'one actual linker invocation required')
    words = shlex.split(lines[0]); environment = {}; removed = []
    require(words and words.pop(0) == 'env', 'actual linker env wrapper required')
    while words and words[0] == '-u':
        require(len(words) >= 2 and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', words[1]), 'invalid linker env removal')
        removed.append(words[1]); words = words[2:]
    require(removed == ['IPHONEOS_DEPLOYMENT_TARGET', 'TVOS_DEPLOYMENT_TARGET', 'XROS_DEPLOYMENT_TARGET'],
            'source-bound Apple deployment environment removals differ')
    while words and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*=.*', words[0], re.S):
        name, value = words.pop(0).split('=', 1)
        require(name not in environment, 'duplicate linker environment')
        environment[name] = value
    require(words and words[0] == clang, 'actual linker provider differs')
    require(not any(k.startswith(('DYLD_', 'LD_')) for k in environment), 'unadmitted linker loader override')
    positions = [i for i, value in enumerate(words) if value == '-o']
    require(len(positions) == 1 and positions[0]+1 < len(words) and words[positions[0]+1] == str(output), 'linker output differs')
    require('-Wl,-rpath,'+str(runtime_lib) in words, 'runtime rpath not passed to actual linker')
    return dict(argv=words, environment=environment, removed=removed, stdout_sha256=digest(raw))


def stock_macho(data, raw_otool, *, stock, driver, runtime_lib, qualified_private):
    """The fresh thin arm64 executable's load commands, corroborated by -L.

    Existing qualified E2 nodes supply the transitive private closure. Only
    this root node is new. LC_ID_DYLIB and LC_DYLD_ENVIRONMENT cannot be accepted
    as executable dependencies. This produces no synthetic otool observation.
    """
    require(type(data) is bytes and 32 <= len(data) <= 128*2**20, 'bounded native executable required')
    magic, cpu, _, kind, count, size = struct.unpack_from('<6I', data)
    require(magic == 0xFEEDFACF and cpu == 0x100000C and kind == 2 and 0 < count < 4096,
            'fresh stock must be a thin arm64 MH_EXECUTE')
    end, position = 32+size, 32
    require(end <= len(data), 'truncated native load commands')
    loads, rpaths = [], []
    supported = {0xC, 0x80000018, 0x8000001F, 0x20, 0x80000023}
    for _ in range(count):
        require(position+8 <= end, 'truncated native load command')
        command, width = struct.unpack_from('<II', data, position)
        require(width >= 8 and width % 8 == 0 and position+width <= end, 'invalid native command width')
        require(command not in [0xD, 0x27], 'dylib identity or dyld environment in stock executable')
        if command in supported | {0x8000001C, 0xE}:
            minimum = 24 if command in supported else 12
            require(width >= minimum + 1, 'truncated native loader string')
            start = struct.unpack_from('<I', data, position+8)[0]
            require(minimum <= start < width, 'native loader string offset differs')
            value = data[position+start:position+width]
            require(b'\0' in value, 'unterminated native loader string')
            token = value.split(b'\0', 1)[0].decode('utf-8', errors='strict')
            require(token and all(ord(c) >= 32 and ord(c) != 127 for c in token), 'invalid native loader token')
            if command == 0x8000001C:
                rpaths.append(token)
            elif command == 0xE:
                require(token == '/usr/lib/dyld', 'foreign dynamic loader')
            else:
                loads.append(token)
        position += width
    require(position == end and rpaths == [str(runtime_lib)], 'exact E2 runtime rpath required')
    require(type(raw_otool) is bytes and 0 < len(raw_otool) <= 2**20 and raw_otool.endswith(b'\n'),
            'bounded complete otool output required')
    lines = raw_otool.decode('utf-8', errors='strict').splitlines()
    require(1 < len(lines) <= 4097 and lines[0] == str(stock)+':', 'actual otool root header differs')
    tokens = []
    version = r'[0-9]+(?:\.[0-9]+){2,3}'
    for line in lines[1:]:
        match = re.fullmatch(r'\t([^\x00-\x1f\x7f]+) \(compatibility version ('+version+
                             r'), current version ('+version+r')\)', line)
        require(match is not None, 'unknown actual otool dependency line')
        tokens.append(match[1])
    require(tokens == loads and loads, 'actual otool dependencies differ from binary commands')
    private = [x for x in loads if not x.startswith(('/usr/lib/', '/System/Library/'))]
    resolved = []
    require(type(qualified_private) is dict and str(driver) in set(qualified_private.values()), 'qualified E2 provider routes required')
    for token in private:
        if token.startswith('@rpath/'):
            path = Path(runtime_lib)/token.removeprefix('@rpath/')
        else:
            path = Path(token)
        require(path.is_absolute() and '..' not in path.parts and str(path) in qualified_private,
                'stock direct private edge is outside exact E2 closure')
        target = str(path.resolve(strict=True))
        require(target == qualified_private[str(path)], 'unqualified stock private alias')
        resolved.append(target)
    require(str(driver) in resolved, 'stock direct driver edge is absent')
    return dict(stock=str(stock), file_sha256=digest(data), rpaths=rpaths, loads=loads,
                private_driver=str(driver), direct_private=resolved, otool_sha256=digest(raw_otool),
                method='actual Mach-O byte parsing plus actual otool -L; no synthetic -l output')
