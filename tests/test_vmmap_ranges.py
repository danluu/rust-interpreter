import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vmmap_ranges import anonymous_executable_ranges


class VmmapRanges(unittest.TestCase):
    # Shape and address interval from the retained macOS 27 report whose
    # Untagged row contains the owned VM's independently dumped code arena.
    row = 'Untagged                    1051ec000-1061ec000    [ 16.0M   944K   944K     0K] rwx/rwx SM=PRV  '

    def report(self, *rows, pid=322, name='rust-interp-vm'):
        return f'Process:         {name} [{pid}]\nCode Type:       ARM64\n\n' + '\n'.join(rows) + '\n'

    def test_current_and_historical_arena_labels_preserve_exact_bounds(self):
        expected = [(0x1051ec000, 0x1061ec000)]
        for label in ['Untagged', 'VM_ALLOCATE']:
            with self.subTest(label=label):
                self.assertEqual(anonymous_executable_ranges(self.report(self.row.replace('Untagged', label)), 322), expected)
        self.assertLessEqual(expected[0][0] + 11313812, expected[0][1])

    def test_process_header_must_identify_exact_owned_vm(self):
        for report, pid in [(self.report(self.row), 323), (self.row, 322),
                (self.report(self.row, name='other-program'), 322),
                (self.report(self.row) + 'Process: rust-interp-vm [322]\n', 322),
                (self.report(self.row), True), (self.report(self.row), 0)]:
            with self.subTest(report=report, pid=pid), self.assertRaises(ValueError):
                anonymous_executable_ranges(report, pid)

    def test_only_complete_anonymous_rwx_rows_are_readiness_candidates(self):
        for row in [self.row.replace('Untagged', '__TEXT'), self.row.replace('Untagged', 'MALLOC'),
                    self.row.replace('rwx/rwx', 'r-x/rwx'), self.row.replace('rwx/rwx', 'rw-/rwx'),
                    self.row.replace('rwx/rwx', 'rwx/r-x'), self.row.replace('rwx/rwx', 'rwx/rwx-extra'),
                    self.row.replace(']', ''), 'Untagged 1051ec000-1061ec000 rwx/rwx']:
            with self.subTest(row=row):
                self.assertEqual(anonymous_executable_ranges(self.report(row), 322), [])

    def test_invalid_and_overlapping_bounds_are_rejected(self):
        for interval in ['0-1061ec000', '1061ec000-1051ec000', '1051ec000-1051ec000', '1-10000000000000001']:
            with self.subTest(interval=interval), self.assertRaises(ValueError):
                anonymous_executable_ranges(self.report(self.row.replace('1051ec000-1061ec000', interval)), 322)
        for extra in [self.row, self.row.replace('1051ec000-1061ec000', '105200000-106200000')]:
            with self.assertRaises(ValueError):
                anonymous_executable_ranges(self.report(self.row, extra), 322)

    def test_disjoint_candidates_and_uppercase_addresses_remain_distinct(self):
        other = self.row.replace('1051ec000-1061ec000', '2051EC000-2061EC000').replace('Untagged', 'VM_ALLOCATE')
        self.assertEqual(anonymous_executable_ranges(self.report(other, self.row), 322),
                         [(0x1051ec000, 0x1061ec000), (0x2051ec000, 0x2061ec000)])

    def test_valid_owned_report_without_an_arena_is_not_ready(self):
        self.assertEqual(anonymous_executable_ranges(self.report(), 322), [])


if __name__ == '__main__':
    unittest.main()
