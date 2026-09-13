"""Prepared synthetic controls only; no real compiler inputs or subprocesses."""
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import compose_sysroot as compose


class ComposeTests(unittest.TestCase):
    def test_stamp_routes_all_three_tags_without_renaming(self):
        host = compose.TREE / 'release/build/macro/key/out/libmacro-key.dylib'
        target = compose.TREE / compose.HOST / 'release/build/compiler/key/out/librustc_a-key.rmeta'
        native = compose.TREE / compose.HOST / 'release/build/native/key/out/libnative.a'
        rows = compose.parse_stamp(b'h' + str(host).encode() + b'\0t' + str(target).encode()
                                   + b'\0s' + str(native).encode() + b'\0')
        base = f'lib/rustlib/{compose.HOST}/lib/'
        self.assertEqual([x['destination'] for x in rows],
                         [base + host.name, base + target.name, base + 'self-contained/' + native.name])
        self.assertEqual([x['source'] for x in rows], list(map(str, (host, target, native))))

    def test_stamp_rejects_incomplete_ambiguous_and_out_of_scope_inputs(self):
        path = str(compose.TREE / compose.HOST / 'release/a/liba.rmeta').encode()
        other = str(compose.TREE / compose.HOST / 'release/b/liba.rmeta').encode()
        invalid = [b'', b't' + path, b'x' + path + b'\0', b'trelative\0',
                   b't/elsewhere/liba.rmeta\0', b't' + path + b'\0h' + path + b'\0',
                   b't' + path + b'\0t' + other + b'\0', b't' + path + b'\0\0',
                   b't' + path + b'/../bad\0', b't/\xff\0']
        for data in invalid:
            with self.subTest(data=data), self.assertRaises((ValueError, UnicodeDecodeError)):
                compose.parse_stamp(data)

    def test_destination_collisions_are_rejected_even_with_identical_bytes(self):
        rows = {}
        compose.add_row(rows, 'lib/a', {'sha256': 'same'})
        for path in ('lib/a', 'lib/a/child', 'lib', '../escape', '/absolute'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                compose.add_row(rows, path, {'sha256': 'same'})

    def test_private_crate_ambiguity_matches_bootstrap_exception(self):
        base = f'lib/rustlib/{compose.HOST}/lib/'
        same = {base + name: {} for name in ('librustc_a-one.rmeta', 'librustc_a-one.dylib',
                                            'librustc_hash-a.rmeta', 'librustc_hash-b.rmeta')}
        compose.check_crate_names(same)
        with self.assertRaises(ValueError):
            compose.check_crate_names({**same, base + 'librustc_a-two.rmeta': {}})

    @staticmethod
    def file(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return dict(path=str(path), sha256=compose.digest(data), size=len(data))

    def fixture(self, root):
        tree = root / 'stage1-rustc'
        stamp = tree / compose.HOST / 'release/.librustc-stamp'
        private = {}
        entries = []
        for name, data in [('librustc_driver-key.rmeta', b'private-meta'),
                           ('librustc_driver-key.dylib', b'runtime-driver')]:
            file = self.file(stamp.parent / 'build/driver/key/out' / name, data)
            private[file['path']] = {k: file[k] for k in ('sha256', 'size')}
            entries.append(b't' + file['path'].encode() + b'\0')
        stamp_record = self.file(stamp, b''.join(entries))
        build = self.file(root / 'D/bin/rustc', b'build-compiler')
        driver = self.file(root / 'E/lib/librustc_driver-key.dylib', b'runtime-driver')
        proof = self.file(root / 'producer.json', b'{"status":"passed"}\n')
        archives, pins = [], {}
        for name, (_, component) in compose.BETA.items():
            path = root / name
            payload_name = ('lib/libbeta-loader.dylib' if component == 'rustc' else
                            f'lib/rustlib/{compose.HOST}/lib/libstd-beta.rlib')
            member = tarfile.TarInfo(name[:-len('.tar.xz')] + '/' + component + '/' + payload_name)
            data = component.encode()
            member.size, member.mode = len(data), 0o644
            with tarfile.open(path, 'w:xz') as archive:
                archive.addfile(member, io.BytesIO(data))
            record = dict(path=str(path), sha256=compose.digest(path.read_bytes()))
            archives.append(record)
            pins[name] = (record['sha256'], component)
        args = dict(archives=archives, stamp=stamp_record, approved_private_files=private,
                    build_compiler=build, runtime_source_commit='1' * 40,
                    runtime_driver=driver, proofs=[proof])
        return tree, stamp, pins, args

    def test_full_ordinary_copy_and_separate_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            tree, stamp, pins, args = self.fixture(root)
            with patch.object(compose, 'TREE', tree), patch.object(compose, 'STAMP', stamp), \
                    patch.object(compose, 'BETA', pins):
                plan = compose.inspect_inputs(**args)
                calls = []
                result = compose.assemble(plan, expected_plan_sha256=compose.digest(compose.encoded(plan)),
                    destination=root / 'B', evidence=root / 'evidence', capacity_guard=lambda: calls.append(True))
                manifest = json.loads((root / 'evidence/private-sysroot.json').read_text())
                self.assertEqual(result['status'], 'assembled-unqualified')
                self.assertFalse(result['compatibility_probes_run'])
                self.assertEqual(set(manifest['files']), set(plan['files']))
                self.assertEqual(manifest['build_compiler_sha256'], args['build_compiler']['sha256'])
                self.assertFalse((root / 'B/bin').exists())
                for item in plan['private']:
                    original, copy = Path(item['source']), root / 'B' / item['destination']
                    self.assertEqual(original.read_bytes(), copy.read_bytes())
                    self.assertNotEqual(original.stat().st_ino, copy.stat().st_ino)
                    self.assertEqual(copy.stat().st_nlink, 1)
                self.assertGreater(len(calls), 2 * len(plan['files']))

    def test_membership_mismatch_and_postfreeze_mutation_precede_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            tree, stamp, pins, args = self.fixture(root)
            with patch.object(compose, 'TREE', tree), patch.object(compose, 'STAMP', stamp), \
                    patch.object(compose, 'BETA', pins):
                missing = dict(args, approved_private_files={})
                with self.assertRaisesRegex(ValueError, 'complete stamp membership'):
                    compose.inspect_inputs(**missing)
                plan = compose.inspect_inputs(**args)
                Path(args['runtime_driver']['path']).write_bytes(b'changed-runtime')
                with self.assertRaises(ValueError):
                    compose.assemble(plan, expected_plan_sha256=compose.digest(compose.encoded(plan)),
                        destination=root / 'B', evidence=root / 'evidence', capacity_guard=lambda: None)
                self.assertFalse((root / 'B').exists())
                self.assertFalse((root / 'evidence').exists())

    def test_archive_link_is_not_followed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            name, (_, component) = next(iter(compose.BETA.items()))
            path = root / name
            member = tarfile.TarInfo(name[:-len('.tar.xz')] + '/' + component + '/lib/link')
            member.type, member.linkname = tarfile.SYMTYPE, '/elsewhere/private'
            with tarfile.open(path, 'w:xz') as archive:
                archive.addfile(member)
            record = dict(path=str(path), sha256=compose.digest(path.read_bytes()))
            with patch.object(compose, 'BETA', {name: (record['sha256'], component)}):
                with self.assertRaisesRegex(ValueError, 'nonordinary beta library member'):
                    compose.archive_rows(record, {})

    def test_capacity_guard_stops_before_next_chunk_and_keeps_written_prefix(self):
        source, output, calls = io.BytesIO(b'x' * (2 * 1024 * 1024)), io.BytesIO(), []

        def capacity():
            calls.append(True)
            if len(calls) == 3:
                raise RuntimeError('running floor reached')

        with self.assertRaisesRegex(RuntimeError, 'running floor'):
            compose.stream_hash(source, output, capacity)
        self.assertEqual(output.getvalue(), b'x' * 1024 * 1024)
        with self.assertRaisesRegex(ValueError, 'capacity guard'):
            compose.stream_hash(io.BytesIO(b'not written'), output)


if __name__ == '__main__':
    unittest.main()
