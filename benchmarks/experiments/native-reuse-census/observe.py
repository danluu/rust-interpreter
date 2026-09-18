"""Compare necessary identity conditions; never certify native code reuse."""
from collections import deque


def functions(report):
    rows = report['functions']
    assert [r['id'] for r in rows] == list(range(len(rows)))
    assert all(all(type(i) is int and 0 <= i < len(rows) for i in r['direct_callees']) for r in rows)
    return rows


def compare(before, after):
    old, new = functions(before), functions(after)
    same = {i for i, row in enumerate(new) if i < len(old) and row['body_sha256'] == old[i]['body_sha256']}
    global_same = before['global_sha256'] == after['global_sha256']
    layouts = {i for i in same if all(j < len(old) and old[j]['layout_sha256'] == new[j]['layout_sha256']
                                    for j in new[i]['direct_callees'])} if global_same else set()
    direct = {i for i in layouts if all(j in same for j in new[i]['direct_callees'])}
    # Reverse reachability on both graphs handles recursion, removed targets and
    # changed call edges. It is deliberately more conservative than the emitter.
    count = max(len(old), len(new)); reverse = [set() for _ in range(count)]
    for rows in [old, new]:
        for row in rows:
            for target in row['direct_callees']: reverse[target].add(row['id'])
    changed = set(range(count)) - same if global_same else set(range(count))
    queue = deque(sorted(changed))
    while queue:
        for parent in reverse[queue.popleft()]:
            if parent not in changed: changed.add(parent); queue.append(parent)
    transitive = set(range(len(new))) - changed
    assert transitive <= direct <= layouts <= same
    return dict(global_equal=global_same, self_equal=sorted(same), self_and_call_layouts=sorted(layouts),
                self_and_direct_bodies=sorted(direct), transitive_direct_bodies=sorted(transitive))


def aggregate(after, identities, code_weights=None):
    rows = functions(after); code_weights = code_weights or {}
    metrics = {}
    for label in ['self_equal', 'self_and_call_layouts', 'self_and_direct_bodies', 'transitive_direct_bodies']:
        ids = identities[label]
        metrics[label] = dict(functions=len(ids), operations=sum(rows[i]['operations'] for i in ids),
            serialized_bytes=sum(rows[i]['serialized_bytes'] for i in ids),
            reference_native_bytes=sum(code_weights.get(i, 0) for i in ids))
    return dict(functions=len(rows), operations=sum(r['operations'] for r in rows),
        serialized_bytes=sum(r['serialized_bytes'] for r in rows), reference_native_bytes=sum(code_weights.values()),
        global_equal=identities['global_equal'], conditions=metrics)


def native_weights(mapping, reference, current):
    ref, rows = functions(reference), functions(current)
    weights = {}; last = 0
    for span in mapping['ranges']:
        assert last <= span['offset'] < span['end'] <= mapping['code_bytes']
        last = span['end']; i = span['function']
        assert ref[i]['name'] == span['name']
        # Count only exact full bodies at the same ID in the saved map artifact.
        if i < len(rows) and rows[i]['body_sha256'] == ref[i]['body_sha256']:
            weights[i] = weights.get(i, 0) + span['end'] - span['offset']
    return weights
