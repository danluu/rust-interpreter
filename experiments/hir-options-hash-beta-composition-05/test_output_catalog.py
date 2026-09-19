"""Unrun adversarial pure controls for competing compiler-output history."""
import copy
import shlex
import unittest

import producer
import test_producer
from compose_sysroot import digest


class CompleteOutputControls(unittest.TestCase):
    def fixture(self, extra=()):
        _, cargo, streams, source = test_producer.ProducerControls().contexts()
        shim = source+'/build/bootstrap/debug/rustc'
        out = source+'/build/aarch64-apple-darwin/stage1-rustc/aarch64-apple-darwin/release/deps'
        pair = [out+'/librustc_driver-abc.dylib', out+'/librustc_driver-abc.rmeta']
        driver = [shim, shim, '--crate-name', 'rustc_driver', 'compiler/rustc_driver/src/lib.rs',
                  '--crate-type', 'dylib', '--emit=dep-info,metadata,link', '-Cextra-filename=-abc', '--out-dir', out]
        consumer = [shim, shim, '--crate-name', 'rustc_main', 'compiler/rustc/src/main.rs',
                    '--crate-type', 'bin', '--emit=dep-info,link', '-Cextra-filename=-def', '--out-dir', out,
                    '--extern', 'rustc_driver='+pair[0], '--extern', 'rustc_driver='+pair[1]]
        rows = [driver, *extra, consumer]
        raw = b''.join(('  Running `'+shlex.join(argv)+'`\n').encode() for argv in rows)
        streams['rustc'].update(raw=raw, stream_kind='stderr', history_index=15, stage_index=1)
        for name in ['cargo0', 'cargo1']:
            streams[name].update(stream_kind='stdout', history_index=15, stage_index=1)
        composition = dict(source=source, private=[dict(source=name) for name in pair])
        return composition, streams, cargo, rows, pair

    def test_complete_inventory_retains_nonnative_commands_and_ordered_pair(self):
        composition, streams, cargo, rows, pair = self.fixture([['/source/build-script', 'argument']])
        catalog = producer.output_catalog(composition, streams, cargo)
        self.assertEqual([row['kind'] for row in catalog], ['rustc-running', 'non-rustc-running', 'rustc-running'])
        private, consumer = producer.last_producers(composition, catalog)
        self.assertEqual(set(private), set(pair))
        self.assertEqual(consumer['ordered_driver_pair'], pair)
        self.assertEqual(consumer['command']['line'], 3)

    def test_later_metadata_only_overwrite_is_selected_then_refused_as_native(self):
        composition, streams, cargo, rows, pair = self.fixture()
        check = [word.replace('--emit=dep-info,metadata,link', '--emit=dep-info,metadata') for word in rows[0]]
        composition, streams, cargo, rows, pair = self.fixture([check])
        catalog = producer.output_catalog(composition, streams, cargo)
        private, _ = producer.last_producers(composition, catalog)
        self.assertEqual(private[pair[0]]['command']['line'], 1)
        self.assertEqual(private[pair[1]]['command']['line'], 2)
        with self.assertRaises(ValueError):
            producer.rust_outputs(private[pair[1]]['parsed']['argv'])

    def test_duplicate_real_producer_cannot_select_convenient_earlier_line(self):
        composition, streams, cargo, rows, pair = self.fixture()
        composition, streams, cargo, rows, pair = self.fixture([rows[0]])
        catalog = producer.output_catalog(composition, streams, cargo)
        private, _ = producer.last_producers(composition, catalog)
        self.assertEqual(len(catalog), 3)
        self.assertTrue(all(binding['command']['line'] == 2 for binding in private.values()))

    def test_other_compiler_cannot_overwrite_one_qualified_output(self):
        composition, streams, cargo, rows, pair = self.fixture()
        bad = ['/foreign/rustc', *rows[0][1:]]
        composition, streams, cargo, rows, pair = self.fixture([bad])
        with self.assertRaises(ValueError):
            producer.output_catalog(composition, streams, cargo)

    def test_ambiguous_real_context_still_rejects_full_environment_difference(self):
        composition, streams, cargo, _, _ = self.fixture()
        selected = cargo[1]
        parsed = selected['parsed']; parsed['environment']['ARBITRARY_ENV_INPUT'] = 'different'
        words = ['cd', '/source', '&&', 'env', *[key+'='+value for key, value in parsed['environment'].items()],
                 *parsed['argv'], '(failure_mode=Exit)']
        raw = ('running: '+shlex.join(words)+'\n').encode()
        streams['cargo1']['raw'] = raw
        selected['command']['line_sha256'] = digest(raw)
        with self.assertRaises(ValueError):
            producer.output_catalog(composition, streams, cargo)

    def test_catalog_order_and_complete_private_membership_are_required(self):
        composition, streams, cargo, _, _ = self.fixture()
        catalog = producer.output_catalog(composition, streams, cargo)
        with self.assertRaises(ValueError):
            producer.last_producers(composition, list(reversed(catalog)))
        with self.assertRaises(ValueError):
            producer.last_producers(composition, catalog[1:])

    def test_explicit_output_redirection_is_not_silently_ignored(self):
        composition, streams, cargo, rows, _ = self.fixture()
        bad = [word.replace('--emit=dep-info,metadata,link', '--emit=metadata=/source/elsewhere') for word in rows[0]]
        composition, streams, cargo, _, _ = self.fixture([bad])
        with self.assertRaises(ValueError):
            producer.output_catalog(composition, streams, cargo)

    def test_later_child_order_wins_without_cross_stream_timestamp_guess(self):
        composition, streams, cargo, _, pair = self.fixture()
        first = producer.output_catalog(composition, streams, cargo)
        later = copy.deepcopy(first)
        for row in later:
            row['history_index'] = 16
            row['command']['stream'] = 'later'
            if 'binding' in row:
                row['binding']['command']['stream'] = 'later'
        selected, _ = producer.last_producers(composition, [*first, *later])
        self.assertTrue(all(row['command']['stream'] == 'later' for row in selected.values()))


if __name__ == '__main__':
    unittest.main()
