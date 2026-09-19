"""Recognize only complete baseline and bounded scalar-padding instruction runs."""
import struct

GENERAL = struct.pack('<12I', 0x8b03004b, 0x8b15004c,
    0xcb0b0189, 0xd280020a, 0xeb0a013f, 0x54000063, 0xa8817d7f, 0x17fffffb,
    0xeb0c017f, 0x54000060, 0x3800157f, 0x17fffffd)
STORES = {8: 0xf800857f, 4: 0xb800457f, 2: 0x7800257f, 1: 0x3800157f}


def patterns():
    found = {}
    for alignment in [2, 4, 8, 16]:
        for minimum in [1, 2, 4, 8]:
            if minimum >= alignment:
                continue
            widths = tuple(w for w in [8, 4, 2, 1] if minimum <= w < alignment)
            tail = []
            for w in widths:
                if len(widths) != 1:
                    tail.append(0x36000000 | ((w.bit_length() - 1) << 19) | (2 << 5) | 9)
                tail.append(STORES[w])
            words = [0x8b03004b, 0xcb0302a9, 0xb4000009 | ((1 + len(tail)) << 5), *tail]
            data = struct.pack('<' + 'I' * len(words), *words)
            assert data not in found
            found[data] = widths
    assert len(found) == 10
    return found


BOUNDED = patterns()


def matches(data, pattern):
    return [i for i in range(0, len(data) - len(pattern) + 1, 4) if data[i:i + len(pattern)] == pattern]


def bounded_matches(data):
    found = [(i, len(pattern), widths) for pattern, widths in BOUNDED.items() for i in matches(data, pattern)]
    return sorted(found)


def controls():
    mutations = 0
    for pattern, widths in BOUNDED.items():
        assert bounded_matches(pattern) == [(0, len(pattern), widths)]
        assert not matches(pattern, GENERAL)
        assert not bounded_matches(b'X' + pattern)
        for offset in range(0, len(pattern), 4):
            mutated = bytearray(pattern)
            mutated[offset] ^= 1
            assert not bounded_matches(mutated)
            mutations += 1
    assert not bounded_matches(GENERAL)
    assert matches(GENERAL, GENERAL) == [0]
    assert not matches(b'X' + GENERAL, GENERAL)
    return dict(bounded_shapes=10, mutated_words_rejected=mutations,
                general_and_unaligned_patterns_rejected=True)
