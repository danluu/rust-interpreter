"""Pure saved-byte parser controls; no subprocess, compiler, loader or edits.

The future supervised test launch must bind the saved raw input named below
alongside this source and linker_parser.py. These tests have not been run by
the source preparer. Original metadata03 evidence is read only.
"""
import hashlib
from pathlib import Path
import unittest

import linker_parser as parser


OWNER = Path(__file__).resolve().parents[3]
SAVED = OWNER/'.work/hir-options-hash-compiler-metadata-03/commands/047/stderr'
SAVED_SHA256 = '950bfdc12496b487e06869981eb0dd12b45e29a9268804f4fc5c8e79899755a3'
PID = 79778
TOOLCHAIN = '/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr'
EXPECTED = [TOOLCHAIN+'/bin/ld', *[TOOLCHAIN+'/lib/'+name for name in (
    'libLTO.dylib', 'libcodedirectory.dylib', 'libswiftDemangle.dylib', 'libtapi.dylib')]]


class LinkerParserControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        def stamp(value):
            return tuple(getattr(value, 'st_'+name) for name in
                         ('dev', 'ino', 'mode', 'size', 'mtime_ns', 'ctime_ns', 'nlink'))
        before = SAVED.stat()
        if not (SAVED.resolve(strict=True) == SAVED and 0 < before.st_size <= 2**20):
            raise AssertionError('bounded original saved stderr required')
        cls.raw = SAVED.read_bytes()
        if stamp(SAVED.stat()) != stamp(before) or hashlib.sha256(cls.raw).hexdigest() != SAVED_SHA256:
            raise AssertionError('original saved stderr changed')

    def reject(self, raw, *, pid=PID, expected=EXPECTED):
        with self.assertRaises((RuntimeError, UnicodeError)):
            parser.parse(raw, pid, list(expected))

    def test_actual_saved_report_is_lossless(self):
        result = parser.parse(self.raw, PID, list(EXPECTED))
        self.assertEqual(result['raw_sha256'], SAVED_SHA256)
        self.assertEqual(result['raw_bytes'], len(self.raw))
        self.assertEqual(result['private_paths'], sorted(EXPECTED))
        self.assertEqual(len(result['lines']), 713)
        self.assertEqual(len(result['version_lines']), 6)
        self.assertEqual(result['version_text'], parser.VERSION_TEXT)
        self.assertTrue(result['delayed'])
        cursor = 0
        for number, row in enumerate(result['lines'], 1):
            data = bytes.fromhex(row['raw_hex'])
            self.assertEqual(row['line'], number)
            self.assertEqual(row['start'], cursor)
            cursor += len(data)
            self.assertEqual(row['end'], cursor)
            self.assertEqual(data, row['raw'].encode('utf-8'))
            self.assertEqual(self.raw[row['start']:row['end']], data)
        self.assertEqual(cursor, len(self.raw))
        self.assertEqual(b''.join(bytes.fromhex(row['raw_hex']) for row in result['lines']), self.raw)
        for row in result['delayed']:
            self.assertTrue(parser.system(row['image']))
            self.assertNotIn(row['image'], result['private_paths'])

    def test_each_version_line_is_exact_and_required(self):
        for line in parser.VERSION_TEXT.encode().splitlines(keepends=True):
            self.assertEqual(self.raw.count(line), 1)
            for replacement in (b'', line+line, line[:-1]+b' changed\n'):
                with self.subTest(line=line, replacement=replacement):
                    self.reject(self.raw.replace(line, replacement, 1))

    def test_version_line_order_is_required(self):
        lines = parser.VERSION_TEXT.encode().splitlines(keepends=True)
        reordered = b''.join([lines[1], lines[0], *lines[2:]])
        self.reject(self.raw.replace(parser.VERSION_TEXT.encode(), reordered, 1))

    def test_unknown_lines_and_invented_search_sections_are_rejected(self):
        for extra in (b'warning: unreviewed diagnostic\n', b'Library search paths:\n',
                      b'Framework search paths:\n', b'\n', b'\t/usr/lib\n'):
            with self.subTest(extra=extra):
                self.reject(self.raw+extra)
                self.reject(extra+self.raw)

    def test_wrong_pid_and_unknown_dyld_grammar_are_rejected(self):
        self.reject(self.raw, pid=PID+1)
        self.reject(self.raw.replace(f'dyld[{PID}]'.encode(), f'dyld[{PID+1}]'.encode(), 1))
        self.reject(self.raw+f'dyld[{PID}]: unknown loader event\n'.encode())

    def test_private_loaded_set_is_exact(self):
        self.reject(self.raw.replace(EXPECTED[0].encode(), b'/private/foreign/ld', 1))
        missing = b''.join(line for line in self.raw.splitlines(keepends=True)
                           if not line.endswith(EXPECTED[1].encode()+b'\n'))
        self.assertNotEqual(missing, self.raw)
        self.reject(missing)
        self.reject(self.raw, expected=EXPECTED[:-1])
        self.reject(self.raw, expected=[*EXPECTED[:-1], EXPECTED[0]])
        self.reject(self.raw, expected=[*EXPECTED[:-1], '/private/foreign/libtapi.dylib'])

    def test_delayed_foreign_private_or_unseen_image_is_rejected(self):
        for name in ('libLTO.dylib', 'never-loaded-system-image.dylib'):
            with self.subTest(name=name):
                self.reject(self.raw+f'dyld[{PID}]: move loaded to delayed: {name}\n'.encode())
        self.reject(f'dyld[{PID}]: move loaded to delayed: libSystem.B.dylib\n'.encode()+self.raw)

    def test_noncanonical_or_incomplete_bytes_are_rejected(self):
        for raw in (self.raw[:-1], self.raw.replace(b'\n', b'\r\n', 1), self.raw+b'\x00\n',
                    self.raw+b'\xff\n', self.raw.replace(EXPECTED[0].encode(),
                    (TOOLCHAIN+'/bin/../bin/ld').encode(), 1)):
            with self.subTest(suffix=raw[-50:]):
                self.reject(raw)

    def test_input_size_type_and_pid_bounds(self):
        for raw in (b'', b'x'*(8*2**20+1), self.raw.decode()):
            self.reject(raw)
        for pid in (0, -1, True):
            self.reject(self.raw, pid=pid)


if __name__ == '__main__':
    unittest.main()
