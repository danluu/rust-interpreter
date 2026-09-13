"""Prepared source-observable contracts; no compiler/Cargo/VM workloads."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import qualify_std_source_observables as qualify
from std_source_observables import validate_source_observables


class SourceObservableContracts(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        qualify.fixture(self.root / 'app')
        self.app = self.root / 'app'

    def output(self):
        rows = []
        for label, relative in [('main', 'src/main.rs'), ('std-looking', 'src/core/src/panic.rs')]:
            lines = (self.app / relative).read_text().splitlines()
            index = next(i for i, line in enumerate(lines) if 'observe!(marker)' in line)
            rows.append('|'.join([label, relative, relative, str(self.app / relative),
                                   str(index+1), str(lines[index].index('marker')+1)]))
        return '\n'.join(rows) + '\n'

    def values(self):
        return qualify.observable_values(self.output(), self.app, self.app)

    def test_actual_owned_std_looking_filenames_and_coordinates_are_checked(self):
        manifest = tomllib.loads((self.app / 'Cargo.toml').read_text())
        self.assertEqual(manifest['lib']['path'], 'src/main.rs')
        self.assertFalse(manifest['package']['autobins'])
        values = self.values()
        self.assertEqual(values['std-looking']['relative'], 'src/core/src/panic.rs')
        for output in [self.output().replace('src/main.rs', 'elsewhere.rs'),
                       self.output().replace('|src/main.rs|', '|/unknown/source.rs|', 1),
                       self.output().splitlines()[0] + '\n']:
            with self.subTest(output=output), self.assertRaises(RuntimeError):
                qualify.observable_values(output, self.app, self.app)
        with self.assertRaises(RuntimeError):
            qualify.observable_values(self.output(), self.root / 'artifact-cache', self.app)

    def test_application_scope_sensitivity_allows_only_span_display_path(self):
        original = self.values()
        values = {phase: copy.deepcopy(original) for phase in qualify.PHASES}
        for value in values['application-map'].values():
            value['span_file'] = qualify.APP_PREFIX + '/' + value['relative'].removeprefix('src/')
        before = copy.deepcopy(values)
        qualify.compare_observables(values)
        self.assertEqual(values, before)
        for field, replacement in [('file', 'changed'), ('local_file', 'changed'), ('line', 99), ('column', 99)]:
            broken = copy.deepcopy(values); broken['application-map']['main'][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                qualify.compare_observables(broken)
        broken = copy.deepcopy(values); broken['std-only']['main']['span_file'] = 'changed'
        with self.assertRaises(RuntimeError):
            qualify.compare_observables(broken)

    def test_same_width_phase_edits_preserve_macro_source_coordinates(self):
        path = self.app / 'src/main.rs'; original = path.read_bytes()
        outputs = []
        for index in range(4):
            path.write_bytes(original.replace(b'000000000000000', (str(index)*15).encode()))
            outputs.append(self.output())
        self.assertEqual(len(set(outputs)), 1)
        path.write_bytes(original)

    def test_unicode_position_edit_requires_exact_actual_byte_and_line_motion(self):
        source = self.app / 'source.rs'
        span = dict(file_name=str(source), byte_start=1, byte_end=2, line_start=1, line_end=1,
                    column_start=2, column_end=3)
        original = [dict(spans=[span])]
        prefix = '// café\n\n'.encode()
        moved = copy.deepcopy(original)
        for name in ['byte_start', 'byte_end']: moved[0]['spans'][0][name] += len(prefix)
        for name in ['line_start', 'line_end']: moved[0]['spans'][0][name] += 2
        qualify.position_control(original, moved, source, prefix)
        moved[0]['spans'][0]['byte_start'] -= 1
        with self.assertRaises(RuntimeError):
            qualify.position_control(original, moved, source, prefix)

    def test_cargo_mapping_keeps_identical_explicit_host_and_target_flags(self):
        flags = ['--remap-path-scope=diagnostics', '--remap-path-prefix=src=' + qualify.APP_PREFIX]
        parsed = tomllib.loads(qualify.cargo_configuration(flags, 'aarch64-apple-darwin').decode())
        self.assertFalse(parsed['target-applies-to-host'])
        self.assertEqual(parsed['host']['rustflags'], flags)
        self.assertEqual(parsed['host']['aarch64-apple-darwin']['rustflags'], flags)
        self.assertEqual(parsed['target']['aarch64-apple-darwin']['rustflags'], flags)

    def test_missing_or_old_qualification_cannot_satisfy_archived_prerequisite(self):
        owner = Path('/owned/project'); path = owner / '.work/source-controls/result.json'
        stds = {m: dict(key=m, sysroot='/std/' + m, target='host') for m in ['off', 'on']}
        for result in [{}, {'status': 'passed', 'policy': 'stable-mono-cgu-integration-v1', 'commands': 36},
                       {'status': 'passed', 'policy': qualify.POLICY, 'diagnostics_rewritten': True}]:
            reads = []
            def read(selected):
                reads.append(selected)
                return json.dumps(result).encode()
            with self.subTest(result=result), self.assertRaises(RuntimeError):
                validate_source_observables(path, owner, 'compiler', 'tools', stds,
                    compiler_sysroot='/compiler', read_bytes=read)
            self.assertEqual(reads, [path])


if __name__ == '__main__':
    unittest.main()
