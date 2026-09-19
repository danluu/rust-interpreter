"""Independent integer and byte oracle for a layout-bounded scalar clear."""
from math import gcd


def alignment(caller_align, caller_size):
    assert caller_align > 0 and caller_align & (caller_align - 1) == 0
    assert caller_size >= 0
    return gcd(caller_align, max(caller_size, 1))


def widths(caller_align, caller_size, callee_align):
    assert callee_align > 0 and callee_align & (callee_align - 1) == 0
    minimum = alignment(caller_align, caller_size)
    if minimum >= callee_align:
        return []
    if callee_align > 16:
        return None
    return [w for w in [8, 4, 2, 1] if minimum <= w < callee_align]


def controls():
    aligns = [1, 2, 4, 8, 16, 32, 64, 256, 4096]
    sizes = [0, 1, 2, 3, 4, 7, 8, 15, 16, 24, 31, 64, 120, 128, 256, 511, 512, 513]
    histories = canaries = 0

    # Division/ceiling is intentionally independent of the runtime bit-mask.
    def rounded(n, a):
        return ((n + a - 1) // a) * a

    for ca in aligns:
        for size in sizes:
            d = alignment(ca, size)
            for base in [0, ca, 7 * ca, 1024 * ca]:
                initial = base + max(size, 1)
                assert initial % d == 0
                ends = [initial]
                for first in aligns:
                    for second in aligns:
                        ends.append(rounded(rounded(initial, first), second))
                end = initial
                for a in (aligns + aligns[::-1]) * 8:
                    end = rounded(end, a)
                    ends.append(end)
                for end in ends:
                    assert end % d == 0
                    for a in aligns:
                        padding = rounded(end, a) - end
                        assert 0 <= padding < a
                        assert padding % min(d, a) == 0
                        if d >= a:
                            assert padding == 0
                        else:
                            assert padding <= a - d
                        histories += 1
            for a in aligns:
                allowed = widths(ca, size, a)
                if allowed is None:
                    continue
                for padding in range(0, a, min(d, a)):
                    selected = [w for w in allowed if padding & w]
                    assert sum(selected) == padding
                    for offset in range(16):
                        start = 32 + offset
                        actual = bytearray([0xa5] * (start + padding + 32))
                        expected = actual.copy()
                        expected[start:start + padding] = bytes(padding)
                        cursor = start
                        for width in selected:
                            actual[cursor:cursor + width] = bytes(width)
                            cursor += width
                        assert cursor == start + padding and actual == expected
                        canaries += 1

    # A frame with size0 reserves one byte, not an aligned empty extent.
    assert alignment(16, 0) == 1 and widths(16, 0, 16) == [8, 4, 2, 1]
    assert widths(16, 120, 16) == [8]
    assert rounded(120, 16) - 120 == 8
    assert rounded(rounded(120, 32), 16) - rounded(120, 32) == 0
    # Missing base alignment invalidates the proposed8-byte-only store.
    assert rounded(1 + 120, 16) - (1 + 120) == 7
    # Missing extent divisibility also invalidates it.
    assert rounded(16 + 1, 16) - (16 + 1) == 15
    assert widths(1, 120, 32) is None
    assert widths(64, 128, 32) == []
    # Invalid alignment and negative extent must fail closed.
    rejected = 0
    for args in [(0, 120, 16), (3, 120, 16), (16, -1, 16), (16, 120, 3), (16, 120, 0)]:
        try:
            widths(*args)
        except AssertionError:
            rejected += 1
        else:
            raise AssertionError(args)
    assert rejected == 5
    return dict(history_cases=histories, byte_canary_cases=canaries,
                invalid_layouts_rejected=rejected, zero_frame_and_missing_hypotheses_checked=True)
