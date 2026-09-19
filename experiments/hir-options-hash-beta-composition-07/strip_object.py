"""Unchanged bounded B2 section-equivalence proof, applied to fresh B3 objects."""
import hashlib
import struct
from compose_sysroot import require


def object_sections(data):
    """Read ordinary arm64 MH_OBJECT sections, preserving all non-DWARF bytes."""
    require(32 <= len(data) <= 16 * 2**20, 'bounded Mach-O object required')
    magic, cpu, _, kind, commands, command_bytes, _, _ = struct.unpack_from('<IiiIIIII', data)
    require(magic == 0xfeedfacf and cpu == 0x100000c and kind == 1
            and 0 < commands <= 256 and 32 + command_bytes <= len(data), 'arm64 Mach-O object header differs')
    offset = 32
    result = {}
    for _ in range(commands):
        require(offset + 8 <= 32 + command_bytes, 'truncated Mach-O command')
        command, size = struct.unpack_from('<II', data, offset)
        require(size >= 8 and size % 8 == 0 and offset + size <= 32 + command_bytes, 'invalid load-command bounds')
        if command == 0x19:  # LC_SEGMENT_64
            require(size >= 72, 'truncated segment')
            count = struct.unpack_from('<I', data, offset + 64)[0]
            require(size == 72 + count * 80, 'segment section count differs')
            for index in range(count):
                values = struct.unpack_from('<16s16sQQIIIIIIII', data, offset + 72 + index * 80)
                name, segment = (value.split(b'\0', 1)[0].decode('ascii') for value in values[:2])
                length, location, flags = values[3], values[4], values[8]
                zero_fill = flags & 255 in (1, 12, 18)
                require(name and segment and (segment, name) not in result, 'empty/duplicate section identity')
                require(zero_fill or location + length <= len(data), 'section exceeds object bounds')
                payload = None if zero_fill else data[location:location + length]
                result[(segment, name)] = dict(size=length, flags=flags,
                    sha256=None if payload is None else hashlib.sha256(payload).hexdigest())
        offset += size
    require(offset == 32 + command_bytes and result, 'incomplete object command table')
    return result


def check_strip(before, after):
    before_sections, after_sections = object_sections(before), object_sections(after)
    def debug(key):
        return key[0] == '__DWARF' or key[1].startswith(('__debug_', '__zdebug_'))
    prior_debug = {key: value for key, value in before_sections.items() if debug(key)}
    require(('__DWARF', '__debug_info') in prior_debug and any(value['size'] for value in prior_debug.values()),
            'real embedded DWARF required before strip')
    require(not any(debug(key) for key in after_sections), 'debug sections remain after strip')
    native = {key: value for key, value in before_sections.items() if not debug(key)}
    require(native and native == after_sections and len(after) < len(before), 'non-debug sections changed or no strip occurred')
    return dict(debug_sections=[dict(segment=k[0], name=k[1], **v) for k, v in sorted(prior_debug.items())],
                retained_sections=[dict(segment=k[0], name=k[1], **v) for k, v in sorted(native.items())],
                before_bytes=len(before), after_bytes=len(after),
                before_sha256=hashlib.sha256(before).hexdigest(), after_sha256=hashlib.sha256(after).hexdigest())

