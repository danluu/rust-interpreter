"""Pure expected outcomes for the owned real-macro fixtures, not a runner.

Raw compiler JSON, native output, events and later exported artifacts must also
be compared independently. Nothing here repairs or normalizes compiler output.
"""
import json


HISTORY = (
    # name, macro offset, tracked file integer, tracked env integer, blank lines
    ('cold', 11, 5, 7, 0),
    ('position-edit', 11, 5, 7, 2),
    ('position-restore', 11, 5, 7, 0),
    ('file-edit', 11, 13, 7, 0),
    ('file-restore', 11, 5, 7, 0),
    ('environment-edit', 11, 5, 17, 0),
    ('environment-restore', 11, 5, 7, 0),
    ('macro-edit', 19, 5, 7, 0),
    ('macro-restore', 11, 5, 7, 0),
)
ERRORS = {
    'type_error': ('E0308', None),
    'borrow_error': ('E0382', None),
    'const_error': ('E0080', None),
    'macro_error': (None, 'bridge fixture explicit error'),
    'macro_panic': (None, 'bridge fixture deliberate panic'),
}
BRIDGE_TESTS = (
    'span_transport_grows_and_reuses_handles_in_both_strategies',
    'stale_same_thread_span_reaches_real_dispatcher_and_is_rejected',
    'token_stream_drop_order_survives_span_store_change',
    'nested_dispatch_and_both_panic_boundaries_restore_bridge_state',
)


def events(raw):
    rows = []
    for line in raw.decode('utf-8').splitlines():
        identity, event, encoded = line.split('\t', 2)
        value = json.loads(encoded)
        if not isinstance(value, str):
            raise ValueError('event value is not a string')
        rows.append((identity, event, value))
    return rows


def require(condition, message):
    if not condition:
        raise ValueError(message)


def positive(raw, stdout, state):
    name, offset, file_value, env_value, _position_lines = state
    rows = events(raw)
    require(len(rows) == 50, name + ': missing/duplicated macro side effects')
    require(set(row[0] for row in rows) == {'warning', 'first', 'second', 'outer', 'inner'},
            'unexpected macro invocation')
    for identity in ('first', 'second'):
        group = [(event, value) for who, event, value in rows if who == identity]
        require([event for event, _ in group[:3]] == ['begin', 'env', 'file'], 'effect order changed')
        require(group[:3] == [('begin', 'probe'), ('env', str(env_value)), ('file', str(file_value) + '\n')],
                'actual tracked inputs differ')
        require(group[-2:] == [('tokens', '10'), ('end', str(offset + file_value + env_value))],
                'actual probe output/recursive token count differs')
        middle = group[3:-2]
        require(len(middle) == 16 and sum(event == 'span' for event, _ in middle) == 10
                and sum(event == 'group-open' for event, _ in middle) == 3
                and sum(event == 'group-close' for event, _ in middle) == 3,
                'span/group transport omitted')
    nesting = [(who, event) for who, event, _ in rows if who in {'outer', 'inner'}]
    require(nesting == [('outer', 'begin'), ('inner', 'begin'), ('inner', 'span'),
                        ('inner', 'end'), ('outer', 'span-after'), ('outer', 'end')],
            'nested macro was skipped, repeated or reordered')
    require([(event, value) for who, event, value in rows if who == 'warning'][:1] == [('begin', 'diagnostic')]
            and [event for who, event, _ in rows if who == 'warning'] == ['begin', 'end'],
            'diagnostic macro invocation differs')
    expected = 2 * (offset + file_value + env_value) + 17
    require(stdout == f'{expected}\n'.encode(), 'native result differs')
    return expected


def negative(raw, cfg):
    require(cfg in ERRORS, 'unknown error control')
    rows = events(raw)
    require([(who, event) for who, event, _ in rows if who == 'warning'] == [('warning', 'begin'), ('warning', 'end')],
            'warning macro did not execute exactly once')
    extra = [(who, event) for who, event, _ in rows if who != 'warning']
    expected = {'macro_error': [('failure', 'begin'), ('failure', 'end')],
                'macro_panic': [('panic', 'begin')]}.get(cfg, [])
    require(extra == expected, 'failing macro invocation was skipped, repeated or reordered')
    return ERRORS[cfg]


def equal_raw(baseline, candidate):
    require(baseline == candidate, 'raw matched-state evidence differs')

