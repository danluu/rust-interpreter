"""Synthetic source controls only; they run no compiler or actual inspection."""
import unittest
import shlex

import producer
from compose_sysroot import digest


class ProducerControls(unittest.TestCase):
    def contexts(self, changes=None, second_child='child'):
        source = '/source'; host = 'aarch64-apple-darwin'; d = source + '/build/' + host + '/stage0'
        shim = source + '/build/bootstrap/debug/rustc'
        env = dict(RUSTC=shim, RUSTC_WRAPPER=shim, RUSTC_REAL=d + '/bin/rustc', RUSTC_SNAPSHOT=d + '/bin/rustc',
            RUSTC_LIBDIR=d + '/lib', RUSTC_SNAPSHOT_LIBDIR=d + '/lib', RUSTC_STAGE='0',
            RUSTC_SYSROOT=source + '/build/' + host + '/stage0-sysroot',
            CARGO_TARGET_DIR=source + '/build/' + host + '/stage1-rustc',
            CARGO_BUILD_BUILD_DIR=source + '/build/' + host + '/stage1-rustc')
        env['DYLD_LIBRARY_PATH'] = ':'.join(producer.test_loader_paths(source))
        row = dict(argv=[shim, shim, '--crate-name', 'test', '--target', host], environment={})
        raw = ('  Running `' + shlex.join(row['argv']) + '`\n').encode()
        coordinate = dict(stream='rustc', line=1, line_sha256=digest(raw))
        streams = {'rustc': dict(raw=raw, child_receipt='child', environment={})}
        catalog = []
        for index, extra in enumerate([{}, changes or {}]):
            name = 'cargo' + str(index)
            command = ['cd', source, '&&', 'env', *[key + '=' + value for key, value in (env | extra).items()],
                       d + '/bin/cargo', 'test', '(failure_mode=Exit)']
            text = ('running: ' + shlex.join(command) + '\n').encode()
            coord = dict(stream=name, line=1, line_sha256=digest(text))
            parsed = producer.bootstrap_line(text, coord, source)
            child = 'child' if index == 0 else second_child
            streams[name] = dict(raw=text, child_receipt=child, environment={})
            catalog.append(dict(command=coord, parsed=parsed, child_receipt=child, stage_index=0, execution='real'))
        binding = dict(command=coordinate, cargo_command=catalog[0]['command'], parsed=row,
                       parsed_cargo=catalog[0]['parsed'])
        return binding, catalog, streams, source

    def test_all_same_child_contexts_are_considered_despite_selected_coordinate(self):
        for key in ['CFG_RELEASE', 'RUSTC_HOST_FLAGS', 'AR', 'SDKROOT', 'ARBITRARY_ENV_INPUT']:
            for selected in [0, 1]:
                with self.subTest(key=key, selected=selected), self.assertRaises(ValueError):
                    binding, catalog, streams, source = self.contexts({key: 'different'})
                    binding['cargo_command'] = catalog[selected]['command']
                    binding['parsed_cargo'] = catalog[selected]['parsed']
                    producer.actual_command(binding, catalog, streams, source)

    def test_repeated_equivalent_contexts_pass_without_claiming_nesting(self):
        binding, catalog, streams, source = self.contexts()
        row, environment = producer.actual_command(binding, catalog, streams, source)
        self.assertEqual(row, binding['parsed'])
        self.assertEqual(environment, catalog[0]['parsed']['environment'])

    def test_foreign_provider_in_unchosen_same_child_context_is_rejected(self):
        with self.assertRaises(ValueError):
            producer.actual_command(*self.contexts({'RUSTC_REAL': '/foreign/rustc'}))

    def test_other_child_context_is_not_misattributed_to_selected_child(self):
        binding, catalog, streams, source = self.contexts({'CFG_RELEASE': 'different'}, 'other-child')
        producer.actual_command(binding, catalog, streams, source)
        binding['cargo_command'] = catalog[1]['command']; binding['parsed_cargo'] = catalog[1]['parsed']
        with self.assertRaises(ValueError):
            producer.actual_command(binding, catalog, streams, source)

    def test_same_child_inherited_environment_records_must_agree(self):
        binding, catalog, streams, source = self.contexts()
        streams['cargo1']['environment'] = {'ARBITRARY_ENV_INPUT': 'different'}
        with self.assertRaises(ValueError):
            producer.actual_command(binding, catalog, streams, source)

    def test_effective_environment_comparison_retains_unset_semantics(self):
        binding, catalog, streams, source = self.contexts()
        row, cargo = binding['parsed'], catalog[0]['parsed']
        one = dict(cargo=cargo, inherited={})
        two = dict(cargo=cargo | {'removed': ['EXTRA']}, inherited={'EXTRA': 'x'})
        self.assertEqual(producer.unambiguous_environment(row, [one, two], source), cargo['environment'])
        with self.assertRaises(ValueError):
            producer.unambiguous_environment(row, [one, dict(cargo=cargo, inherited={'EXTRA': 'x'})], source)
        with self.assertRaises(ValueError):
            producer.unambiguous_environment(row, [], source)

    def test_selfcheck_is_preserved_but_cannot_be_selected_as_real(self):
        binding, catalog, streams, source = self.contexts({'ARBITRARY_ENV_INPUT': 'different'})
        catalog[1]['execution'] = 'self-check-print'
        producer.actual_command(binding, catalog, streams, source)
        binding['cargo_command'] = catalog[1]['command']; binding['parsed_cargo'] = catalog[1]['parsed']
        with self.assertRaises(ValueError): producer.actual_command(binding, catalog, streams, source)

    def test_exact_test_loader_order_and_absent_inherited_or_crate_overrides(self):
        binding, catalog, streams, source = self.contexts()
        row, cargo = binding['parsed'], catalog[0]['parsed']
        producer.mechanism(row, cargo, {}, source)
        exact = ':'.join(producer.test_loader_paths(source))
        for value in [None, '', exact + ':/foreign', ':'.join(reversed(producer.test_loader_paths(source)))]:
            env = dict(cargo['environment'])
            if value is None: del env['DYLD_LIBRARY_PATH']
            else: env['DYLD_LIBRARY_PATH'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                producer.mechanism(row, cargo | {'environment': env}, {}, source)
        for key in ['DYLD_LIBRARY_PATH', 'DYLD_FALLBACK_LIBRARY_PATH', 'DYLD_INSERT_LIBRARIES', 'DYLD_FRAMEWORK_PATH', 'LD_PRELOAD']:
            with self.subTest(key=key), self.assertRaises(ValueError): producer.mechanism(row, cargo, {key: '/foreign'}, source)
            with self.subTest(key=key), self.assertRaises(ValueError): producer.mechanism(row | {'environment': {key: exact}}, cargo, {}, source)
        for mode in ['build', 'check']:
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                producer.mechanism(row, cargo | {'argv': [cargo['argv'][0], mode]}, {}, source)
            clean = dict(cargo['environment']); del clean['DYLD_LIBRARY_PATH']
            producer.mechanism(row, cargo | {'argv': [cargo['argv'][0], mode], 'environment': clean}, {}, source)

    def argv(self):
        return ['/candidate/bootstrap/rustc', '--crate-name', 'rustc_test', 'compiler/test.rs',
                '--crate-type', 'lib', '--emit=dep-info,metadata,link',
                '-C', 'extra-filename=-abcdef', '--out-dir', '/candidate/build/out']

    def test_actual_quoted_cargo_line_preserves_environment_and_argument_order(self):
        raw = b"  Running `CFG_VALUE='with spaces' /candidate/bootstrap/rustc --crate-name rustc_main --extern rustc_driver=/d.dylib --extern rustc_driver=/d.rmeta`\n"
        result = producer.running_line(raw, dict(line=1, line_sha256=digest(raw)))
        self.assertEqual(result['environment'], {'CFG_VALUE': 'with spaces'})
        self.assertEqual(result['argv'][-4:], ['--extern', 'rustc_driver=/d.dylib', '--extern', 'rustc_driver=/d.rmeta'])

    def test_raw_line_hash_and_coordinate_cannot_be_relabelled(self):
        raw = b'  Running `/candidate/rustc --crate-name x`\n'
        for coordinate in [dict(line=1, line_sha256='0' * 64), dict(line=0, line_sha256=digest(raw)),
                           dict(line=2, line_sha256=digest(raw))]:
            with self.subTest(coordinate=coordinate), self.assertRaises(ValueError):
                producer.running_line(raw, coordinate)

    def test_non_command_duplicate_environment_or_relative_executor_rejected(self):
        for raw in [b'Fresh rustc_main\n', b'Running `A=1 A=2 /candidate/rustc`\n', b'Running `rustc --crate-name x`\n']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                producer.running_line(raw, dict(line=1, line_sha256=digest(raw)))

    def test_rust_metadata_link_and_proc_macro_outputs_derive_exact_paths(self):
        argv = self.argv()
        self.assertEqual(producer.rust_outputs(argv), {'/candidate/build/out/librustc_test-abcdef.rmeta', '/candidate/build/out/librustc_test-abcdef.rlib'})
        argv[argv.index('lib')] = 'proc-macro'
        self.assertEqual(producer.rust_outputs(argv), {'/candidate/build/out/librustc_test-abcdef.rmeta', '/candidate/build/out/librustc_test-abcdef.dylib'})

    def test_duplicate_options_and_explicit_emit_paths_need_separate_proof(self):
        for argv in [self.argv() + ['--out-dir=/other'], self.argv() + ['-Cextra-filename=-other'],
                     [x.replace('--emit=dep-info,metadata,link', '--emit=metadata=/outside') for x in self.argv()]]:
            with self.subTest(argv=argv), self.assertRaises(ValueError):
                producer.rust_outputs(argv)

    def test_noncanonical_directory_and_foreign_output_kind_rejected(self):
        for argv in [[x.replace('/candidate/build/out', '/candidate/../outside') for x in self.argv()],
                     [x.replace('/candidate/build/out', 'relative') for x in self.argv()],
                     ['staticlib' if x == 'lib' else x for x in self.argv()]]:
            with self.subTest(argv=argv), self.assertRaises(ValueError):
                producer.rust_outputs(argv)

    def test_check_only_metadata_and_test_executable_do_not_qualify_private_outputs(self):
        for argv in [[x.replace('--emit=dep-info,metadata,link', '--emit=dep-info,metadata') for x in self.argv()], self.argv() + ['--test']]:
            with self.subTest(argv=argv), self.assertRaises(ValueError):
                producer.rust_outputs(argv)

    def test_bootstrap_cargo_command_preserves_unsets_and_inherited_routing(self):
        raw = b'running: cd "/source" && env -u CARGO_ENCODED_RUSTFLAGS RUSTC_REAL="/source/D/bin/rustc" /source/D/bin/cargo test --profile=release (failure_mode=Exit)\n'
        result = producer.bootstrap_line(raw, dict(line=1, line_sha256=digest(raw)), '/source')
        self.assertEqual(result['removed'], ['CARGO_ENCODED_RUSTFLAGS'])
        self.assertEqual(result['environment']['RUSTC_REAL'], '/source/D/bin/rustc')
        self.assertEqual(result['argv'], ['/source/D/bin/cargo', 'test', '--profile=release'])
        for bad in [raw.replace(b'/source"', b'/foreign"'), raw.replace(b'(failure_mode=Exit)', b'(failure_mode=Ignore)')]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                producer.bootstrap_line(bad, dict(line=1, line_sha256=digest(bad)), '/source')

    def test_actual_wrapper_real_and_snapshot_routes_must_be_qualified_D2(self):
        source = '/source'; host = 'aarch64-apple-darwin'; d = source + '/build/' + host + '/stage0'
        shim = source + '/build/bootstrap/debug/rustc'
        env = dict(RUSTC=shim, RUSTC_WRAPPER=shim, RUSTC_REAL=d + '/bin/rustc', RUSTC_SNAPSHOT=d + '/bin/rustc',
            RUSTC_LIBDIR=d + '/lib', RUSTC_SNAPSHOT_LIBDIR=d + '/lib', RUSTC_STAGE='0',
            RUSTC_SYSROOT=source + '/build/' + host + '/stage0-sysroot',
            CARGO_TARGET_DIR=source + '/build/' + host + '/stage1-rustc',
            CARGO_BUILD_BUILD_DIR=source + '/build/' + host + '/stage1-rustc')
        env['DYLD_LIBRARY_PATH'] = ':'.join(producer.test_loader_paths(source))
        cargo = dict(argv=[d + '/bin/cargo', 'test'], environment=env, removed=[])
        row = dict(argv=[shim, shim, '--crate-name', 'test', '--target', host], environment={})
        self.assertEqual(producer.mechanism(row, cargo, {}, source), env)
        for name in ['RUSTC_REAL', 'RUSTC_SNAPSHOT', 'RUSTC_WRAPPER', 'RUSTC_SYSROOT', 'RUSTC_LIBDIR']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                producer.mechanism(row, cargo | {'environment': env | {name: '/foreign'}}, {}, source)
        with self.assertRaises(ValueError):
            producer.mechanism(row | {'argv': ['/foreign', *row['argv'][1:]]}, cargo, {}, source)
        with self.assertRaises(ValueError):
            producer.mechanism(row | {'environment': {'RUSTC_WRAPPER_REAL': '/foreign'}}, cargo, {}, source)


if __name__ == '__main__':
    unittest.main()
