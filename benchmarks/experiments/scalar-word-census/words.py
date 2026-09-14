"""Bounded recognizer for the source-pinned scalar emitter, not a disassembler."""
from collections import Counter, deque
from dataclasses import dataclass

FLAGS = 32
VECTOR = 33
MAX_WORDS = 65536


def reg(n, sp=False):
    return 1 << n if n != 31 or sp else 0


@dataclass(frozen=True)
class Word:
    reads: int
    writes: int
    pure: bool
    successors: tuple
    kind: str


def decode(w, pc, length):
    rd, rn, rm = w & 31, (w >> 5) & 31, (w >> 16) & 31
    fall = (pc + 1,)

    def item(reads, writes, kind, pure=True, successors=fall):
        assert all(0 <= p < length for p in successors), 'external edge or falloff'
        return Word(reads, writes, pure, successors, kind)

    if w == 0xd65f03c0:  # RET x30; scalar ABI result is x0.
        preserved = sum(1 << r for r in [*range(4, 9), *range(18, 32)])
        return item(reg(0) | preserved, 0, 'return', False, ())
    if w & 0xfc000000 == 0x14000000:
        delta = w & 0x3ffffff
        if delta & (1 << 25): delta -= 1 << 26
        return item(0, 0, 'branch', False, (pc + delta,))
    if w & 0xff000010 == 0x54000000:
        delta = (w >> 5) & 0x7ffff
        if delta & (1 << 18): delta -= 1 << 19
        assert w & 15 < 14, 'unsupported unconditional condition'
        return item(1 << FLAGS, 0, 'condition', False, (pc + delta, pc + 1))
    if w & 0xff800000 in (0xd2800000, 0xf2800000):
        keep = w & 0xff800000 == 0xf2800000
        return item(reg(rd) if keep else 0, reg(rd), 'movk' if keep else 'movz')
    if w & 0xffc00000 in (0xf9000000, 0xf9400000):
        load = w & 0xffc00000 == 0xf9400000
        return item(reg(rn, True) | (0 if load else reg(rd)), reg(rd) if load else 0,
                    'load' if load else 'store', False)
    if w & 0xff800000 in (0x91000000, 0xd1000000):
        return item(reg(rn, True), reg(rd, True), 'addsub_immediate', rd != 31)
    if w & 0xffc00000 in (0x93400000, 0xd3400000):
        assert w & (1 << 22), 'invalid 64-bit bitfield'
        return item(reg(rn), reg(rd), 'bitfield')
    if w & 0xffe00000 == 0x93c00000:
        return item(reg(rn) | reg(rm), reg(rd), 'extract')
    # Shifted-register operations. Register 31 denotes XZR, including CMP.
    if w & 0xff200000 in (0x8a000000, 0xaa000000, 0xaa200000, 0xca000000,
                          0x8b000000, 0xcb000000, 0xab000000, 0xeb000000):
        flags = w & 0xff200000 in (0xab000000, 0xeb000000)
        return item(reg(rn) | reg(rm), reg(rd) | ((1 << FLAGS) if flags else 0),
                    'register_flags' if flags else 'register')
    if w & 0xffe00c00 in (0x9a800000, 0x9a800400):
        return item(reg(rn) | reg(rm) | (1 << FLAGS), reg(rd), 'select')
    if w & 0xfffffc00 in (0xdac00000, 0xdac00c00, 0xdac01000):
        return item(reg(rn), reg(rd), 'unary')
    if w & 0xffe0fc00 in (0x9ac00800, 0x9ac00c00, 0x9ac02000, 0x9ac02400,
                          0x9ac02800, 0x9ac02c00, 0x1ac02c00):
        return item(reg(rn) | reg(rm), reg(rd), 'division_or_shift')
    if w & 0xffe08000 in (0x9b000000, 0x9b008000):
        return item(reg(rn) | reg(rm) | reg((w >> 10) & 31), reg(rd), 'multiply_add')
    if w & 0xffe0fc00 in (0x9b407c00, 0x9bc07c00):
        return item(reg(rn) | reg(rm), reg(rd), 'multiply_high')
    # The only SIMD sequence emitted: FMOV d0,x9; CNT; ADDV; UMOV w9.
    vectors = {0x9e670120: (reg(9), 1 << VECTOR),
               0x0e205800: (1 << VECTOR, 1 << VECTOR),
               0x0e31b800: (1 << VECTOR, 1 << VECTOR),
               0x0e013c09: (1 << VECTOR, reg(9))}
    if w in vectors:
        return item(*vectors[w], 'vector')
    raise AssertionError(f'unknown scalar word {w:08x} at {pc}')


def analyze(words):
    assert 0 < len(words) <= MAX_WORDS
    ops = [decode(w, pc, len(words)) for pc, w in enumerate(words)]
    # Prove the complete machine CFG acyclic, including unused failure tails.
    predecessors = [[] for _ in ops]
    for pc, op in enumerate(ops):
        for target in set(op.successors): predecessors[target].append(pc)
    pending = list(map(len, predecessors))
    queue = deque(pc for pc, n in enumerate(pending) if n == 0)
    order = []
    while queue:
        pc = queue.popleft(); order.append(pc)
        for target in set(ops[pc].successors):
            pending[target] -= 1
            if pending[target] == 0: queue.append(target)
    assert len(order) == len(ops), 'cyclic scalar machine CFG'
    reachable = {0}
    for pc in order:
        if pc in reachable: reachable.update(ops[pc].successors)
    # Removing pure dead definitions can expose their operands as dead. One
    # reverse topological pass propagates the final liveness through a DAG.
    live = [0] * len(ops)
    dead = set()
    for pc in reversed(order):
        op = ops[pc]
        out = 0
        for successor in op.successors: out |= live[successor]
        if op.pure and op.writes and not op.writes & out:
            dead.add(pc); live[pc] = out
        else: live[pc] = op.reads | (out & ~op.writes)
    dead &= reachable
    # Keep failure returns out of the successful-call path bounds. Every
    # return must have the exact immediately preceding scalar ABI status.
    bounds = [None] * len(ops)
    returns = []
    for pc in reversed(order):
        op = ops[pc]
        if op.kind == 'return':
            assert pc > 0 and words[pc - 1] in (0xaa1f03e0, 0xd2800020), 'unknown return status'
            if words[pc - 1] == 0xaa1f03e0:
                bounds[pc] = (0, 0); returns.append(pc)
        else:
            following = [bounds[s] for s in op.successors if bounds[s] is not None]
            if following:
                cost = int(pc in dead)
                bounds[pc] = (min(p[0] for p in following) + cost,
                              max(p[1] for p in following) + cost)
    kinds = Counter(ops[pc].kind for pc in dead)
    destinations = Counter(str((words[pc] & 31)) for pc in dead)
    return dict(words=len(words), reachable_words=len(reachable), dead_words=len(dead),
                dead_word_offsets=sorted(dead), by_kind=dict(kinds), by_destination=dict(destinations),
                successful_returns=len(returns), successful_path_bounds=bounds[0])
