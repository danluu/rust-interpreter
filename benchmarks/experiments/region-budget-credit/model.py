"""Budget-credit DAG model only; no guest/native code is emitted."""
from dataclasses import dataclass

MAX_NODES = 65536
MAX_EDGES = 262144
MAX_CREDIT = 4096


@dataclass(frozen=True)
class Region:
    cost: int
    successors: tuple
    guarded: bool = False


def plan(nodes, cap=MAX_CREDIT):
    if not 1 <= len(nodes) <= MAX_NODES or type(cap) is not int or cap < 1:
        raise ValueError('invalid shape or cap')
    edges = 0
    for pc, node in nodes.items():
        if type(pc) is not int or pc < 0 or type(node.cost) is not int or not 1 <= node.cost <= min(1024, cap):
            raise ValueError('invalid PC or region cost')
        if type(node.guarded) is not bool or not isinstance(node.successors, tuple):
            raise ValueError('invalid region fields')
        edges += len(node.successors)
        if edges > MAX_EDGES or any(type(t) is not int or t < 0 for t in node.successors):
            raise ValueError('invalid edges')
        if len(set(node.successors)) != len(node.successors):
            raise ValueError('duplicate edge')
    credit, fast = {}, {}
    for pc in sorted(nodes, reverse=True):
        node = nodes[pc]
        targets = tuple(t for t in node.successors if t > pc and t in nodes and not nodes[t].guarded)
        required = node.cost + max((credit[t] for t in targets), default=0)
        if required > cap:
            targets, required = (), node.cost
        credit[pc], fast[pc] = required, targets
    incoming = {t for targets in fast.values() for t in targets}
    extra_immediate = {pc for pc in nodes if pc in incoming or credit[pc] != nodes[pc].cost}
    for pc, targets in fast.items():
        for t in targets:
            assert pc < t and not nodes[t].guarded and credit[pc] >= nodes[pc].cost + credit[t]
    return dict(credit=credit, fast=fast, incoming=incoming, extra_immediate=extra_immediate)


def oracle(nodes, path, budget, fault=None):
    """Independent operation-at-a-time observation, with an optional fault PC."""
    observed = []
    for visit, pc in enumerate(path):
        for op in range(nodes[pc].cost):
            if budget == 0:
                return observed, 'budget', 0
            budget -= 1
            observed.append((visit, pc, op))
            if fault == (visit, op):
                return observed, 'fault', budget
    return observed, 'end', budget


def simulate(nodes, path, budget, fault=None, external=()):
    """Abstract prefix model. Native fault cursor publication is NOT modeled.

    Successful native regions debit their entire original cost. For a fault we
    expose the semantic single-step prefix, not an emitted precharged cursor.
    This distinction must be reviewed separately before a production change.
    """
    p = plan(nodes)
    observed, fast_entry, checks, tails = [], False, 0, 0
    for visit, pc in enumerate(path):
        if visit and pc not in nodes[path[visit - 1]].successors:
            raise ValueError('path is not a CFG walk')
        if visit in external:
            fast_entry = False
        native = fast_entry
        if not fast_entry:
            checks += 1
            native = budget >= p['credit'][pc]
        if native:
            assert budget >= p['credit'][pc] >= nodes[pc].cost
        else:
            tails += 1
        for op in range(nodes[pc].cost):
            if not native and budget == 0:
                return (observed, 'budget', 0), checks, tails
            assert budget > 0
            budget -= 1
            observed.append((visit, pc, op))
            if fault == (visit, op):
                return (observed, 'fault', budget), checks, tails
        next_pc = path[visit + 1] if visit + 1 < len(path) else None
        fast_entry = native and next_pc in p['fast'][pc]
    return (observed, 'end', budget), checks, tails
