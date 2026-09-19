"""Pure diagnostic/linker readback and synthetic Mach-O controls; no probes."""
import json
from pathlib import Path
import shlex
import struct
import tempfile
import unittest

import observations as observed


def diagnostic(code='E0308', message='mismatched types', children=None):
    return {'$message_type': 'diagnostic', 'level': 'error', 'code': {'code': code},
            'message': message, 'children': [] if children is None else children}


def raw_diagnostic(value):
    return (json.dumps(value) + '\n').encode()


class DiagnosticControls(unittest.TestCase):
    def test_exact_raw_uncalled_error_is_preserved(self):
        raw = raw_diagnostic(diagnostic())
        result = observed.error_pair((b'', raw), (b'', raw), 'E0308')
        self.assertEqual(result['raw_sha256'], observed.digest(raw))
        self.assertEqual(result['records'], 1)
        self.assertEqual(result['code'], 'E0308')

    def test_raw_difference_stdout_or_wrong_error_cannot_pass(self):
        raw = raw_diagnostic(diagnostic())
        for one, two in [((b'', raw), (b'', raw.replace(b'types', b'type'))),
                         ((b'noise', raw), (b'noise', raw)),
                         ((b'', raw[:-1]), (b'', raw[:-1]))]:
            with self.subTest(one=one, two=two), self.assertRaises(ValueError):
                observed.error_pair(one, two, 'E0308')
        wrong = raw_diagnostic(diagnostic('E0463', 'cannot find crate'))
        with self.assertRaises(ValueError):
            observed.error_pair((b'', wrong), (b'', wrong), 'E0308')

    def test_duplicate_json_nonfinite_and_warning_records_reject(self):
        raw = raw_diagnostic(diagnostic())
        variants = [raw.replace(b'"level": "error"', b'"level": "error", "level": "error"'),
                    raw.replace(b'"children": []', b'"children": [], "unused": NaN'),
                    raw + raw_diagnostic(diagnostic() | {'level': 'warning'}),
                    raw + b'{"$message_type":"artifact"}\n']
        for value in variants:
            with self.subTest(raw=value), self.assertRaises(ValueError):
                observed.error_pair((b'', value), (b'', value), 'E0308')

    def test_wrong_role_requires_incompatibility_and_qualified_std_path(self):
        path = '/qualified/B3/lib/rustlib/aarch64-apple-darwin/lib/libstd-a123.rlib'
        note = {'level': 'note', 'message': 'the following crate versions were found:\ncrate `std`: ' + path}
        value = diagnostic('E0514', 'found crate `std` compiled by an incompatible version of rustc', [note])
        raw = raw_diagnostic(value)
        result = observed.wrong_pair((b'', raw), (b'', raw), [path])
        self.assertEqual(result['beta_std_paths'], [path])
        for modified in [value | {'message': 'cannot find crate `std`'},
                         value | {'children': []},
                         value | {'children': [{'level': 'note', 'message': 'unrelated mention: ' + path}]},
                         value | {'children': [{'level': 'note', 'message': note['message'] + '.foreign'}]}]:
            bad = raw_diagnostic(modified)
            with self.subTest(value=modified), self.assertRaises(ValueError):
                observed.wrong_pair((b'', bad), (b'', bad), [path])

    def test_warm_hit_proof_requires_every_verification_and_valid_interval(self):
        raw = b'[hir-body-reuse] anchor hit cache_hits=1 verify_tree=1 verify_journal=1 verify_poststate=1 S=12 E=42\n'
        self.assertEqual(observed.hit(raw)['values'], [12, 42])
        variants = [raw + raw, raw.replace(b'verify_journal=1', b'verify_journal=0'),
                    raw.replace(b'S=12 E=42', b'S=42 E=42'), raw.replace(b'cache_hits=1', b'cache_hits=2'),
                    raw + b'warning: failed to strip\n']
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ValueError):
                observed.hit(value)

    def test_cold_capture_is_distinct_from_reuse_and_bounds_all_counters(self):
        raw = (b'[hir-body-capture] anchor cold-tree-and-journal-after-stock-lowering '
               b'S=12 E=42 events=3 cache_hits=0 body_codec=1 prepared_values=1 '
               b'cold_materialization_audit=1 hit_materializer=0 body_bytes=256 body_ast=20 '
               b'param_ast=2 trait_entries=1 trait_candidates=1 external_refs=0\n')
        result = observed.hit(raw, cold=True)
        self.assertTrue(result['cold']); self.assertEqual(result['values'][:3], [12, 42, 3])
        with self.assertRaises(ValueError):
            observed.hit(raw)
        with self.assertRaises(ValueError):
            observed.hit(raw.replace(b'body_bytes=256', b'body_bytes=18446744073709551616'), cold=True)


class LinkerControls(unittest.TestCase):
    CLANG = '/qualified/Xcode/usr/bin/clang'
    OUTPUT = Path('/owned/native/stock')
    LIB = Path('/qualified/E2/lib')

    def words(self):
        return ['env', '-u', 'IPHONEOS_DEPLOYMENT_TARGET', '-u', 'TVOS_DEPLOYMENT_TARGET',
                '-u', 'XROS_DEPLOYMENT_TARGET', 'SDKROOT=/qualified/SDK', 'LC_ALL=C', self.CLANG,
                '/qualified/B3/librustc_driver-abcd.dylib', '-o', str(self.OUTPUT),
                '-Wl,-rpath,' + str(self.LIB)]

    def check(self, words):
        return observed.link_command((shlex.join(words) + '\n').encode(), clang=self.CLANG,
                                     output=self.OUTPUT, runtime_lib=self.LIB)

    def test_apple_environment_prefix_retains_actual_linker_and_arguments(self):
        words = self.words(); result = self.check(words)
        self.assertEqual(result['argv'], words[9:])
        self.assertEqual(result['environment'], {'SDKROOT': '/qualified/SDK', 'LC_ALL': 'C'})
        self.assertEqual(result['removed'], ['IPHONEOS_DEPLOYMENT_TARGET', 'TVOS_DEPLOYMENT_TARGET', 'XROS_DEPLOYMENT_TARGET'])

    def test_unproved_linker_route_or_loader_override_rejects(self):
        words = self.words()
        for changed in [words[1:], words[:3] + words[5:],
                        words[:9] + ['DESCRIPTION=' + self.CLANG, '/foreign/clang'] + words[10:],
                        words[:9] + ['DYLD_LIBRARY_PATH=/foreign'] + words[9:],
                        words[:9] + ['SDKROOT=/qualified/SDK'] + words[9:]]:
            with self.subTest(words=changed), self.assertRaises(ValueError):
                self.check(changed)

    def test_wrong_output_missing_rpath_and_multiple_linker_rows_reject(self):
        words = self.words()
        for changed in [words + ['-o', '/foreign'],
                        ['/foreign' if word == str(self.OUTPUT) else word for word in words], words[:-1]]:
            with self.subTest(words=changed), self.assertRaises(ValueError):
                self.check(changed)
        raw = (shlex.join(words) + '\nother\n').encode()
        with self.assertRaises(ValueError):
            observed.link_command(raw, clang=self.CLANG, output=self.OUTPUT, runtime_lib=self.LIB)


def string_command(command, token, *, offset=None):
    start = (24 if command == 0xC else 12) if offset is None else offset
    value = token.encode() + b'\0'
    width = (start + len(value) + 7) // 8 * 8
    return struct.pack('<III', command, width, start) + bytes(start-12) + value + bytes(width-start-len(value))


def executable(commands):
    body = b''.join(commands)
    return struct.pack('<8I', 0xFEEDFACF, 0x100000C, 0, 2, len(commands), len(body), 0, 0) + body


class LoaderControls(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve(strict=True)
        self.lib = self.base / 'E2/lib'; self.lib.mkdir(parents=True)
        self.driver = self.lib / 'librustc_driver-abcd.dylib'; self.driver.write_bytes(b'synthetic driver')
        self.llvm = self.lib / 'libLLVM.dylib'; self.llvm.write_bytes(b'synthetic LLVM')
        self.stock = self.base / 'stock'
        self.private = {str(path): str(path) for path in [self.driver, self.llvm]}
        self.loads = ['@rpath/' + self.driver.name, '@rpath/libLLVM.dylib', '/usr/lib/libSystem.B.dylib']

    def commands(self, loads=None):
        return [string_command(0x8000001C, str(self.lib))] + [string_command(0xC, value) for value in (self.loads if loads is None else loads)]

    def otool(self, loads=None):
        return (str(self.stock) + ':\n' + ''.join('\t' + token + ' (compatibility version 0.0.0, current version 0.0.0)\n'
                                               for token in (self.loads if loads is None else loads))).encode()

    def check(self, *, commands=None, raw=None, private=None):
        return observed.stock_macho(executable(self.commands() if commands is None else commands),
            self.otool() if raw is None else raw, stock=self.stock, driver=self.driver,
            runtime_lib=self.lib, qualified_private=self.private if private is None else private)

    def test_both_driver_and_llvm_direct_edges_are_accepted_when_qualified(self):
        result = self.check()
        self.assertEqual(result['direct_private'], [str(self.driver), str(self.llvm)])
        self.assertEqual(result['loads'], self.loads)

    def test_foreign_or_missing_driver_edge_rejects(self):
        for loads in [self.loads[1:], self.loads + ['@rpath/libforeign.dylib']]:
            with self.subTest(loads=loads), self.assertRaises(ValueError):
                self.check(commands=self.commands(loads), raw=self.otool(loads))
        wrong = self.private | {str(self.llvm): str(self.base / 'foreign')}
        with self.assertRaises(ValueError):
            self.check(private=wrong)

    def test_otool_disagreement_foreign_header_or_extra_diagnostic_rejects(self):
        for raw in [self.otool(self.loads[:-1]), self.otool().replace((str(self.stock) + ':').encode(), b'/foreign/stock:'),
                    self.otool() + b'otool: unexpected diagnostic\n']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.check(raw=raw)

    def test_dylib_string_inside_fixed_header_rejects(self):
        commands = self.commands()
        commands[1] = string_command(0xC, self.loads[0], offset=12)
        with self.assertRaises(ValueError):
            self.check(commands=commands)

    def test_dyld_environment_dylib_identity_and_foreign_rpath_reject(self):
        for commands in [self.commands() + [struct.pack('<II', 0x27, 8)],
                         self.commands() + [struct.pack('<II', 0xD, 8)],
                         [string_command(0x8000001C, '/foreign')] + self.commands()[1:]]:
            with self.subTest(commands=commands), self.assertRaises(ValueError):
                self.check(commands=commands)


if __name__ == '__main__':
    unittest.main(verbosity=2)
