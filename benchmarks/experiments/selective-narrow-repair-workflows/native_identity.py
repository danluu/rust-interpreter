"""Compare exact native layouts, allowing only checked scalar target relocation.

Callers first validate each process's operation map against its bytes/profile.
Different materialization lengths intentionally fail this conservative check.
"""
import hashlib
import struct


def normalized(mapping, code, profile):
    assert len(code) % 4 == 0 and len(code) <= 16 * 1024**2
    assert mapping['code_sha256'] == hashlib.sha256(code).hexdigest()
    assert mapping['code_bytes'] == len(code)
    base = mapping['arena_base']
    assert type(base) is int and 0 < base < 2**64
    bodies = {f['offset']: f['function'] for f in mapping['functions']
              if len(f['spans']) == 1 and f['spans'][0]['kind'] == 'scalar_leaf'}
    words = list(struct.unpack('<' + 'I' * (len(code)//4), code))
    targets = []
    for function in mapping['functions']:
        for span in function['spans']:
            if span['kind'] != 'transition':
                continue
            op = profile['functions'][function['function']]['operations'][span['pc']]
            if op != 'Call':
                continue
            start, end = span['offset']//4, span['end']//4
            assert 0 <= start < end <= len(words)
            for call in range(start, end):
                if words[call] != 0xd63f0200:  # BLR x16, scalar_calls.rs
                    continue
                at = call - 1
                while at >= start and words[at] & 0xff80001f == 0xf2800010:
                    at -= 1
                assert at >= start and 1 <= call-at <= 4
                assert words[at] & 0xffe0001f == 0xd2800010  # MOVZ x16, LSL 0
                value = (words[at] >> 5) & 0xffff
                last_shift = 0
                for word in words[at+1:call]:
                    shift = (word >> 21) & 3
                    part = (word >> 5) & 0xffff
                    assert last_shift < shift <= 3 and part != 0
                    value |= part << (16*shift)
                    last_shift = shift
                offset = value - base
                assert offset in bodies, 'scalar target is not a published body entry'
                targets.append((function['function'], span['pc'], call*4, offset, bodies[offset]))
                for i in range(at, call):
                    words[i] &= ~0x1fffe0  # Only the validated immediate field.
    return struct.pack('<' + 'I' * len(words), *words), targets


def compare_native(current_map, current_code, current_profile,
                   previous_map, previous_code, previous_profile):
    def layout(mapping):
        return {k: v for k, v in mapping.items() if k not in {'pid', 'arena_base', 'code_sha256'}}
    assert layout(current_map) == layout(previous_map), 'native layout changed'
    assert len(current_profile['functions']) == len(previous_profile['functions'])
    for a, b in zip(current_profile['functions'], previous_profile['functions']):
        for key in ['name', 'operations', 'frame_size', 'registers', 'interpreted',
                    'jit_blocks', 'jit_block_ends', 'jit_tree_blocks', 'jit_tree_block_ends',
                    'jit_scalar_hits']:
            assert a.get(key) == b.get(key), ('execution distribution changed', key)
    current, targets = normalized(current_map, current_code, current_profile)
    previous, old_targets = normalized(previous_map, previous_code, previous_profile)
    assert targets == old_targets, 'scalar target identity changed'
    assert current == previous, 'native bytes changed outside scalar target immediates'
    return dict(exact_layout=True, exact_execution_distribution=True,
                bytes_equal_except_validated_scalar_addresses=True,
                scalar_target_sites=len(targets), native_bytes=len(current_code),
                normalized_sha256=hashlib.sha256(current).hexdigest())
