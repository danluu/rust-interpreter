"""Exact adopted small-frame padding helper, separate from payload stores."""
import struct

WORDS = [0x8b15004c, 0xeb0c017f, 0x54000160,
         0xcb0b0189, 0xd280020a, 0xeb0a013f, 0x54000063, 0xa8817d7f,
         0x17fffffb, 0xeb0c017f, 0x54000060, 0x3800157f, 0x17fffffd]
PATTERN = struct.pack('<13I', *WORDS)


def matches(data):
    assert len(data) % 4 == 0
    return [i for i in range(0, len(data) - len(PATTERN) + 1, 4)
            if data[i:i + len(PATTERN)] == PATTERN]


def classify_layout(row):
    ca, size, a, payload = [row[k] for k in
        ['caller_frame_align', 'caller_frame_size', 'callee_frame_align', 'callee_frame_size']]
    assert ca > 0 and ca & (ca - 1) == 0
    assert a > 0 and a & (a - 1) == 0
    assert size >= 0 and payload >= 0
    if max(payload, 1) > 256:
        return 'large_payload'
    if ca >= a and max(size, 1) % a == 0:
        return 'fixed_payload'
    return 'bounded_padding' if a <= 16 else 'large_alignment_padding'


def controls():
    assert matches(PATTERN) == [0]
    assert matches(bytes(4) + PATTERN + PATTERN) == [4, 56]
    assert matches(b'X' + PATTERN + bytes(3)) == []
    for i in range(len(WORDS)):
        words = WORDS.copy()
        words[i] ^= 1
        assert matches(struct.pack('<13I', *words)) == []
    def row(ca, size, a, payload):
        return dict(caller_frame_align=ca, caller_frame_size=size,
                    callee_frame_align=a, callee_frame_size=payload)
    cases = [(row(16, 120, 16, 40), 'bounded_padding'),
             (row(16, 153, 16, 40), 'bounded_padding'),
             (row(16, 160, 16, 40), 'fixed_payload'),
             (row(1, 160, 16, 40), 'bounded_padding'),
             (row(16, 0, 16, 0), 'bounded_padding'),
             (row(16, 1, 64, 40), 'large_alignment_padding'),
             (row(16, 160, 16, 257), 'large_payload')]
    for layout, expected in cases:
        assert classify_layout(layout) == expected
    # The empty skip branch must jump over all ten helper words, not payload.
    assert (WORDS[2] >> 5) & 0x7ffff == 11
    return dict(pattern_words=13, mutated_words_rejected=13,
                unaligned_pattern_rejected=True, layout_cases=len(cases),
                exact_empty_skip_target=True)
