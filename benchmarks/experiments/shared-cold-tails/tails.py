"""Exact adopted-tail recognizer and bounded intra-function census model."""

# Exact resumable return_to_vm: publish memory/budget, restore the external
# host frame, RET x30. This is a source-pinned byte pattern, not a disassembler.
EPILOGUE = (0xf9000a63, 0xf9000276, 0xa94157f4, 0xa9427ff6, 0xa94363f7,
            0xa9446bf9, 0xa94573fb, 0xa8c67bf3, 0xd65f03c0)


def eligible(words):
    words = tuple(words)
    if len(words) < len(EPILOGUE) + 1 or words[-len(EPILOGUE):] != EPILOGUE:
        return False
    prefix = words[:-len(EPILOGUE)]
    # The original emitter starts with MOVZ x0, then ascending nonzero MOVKs.
    if len(prefix) > 4 or prefix[0] & 0xffe0001f != 0xd2800000:
        return False
    last = 0
    for word in prefix[1:]:
        shift = (word >> 21) & 3
        if word & 0xff80001f != 0xf2800000 or shift <= last or (word >> 5) & 65535 == 0:
            return False
        last = shift
    return True


def branch_word(source, target):
    assert type(source) is int and type(target) is int
    assert source >= 0 and target >= 0 and source % 4 == target % 4 == 0
    delta = (target - source) // 4
    return 0x14000000 | (delta & 0x3ffffff) if -(1 << 25) <= delta < (1 << 25) else None


def census(tails, maximum_keys=256):
    assert 0 <= maximum_keys <= 256
    retained, replacements, declined = {}, [], 0
    previous_end = 0
    for offset, words in tails:
        words = tuple(words)
        assert offset >= previous_end and offset % 4 == 0
        previous_end = offset + len(words) * 4
        if not eligible(words):
            declined += 1
            continue
        target = retained.get(words)
        jump = None if target is None else branch_word(offset, target)
        if jump is not None:
            replacements.append(dict(offset=offset, target=target, original_words=len(words),
                                     branch_word=jump, saved_bytes=(len(words)-1)*4))
        elif len(retained) < maximum_keys:
            retained[words] = offset
        else:
            declined += 1
    return dict(replacements=replacements, retained_tails=len(retained), declined=declined,
                saved_bytes=sum(r['saved_bytes'] for r in replacements))
