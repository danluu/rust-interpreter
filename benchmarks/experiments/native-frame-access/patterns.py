"""Exact adopted private-frame sequences; a census, never a code rewriter."""

# Source: adopted resumable_call/resumable_return and their asserted layouts.
# Offsets describe the two memory instructions, not an assumed removed sample.
PATTERNS = {
    'call_function_pc': ('Call', (0xf9000289, 0xf900069f), (0, 1)),
    'call_base_register': ('Call', (0xf9000a95, 0xf9401269, 0xf9000e89), (0, 2)),
    'return_base_register': ('Return',
        (0xf9400e89, 0xd37ced29, 0xf9402660, 0x8b090000, 0xf9400a81), (0, 4)),
}


def recognize(words, operation, base=0):
    assert operation in {'Call', 'Return'}
    assert type(base) is int and 0 <= base <= 16*1024**2 and base % 4 == 0
    assert len(words) <= 16*1024**2//4 and base+4*len(words) <= 16*1024**2
    assert all(type(w) is int and 0 <= w < 2**32 for w in words)
    result=[]
    for name,(kind,pattern,memory) in PATTERNS.items():
        if operation != kind: continue
        for index in range(len(words)-len(pattern)+1):
            if tuple(words[index:index+len(pattern)]) == pattern:
                result.append(dict(kind=name,offset=base+index*4,end=base+(index+len(pattern))*4,
                    memory_offsets=[base+(index+i)*4 for i in memory],prospective_words_saved=1))
    result.sort(key=lambda row:row['offset'])
    assert all(a['end'] <= b['offset'] for a,b in zip(result,result[1:]))
    return result


def classify(offsets, candidates):
    assert offsets and all(type(x) is int and x >= 0 and x % 4 == 0 for x in offsets)
    labels={candidates.get(x) for x in offsets}
    if labels == {None}: return 'other',None
    if len(labels)==1: return 'certain',next(iter(labels))
    return 'ambiguous',None
