"""Synthetic wire/control failures; no child, compiler or benchmark execution."""
import copy
import json
import unittest

from observations import LABELS, MAX_BYTES, parse


def records(mode='serial', base=0):
    rows = [dict(label=label, incremental_hash=base, crate_hash=base + 1,
                 workers=2 if mode == 'parallel' else 1, status='passed')
            for label in LABELS]
    rows[2].update(incremental_hash=base + 2, crate_hash=base + 3)
    rows[4]['incremental_hash'] = base + 4
    return rows + [dict(status='passed', contexts=8, parallel=mode == 'parallel')]


def encode(rows):
    return b''.join(json.dumps(row, separators=(',', ':')).encode() + b'\n' for row in rows)


class Observations(unittest.TestCase):
    def reject(self, rows, mode='serial'):
        with self.assertRaises(ValueError):
            parse(encode(rows), mode=mode)

    def test_accepts_both_modes_and_u64_boundaries(self):
        for mode in ('serial', 'parallel'):
            for base in (0, 2**64 - 5):
                with self.subTest(mode=mode, base=base):
                    self.assertEqual(parse(encode(records(mode, base)), mode=mode)['contexts'], 8)

    def test_process_hashes_need_not_match(self):
        serial = parse(encode(records('serial', 4)), mode='serial')
        parallel = parse(encode(records('parallel', 100)), mode='parallel')
        self.assertNotEqual(serial['observations'][0]['incremental_hash'],
                            parallel['observations'][0]['incremental_hash'])

    def test_duplicate_keys_are_rejected_even_when_values_match(self):
        raw = encode(records())
        for before, after in [(b'"workers":1', b'"workers":1,"workers":1'),
                              (b'"contexts":8', b'"contexts":8,"contexts":8')]:
            with self.subTest(before=before), self.assertRaises(ValueError):
                parse(raw.replace(before, after, 1), mode='serial')

    def test_missing_extra_blank_or_unterminated_records(self):
        raw = encode(records())
        for bad in (encode(records()[:-1]), raw + b'{}\n', raw + b'\n', raw[:-1], b''):
            with self.subTest(raw=bad[:30]), self.assertRaises(ValueError):
                parse(bad, mode='serial')

    def test_duplicate_unknown_and_reordered_labels(self):
        for label in ('base-first', 'unknown', 'tracked-change'):
            rows = records(); rows[1]['label'] = label
            with self.subTest(label=label):
                self.reject(rows)
        rows = records(); rows[2], rows[3] = rows[3], rows[2]; self.reject(rows)

    def test_non_u64_hashes(self):
        for key in ('incremental_hash', 'crate_hash'):
            for value in (-1, 2**64, True, 0.0, '0', None, [], {}, float('nan'), float('inf')):
                rows = records(); rows[0][key] = value
                with self.subTest(key=key, value=value):
                    self.reject(rows)

    def test_mode_and_worker_counts(self):
        for value in (0, 2, True, 1.0, '1'):
            rows = records(); rows[3]['workers'] = value
            with self.subTest(value=value):
                self.reject(rows)
        self.reject(records('serial'), mode='parallel')
        self.reject(records('parallel'), mode='serial')
        with self.assertRaises(ValueError):
            parse(encode(records()), mode='both')

    def test_terminal_schema_and_types(self):
        for key, value in [('contexts', True), ('contexts', 8.0), ('contexts', 7),
                           ('parallel', 0), ('parallel', True), ('status', 'failed')]:
            rows = records(); rows[-1][key] = value
            with self.subTest(key=key, value=value):
                self.reject(rows)

    def test_schema_missing_or_extra_fields(self):
        for index in (0, 8):
            rows = records(); rows[index]['extra'] = 0; self.reject(rows)
            rows = records(); del rows[index]['status']; self.reject(rows)
            for replacement in ([], None, 0, 'passed'):
                rows = records(); rows[index] = replacement; self.reject(rows)

    def test_nonpassing_observation_status(self):
        rows = records(); rows[6]['status'] = 'failed'; self.reject(rows)

    def test_each_restore_and_repeat_relation_is_enforced(self):
        for index in (1, 3, 5, 6, 7):
            for key in ('incremental_hash', 'crate_hash'):
                rows = records(); rows[index][key] += 1
                with self.subTest(index=index, key=key):
                    self.reject(rows)

    def test_stale_global_cache_and_wrong_hash_variant(self):
        for key in ('incremental_hash', 'crate_hash'):
            rows = records(); rows[2][key] = rows[0][key]; self.reject(rows)
        rows = records(); rows[4]['incremental_hash'] = rows[0]['incremental_hash']; self.reject(rows)
        rows = records(); rows[4]['crate_hash'] += 1; self.reject(rows)

    def test_invalid_bytes_json_and_size(self):
        raw = encode(records())
        for bad in (raw.replace(b'base-first', b'\xff'), raw.replace(b'{', b'[', 1),
                    b' ' * MAX_BYTES + raw, raw.decode()):
            with self.subTest(kind=type(bad).__name__), self.assertRaises(ValueError):
                parse(bad, mode='serial')

    def test_parser_does_not_mutate_input(self):
        rows = records(); before = copy.deepcopy(rows); raw = encode(rows)
        self.assertEqual(parse(raw, mode='serial')['observations'], before[:8])
        self.assertEqual(rows, before)


if __name__ == '__main__':
    unittest.main()
