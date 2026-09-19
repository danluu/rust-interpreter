"""Source-only readback policies for already byte-qualified beta providers."""
from pathlib import Path
import re
import struct

from compose_sysroot import require


def beta_version(raw, stage0_source, host):
    require(type(raw) is bytes and 0 < len(raw) <= 4096 and raw.endswith(b'\n'), 'bounded complete D2 version required')
    pins = dict(line.split('=', 1) for line in stage0_source.splitlines() if line and not line.startswith('#') and '=' in line)
    commit = pins['compiler_git_commit_hash']
    require(pins['compiler_version'] == 'beta' and re.fullmatch('[a-f0-9]{40}', commit), 'source beta compiler pin differs')
    text = raw.decode('utf-8', errors='strict'); lines = text.splitlines()
    require(len(lines) == 7, 'D2 version output shape differs')
    fields = {}
    for line in lines[1:]:
        require(': ' in line, 'D2 version field malformed')
        key, value = line.split(': ', 1)
        require(key not in fields, 'duplicate D2 version field')
        fields[key] = value
    require(set(fields) == {'binary', 'commit-hash', 'commit-date', 'host', 'release', 'LLVM version'}
            and fields['binary'] == 'rustc' and fields['host'] == host and fields['commit-hash'] == commit,
            'D2 version identity differs from exact beta/source pin')
    require(re.fullmatch(r'\d+\.\d+\.\d+-beta(?:\.\d+)?', fields['release'])
            and re.fullmatch(r'\d{4}-\d{2}-\d{2}', fields['commit-date'])
            and re.fullmatch(r'\d+\.\d+\.\d+', fields['LLVM version']), 'D2 release/date/LLVM grammar differs')
    require(lines[0] == 'rustc '+fields['release']+' ('+commit[:9]+' '+fields['commit-date']+')', 'D2 summary disagrees with fields')
    return dict(text=text, fields=fields)


def objcopy_version(raw, beta_fields):
    require(type(raw) is bytes and 0 < len(raw) <= 4096 and raw.endswith(b'\n'), 'bounded complete objcopy version required')
    llvm_version = beta_fields['LLVM version']
    # The pinned beta distribution uses LLVM's Rust package suffix without
    # Rust's beta iteration. Bound saved text documents this grammar only;
    # actual D2 fields and the exact new archive/provider bytes establish role.
    require(re.fullmatch(r'\d+\.\d+\.\d+-beta(?:\.\d+)?', beta_fields['release']), 'beta release grammar differs')
    package = beta_fields['release'].split('-beta', 1)[0]+'-beta'
    expected = ('llvm-objcopy, compatible with GNU objcopy\nLLVM (http://llvm.org/):\n'
                '  LLVM version '+llvm_version+'-rust-'+package+'\n  Optimized build.\n')
    require(raw.decode('utf-8', errors='strict') == expected, 'beta objcopy version/format differs from actual D2 LLVM')
    return dict(text=expected, llvm_version=llvm_version, rust_package=package)


def macho_declarations(path):
    """Pure future-layout planning from the actual D2 bytes, no otool probe.

    B3 must copy exactly these ordinary archive bytes; its actual -L/-l calls
    independently check the declarations after relocation. No plan is a loader
    observation and no fabricated otool text is emitted.
    """
    path = Path(path)
    require(32 <= path.stat().st_size <= 256*2**20, 'bounded provider Mach-O required')
    data = path.read_bytes(); offset = 0
    if data[:4] in [b'\xca\xfe\xba\xbe', b'\xca\xfe\xba\xbf']:
        count = struct.unpack_from('>I', data, 4)[0]
        wide = data[3] == 0xbf; width = 32 if wide else 20
        require(0 < count < 32 and 8+count*width <= len(data), 'bounded fat architecture table required')
        offsets = []
        for index in range(count):
            base = 8+index*width
            if struct.unpack_from('>I', data, base)[0] == 0x100000c:
                start, length = struct.unpack_from('>QQ' if wide else '>II', data, base+8)
                require(start+length <= len(data), 'provider fat slice exceeds input')
                offsets.append((start, length))
        require(len(offsets) == 1, 'unique provider arm64 slice required')
        offset, length = offsets[0]
        data = data[offset:offset+length]; offset = 0
    require(data[:4] == b'\xcf\xfa\xed\xfe' and struct.unpack_from('<I', data, 4)[0] == 0x100000c,
            'provider Mach-O is not arm64')
    count, size = struct.unpack_from('<II', data, 16)
    position, end = 32, 32+size
    require(0 < count < 4096 and end <= len(data), 'provider load-command bound exceeded')
    kinds = {0xc:'LC_LOAD_DYLIB', 0xd:'LC_ID_DYLIB', 0x80000018:'LC_LOAD_WEAK_DYLIB',
             0x8000001f:'LC_REEXPORT_DYLIB', 0x20:'LC_LAZY_LOAD_DYLIB', 0x80000023:'LC_LOAD_UPWARD_DYLIB',
             0xe:'LC_LOAD_DYLINKER'}
    result = dict(rpaths=[], loads=[], identities=[])
    for _ in range(count):
        require(position+8 <= end, 'truncated provider load-command header')
        command, width = struct.unpack_from('<II', data, position)
        require(width >= 8 and width % 8 == 0 and position+width <= end and command != 0x27,
                'malformed provider command or unadmitted dyld environment')
        if command in kinds or command == 0x8000001c:
            minimum = 24 if command in kinds and command != 0xe else 12
            require(width > minimum, 'truncated provider load string')
            start = struct.unpack_from('<I', data, position+8)[0]
            require(minimum <= start < width, 'provider load string points into header')
            string = data[position+start:position+width]
            require(b'\0' in string, 'unterminated provider load string')
            value = string.split(b'\0', 1)[0].decode('utf-8', errors='strict')
            require(value and all(ord(c) >= 32 and ord(c) != 127 for c in value), 'invalid provider path token')
            if command == 0x8000001c:
                result['rpaths'].append(value)
            else:
                result['identities' if command == 0xd else 'loads'].append([kinds[command], value])
        position += width
    require(position == end, 'provider load-command size differs')
    return result
