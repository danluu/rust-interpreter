"""Diagnostic normal-return CFG, not a compiler proof or alias analysis."""
from bisect import bisect_right
from collections import Counter
import re

LIMIT = 1_000_000
FALLTHROUGH = set('Local Imm Binary Copy Load Store Cast Call Assert FillBytes Select '
    'CopyDynamic CallIndirect Unary CompareBytes Deallocate Reallocate CpuFeatureQuery '
    'Allocate CAllocate RegisterTlsDestructor CAlignedAllocate '
    'RandomBytes CDeallocate'.split())
CALLS = {'Call', 'CallIndirect'}
MEMORY = set('Copy Load Store FillBytes CopyDynamic CompareBytes'.split())
EFFECTS = set('Deallocate Reallocate CpuFeatureQuery ResetThreadLocals Allocate '
    'CAllocate RegisterTlsDestructor CAlignedAllocate RandomBytes CDeallocate'.split())


def successors(text, pc, length):
    """Parse exact branch renderings; other known opcodes may return normally.

    Calls/assertions/memory faults can terminate execution. Their normal-return
    edges overapproximate possible cycles. This cannot establish optimization
    safety, termination, dynamic branch direction, or alias properties.
    """
    if not (type(pc) is int and type(length) is int and 0 <= pc < length <= LIMIT):
        raise ValueError('invalid operation bounds')
    variant = text.split(' ', 1)[0]
    if text == 'Return' or re.fullmatch(r'Trap \{ message: "(?:[^"\\]|\\.)*" \}', text):
        return (), True
    match = re.fullmatch(r'Jump \{ target: ([0-9]+) \}', text)
    if match:
        targets = [int(match[1])]
    else:
        match = re.fullmatch(r'Switch \{ value: ([0-9]+), cases: \[(.*)\], otherwise: ([0-9]+) \}', text)
        if match:
            body = match[2]
            pairs = [] if not body else body.split('), (')
            if body:
                if not body.startswith('(') or not body.endswith(')'):
                    raise ValueError('invalid switch pairs')
                pairs = body[1:-1].split('), (')
            targets = [int(match[3])]
            seen_values = set()
            for pair in pairs:
                item = re.fullmatch(r'([0-9]+), ([0-9]+)', pair)
                if item is None or int(item[1]) >= 2**128:
                    raise ValueError('invalid switch pair/value')
                value, target = int(item[1]), int(item[2])
                if not 0 <= target < length:
                    raise ValueError('branch target out of range')
                if value not in seen_values:
                    targets.append(target)
                    seen_values.add(value)
        elif text == 'ResetThreadLocals' or (variant in FALLTHROUGH and text.startswith(variant + ' { ') and text.endswith(' }')):
            if pc + 1 >= length:
                raise ValueError('normal-return edge falls off function')
            return (pc + 1,), False
        else:
            raise ValueError('unknown or malformed operation: ' + text[:120])
    if any(target < 0 or target >= length for target in targets):
        raise ValueError('branch target out of range')
    return tuple(sorted(set(targets))), True


def components(edges):
    """Iterative Kosaraju; bounded O(vertices + edges), no recursive stack."""
    n = len(edges)
    if not 0 < n <= LIMIT or sum(map(len, edges)) > 4 * LIMIT:
        raise ValueError('graph exceeds budget')
    reverse = [[] for _ in edges]
    for source, targets in enumerate(edges):
        for target in targets:
            if type(target) is not int or not 0 <= target < n:
                raise ValueError('invalid graph edge')
            reverse[target].append(source)
    seen, finish = set(), []
    for start in range(n):
        if start in seen:
            continue
        seen.add(start)
        stack = [(start, iter(edges[start]))]
        while stack:
            vertex, targets = stack[-1]
            target = next(targets, None)
            if target is None:
                finish.append(vertex)
                stack.pop()
            elif target not in seen:
                seen.add(target)
                stack.append((target, iter(edges[target])))
    membership = [-1] * n
    groups = []
    for start in reversed(finish):
        if membership[start] != -1:
            continue
        group, stack = [], [start]
        membership[start] = len(groups)
        while stack:
            vertex = stack.pop()
            group.append(vertex)
            for target in reverse[vertex]:
                if membership[target] == -1:
                    membership[target] = len(groups)
                    stack.append(target)
        groups.append(sorted(group))
    return groups, membership


def analyze(operations):
    n = len(operations)
    if not 0 < n <= LIMIT:
        raise ValueError('function exceeds budget or is empty')
    starts, branches = {0}, {}
    for pc, text in enumerate(operations):
        targets, terminator = successors(text, pc, n)
        if terminator:
            branches[pc] = targets
            starts.update(targets)
            if pc + 1 < n:
                starts.add(pc + 1)
    starts = sorted(starts)
    ends = starts[1:] + [n]
    lookup = {start: i for i, start in enumerate(starts)}
    edges = []
    for end in ends:
        targets = branches.get(end - 1, (end,))
        edges.append(tuple(lookup[target] for target in targets))
    groups, membership = components(edges)
    reachable, pending = {0}, [0]
    while pending:
        for target in edges[pending.pop()]:
            if target not in reachable:
                reachable.add(target)
                pending.append(target)
    cycles, block_cycle = [], [-1] * len(starts)
    incoming = [set() for _ in groups]
    if 0 in reachable:
        incoming[membership[0]].add(0)
    for source in reachable:
        for target in edges[source]:
            if membership[source] != membership[target]:
                incoming[membership[target]].add(target)
    for group_id, blocks in enumerate(groups):
        if len(blocks) == 1 and blocks[0] not in edges[blocks[0]]:
            continue
        histogram = Counter(operations[pc].split(' ', 1)[0]
            for block in blocks for pc in range(starts[block], ends[block]))
        active = blocks[0] in reachable
        assert all((block in reachable) == active for block in blocks)
        index = len(cycles)
        for block in blocks:
            block_cycle[block] = index
        cycles.append(dict(index=index, reachable=active,
            ranges=[[starts[b], ends[b]] for b in blocks], blocks=len(blocks),
            entries=sorted(starts[b] for b in incoming[group_id]),
            exits=sorted({starts[t] for b in blocks for t in edges[b] if membership[t] != group_id}),
            operations=sum(histogram.values()), histogram=dict(sorted(histogram.items())),
            calls=sum(histogram[k] for k in CALLS),
            memory_operations=sum(histogram[k] for k in MEMORY),
            other_effects=sum(histogram[k] for k in EFFECTS)))
    return dict(starts=starts, ends=ends, cycles=cycles, block_cycle=block_cycle,
        blocks=len(starts), reachable_blocks=len(reachable),
        unreachable_operations=sum(ends[b] - starts[b] for b in range(len(starts)) if b not in reachable))


def cycle_at(graph, pc):
    if not 0 <= pc < graph['ends'][-1]:
        raise ValueError('PC out of bounds')
    return graph['block_cycle'][bisect_right(graph['starts'], pc) - 1]


def range_cycle(graph, start, end):
    """Attribute overhead only if its entire native region belongs to one SCC."""
    if not 0 <= start < end <= graph['ends'][-1]:
        raise ValueError('region out of bounds')
    ids = {graph['block_cycle'][i] for i in range(
        bisect_right(graph['starts'], start) - 1, bisect_right(graph['starts'], end - 1))}
    return next(iter(ids)) if len(ids) == 1 else None
