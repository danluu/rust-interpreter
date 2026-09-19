"""Saved actual binary/doctest rows and adversarial non-private-output controls."""
import json
from pathlib import Path
import shlex
import tomllib
import unittest

import producer
import test_output_catalog
from compose_sysroot import digest, parse_stamp

HERE = Path(__file__).resolve().parent


class NonPrivateOutputs(unittest.TestCase):
    def test_repeated_library_types_cover_every_rustc_output(self):
        argv = ['/source/rustc', '--crate-name', 'std', '--crate-type', 'dylib',
                '--crate-type', 'rlib', '--emit=dep-info,metadata,link',
                '-Cextra-filename=-abc', '--out-dir', '/source/out']
        expected = {'/source/out/libstd-abc.'+suffix for suffix in ['rlib', 'rmeta', 'dylib']}
        self.assertEqual(producer.rust_outputs(argv), expected)
        joined = [*argv[:3], '--crate-type=dylib,rlib', *argv[7:]]
        self.assertEqual(producer.rust_outputs(joined), expected)

    def test_lib_alias_and_repeated_types_have_identical_output_sets(self):
        self.assertEqual(producer.crate_types(['--crate-type', 'lib', '--crate-type=rlib,dylib,lib']),
                         ['rlib', 'dylib'])

    def test_empty_unknown_and_mixed_output_types_reject(self):
        for argv in [[], ['--crate-type'], ['--crate-type='], ['--crate-type=rlib,'],
                     ['--crate-type=unknown'], ['--crate-type=bin,rlib'], ['--crate-type=proc-macro,lib']]:
            with self.subTest(argv=argv), self.assertRaises(ValueError):
                producer.crate_types(argv)

    def test_repeated_types_do_not_hide_later_private_overwrite(self):
        composition, streams, cargo, rows, pair = test_output_catalog.CompleteOutputControls().fixture()
        extra = rows[0]+['--crate-type', 'rlib']
        composition, streams, cargo, _, _ = test_output_catalog.CompleteOutputControls().fixture([extra])
        catalog = producer.output_catalog(composition, streams, cargo)
        selected, _ = producer.last_producers(composition, catalog)
        self.assertEqual(len(catalog[1]['outputs']), 3)
        self.assertTrue(all(selected[path]['command']['line'] == 2 for path in pair))

    def test_complete_saved_actual_catalog_has_all_256_final_private_producers(self):
        bindings = json.loads((HERE/'source-bindings.json').read_bytes())['references']
        def bound(name):
            row = bindings[name]; raw = Path(row['path']).read_bytes()
            self.assertEqual(digest(raw), row['sha256'])
            return raw
        compiled = json.loads(bound('actual-compiled03'))
        stamp = Path(bindings['actual-native-stamp']['path']); tree = stamp.parents[2]
        source = tree.parents[2]
        composition = dict(source=str(source), tree=str(tree),
                           private=parse_stamp(bound('actual-native-stamp'), tree=tree))
        streams = {}
        history = compiled['actual_command_history']
        self.assertEqual(len(history), 26)
        for i, ref in enumerate(history):
            if ref['command'][0] != './x':
                continue
            child = json.loads(bound('actual-catalog-receipt-'+str(i)))
            self.assertEqual(child['command'], ref['command'])
            for kind in ['stdout', 'stderr']:
                row = bindings['actual-catalog-'+str(i)+'-'+kind]
                raw = bound('actual-catalog-'+str(i)+'-'+kind)
                self.assertEqual(digest(raw), child[kind+'_sha256'])
                streams[row['path']] = dict(raw=raw, child_receipt=ref['path'],
                    history_index=i, stage_index=i, stream_kind=kind,
                    outer_argv=child['command'], environment=child['environment'])
        # This is a saved-byte parser control, not a new provenance/admission
        # claim. The ordinary discovery independently repeats complete history.
        proof = producer.discover(composition, streams, tomllib.loads(bound('actual-bootstrap-config').decode()))
        self.assertEqual(set(proof['private']), {row['source'] for row in composition['private']})
        self.assertEqual(len(proof['private']), 256)
        self.assertEqual(len(proof['consumer']['ordered_driver_pair']), 2)

    def binary(self):
        return ['/source/build/bootstrap/debug/rustc']*2 + [
            '--crate-name', 'build_script_build', 'build.rs', '--crate-type', 'bin',
            '--emit=dep-info,link', '--out-dir', '/source/build/script/out']

    def documentation(self):
        return ['/source/build/bootstrap/debug/rustdoc', '--crate-name', 'rustc_interface',
                '--crate-type', 'lib', '--test', 'compiler/rustc_interface/src/lib.rs',
                '--target', 'aarch64-apple-darwin', '--test-run-directory', '/source/compiler/rustc_interface']

    def test_saved_all_47_binary_and_two_documentation_commands(self):
        bindings = json.loads((HERE/'source-bindings.json').read_bytes())['references']
        report = Path(bindings['failed-discovery04']['path'])
        self.assertEqual(digest(report.read_bytes()), bindings['failed-discovery04']['sha256'])
        records = json.loads(report.read_bytes())['unexpected_output_command_forms']
        self.assertEqual(len(records), 49)
        binary, documentation = 0, 0
        for record in records:
            raw = Path(record['path']).read_bytes()
            row = producer.running_line(raw, dict(line=record['line'], line_sha256=record['line_sha256']))
            argv = row['argv']; source = str(Path(argv[0]).parents[3])
            if Path(argv[0]).name == 'rustdoc':
                self.assertEqual(producer.rustdoc_test(argv, source)['private_outputs'], [])
                documentation += 1
            else:
                self.assertEqual(producer.rust_outputs(argv, native=False), set())
                binary += 1
        self.assertEqual((binary, documentation), (47, 2))

    def test_binary_has_no_private_output_but_is_retained(self):
        composition, streams, cargo, _, _ = test_output_catalog.CompleteOutputControls().fixture([self.binary()])
        rows = producer.output_catalog(composition, streams, cargo)
        self.assertEqual(rows[1]['kind'], 'rustc-running')
        self.assertEqual(rows[1]['outputs'], [])
        self.assertEqual(rows[1]['parsed']['argv'], self.binary())

    def test_binary_mixed_role_or_metadata_rejects(self):
        for before, after in [('bin', 'bin,rlib'), ('bin', 'lib'),
                              ('--emit=dep-info,link', '--emit=dep-info,metadata,link')]:
            with self.subTest(after=after), self.assertRaises(ValueError):
                producer.rust_outputs([after if word == before else word for word in self.binary()], native=False)

    def test_binary_output_redirect_or_indirect_args_reject(self):
        for extra in [['-o', '/source/libx.rlib'], ['-o/source/libx.rlib'],
                      ['--output=/source/libx.rlib'], ['@/source/args']]:
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                producer.rust_outputs(self.binary()+extra, native=False)

    def test_library_without_extra_filename_remains_rejected(self):
        argv = [word.replace('build_script_build', 'ordinary_library').replace('bin', 'rlib') for word in self.binary()]
        with self.assertRaises(ValueError):
            producer.rust_outputs(argv, native=False)

    def test_duplicate_filename_and_explicit_emit_remain_rejected(self):
        for argv in [self.binary()+['-Cextra-filename=-a', '-Cextra-filename=-b'],
                     [word.replace('--emit=dep-info,link', '--emit=link=/source/libx.rlib') for word in self.binary()]]:
            with self.subTest(argv=argv), self.assertRaises(ValueError):
                producer.rust_outputs(argv, native=False)

    def test_documentation_retained_with_explicit_nonprivate_role(self):
        composition, streams, cargo, _, _ = test_output_catalog.CompleteOutputControls().fixture([self.documentation()])
        rows = producer.output_catalog(composition, streams, cargo)
        self.assertEqual(rows[1]['kind'], 'rustdoc-test-running')
        self.assertEqual(rows[1]['outputs'], [])
        self.assertEqual(rows[1]['parsed']['argv'], self.documentation())

    def test_documentation_outputs_and_response_files_reject(self):
        for extra in [['--persist-doctests', '/source/out'], ['--out-dir=/source/out'],
                      ['--emit=metadata'], ['-o/source/out'], ['@/source/args'],
                      ['--test-builder=/foreign/compiler']]:
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                producer.rustdoc_test(self.documentation()+extra, '/source')

    def test_documentation_foreign_route_target_or_input_rejects(self):
        for before, after in [('/source/build/bootstrap/debug/rustdoc', '/foreign/rustdoc'),
                              ('lib', 'proc-macro'),
                              ('aarch64-apple-darwin', 'x86_64-apple-darwin'),
                              ('compiler/rustc_interface/src/lib.rs', 'compiler/other/src/lib.rs'),
                              ('/source/compiler/rustc_interface', '/foreign/cwd')]:
            with self.subTest(after=after), self.assertRaises(ValueError):
                producer.rustdoc_test([after if word == before else word for word in self.documentation()], '/source')

    def test_documentation_missing_or_duplicate_test_mode_rejects(self):
        for argv in [self.documentation()+['--test'], [word for word in self.documentation() if word != '--test']]:
            with self.subTest(argv=argv), self.assertRaises(ValueError):
                producer.rustdoc_test(argv, '/source')


if __name__ == '__main__':
    unittest.main()
