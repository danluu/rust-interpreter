import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import interpreter
from suite_reports import validate_runtime_limits


class CodeLimitContracts(unittest.TestCase):
    def test_invalid_limits_and_nonexecution_modes_fail_before_tool_setup(self):
        base = ['interpreter.py', '--package', 'fixture', '--entry', 'entry']
        cases = [['--engine', 'jit', '--jit-code-limit', n] for n in ['-1', '33554433', '1.5', 'bad']]
        cases += [['--jit-code-limit', '0'],
                  ['--engine', 'jit', '--jit-code-limit', '0', '--list-tests', '--test-body'],
                  ['--engine', 'jit', '--jit-code-limit', '0', '--audit-entries', 'must-not-be-read', '--test-body']]
        for args in cases:
            with self.subTest(args=args), patch.object(sys, 'argv', base + args), \
                    patch.object(interpreter, 'checked_tools') as tools, \
                    contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as failure:
                interpreter.main()
            self.assertEqual(failure.exception.code, 2)
            tools.assert_not_called()

    def test_capability_probe_rejects_old_or_malformed_vm_before_cargo(self):
        good = dict(schema_version=1, bytecode_version=5,
                    jit_code_limit=dict(default=16*1024*1024, maximum=32*1024*1024))
        for limit in [0, 16*1024*1024, 32*1024*1024]:
            with patch.object(interpreter.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps(good), '')) as run:
                interpreter.require_jit_code_limit(Path('/owned-tools'), limit)
            run.assert_called_once_with(['/owned-tools/rust-interp-vm', '--rust-interp-capabilities'], capture_output=True, text=True)
        bad = [{}, [], dict(good, bytecode_version=4),
               dict(good, jit_code_limit=dict(default=True, maximum=32*1024*1024)),
               dict(good, jit_code_limit=dict(default=16*1024*1024, maximum=16*1024*1024))]
        for value in bad:
            with patch.object(interpreter.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps(value), '')), \
                    self.assertRaisesRegex(RuntimeError, 'selected VM does not support'):
                interpreter.require_jit_code_limit(Path('/owned-tools'), 32*1024*1024)
        with patch.object(interpreter.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'old VM')), \
                self.assertRaisesRegex(RuntimeError, 'selected VM does not support'):
            interpreter.require_jit_code_limit(Path('/owned-tools'), 0)

    def test_effective_receipt_requires_exact_explicit_capacity(self):
        report = dict(runtime_limits=dict(instructions=100_000_000, allocations=100_000,
            memory_bytes=64*1024*1024, frames=4096), jit_code_limit_bytes=16*1024*1024)
        validate_runtime_limits(report, required=True)
        for limit in [0, 16*1024*1024, 32*1024*1024]:
            current = dict(report, jit_code_limit_bytes=limit)
            validate_runtime_limits(current, jit_code_limit=limit, required=True)
            with self.assertRaises(RuntimeError):
                validate_runtime_limits(current, jit_code_limit=limit + 1, required=True)
        with self.assertRaises(RuntimeError):
            validate_runtime_limits(dict(report, jit_code_limit_bytes=32*1024*1024), required=True)
        for invalid in [True, -1, 32*1024*1024 + 1]:
            with self.assertRaises(RuntimeError):
                validate_runtime_limits(report, jit_code_limit=invalid)
        with self.assertRaises(RuntimeError):
            validate_runtime_limits({}, jit_code_limit=16*1024*1024)


if __name__ == '__main__':
    unittest.main()
