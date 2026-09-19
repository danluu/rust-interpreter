"""Recognize complete ordinary setup plus exact baseline/candidate clear bodies."""
import struct

PADDING = [0x8b15004c,0xeb0c017f,0x54000160,0xcb0b0189,0xd280020a,
           0xeb0a013f,0x54000063,0xa8817d7f,0x17fffffb,0xeb0c017f,
           0x54000060,0x3800157f,0x17fffffd]
MARKER = struct.pack('<I',0x8b03004b)
TAIL = {a: (opcode | ((512-a)<<12) | (12<<5) | 31)
        for a,opcode in [(2,0x78000000),(4,0xb8000000),(8,0xf8000000)]}
TAIL[16] = 0xa93f7d9f


def pack(words):
    return struct.pack('<'+'I'*len(words),*words)


def fixed(payload):
    assert 1 <= payload <= 256
    result = [0xa9000000 | ((off//8)<<15) | (31<<10) | (11<<5) | 31
              for off in range(0,payload//16*16,16)]
    offset = payload//16*16
    for width,opcode in [(8,0xf9000000),(4,0xb9000000),(2,0x79000000),(1,0x39000000)]:
        if payload-offset >= width:
            result.append(opcode | ((offset//width)<<10) | (11<<5) | 31)
            offset += width
    assert offset == payload
    return result


def pattern(payload, alignment=None):
    setup = [0x8b03004b,0xd2800009 | (payload<<5),0x8b0902a3,0x8b03004c]
    if alignment is None: return pack(setup+PADDING+fixed(payload))
    assert alignment in TAIL and alignment <= payload <= 256
    return pack(setup+fixed(payload)+[TAIL[alignment]])


def find(data):
    found = []
    pos = -1
    while True:
        pos = data.find(MARKER,pos+1)
        if pos < 0: break
        if pos % 4 or pos+16 > len(data): continue
        immediate, = struct.unpack_from('<I',data,pos+4)
        if immediate & 0xffe0001f != 0xd2800009: continue
        payload = (immediate >> 5) & 0xffff
        if not 1 <= payload <= 256: continue
        candidates = [('general',None),*[('overlap',a) for a in TAIL if a <= payload]]
        for kind,alignment in candidates:
            candidate = pattern(payload,alignment)
            if data[pos:pos+len(candidate)] == candidate:
                found.append((pos,len(candidate),kind,payload,alignment))
    assert len({r[0] for r in found}) == len(found)
    return found


def controls():
    shapes = mutations = 0
    for payload in range(1,257):
        for alignment in [None,*[a for a in TAIL if a <= payload]]:
            data = pattern(payload,alignment)
            kind = 'general' if alignment is None else 'overlap'
            assert find(data) == [(0,len(data),kind,payload,alignment)]
            assert find(bytes(4)+data) == [(4,len(data),kind,payload,alignment)]
            assert not find(b'X'+data)
            assert not find(data[:-4])
            for i in range(0,len(data),4):
                bad = bytearray(data);bad[i] ^= 1
                assert not find(bytes(bad))
                mutations += 1
            if alignment is not None:
                assert len(pattern(payload))-len(data) == 48
            shapes += 1
    return dict(complete_shapes=shapes,mutated_words_rejected=mutations,
                unaligned_and_truncated_rejected=True,exact_shrinkage_bytes=48)
