import copy
import unittest
from pathlib import Path

import qualify_projects as project


class ProjectQualificationTests(unittest.TestCase):
    def test_both_reference_catalog_schemas_require_one_unambiguous_artifact(self):
        artifact = dict(path='test.rbc', sha256='bytecode')
        catalog = dict(path='test.json', sha256='catalog')
        for key in ['catalog', 'entry_catalog']:
            row = dict(artifact=artifact, **{key: catalog})
            self.assertEqual(project.reference_artifact(row, 'artifact'), artifact)
            self.assertEqual(project.reference_artifact(row, 'entry_catalog'), catalog)
        for row in [{}, dict(catalog=catalog, entry_catalog=catalog)]:
            with self.assertRaises(AssertionError):
                project.reference_artifact(row, 'entry_catalog')

    def test_remaining_cases_are_unique_and_keep_declared_order(self):
        self.assertEqual(project.selected_cases(['token', 'folded', 'pgrust']),
                         ['token', 'folded', 'pgrust'])
        for names in [[], ['token', 'token'], ['pgrust', 'token'], ['unknown']]:
            with self.assertRaises(AssertionError):
                project.selected_cases(names)

    def test_reference_restoration_uses_first_completed_history(self):
        rows = [dict(mode=mode, cycle=cycle, state=state)
                for mode in ['baseline', 'candidate'] for cycle in range(4)
                for state in [0, -1, 1, 2, 3, 4, 5]]
        selected = project.references(rows)
        self.assertEqual([(r['cycle'], r['state']) for r in selected],
                         [(0, s) for s in [0, -1, 1, 2, 3, 4, 5]] + [(1, 0)])
        with self.assertRaises(AssertionError):
            project.references(rows + [copy.deepcopy(selected[-1])])

    def test_rewrite_preserves_selection_and_isolates_every_output(self):
        command = ['python', 'interpreter.py', '--entry', 'chosen', '--tool-key', 'old',
                   '--cache-namespace', 'retained', '--suite-report', 'old.json',
                   '--function-cache', 'auto', '--jobs', '2']
        rewritten = project.rewrite_command(command, 'new', 'integration', Path('new.json'))
        self.assertEqual(command[command.index('--tool-key') + 1], 'old')
        self.assertEqual(rewritten[rewritten.index('--entry') + 1], 'chosen')
        for option, value in [('--tool-key', 'new'), ('--cache-namespace', 'integration'),
                              ('--suite-report', 'new.json'), ('--function-cache', 'auto'), ('--jobs', '2')]:
            self.assertEqual(rewritten[rewritten.index(option) + 1], value)

    def test_missing_duplicate_or_reused_outputs_are_rejected(self):
        command = ['python', '--tool-key', 'old', '--cache-namespace', 'retained',
                   '--suite-report', 'old.json']
        for bad in [command[:-2], command + ['--suite-report', 'extra.json'], command[:-1]]:
            with self.subTest(command=bad), self.assertRaises(AssertionError):
                project.rewrite_command(bad, 'new', 'integration', Path('new.json'))
        with self.assertRaises(AssertionError):
            project.rewrite_command(command, 'new', 'retained', Path('new.json'))

    def test_production_edit_history_preserves_tests_and_restores_bytes(self):
        original = b'fn helper() { let x = 0; }\n#[cfg(test)]\nmod tests { /* original assertions */ }\n'
        case = dict(negative=['wrong', 'x = 0', 'x = 9'],
                    edits=[[str(i), 'x = ' + str(i), 'x = ' + str(i + 1)] for i in range(5)])
        states = project.project_states(original, case)
        self.assertEqual([s['state'] for s in states], project.STATES)
        self.assertEqual(states[-1]['source'], original)
        for state in states:
            self.assertIsInstance(state['source'], bytes)
            self.assertEqual(state['source'].split(b'#[cfg(test)]')[1], original.split(b'#[cfg(test)]')[1])


if __name__ == '__main__':
    unittest.main()
