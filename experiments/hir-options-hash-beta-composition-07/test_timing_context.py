"""Prepared source/trace controls only; no compiler or subprocess invocation."""
import json
from pathlib import Path
import shlex
import unittest

import producer
import timing_context as timing
from compose_sysroot import digest


class TimingControls(unittest.TestCase):
    SOURCE = '/source'
    HOST = 'aarch64-apple-darwin'

    def step(self, mode='build'):
        compiler = 'Compiler { stage: 0, host: ' + self.HOST + ', forced_compiler: false }'
        return {
            'build': 'compile::Rustc { target: ' + self.HOST + ', build_compiler: ' + compiler + ', crates: [] }',
            'test': 'test::Crate { build_compiler: ' + compiler + ', target: ' + self.HOST + ', mode: Rustc, crates: ["rustc_ast_lowering"] }',
            'check': 'check::Rustc { check_kind: Check, build_compiler: CompilerForCheck { build_compiler: ' + compiler
                     + ', rustc_rmeta_sysroot: None, std_rmeta_sysroot: None }, target: ' + self.HOST + ', crates: ["rustc_ast_lowering"] }',
        }[mode]

    def cargo(self, mode='build', extra=None):
        tree = self.SOURCE + '/build/' + self.HOST + '/stage1-rustc'
        env = dict(CARGO_TARGET_DIR=tree, CARGO_BUILD_BUILD_DIR=tree) | (extra or {})
        argv = [self.SOURCE + '/build/' + self.HOST + '/stage0/bin/cargo', mode, '--target', self.HOST,
                '--manifest-path', self.SOURCE + '/compiler/rustc/Cargo.toml']
        if mode == 'test': argv += ['-p', 'rustc_ast_lowering', '--', '-Z', 'unstable-options', '--format', 'json']
        else:
            if mode == 'check': argv += ['-p', 'rustc_ast_lowering']
            argv += ['--message-format', 'json-render-diagnostics']
        return dict(argv=argv, environment=env, removed=[])

    def printed(self, cargo):
        words = ['cd', self.SOURCE, '&&', 'env', *[key + '=' + value for key, value in cargo['environment'].items()],
                 *cargo['argv'], '(failure_mode=Exit)']
        return 'running: ' + shlex.join(words) + '\n'

    def entries(self, raw):
        result = []
        for number, line in enumerate(raw.splitlines(keepends=True), 1):
            if line.startswith(b'running: '):
                coord = dict(stream='stdout', line=number, line_sha256=digest(line))
                result.append(dict(command=coord, parsed=producer.bootstrap_line(raw, coord, self.SOURCE)))
        return result

    def classify(self, raw):
        return timing.classify(raw, self.entries(raw), lambda cargo, step: producer.native_emitter(cargo, step, self.SOURCE))

    def complete(self, cargo=None):
        cargo = cargo or self.cargo(); step = self.step(cargo['argv'][1])
        return ('[TIMING:start] outer::Setup { name: "before" }\n[TIMING:end] outer::Setup { name: "before" } -- 0.001\n'
                + self.printed(cargo) + '[TIMING:start] compile::Assemble { value: 1 }\n'
                + '[TIMING:start] ' + step + '\n' + self.printed(cargo)
                + '[TIMING:end] ' + step + ' -- 0.001\n[TIMING:end] compile::Assemble { value: 1 } -- 0.002\n').encode()

    def test_setup_timing_does_not_relabel_later_selfcheck_and_nested_real(self):
        result = self.classify(self.complete())
        self.assertEqual([r['execution'] for r in result['commands']], ['self-check-print', 'real'])
        self.assertEqual([len(r['timing_stack']) for r in result['commands']], [0, 2])
        self.assertEqual(len(result['events']), 6)
        self.assertEqual(result['commands'][0]['parsed'], result['commands'][1]['parsed'])
        self.assertNotEqual(result['commands'][0]['command'], result['commands'][1]['command'])

    def test_complete_actual_historical_native_context_catalog(self):
        refs = json.loads(Path(__file__).with_name('source-bindings.json').read_bytes())['references']
        row = refs['historical_native_stdout']; raw = Path(row['path']).read_bytes()
        self.assertEqual(len(raw), row['size']); self.assertEqual(digest(raw), row['sha256'])
        source = '/Users/danluu/dev/rustc-hir-capture-check-20260913'
        entries = []
        for number, line in enumerate(raw.splitlines(keepends=True), 1):
            if line.startswith(b'running: ') and b'CARGO_TARGET_DIR=' in line and (source + '/build/' + self.HOST + '/stage1-rustc').encode() in line:
                coord = dict(stream='stdout', line=number, line_sha256=digest(line))
                parsed = producer.bootstrap_line(raw, coord, source)
                if parsed['environment']['CARGO_TARGET_DIR'].endswith('/stage1-rustc'):
                    entries.append(dict(command=coord, parsed=parsed))
        result = timing.classify(raw, entries, lambda cargo, step: producer.native_emitter(cargo, step, source))
        self.assertEqual(len(result['events']), 30)
        self.assertEqual([r['command']['line'] for r in result['commands']], [32, 57])
        self.assertEqual([r['execution'] for r in result['commands']], ['self-check-print', 'real'])
        self.assertNotEqual(entries[0]['parsed']['environment'], entries[1]['parsed']['environment'])

    def test_saved_successful_lowering_child_keeps_exact_test_loader_paths(self):
        refs = json.loads(Path(__file__).with_name('source-bindings.json').read_bytes())['references']
        row = refs['candidate_lowering_test_stdout']; raw = Path(row['path']).read_bytes()
        self.assertEqual(len(raw), row['size']); self.assertEqual(digest(raw), row['sha256'])
        source = str(Path(row['source_root']))
        entries = []
        for number, line in enumerate(raw.splitlines(keepends=True), 1):
            if line.startswith(b'running: ') and b'CARGO_TARGET_DIR=' in line and (source + '/build/' + self.HOST + '/stage1-rustc').encode() in line:
                coord = dict(stream='stdout', line=number, line_sha256=digest(line))
                parsed = producer.bootstrap_line(raw, coord, source)
                if parsed['environment']['CARGO_TARGET_DIR'].endswith('/stage1-rustc'):
                    entries.append(dict(command=coord, parsed=parsed))
        result = timing.classify(raw, entries, lambda cargo, step: producer.native_emitter(cargo, step, source))
        self.assertEqual(len(result['events']), 26)
        self.assertEqual([r['command']['line'] for r in result['commands']], [31, 58])
        self.assertEqual([r['execution'] for r in result['commands']], ['self-check-print', 'real'])
        receipt_row = refs['candidate_lowering_test_receipt']; receipt_raw = Path(receipt_row['path']).read_bytes()
        self.assertEqual(digest(receipt_raw), receipt_row['sha256'])
        receipt = json.loads(receipt_raw)
        self.assertEqual(receipt['status'], 'finished'); self.assertEqual(receipt['returncode'], 0)
        self.assertEqual(receipt['stdout_sha256'], digest(raw))
        self.assertEqual(receipt['command'], producer.allowed_bootstrap_commands()[1])
        for entry in result['commands']:
            self.assertEqual(producer.loader_policy({'environment': {}}, entry['parsed'], receipt['environment'], source),
                             ':'.join(producer.test_loader_paths(source)))

    def test_check_and_rendered_test_steps_use_specific_source_routes(self):
        for mode, expected in [('check', 'check::Rustc/run_cargo/stream_cargo'),
                               ('test', 'test::Crate/run_cargo_test/render_tests::run_tests')]:
            with self.subTest(mode=mode):
                result = self.classify(self.complete(self.cargo(mode)))
                self.assertEqual({row['source_route'] for row in result['commands']}, {expected})

    def test_unknown_real_emitter_or_compiler_role_is_rejected(self):
        for old, new in [(b'compile::Rustc {', b'unknown::Rustc {'),
                         (b'stage: 0', b'stage: 1'), (b'forced_compiler: false', b'forced_compiler: true')]:
            with self.subTest(new=new), self.assertRaises(ValueError):
                self.classify(self.complete().replace(old, new))

    def test_unknown_cargo_route_is_rejected_even_without_open_step(self):
        for key, value in [('CARGO_TARGET_DIR', '/foreign'), ('CARGO_BUILD_BUILD_DIR', '/foreign')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.classify(self.complete(self.cargo(extra={key: value})))
        cargo = self.cargo(); cargo['argv'][0] = '/foreign/cargo'
        with self.assertRaises(ValueError): self.classify(self.complete(cargo))

    def test_unclosed_mismatched_or_extra_timing_events_are_rejected(self):
        original = self.complete()
        bad = [original.rsplit(b'[TIMING:end]', 1)[0],
               original + b'[TIMING:end] no::Step -- 0.000\n',
               original.replace(b'[TIMING:end] compile::Assemble', b'[TIMING:end] wrong::Assemble'),
               original + b'[TIMING:unknown] no::Step\n',
               original + b' [TIMING:start] no::Step\n',
               original + b'[TIMING start] no::Step\n',
               original + b'[TIMING:start] no::Step\n']
        for raw in bad:
            with self.subTest(raw=raw[-80:]), self.assertRaises(ValueError): self.classify(raw)

    def test_events_after_last_relevant_command_are_not_ignored(self):
        raw = self.complete() + b'[TIMING:start] after::Step { value: 1 }\n'
        with self.assertRaises(ValueError): self.classify(raw)

    def test_timing_representation_requires_complete_bounded_debug_shape(self):
        for step in ['Step', 'x::Step { x: [ }', 'x::Step { x: "unterminated }', 'x::Step\t', 'x::Step ' + 'a' * 17000]:
            with self.subTest(step=step[:50]), self.assertRaises(ValueError): timing.step_name(step)
        self.assertEqual(timing.step_name('x::Step { x: "[quoted]", y: Some([1, 2]) }'), 'x::Step')

    def test_raw_coordinates_missing_duplicate_or_changed_are_rejected(self):
        raw = self.complete(); entries = self.entries(raw)
        for bad in [[entries[0], entries[0]], [dict(entries[0], command=entries[0]['command'] | {'line_sha256': '0' * 64})],
                    [dict(entries[0], command=entries[0]['command'] | {'line': 999})]]:
            with self.assertRaises(ValueError):
                timing.classify(raw, bad, lambda cargo, step: producer.native_emitter(cargo, step, self.SOURCE))

    def test_step_and_cargo_package_selection_must_match(self):
        for mode in ['build', 'check', 'test']:
            cargo = self.cargo(mode)
            cargo['argv'][2:2] = ['-p', 'other']
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.classify(self.complete(cargo))
        for flags in [['--package=other'], ['--workspace'], ['-prustc_ast_lowering']]:
            cargo = self.cargo(); cargo['argv'][2:2] = flags
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                self.classify(self.complete(cargo))

    def test_configuration_and_outer_cli_must_be_exactly_admitted(self):
        allowed = producer.allowed_bootstrap_commands(); config = dict(build={'print-step-timings': True})
        timing.configured(config, allowed[0], allowed)
        for cfg, command in [(dict(build={'print-step-timings': False}), allowed[0]), ({}, allowed[0]),
                             (config, allowed[0] + ['--dry-run']), (config, ['./x', 'build'])]:
            with self.subTest(command=command), self.assertRaises(ValueError): timing.configured(cfg, command, allowed)


if __name__ == '__main__': unittest.main()
