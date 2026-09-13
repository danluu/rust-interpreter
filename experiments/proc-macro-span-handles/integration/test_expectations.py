"""Prepared pure fixture-contract controls. No compiler or filesystem workload."""
import json
import unittest

import expectations as check


def encode(rows):
    return ''.join(f'{who}\t{event}\t{json.dumps(value)}\n' for who, event, value in rows).encode()


def sample(state):
    _, offset, file_value, env_value, _ = state
    rows = [('warning', 'begin', 'diagnostic'), ('warning', 'end', 'raw-span')]
    for who in ('first', 'second'):
        rows += [(who, 'begin', 'probe'), (who, 'env', str(env_value)), (who, 'file', str(file_value) + '\n')]
        rows += [(who, 'span', 'raw-span')] * 10
        rows += [(who, 'group-open', 'raw-span')] * 3 + [(who, 'group-close', 'raw-span')] * 3
        rows += [(who, 'tokens', '10'), (who, 'end', str(offset + file_value + env_value))]
    rows += [('outer', 'begin', 'nested expansion'), ('inner', 'begin', 'nested expansion'),
             ('inner', 'span', 'raw-span'), ('inner', 'end', '17'),
             ('outer', 'span-after', 'raw-span'), ('outer', 'end', '17')]
    return rows


class FixtureContract(unittest.TestCase):
    def test_all_edits_require_actual_changed_values_and_full_event_counts(self):
        for state in check.HISTORY:
            rows = sample(state)
            expected = 2 * sum(state[1:4]) + 17
            self.assertEqual(check.positive(encode(rows), f'{expected}\n'.encode(), state), expected)
            for changed in [rows[:-1], rows + rows[:1]]:
                with self.assertRaises(ValueError):
                    check.positive(encode(changed), f'{expected}\n'.encode(), state)
            with self.assertRaises(ValueError):
                check.positive(encode(rows), f'{expected + 1}\n'.encode(), state)

    def test_nested_execution_and_tracked_effect_order_cannot_be_rearranged(self):
        state = check.HISTORY[0]
        rows = sample(state)
        for left, right in [(3, 4), (len(rows) - 5, len(rows) - 2)]:
            changed = rows.copy()
            changed[left], changed[right] = changed[right], changed[left]
            with self.assertRaises(ValueError):
                check.positive(encode(changed), b'63\n', state)

    def test_error_compilation_still_requires_each_macro_side_effect(self):
        warning = [('warning', 'begin', 'diagnostic'), ('warning', 'end', 'raw-span')]
        for cfg in check.ERRORS:
            extra = {'macro_error': [('failure', 'begin', 'diagnostic'), ('failure', 'end', 'raw-span')],
                     'macro_panic': [('panic', 'begin', 'raw-span')]}.get(cfg, [])
            rows = warning + extra
            self.assertEqual(check.negative(encode(rows), cfg), check.ERRORS[cfg])
            with self.assertRaises(ValueError):
                check.negative(encode(rows[1:]), cfg)

    def test_raw_comparison_preserves_every_span_and_side_effect_byte(self):
        original = encode(sample(check.HISTORY[0]))
        check.equal_raw(original, original)
        with self.assertRaises(ValueError):
            check.equal_raw(original, original.replace(b'raw-span', b'changed-span', 1))


if __name__ == '__main__':
    unittest.main()
