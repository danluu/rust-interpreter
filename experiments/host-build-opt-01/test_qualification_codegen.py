"""Pure saved-argv regression; extracts only the two parser functions by AST."""
import ast
import hashlib
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
INPUTS_SHA = 'f1d6e45631e504a060ca5089cf3e366726538a32824d19cf484501f33b53b614'
manifest = HERE/'qualification-parser-saved-inputs-01.json'
assert hashlib.sha256(manifest.read_bytes()).hexdigest() == INPUTS_SHA
inputs = json.loads(manifest.read_text())
driver = Path(inputs['driver']['path'])
source = driver.read_bytes()
assert hashlib.sha256(source).hexdigest() == inputs['driver']['sha256']
tree = ast.parse(source, filename=str(driver))
functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name in ['require', 'codegen']]
assert len(functions) == 2
namespace = {}
exec(compile(ast.Module(body=functions, type_ignores=[]), str(driver), 'exec'), namespace)
codegen = namespace['codegen']


class CodegenParser(unittest.TestCase):
    def test_all_eleven_actual_saved_argv(self):
        self.assertEqual(len(inputs['saved_argv']), 11)
        macro = 0
        for ref in inputs['saved_argv']:
            payload = Path(ref['path']).read_bytes()
            self.assertEqual(hashlib.sha256(payload).hexdigest(), ref['sha256'])
            row = json.loads(payload)
            parsed = codegen(row['argv'][1:])
            if 'prefer-dynamic' in parsed:
                macro += 1
                self.assertEqual(parsed['prefer-dynamic'], 'yes')
                self.assertEqual(row['environment']['CARGO_PKG_NAME'], 'profile-host-fixture')
        self.assertEqual(macro, 1)

    def test_documented_bare_boolean_equivalent_to_yes(self):
        self.assertEqual(codegen(['-C', 'prefer-dynamic']), {'prefer-dynamic': 'yes'})
        self.assertEqual(codegen(['-Cprefer-dynamic']), codegen(['-Cprefer-dynamic=yes']))

    def test_other_valueless_options_remain_rejected(self):
        for flag in ['opt-level', 'metadata', 'debug-assertions', 'embed-bitcode', 'unknown']:
            with self.subTest(flag=flag), self.assertRaises(RuntimeError):
                codegen(['-C', flag])

    def test_duplicates_remain_rejected(self):
        for argv in [['-Cprefer-dynamic', '-Cprefer-dynamic=no'],
                     ['-Cprefer_dynamic', '-Cprefer-dynamic'],
                     ['-Copt-level=0', '-Copt-level=3']]:
            with self.subTest(argv=argv), self.assertRaises(RuntimeError):
                codegen(argv)

    def test_valued_options_preserved_and_missing_value_rejected(self):
        self.assertEqual(codegen(['-C', 'opt-level=3', '-Cmetadata=abc', '-Cprefer-dynamic=no']),
                         {'opt-level': '3', 'metadata': 'abc', 'prefer-dynamic': 'no'})
        with self.assertRaises(IndexError):
            codegen(['-C'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
