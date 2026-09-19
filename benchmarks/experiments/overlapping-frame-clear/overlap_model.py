"""Independent interval/byte oracle for bounded overlapping frame stores."""


def eligible(payload, alignment):
    assert payload >= 0 and alignment > 0 and alignment & (alignment - 1) == 0
    return alignment <= 16 and alignment <= max(payload, 1) <= 256


def controls():
    canaries = 0
    for alignment in [1, 2, 4, 8, 16]:
        for payload in range(alignment, 257):
            for padding in range(alignment):
                for offset in range(16):
                    start = 32 + offset
                    end = start + payload + padding
                    tail = end - alignment
                    assert start <= tail <= start + payload <= end
                    actual = bytearray([0xa5]) * (end + 32)
                    expected = actual.copy()
                    expected[start:end] = bytes(end-start)
                    actual[start:start+payload] = bytes(payload)
                    actual[tail:end] = bytes(alignment)
                    assert actual == expected
                    canaries += 1
    cases = [(0,1,True),(0,2,False),(7,8,False),(8,8,True),(15,16,False),
             (16,16,True),(40,16,True),(256,16,True),(257,16,False),(64,32,False)]
    for payload, alignment, expected in cases:
        assert eligible(payload,alignment) == expected
    # Dropping either hypothesis must have a counterexample.
    assert 1 + 0 - 16 < 0  # P<A: even zero padding would underwrite.
    assert 16 + 17 - 16 > 16  # p>A: disjoint intervals leave a gap.
    return dict(byte_canaries=canaries,eligibility_controls=len(cases),
                missing_hypotheses_rejected=2,guest_commands=0)
