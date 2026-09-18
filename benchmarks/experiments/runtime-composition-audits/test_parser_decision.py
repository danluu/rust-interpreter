import copy
import unittest
from parser_decision import parser_decision


class ParserDecisionTests(unittest.TestCase):
    def results(self):
        return [dict(profile=p, commands=88, tests=114, gate_passed=True)
                for p in ['incremental', 'repository']]

    def test_all_guards_are_required_for_admission(self):
        self.assertEqual(parser_decision(self.results()), dict(passed=True, unstarted=[]))
        for rows in [[], self.results()[:1]]:
            with self.assertRaises(AssertionError):
                parser_decision(rows)

    def test_either_failure_is_terminal_and_cancels_only_unstarted_guard(self):
        for index in range(2):
            rows = self.results()[:index+1]
            rows[-1]['gate_passed'] = False
            self.assertEqual(parser_decision(rows), dict(passed=False,
                unstarted=['repository'] if index == 0 else []))

    def test_no_reordering_missing_commands_or_run_after_failure(self):
        original = self.results()
        changes = [lambda r: r.reverse(), lambda r: r[0].update(commands=87),
                   lambda r: r[1].update(tests=113),
                   lambda r: r[0].update(gate_passed=False),
                   lambda r: r[1].update(gate_passed=1)]
        for change in changes:
            rows = copy.deepcopy(original)
            change(rows)
            with self.assertRaises(AssertionError):
                parser_decision(rows)


if __name__ == '__main__':
    unittest.main()
