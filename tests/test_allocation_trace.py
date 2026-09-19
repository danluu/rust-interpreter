"""Exercise allocation sidecar parsing and selected-artifact error routing."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import allocation_trace


class AllocationTraceTests(unittest.TestCase):
    digest = 'a' * 64
    header = dict(kind='allocation-trace', schema_version=1, strict_frontend=True, event=0)
    body = dict(kind='function', event=1)

    @staticmethod
    def encode(events):
        return b''.join(json.dumps(event, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
                        + b'\n' for event in events)

    def good(self, digest=None):
        return self.encode([
            self.header,
            dict(self.body, parent=0, value={'repeated': 'snowman \u2603', 'number': 1.25}),
            dict(kind='constant-origin', event=2, parent=1,
                 value={'repeated': 'quoted " value', 'nested': [{'number': -2.5}]}),
            dict(kind='complete', event=3, prior_events=3,
                 artifact_sha256=self.digest if digest is None else digest),
        ])

    def assert_error(self, call, message, kind=ValueError):
        with self.assertRaises(kind) as caught:
            call()
        self.assertIs(type(caught.exception), kind)
        self.assertEqual(str(caught.exception), message)
        return caught.exception

    def test_multiple_events_exact_bounds_and_independent_calls(self):
        data = self.good()
        for _ in range(2):
            self.assertEqual(allocation_trace.validate_trace(
                data, self.digest, max_bytes=len(data), max_events=4), 4)
        # JSON whitespace is allowed on either side of each individual record.
        spaced = b''.join(b' \t' + line + b'\r \n' for line in data.splitlines())
        self.assertEqual(allocation_trace.validate_trace(spaced, self.digest), 4)
        # parse_constant rejects named constants, not overflow of ordinary JSON floats.
        overflow = data.replace(b'"number":1.25', b'"number":1e999')
        self.assertNotEqual(overflow, data)
        self.assertEqual(allocation_trace.validate_trace(overflow, self.digest), 4)

    def test_duplicate_fields_at_root_and_in_nested_objects(self):
        prefix = self.encode([self.header, self.body])
        cases = [
            b'{"event":2,"event":2,"kind":"function"}',
            b'{"event":2,"kind":"function","value":{"x":1,"x":2}}',
            b'{"event":2,"kind":"function","value":[{"x":1,"x":2}]}',
            b'{"event":2,"kind":"function","value":{"x":1,"\\u0078":2}}',
        ]
        for record in cases:
            with self.subTest(record=record):
                self.assert_error(lambda: allocation_trace.validate_trace(
                    prefix + record + b'\n', self.digest), 'duplicate allocation trace field')
        self.assertEqual(allocation_trace.validate_trace(self.good(), self.digest), 4)

    def test_nonfinite_values_at_root_and_nested_positions(self):
        prefix = self.encode([self.header, self.body])
        for value in [b'NaN', b'Infinity', b'-Infinity']:
            for nested in [False, True]:
                with self.subTest(value=value, nested=nested):
                    payload = b'[{"number":' + value + b'}]' if nested else value
                    record = b'{"event":2,"kind":"function","value":' + payload + b'}\n'
                    self.assert_error(lambda: allocation_trace.validate_trace(
                        prefix + record, self.digest),
                        'nonfinite allocation trace value: ' + value.decode('ascii'))
        self.assertEqual(allocation_trace.validate_trace(self.good(), self.digest), 4)

    def test_parser_error_details_match_json_loads_on_each_record(self):
        records = [
            b'\xef\xbb\xbf{}',                 # BOM at the start of a decoded record.
            b' \t\xef\xbb\xbf{}',             # BOM after JSON whitespace has a different position.
            b'', b' \t', b'{} {}',           # Blank records and trailing JSON documents.
            b'{"value":[1,]}', b'{"value":', # Malformed nested or incomplete data.
            b'{"value":"\x01"}',            # Strict control character rejection.
            b'{"value":"\xff"}', b'\xed\xa0\x80',
        ]
        for prefix in [b'', self.encode([self.header, self.body])]:
            for record in records:
                with self.subTest(prefix_events=prefix.count(b'\n'), record=record):
                    with self.assertRaises(ValueError) as expected:
                        json.loads(record.decode('utf-8'))
                    with self.assertRaises(ValueError) as actual:
                        allocation_trace.validate_trace(prefix + record + b'\n', self.digest)
                    self.assertIs(type(actual.exception), type(expected.exception))
                    self.assertEqual(str(actual.exception), str(expected.exception))
                    if isinstance(expected.exception, json.JSONDecodeError):
                        for name in ['msg', 'doc', 'pos', 'lineno', 'colno']:
                            self.assertEqual(getattr(actual.exception, name),
                                             getattr(expected.exception, name), name)
                    else:
                        self.assertIsInstance(expected.exception, UnicodeDecodeError)
                        for name in ['encoding', 'object', 'start', 'end', 'reason']:
                            self.assertEqual(getattr(actual.exception, name),
                                             getattr(expected.exception, name), name)

    def test_nested_records_and_parser_recovery_with_both_scanners(self):
        prefix = self.encode([self.header])
        suffix = self.encode([dict(kind='complete', event=2, prior_events=2,
                                   artifact_sha256=self.digest)])

        def nested(depth, malformed=False):
            value = b'0,' if malformed else b'0'
            return (prefix + b'{"event":1,"kind":"function","value":'
                    + b'[' * depth + value + b']' * depth + b'}\n' + suffix)

        for scanner in [json.scanner.make_scanner, json.scanner.py_make_scanner]:
            with self.subTest(scanner=scanner), patch.object(json.scanner, 'make_scanner', scanner):
                self.assertEqual(allocation_trace.validate_trace(nested(32), self.digest), 3)
                with self.assertRaises(json.JSONDecodeError):
                    allocation_trace.validate_trace(nested(32, malformed=True), self.digest)
                self.assertEqual(allocation_trace.validate_trace(nested(32), self.digest), 3)
                # The C scanner's nesting budget need not follow Python's recursion limit.
                if scanner is json.scanner.py_make_scanner:
                    with self.assertRaises(RecursionError):
                        allocation_trace.validate_trace(nested(4096), self.digest)
                    self.assertEqual(allocation_trace.validate_trace(nested(32), self.digest), 3)

    def test_validation_error_order_and_bounds(self):
        data = self.good()
        prefix = self.encode([self.header])
        cases = [
            (b'', 'invalid', {}, 'allocation trace exceeds byte bound or is empty'),
            (data, 'invalid', {'max_bytes': len(data) - 1},
             'allocation trace exceeds byte bound or is empty'),
            (b'{', 'invalid', {}, 'allocation trace lacks final newline'),
            (b'{\n', 'invalid', {}, 'invalid selected artifact digest'),
            (b'\xef\xbb\xbf{}\n', self.digest, {'max_events': 0},
             'allocation trace exceeds event bound or continues after completion'),
            (prefix + b'{\n', self.digest, {'max_events': 1},
             'allocation trace exceeds event bound or continues after completion'),
            (data + b'{\n', self.digest, {},
             'allocation trace exceeds event bound or continues after completion'),
            (self.encode([dict(self.header, strict_frontend=False)]) + b'{\n',
             self.digest, {}, 'incompatible allocation trace header'),
            (self.encode([self.header, dict(self.body, event=True, parent=2)]),
             self.digest, {}, 'allocation trace event identity differs'),
            (self.encode([self.header, dict(self.body, parent=1)]) + b'{\n',
             self.digest, {}, 'allocation trace parent is not an earlier event'),
            (prefix, self.digest, {}, 'allocation trace is incomplete'),
        ]
        for wire, digest, kwargs, message in cases:
            with self.subTest(wire=wire, kwargs=kwargs, message=message):
                self.assert_error(lambda: allocation_trace.validate_trace(wire, digest, **kwargs),
                                  message)

    def test_selected_trace_receipt_and_parser_error_causes(self):
        with tempfile.TemporaryDirectory() as temporary:
            artifact = Path(temporary).resolve() / 'program.rbc'
            program = b'owned selected-artifact fixture'
            artifact.write_bytes(program)
            digest = hashlib.sha256(program).hexdigest()
            sidecar = Path(str(artifact) + '.allocations.jsonl')
            data = self.good(digest)
            sidecar.write_bytes(data)
            self.assertEqual(allocation_trace.selected_trace(artifact), dict(
                kind='allocation-trace', schema_version=1, strict_frontend=True,
                path=str(sidecar), bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                events=4, artifact_path=str(artifact), artifact_bytes=len(program),
                artifact_sha256=digest))
            malformed = [b'\xef\xbb\xbf{}\n',
                         self.encode([self.header, self.body])
                         + b'{"event":2,"kind":"function","value":{"x":1,"x":2}}\n',
                         self.encode([self.header]) + b'\xff\n']
            for wire in malformed:
                with self.subTest(wire=wire):
                    sidecar.write_bytes(wire)
                    with self.assertRaises(ValueError) as direct:
                        allocation_trace.validate_trace(wire, digest)
                    wrapped = self.assert_error(lambda: allocation_trace.selected_trace(artifact),
                        'Cargo selected an invalid allocation trace; no program was run: '
                        + str(direct.exception), RuntimeError)
                    self.assertIs(type(wrapped.__cause__), type(direct.exception))
                    self.assertEqual(str(wrapped.__cause__), str(direct.exception))
            sidecar.write_bytes(data)
            self.assertEqual(allocation_trace.selected_trace(artifact)['events'], 4)


if __name__ == '__main__':
    unittest.main()
