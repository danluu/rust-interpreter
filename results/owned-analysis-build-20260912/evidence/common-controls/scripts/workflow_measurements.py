"""Repeated source states and accounting shared by the workflow harness."""
import itertools
import resource
import statistics


def initial_modes(defaults, requested=None):
    if requested is None:
        return list(defaults)
    if (not isinstance(requested, list) or len(requested) != len(defaults) or
            not all(isinstance(m, str) for m in requested) or set(requested) != set(defaults)):
        raise ValueError('initial mode order must contain each comparison mode exactly once')
    return list(requested)


def mode_order(modes, cycle, state, paired):
    """Order one source state; arbitrary initial permutations balance cold runs."""
    order = list(modes if state % 2 == 0 else reversed(modes))
    if paired and state > 0:
        permutations = list(itertools.permutations(modes))
        permutations = [permutations[i] for i in [0, 1, 2, 4, 3, 5]]
        order = list(permutations[(state - 1) % len(permutations)])
    if (cycle // len(modes)) % 2:
        order.reverse()
    rotation = cycle % len(modes)
    return order[rotation:] + order[:rotation]


def source_states(original, case, cycles, modes, paired):
    """Replay real edits after an original-source anchor in every cycle."""
    if cycles < 1:
        raise ValueError('cycles must be positive')
    if len(modes) != 3 or len(set(modes)) != 3:
        raise ValueError('expected three distinct comparison modes')
    marker = '\n#[cfg(test)]\nmod tests {'
    if original.count(marker) != 1:
        raise ValueError('expected exactly one original test module')
    original_tests = original.split(marker)[1]
    for cycle in range(cycles):
        for state in [0, -1, *range(1, len(case['edits']) + 1)]:
            candidate = original
            label = 'cold-original' if cycle == 0 else 'cycle-original'
            phase = ('cold' if cycle == 0 else 'anchor') if state == 0 else 'edit'
            changes = []
            if state == -1:
                phase = 'wrong-edit'
                changes = [case['negative']]
            elif state > 0:
                changes = case['edits'][:state]
            for label, before, after in changes:
                if before == after or candidate.count(before) != 1:
                    raise ValueError('edit must change exactly one occurrence: ' + label)
                candidate = candidate.replace(before, after)
            if candidate.count(marker) != 1 or candidate.split(marker)[1] != original_tests:
                raise ValueError('test source changed')
            yield dict(cycle=cycle, state=state, phase=phase, label=label,
                       source=candidate.encode(), modes=mode_order(modes, cycle, state, paired))


def child_usage():
    """Cumulative CPU for this process's waited-for child trees."""
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime, usage.ru_stime


def child_cpu_since(before):
    after = child_usage()
    user, system = (a - b for a, b in zip(after, before))
    if user < 0 or system < 0:
        raise RuntimeError('child CPU accounting moved backwards')
    return dict(user_seconds=user, system_seconds=system, total_seconds=user + system)


def sample_path(state, index, cycles, suffix):
    """Preserve old single-cycle paths; every repeated sample gets a new path."""
    prefix = '' if cycles == 1 else f"cycle-{state['cycle']}/"
    return f"{prefix}{state['state']}-{index}.{suffix}"


def per_edit_spread(pairs):
    """Keep distinct edit states separate; describe spread without inference."""
    result = []
    for state in sorted({p['state'] for p in pairs}):
        selected = [p for p in pairs if p['state'] == state]
        if len({p['cycle'] for p in selected}) != len(selected):
            raise ValueError('duplicate cycle/edit pair')
        if len({p['source_sha256'] for p in selected}) != 1:
            raise ValueError('repeated edit states contain different source')
        spread = {}
        for field in ['baseline_seconds', 'candidate_seconds', 'native_seconds',
                      'difference_seconds', 'cpu_difference_seconds']:
            values = [p[field] for p in selected]
            spread[field] = dict(min=min(values), median=statistics.median(values), max=max(values))
        result.append(dict(state=state, cycles=[p['cycle'] for p in selected],
            source_sha256=selected[0]['source_sha256'], samples=len(selected), spread=spread))
    return result
