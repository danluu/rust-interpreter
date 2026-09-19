"""Exact current-helper recognition and a bounded proposed-tail ISA model."""
import struct

OLD_WORDS = [0xcb0b0189,0xd280020a,0xeb0a013f,0x54000063,0xa8817d7f,
             0x17fffffb,0xeb0c017f,0x54000060,0x3800157f,0x17fffffd]
OLD = struct.pack('<10I',*OLD_WORDS)
TAIL = [0xb4000129,0x36180049,0xf800857f,0x36100049,0xb800457f,
        0x36080049,0x7800257f,0x36000049,0x3800157f]
ASM = '''.text
.p2align 2
_short_clear_tail:
    cbz x9, done
    tbz x9, #3, four
    str xzr, [x11], #8
four:
    tbz x9, #2, two
    str wzr, [x11], #4
two:
    tbz x9, #1, one
    strh wzr, [x11], #2
one:
    tbz x9, #0, done
    strb wzr, [x11], #1
done:
'''


def helpers(code):
    assert len(code)%4 == 0
    matches,at = [],0
    while True:
        at = code.find(OLD,at)
        if at < 0: return matches
        if at%4 == 0: matches.append(at)
        at += 1


def tail_machine(words, remaining, memory, pointer):
    """Decode the actual CBZ/TBZ/STR encodings, not the emitter's length loop."""
    assert 0 <= remaining < 16
    pc,steps = 0,0
    stores = {0xf8000000:8,0xb8000000:4,0x78000000:2,0x38000000:1}
    while pc < len(words):
        assert 0 <= pc and steps < 16
        word = words[pc]
        steps += 1
        if word & 0xff00001f == 0xb4000009:
            delta = (word>>5)&0x7ffff
            if delta & 0x40000: delta -= 0x80000
            pc += delta if remaining == 0 else 1
        elif word & 0x7f00001f == 0x36000009:
            bit = ((word>>19)&31)|((word>>26)&32)
            delta = (word>>5)&0x3fff
            if delta & 0x2000: delta -= 0x4000
            pc += delta if remaining & (1<<bit) == 0 else 1
        else:
            size = stores.get(word & 0xffe00000)
            assert size is not None and word & 0xc1f == 0x41f and (word>>5)&31 == 11
            advance = (word>>12)&0x1ff
            if advance & 0x100: advance -= 0x200
            assert advance == size and 0 <= pointer <= len(memory)-size
            for offset in range(size): memory[pointer+offset] = 0
            pointer += advance
            pc += 1
    assert pc == len(words)
    return pointer,steps


def controls():
    assert helpers(OLD) == [0]
    assert helpers(bytes(4)+OLD+OLD) == [4,44]
    assert helpers(bytes(1)+OLD+bytes(3)) == []
    for i in range(10):
        changed = OLD_WORDS.copy();changed[i] ^= 1
        assert helpers(struct.pack('<10I',*changed)) == []
    max_steps = {}
    for remaining in range(16):
        for start in range(64,128):
            actual = bytearray([0xa5]*(start+remaining+64))
            expected = actual.copy();expected[start:start+remaining] = bytes(remaining)
            end,steps = tail_machine(TAIL,remaining,actual,start)
            assert actual == expected and end == start+remaining
            max_steps[str(remaining)] = steps
    # A true empty, one-past-end range must perform no store.
    memory = bytearray([0x5a]*16)
    assert tail_machine(TAIL,0,memory,len(memory)) == (16,1) and memory == bytearray([0x5a]*16)
    # Mutation demonstrates that the byte oracle catches an overwide store.
    changed = TAIL.copy();changed[-1] = 0xb800457f
    memory = bytearray([0xa5]*64)
    end,_ = tail_machine(changed,1,memory,16)
    assert end != 17 and memory[17] == 0
    return dict(pattern_mutations=10,unaligned_pattern_rejected=True,canary_cases=1024,
        empty_one_past_end=True,overwide_mutation_detected=True,tail_steps=max_steps)
