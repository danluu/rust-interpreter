"""Exact existing large-frame helper and independently bounded word ownership."""
import struct

WORDS = [0xcb0b0189,0xd280080a,0xa9007d7f,0xa9017d7f,0xa9027d7f,0xa9037d7f,
         0x9101016b,0xd1010129,0xeb0a013f,0x54ffff22,
         0xcb0b0189,0xd280020a,0xeb0a013f,0x54000063,0xa8817d7f,0x17fffffb,
         0xeb0c017f,0x54000060,0x3800157f,0x17fffffd]
PATTERN = struct.pack('<20I',*WORDS)


def matches(data):
    assert len(data)%4 == 0
    return [i for i in range(0,len(data)-len(PATTERN)+1,4) if data[i:i+len(PATTERN)] == PATTERN]


def part(relative):
    assert relative%4 == 0 and relative < 80
    if relative < 0: return 'ordinary_setup'
    word = relative//4
    if word < 2: return 'batch_setup'
    if word < 6: return 'batch_store'
    if word < 10: return 'batch_control'
    if word < 16: return 'chunk_store' if word == 14 else 'chunk_control'
    return 'byte_store' if word == 18 else 'byte_control'


def displacement(word,bits,shift):
    value = (word>>shift)&((1<<bits)-1)
    return value-(1<<bits) if value>>(bits-1) else value


def controls():
    assert matches(PATTERN) == [0]
    assert matches(bytes(8)+PATTERN+PATTERN) == [8,88]
    assert not matches(b'X'+PATTERN+bytes(3))
    assert not matches(PATTERN[:-4])
    for i in range(20):
        bad = WORDS.copy();bad[i] ^= 1
        assert not matches(struct.pack('<20I',*bad))
    assert 9+displacement(WORDS[9],19,5) == 2
    assert 13+displacement(WORDS[13],19,5) == 16
    assert 15+displacement(WORDS[15],26,0) == 10
    assert 17+displacement(WORDS[17],19,5) == 20
    assert 19+displacement(WORDS[19],26,0) == 16
    from collections import Counter
    ownership = dict(Counter(part(i*4) for i in range(20)))
    assert ownership == dict(batch_setup=2,batch_store=4,batch_control=4,chunk_control=5,chunk_store=1,byte_control=3,byte_store=1)
    assert part(-4) == 'ordinary_setup'
    return dict(pattern_words=20,mutated_words_rejected=20,exact_branch_targets=5,
                word_partition=ownership,unaligned_and_truncated_rejected=True)
