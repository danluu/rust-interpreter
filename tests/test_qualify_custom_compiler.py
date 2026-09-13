"""Small fault checks for the real harness; no compiler/Cargo/VM is executed."""
import json
import copy
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import qualify_custom_compiler as qualification
from std_mir import source_digest
from verified_std_diagnostics import SOURCE_PREFIX, VerifiedStandardSources, source_span_text


class QualificationTests(unittest.TestCase):
    def standard_sources(self, root):
        payload = '// é\npub macro panic {}\n'.encode()
        relative = 'core/src/panic.rs'
        compiler = SimpleNamespace(key='compiler-key', sysroot=root / 'sysroot',
            identity={'files': {SOURCE_PREFIX + relative: qualification.hashlib.sha256(payload).hexdigest()},
                      'source_sha256': 'inventoried-library-identity'})
        public = root / 'public/library'
        prepared = {mode: root / mode / 'ready.json' for mode in ['off', 'on']}
        for directory in [compiler.sysroot / SOURCE_PREFIX, public,
                          *(path.parent / 'library' for path in prepared.values())]:
            path = directory / relative
            path.parent.mkdir(parents=True)
            path.write_bytes(payload)
        for mode, path in prepared.items():
            sha = source_digest(path.parent / 'library')
            path.write_text(json.dumps(dict(source_sha256=sha, identity=dict(compiler_key=compiler.key,
                source_sha256=compiler.identity['source_sha256'], namespace='stable-cgu:' + mode))))
            (path.parent / 'source.json').write_text(json.dumps(dict(sha256=sha)))
        verified = VerifiedStandardSources(compiler, public, prepared)
        span = dict(file_name=str(public / relative), byte_start=6, byte_end=9,
            line_start=2, line_end=2, column_start=1, column_end=4,
            text=[dict(text='pub macro panic {}', highlight_start=1, highlight_end=4)],
            is_primary=False, label='definition', suggested_replacement=None, suggestion_applicability=None)
        return verified, span, payload

    def test_preliminary_comparison_requires_explicit_option_and_never_qualifies_adoption(self):
        parser = qualification.argument_parser()
        args = parser.parse_args(['--compiler-key', 'key', '--tool-key', 'key', '--run-id', 'run'])
        self.assertEqual(args.diagnostic_comparison, 'strict')
        for gaps in [[], [{'kind': 'missing-standard-source-snippet'}]]:
            scope = qualification.qualification_scope('verified-std-source', gaps)
            self.assertEqual(scope['qualification_scope'], 'preliminary-mechanism-only')
            self.assertFalse(scope['full_presentation_qualified'])
            self.assertFalse(scope['adoption_eligible'])
            self.assertFalse(scope['final_target_eligible'])
            self.assertEqual(scope['presentation_gap_count'], len(gaps))

    def test_verified_source_view_retains_raw_gaps_duplicates_and_owned_spans(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            verified, span, _ = self.standard_sources(root)
            original = dict(level='error', code={'code': 'E0080'}, message='evaluation panicked',
                spans=[dict(file_name='shared/src/lib.rs', byte_start=55, line_start=3,
                            expansion=dict(span=span))], children=[])
            public = [original, copy.deepcopy(original)]
            custom = copy.deepcopy(public)
            for record, alias in zip(custom, ['library/core/src/panic.rs', 'core/src/panic.rs']):
                record['spans'][0]['expansion']['span'].update(file_name=alias, text=[])
            preserved = copy.deepcopy(custom)
            public_view = verified.comparison(public, 'public', [])
            self.assertEqual(public_view, verified.comparison(custom, 'off', []))
            self.assertEqual(custom, preserved)
            self.assertEqual(len(public_view), 2)
            self.assertEqual(len(verified.gaps), 2)
            self.assertTrue(all(gap['raw_text'] == [] and gap['source_derived_text'] == span['text']
                                for gap in verified.gaps))
            proof = verified.evidence()
            self.assertFalse(proof['source_derived_text_is_compiler_output'])
            self.assertEqual(proof['files']['core/src/panic.rs']['source_text'], '// é\npub macro panic {}\n')
            for change in ['code', 'owned_span', 'message', 'duplicate']:
                bad = copy.deepcopy(custom)
                if change == 'code': bad[0]['code']['code'] = 'E0308'
                if change == 'owned_span': bad[0]['spans'][0]['byte_start'] += 1
                if change == 'message': bad[0]['message'] = 'other error'
                if change == 'duplicate': bad.pop()
                self.assertNotEqual(public_view, verified.comparison(bad, 'changed', []))

    def test_standard_source_alias_rejects_application_ambiguity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            verified, span, _ = self.standard_sources(root)
            application = root / 'fixture'
            collision = application / 'package/core/src/panic.rs'
            collision.parent.mkdir(parents=True)
            collision.write_text('application code')
            span.update(file_name='core/src/panic.rs', text=[])
            with self.assertRaisesRegex(RuntimeError, 'ambiguous'):
                verified.comparison([span], 'off', [application])

    def test_standard_source_names_are_exact_and_unknown_std_paths_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            verified, span, _ = self.standard_sources(root)
            self.assertIsNone(verified.resolve('panic.rs', []))
            self.assertIsNone(verified.resolve('/application/core/src/panic.rs', []))
            for name in ['library/core/src/missing.rs', 'core/src/../src/panic.rs',
                         str(verified.roots['public'] / 'core/src/missing.rs')]:
                with self.assertRaisesRegex(RuntimeError, 'unrecognized'):
                    verified.resolve(name, [])

    def test_standard_source_requires_identical_bytes_at_every_provenance_location(self):
        for location in ['installed', 'public', 'prepared-off', 'prepared-on']:
            with self.subTest(location=location), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                verified, span, _ = self.standard_sources(root)
                (verified.roots[location] / 'core/src/panic.rs').write_text('wrong source')
                with self.assertRaisesRegex(RuntimeError, 'source bytes differ'):
                    verified.comparison([span], 'off', [])

    def test_prepared_source_and_manifest_replacements_fail_recheck(self):
        for changed in ['source', 'ready', 'source-manifest']:
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                verified, _, _ = self.standard_sources(root)
                path = {'source': root / 'on/library/unrelated.rs', 'ready': root / 'on/ready.json',
                        'source-manifest': root / 'on/source.json'}[changed]
                path.write_text('changed')
                with self.assertRaisesRegex(RuntimeError, 'snapshot changed'):
                    verified.recheck()

    def test_prepared_source_compiler_mode_and_digest_must_match(self):
        for change in ['compiler_key', 'namespace', 'source_sha256', 'snapshot_sha256']:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                verified, _, _ = self.standard_sources(root)
                path = root / 'on/ready.json'
                ready = json.loads(path.read_text())
                if change == 'snapshot_sha256': ready['source_sha256'] = 'different'
                else: ready['identity'][change] = 'different'
                path.write_text(json.dumps(ready))
                with self.assertRaises(RuntimeError):
                    VerifiedStandardSources(verified.compiler, verified.roots['public'],
                        {mode: root / mode / 'ready.json' for mode in ['off', 'on']})

    def test_standard_spans_validate_byte_character_coordinates_and_snippets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            verified, span, _ = self.standard_sources(root)
            for change in [dict(byte_start=5), dict(byte_end=8), dict(line_start=0),
                           dict(line_end=9), dict(column_end=99), dict(column_start=True),
                           dict(column_start=5, byte_start=10), dict(text=[dict(
                               text='wrong source', highlight_start=1, highlight_end=4)]),
                           dict(text=[dict(text='pub macro panic {}', highlight_start=2, highlight_end=4)])]:
                with self.subTest(change=change), self.assertRaises(RuntimeError):
                    verified.comparison([span | change], 'off', [])

    def test_source_coordinate_model_supports_utf8_and_multiline_but_rejects_normalization(self):
        payload = 'é\nab\n'.encode()
        span = dict(byte_start=0, byte_end=4, line_start=1, line_end=2, column_start=1, column_end=2)
        self.assertEqual(source_span_text(span, payload), [
            dict(text='é', highlight_start=1, highlight_end=2),
            dict(text='ab', highlight_start=1, highlight_end=2)])
        for changed in [b'\xef\xbb\xbf' + payload, payload.replace(b'\n', b'\r\n')]:
            with self.assertRaisesRegex(RuntimeError, 'normalization'):
                source_span_text(span, changed)

    def test_public_command_keeps_structured_compiler_messages_and_duplicate_units(self):
        command = qualification.public_command(Path('/owned/source'), 'host', Path('/owned/target'))
        formats = [arg for arg in command if isinstance(arg, str) and arg.startswith('--message-format=')]
        self.assertEqual(formats, ['--message-format=json'])
        message = dict(level='error', code={'code': 'E0308'}, message='mismatched types',
                       spans=[], children=[], rendered='error[E0308]: mismatched types')
        diagnostic = json.dumps(dict(reason='compiler-message', message=message))
        cargo_json = diagnostic + '\n' + diagnostic + '\n' + json.dumps(dict(reason='build-finished', success=False))
        core = qualification.core_diagnostics(qualification.diagnostic_records(cargo_json), Path('/owned'))
        self.assertEqual(len(core), 2)
        self.assertTrue(all(item['code'] == 'E0308' for item in core))
        rendered_only = json.dumps(dict(reason='build-finished', success=False))
        self.assertEqual(qualification.diagnostic_records(rendered_only), [])

    def test_real_cargo_route_parser_requires_both_target_roles_and_host_tools(self):
        wrapper, rustc = Path('/owned tools/wrapper'), Path('/owned compiler/rustc')
        lines = []
        for name, kind, target in [('custom_shared', 'rlib', ''),
                ('custom_shared', 'rlib', '--target=host'), ('custom_macros', 'proc-macro', ''),
                ('build_script_build', 'bin', ''), ('custom_compiler_fixture', 'lib', '--target host')]:
            lines.append(f"     Running `CARGO_PKG_NAME=fixture '{wrapper}' '{rustc}' --crate-name {name} "
                         f'--crate-type {kind} {target}`')
        routes = qualification.compiler_routes('\n'.join(lines), wrapper, rustc)
        qualification.validate_routes(routes, 'host')
        with self.assertRaisesRegex(RuntimeError, 'guest shared'):
            qualification.validate_routes([r for r in routes if not
                (r['crate'] == 'custom_shared' and r['target'])], 'host')
        with self.assertRaisesRegex(RuntimeError, 'different rustc'):
            qualification.compiler_routes('\n'.join(lines).replace(str(rustc), '/stock/rustc'), wrapper, rustc)

    def test_expected_compile_error_cannot_hide_execution_or_success(self):
        bad = dict(returncode=1, stderr='error[E0515]: cannot return reference', stdout='')
        qualification.validate_failure(bad, 'E0515')
        for change in [dict(returncode=0), dict(stdout='0\n'),
                       dict(stderr=bad['stderr'] + '\nrust-interp-launch: {}'),
                       dict(stderr='error[E0308]: mismatch')]:
            with self.assertRaises(RuntimeError):
                qualification.validate_failure(bad | change, 'E0515')

    def test_receipt_rejects_wrong_std_mode_and_replaced_bytecode(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            target = root / 'caches/off/target'; target.mkdir(parents=True)
            artifact = target / 'fixture.rbc'; artifact.write_bytes(b'checked bytecode')
            compiler = SimpleNamespace(key='compiler-key', rustc=root / 'rustc',
                identity={'files': {'bin/rustc': 'compiler-hash'}, 'compiler': 'rustc -vV'})
            std = dict(key='std-off', sysroot='/std/off', target='host')
            report = dict(tool_key='tools', custom_compiler=dict(key=compiler.key,
                rustc=str(compiler.rustc), rustc_sha256='compiler-hash', compiler='rustc -vV',
                stable_cgu_partitioning='off'), std_mir=std,
                toolchain_lookup=dict(mode='cached', outcome='owned-manifest'),
                workspace_path=str(target.parent), artifact_path=str(artifact),
                artifact_sha256=qualification.file_digest(artifact))
            row = dict(returncode=0, stderr='rust-interp-launch: ' + json.dumps(report))
            qualification.validate_launch(row, compiler, 'off', 'tools', std, root / 'caches')
            with self.assertRaisesRegex(RuntimeError, 'std namespace'):
                qualification.validate_launch(row, compiler, 'off', 'tools', std | {'key': 'std-on'}, root / 'caches')
            artifact.write_bytes(b'replaced')
            with self.assertRaisesRegex(RuntimeError, 'bytecode'):
                qualification.validate_launch(row, compiler, 'off', 'tools', std, root / 'caches')

    def test_fixture_is_local_and_has_distinct_actual_body_edits(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'fixture'
            qualification.fixture(source)
            self.assertEqual((source / 'shared/src/lib.rs').read_bytes(), qualification.shared_source(3))
            self.assertNotEqual(qualification.shared_source(3), qualification.shared_source(7))
            self.assertIn('codegen-units=2', (source / 'Cargo.toml').read_text())
            self.assertIn('[build-dependencies]', (source / 'Cargo.toml').read_text())
            self.assertIn('proc-macro=true', (source / 'macros/Cargo.toml').read_text())

    def test_structured_diagnostics_preserve_semantics_and_reject_stale_cache_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            message = dict(level='error', code={'code': 'E0308'}, message='mismatched types',
                spans=[dict(file_name=str(root / 'fixture.rs'), line_start=3, is_primary=True)],
                children=[dict(level='note', message='expected u32', spans=[])], rendered='colored output')
            cargo = json.dumps(dict(reason='compiler-message', message=message))
            cache = json.dumps(message | {'$message_type': 'diagnostic'})
            self.assertEqual(qualification.core_diagnostics(qualification.diagnostic_records(cargo), root),
                             qualification.core_diagnostics(qualification.diagnostic_records(cache), root))
            changed = message | {'message': 'different semantics'}
            self.assertNotEqual(qualification.core_diagnostics([message], root),
                                qualification.core_diagnostics([changed], root))
            target = root / 'target'; target.mkdir()
            output = target / 'output-lib-fixture'; output.write_text(cache)
            records, files = qualification.changed_diagnostics(target, {})
            self.assertEqual(records, qualification.diagnostic_records(cache))
            self.assertEqual(files, {str(output): cache})
            with self.assertRaisesRegex(RuntimeError, 'did not retain'):
                qualification.changed_diagnostics(target, qualification.diagnostic_files(target))

    def test_raw_diagnostic_comparison_retains_summaries_and_both_host_target_units(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            error = dict(level='error', code={'code': 'E0308'}, message='mismatched types', spans=[], children=[])
            abort = dict(level='error', code=None, message='aborting due to 1 previous error', spans=[], children=[])
            note = dict(level='failure-note', code=None, message='For more information, use rustc --explain E0308.', spans=[], children=[])
            payload = '\n'.join(json.dumps(m | {'$message_type': 'diagnostic'}) for m in [error, abort, note])
            for unit in ['host', 'target']:
                directory = root / unit; directory.mkdir()
                (directory / 'output-lib-shared').write_text(payload)
            records, files = qualification.changed_diagnostics(root, {})
            core = qualification.core_diagnostics(records, root)
            self.assertEqual(len(files), 2)
            self.assertEqual(len(core), 6)
            self.assertEqual(sum(item['message'] == abort['message'] for item in core), 2)
            self.assertEqual(sum(item['code'] == 'E0308' for item in core), 2)
            self.assertEqual(sum(item['level'] == 'failure-note' for item in core), 2)


if __name__ == '__main__':
    unittest.main()
