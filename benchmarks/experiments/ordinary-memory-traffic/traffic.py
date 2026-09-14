"""Syntactic register-file accesses; no arbitrary address provenance inference."""


def memory(word):
    tag = word & 0xffc00000
    if tag not in (0xf9000000, 0xf9400000):
        return None
    return dict(direction='load' if tag == 0xf9400000 else 'store',
                base=(word >> 5) & 31, payload=word & 31,
                byte_offset=((word >> 10) & 4095) * 8)


def large_address(words, pc, entries):
    """Return the exact reg_address recipe, bounded by this native region."""
    if pc < 2 or words[pc - 1] != 0x8b100010:  # add x16,x0,x16
        return None
    i = pc - 2
    pieces = []
    while i >= 0 and words[i] & 0xff80001f == 0xf2800010:
        shift = (words[i] >> 21) & 3
        part = (words[i] >> 5) & 65535
        if not shift or not part or len(pieces) >= 3:
            return None
        pieces.append((shift, part))
        i -= 1
    if i < 0 or words[i] & 0xffe0001f != 0xd2800010:
        return None
    pieces.reverse()
    if [s for s, _ in pieces] != sorted({s for s, _ in pieces}):
        return None
    offset = (words[i] >> 5) & 65535
    for shift, part in pieces:
        offset |= part << (16 * shift)
    # Reg is u32; direct addressing handles every byte offset below 32768.
    if offset < 32768 or offset % 8 or offset // 16 > 0xffffffff:
        return None
    if any(j in entries for j in range(i + 1, pc + 1)):
        return None
    return i, offset


def analyze(words, entries=()):
    entries = set(entries)
    accesses = {}
    addresses = {}
    for pc, word in enumerate(words):
        item = memory(word)
        if item is None:
            continue
        if item['base'] == 0:
            item['address_kind'] = 'direct'
        elif item['base'] == 16 and item['byte_offset'] == 0:
            recipe = large_address(words, pc, entries)
            if recipe is None:
                continue
            start, item['byte_offset'] = recipe
            item['address_kind'] = 'large'
            for at in range(start, pc):
                assert at not in addresses
                addresses[at] = pc
        else:
            continue
        item['slot'], half = divmod(item['byte_offset'], 16)
        item['half'] = 'high' if half else 'low'
        item['zero_store'] = item['direction'] == 'store' and item['payload'] == 31
        accesses[pc] = item
    return accesses, addresses
