"""Conservative CFG path-cost bounds for our retained AArch64 scalar bodies.

This reads machine words as data. Conditions are independent alternatives; no
register values, memory, guest code, or generated code are executed.
"""
from collections import deque

LIMIT = 65536
RET = 0xD65F03C0
ZERO_STATUS = 0xAA1F03E9
LOADS = {0x39400000, 0x79400000, 0xB9400000, 0xF9400000}
STORES = {0x39000000, 0x79000000, 0xB9000000, 0xF9000000}


def signed(value, bits):
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def successors(word, pc, length):
    if word == RET:
        return []
    if word & 0xFC000000 == 0x14000000:
        result = [pc + signed(word & 0x3FFFFFF, 26)]
    elif word & 0xFF000010 == 0x54000000:
        if word & 15 >= 14:
            raise ValueError('unsupported conditional encoding')
        result = [pc + signed((word >> 5) & 0x7FFFF, 19), pc + 1]
    else:
        # Reject every unrecognized branch/exception/system encoding, including
        # indirect branches, calls, compare/test branches and non-LR returns.
        if word & 0x1C000000 == 0x14000000:
            raise ValueError('unsupported control instruction')
        result = [pc + 1]
    if any(n < 0 or n >= length for n in result):
        raise ValueError('external edge or falloff')
    return list(dict.fromkeys(result))


def category(word):
    if word == RET or word & 0xFC000000 == 0x14000000 or word & 0xFF000010 == 0x54000000:
        return 'control'
    opcode = word & 0xFFC00000
    if opcode in LOADS | STORES:
        space = 'sp_relative' if (word >> 5) & 31 == 31 else 'other_base'
        return space + ('_load' if opcode in LOADS else '_store')
    return 'other'


def graph(words):
    if not 0 < len(words) <= LIMIT:
        raise ValueError('word limit')
    edges = [successors(w, pc, len(words)) for pc, w in enumerate(words)]
    parents = [[] for _ in words]
    for pc, targets in enumerate(edges):
        for n in targets:
            parents[n].append(pc)
    # Prune only the impossible fallthrough of the emitter's unconditional
    # Trap. The exact CMP must be the branch's only predecessor; no incoming
    # edge may bypass its known flag definition. All other cycles still decline.
    for pc, word in enumerate(words):
        if (pc > 0 and word & 0xFF00001F == 0x54000000
                and words[pc-1] == 0xEB1F03FF and parents[pc] == [pc-1]):
            edges[pc] = edges[pc][:1]
    parents = [[] for _ in words]
    for pc, targets in enumerate(edges):
        for n in targets:
            parents[n].append(pc)
    pending = list(map(len, parents))
    queue = deque(i for i, n in enumerate(pending) if n == 0)
    order = []
    while queue:
        pc = queue.popleft()
        order.append(pc)
        for n in edges[pc]:
            pending[n] -= 1
            if pending[n] == 0:
                queue.append(n)
    if len(order) != len(words):
        raise ValueError('cyclic machine CFG')
    status = {}
    for pc, word in enumerate(words):
        if word != RET:
            continue
        if pc == 0 or parents[pc] != [pc - 1]:
            raise ValueError('return bypasses status assignment')
        previous = words[pc - 1]
        if previous == ZERO_STATUS:
            status[pc] = 0
        elif previous & 0xFFE0001F == 0xD2800009:
            status[pc] = (previous >> 5) & 0xFFFF
        else:
            raise ValueError('unknown return status')
        if status[pc] not in [0, 1, 2]:
            raise ValueError('unknown return contract')
    return edges, order, status


def costs(words):
    edges, order, status = graph(words)
    can_replay = [False] * len(words)
    for pc in reversed(order):
        can_replay[pc] = status.get(pc) == 1 or any(can_replay[n] for n in edges[pc])
    labels = [category(w) for w in words]
    keys = ['words', *sorted(set(labels)), 'replay_reachable_words', 'replay_unreachable_words']
    result = {}
    for key in keys:
        low, high = [None] * len(words), [None] * len(words)
        for pc in reversed(order):
            charge = int(key == 'words' or labels[pc] == key or
                         key == ('replay_reachable_words' if can_replay[pc] else 'replay_unreachable_words'))
            if status.get(pc) == 0:
                low[pc] = high[pc] = charge
            else:
                targets = [n for n in edges[pc] if low[n] is not None]
                if targets:
                    low[pc] = charge + min(low[n] for n in targets)
                    high[pc] = charge + max(high[n] for n in targets)
        if low[0] is None:
            raise ValueError('no CFG path to success')
        result[key] = dict(min=low[0], max=high[0])
    return dict(static_words=len(words), bounds=result,
                return_statuses=sorted(set(status.values())))


def word_delta(before, after):
    """Describe changes only; offset similarity is not equivalence or timing."""
    if len(before) != len(after):
        return dict(equal_words=False, same_word_count=False, shifted_sp_accesses=[], other_changes=[])
    shifted, other = [], []
    for pc, (a, b) in enumerate(zip(before, after)):
        if a == b:
            continue
        mask = 0xFFF << 10
        if (a & 0xFFC00000 in {0xF9000000, 0xF9400000}
                and (a >> 5) & 31 == 31 and a & ~mask == b & ~mask
                and ((b >> 10) & 0xFFF) - ((a >> 10) & 0xFFF) == 6):
            shifted.append(pc)
        else:
            other.append(dict(pc=pc, before=f'{a:08x}', after=f'{b:08x}'))
    return dict(equal_words=not shifted and not other, same_word_count=True,
                shifted_sp_accesses=shifted, other_changes=other)
