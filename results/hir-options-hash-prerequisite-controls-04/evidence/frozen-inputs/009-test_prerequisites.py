"""In-memory failures in the predecessor chain; no process or file operations."""
import copy
import json
from pathlib import Path
import unittest

import prerequisites as p


def raw(value):
    return (json.dumps(value, sort_keys=True)+'\n').encode()


class History(unittest.TestCase):
    def setUp(self):
        self.root = Path('/frozen/predecessor')
        self.files = {}
        self.plan = []
        self.terminal = dict(status='passed', pid=41, parent_pid=40,
                             admitted_at=10, finished_at=20, commands=[])
        for index, rc in enumerate([0, 1]):
            declaration = dict(argv=['/compiler', 'input.rs', str(index)], cwd='/source',
                               environment={'PATH': '/bin'}, expected=[rc], role='control')
            self.plan.append(declaration)
            directory = self.root/'commands'/f'{index:03}'
            for stream in ['stdout', 'stderr']:
                self.files[directory/stream] = (b'output\n' if stream == 'stdout' else b'error\n')
            child = dict(status='finished', pid=50+index, supervisor_pid=41, parent_pid=40,
                         started_at=11+index*2, finished_at=12+index*2,
                         command=declaration['argv'], cwd='/source', environment={'PATH': '/bin'},
                         expected=[rc], returncode=rc,
                         identity=dict(ps=f'{50+index} 41 {50+index} Fri Sep 18 12:00:00 2026 ?? '+
                                       ' '.join(declaration['argv']), ps_returncode=0,
                                       cwd=f'p{50+index}\nfcwd\nn/source\n', cwd_returncode=0))
            for stream in ['stdout', 'stderr']:
                child[stream+'_sha256'] = p.digest(self.files[directory/stream])
            self.files[directory/'receipt.json'] = raw(child)
            self.terminal['commands'].append(dict(path=str(directory/'receipt.json'),
                sha256=p.digest(raw(child)), pid=50+index, command=declaration['argv'], role='control'))

    def update(self, index, transform):
        ref = self.terminal['commands'][index]
        path = Path(ref['path'])
        value = json.loads(self.files[path]); transform(value)
        self.files[path] = raw(value); ref['sha256'] = p.digest(self.files[path])

    def check(self):
        return p.command_history(self.terminal, self.plan, evidence=self.root,
            read_json=lambda path: json.loads(self.files[Path(path)]),
            read_bytes=lambda path: self.files[Path(path)])

    def test_expected_negative_is_a_finished_successful_control(self):
        result = self.check()
        self.assertEqual([r['receipt']['returncode'] for r in result['rows']], [0, 1])
        self.assertEqual(result['unavailable_contemporaneous_cwd_children'], [])

    def test_failed_controller_or_failed_child_cannot_become_qualified(self):
        self.terminal['status'] = 'failed'
        with self.assertRaises(ValueError): self.check()
        self.terminal['status'] = 'passed'
        self.update(1, lambda value: value.update(status='failed'))
        with self.assertRaises(ValueError): self.check()

    def test_changed_raw_bytes_reject_even_with_plausible_receipt(self):
        self.files[self.root/'commands/001/stderr'] += b'extra'
        with self.assertRaises(ValueError): self.check()

    def test_missing_reordered_or_relabelled_child_rejects(self):
        original = copy.deepcopy(self.terminal['commands'])
        for changed in [original[:1], original[::-1], [original[0], dict(original[1], role='other')]]:
            self.terminal['commands'] = changed
            with self.subTest(changed=changed), self.assertRaises(ValueError): self.check()

    def test_pid_parent_command_terminal_and_cwd_substitutions_reject(self):
        original = copy.deepcopy(self.files)
        for field, value in [('supervisor_pid', 100), ('parent_pid', 99), ('cwd', '/elsewhere'),
                             ('environment', {'PATH': '/other'}), ('command', ['/other']), ('pid', 100)]:
            self.files = copy.deepcopy(original)
            self.update(0, lambda row: row.update({field: value}))
            with self.subTest(field=field), self.assertRaises(ValueError): self.check()
        for field, value in [('ps', '50 41 50 Fri Sep 18 12:00:00 2026 ttys001 /compiler input.rs 0'),
                             ('ps', '50 41 50 Fri Sep 18 12:00:00 2026 ?? /other /compiler input.rs 0'),
                             ('cwd', 'p50\nfcwd\nn/elsewhere\n')]:
            self.files = copy.deepcopy(original)
            self.update(0, lambda row: row['identity'].update({field: value}))
            with self.subTest(identity=field, value=value), self.assertRaises(ValueError): self.check()

    def test_wrong_negative_code_and_boolean_code_reject(self):
        for value in [0, 2, True]:
            self.update(1, lambda row: row.update(returncode=value))
            with self.subTest(value=value), self.assertRaises(ValueError): self.check()

    def test_overlapping_out_of_bounds_or_nonfinite_times_reject(self):
        for field, value in [('started_at', 11), ('finished_at', 21), ('started_at', float('nan')),
                             ('finished_at', float('inf'))]:
            self.update(1, lambda row: row.update(started_at=13, finished_at=14))
            self.update(1, lambda row: row.update({field: value}))
            with self.subTest(field=field, value=value), self.assertRaises(ValueError): self.check()

    def test_fast_child_missing_cwd_is_retained_as_a_limitation(self):
        self.update(0, lambda row: row['identity'].update(cwd='', cwd_returncode=1))
        result = self.check()
        self.assertEqual(result['unavailable_contemporaneous_cwd_children'], [0])
        self.update(0, lambda row: row['identity'].update(cwd_returncode=2))
        with self.assertRaises(ValueError): self.check()

    def test_receipt_bytes_and_reference_must_match(self):
        path = self.root/'commands/000/receipt.json'
        self.files[path] += b' '
        with self.assertRaises(ValueError): self.check()


if __name__ == '__main__':
    unittest.main()
