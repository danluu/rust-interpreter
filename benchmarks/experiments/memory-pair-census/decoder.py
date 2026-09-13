"""Conservative structural eligibility; validated memory scope is required separately."""

def pair(first, second):
    if not (0 <= first < 1 << 32 and 0 <= second < 1 << 32):
        return None
    opcode = first & 0xffc00000
    if opcode not in (0xf9400000, 0xf9000000) or second & 0xffc00000 != opcode:
        return None
    base, other_base = (first >> 5) & 31, (second >> 5) & 31
    offset, other_offset = (first >> 10) & 4095, (second >> 10) & 4095
    left, right = first & 31, second & 31
    if base != other_base or base == 31 or other_offset != offset + 1 or offset > 63:
        return None
    load = opcode == 0xf9400000
    if load and (left == right or base in (left, right)):
        return None
    word = (0xa9400000 if load else 0xa9000000) | (offset << 15) | (right << 10) | (base << 5) | left
    return dict(kind='load' if load else 'store', base=base, offset=offset * 8,
                left=left, right=right, word=word)
