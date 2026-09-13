"""Publication failures use dummy bytes only; never execute a tool or workload."""
import json
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import tarfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import public_tool_publication as p


def build_driver():
    path = Path(__file__).resolve().parents[1] / 'benchmarks/experiments/host-proc-macro/build.py'
    spec = importlib.util.spec_from_file_location('macro_build_driver_test', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


class PublicToolPublicationTests(unittest.TestCase):
    def minimal(self, directory):
        payload = directory / 'payload'; (payload / 'provenance').mkdir(parents=True)
        owner = directory / 'owner'; owner.mkdir()
        binaries = {}
        for name in p.BINARIES:
            path = directory / name; path.write_bytes(name.encode()); binaries[name] = path
        values = {
            'provenance/platform.json': p.platform_identity(),
            'provenance/libraries.json': dict(subjects={name: dict(identity=dict(nodes={
                '$CARGO': dict(rpaths=[], dependencies=[])})) for name in p.BINARIES}),
            'provenance/commands.json': [dict(label='capabilities', stdout='provenance/capabilities.stdout')],
            'provenance/capabilities.stdout': dict(schema_version=1, bytecode_version=5),
        }
        for name, value in values.items():(payload / name).write_text(json.dumps(value))
        composition = dict(binaries={name: p.file_digest(path) for name, path in binaries.items()},
            payloads={name: p.file_digest(payload / name) for name in values},
            libraries=dict(platform_sha256=p.file_digest(payload / 'provenance/platform.json')))
        return composition, payload, binaries, owner

    def test_failed_provenance_validation_never_publishes_readiness(self):
        with tempfile.TemporaryDirectory() as temporary:
            composition, payload, binaries, owner = self.minimal(Path(temporary))
            key = p.digest(composition); destination = owner / '.work/interpreter-tools' / key
            def reject(tool, supplied_key, reader, *, qualification_policy):
                self.assertIsNone(qualification_policy)  # This fixture uses the default macro policy.
                self.assertEqual(tool, destination); self.assertEqual(supplied_key, key)
                self.assertFalse((destination / 'ready.json').exists())
                self.assertEqual(json.loads(reader(destination / 'ready.json')), composition['binaries'])
                raise RuntimeError('failed retained correctness')
            with patch.object(p, 'require_space'), patch.object(p, 'validate_public_tool', side_effect=reject):
                with self.assertRaisesRegex(RuntimeError, 'failed retained correctness'):
                    p.immutable_publish(composition, payload, binaries, [owner])
            self.assertFalse((destination / 'ready.json').exists())
            self.assertTrue((destination / 'source.json').is_file())  # Failed attempt remains reviewable.
            self.assertEqual({name: p.file_digest(path) for name, path in binaries.items()}, composition['binaries'])

    def test_existing_installation_and_payload_escape_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            composition, payload, binaries, owner = self.minimal(Path(temporary))
            destination = owner / '.work/interpreter-tools' / p.digest(composition)
            destination.mkdir(parents=True); (destination / 'owner-note').write_bytes(b'existing')
            with self.assertRaisesRegex(RuntimeError, 'replace tools'):
                p.immutable_publish(composition, payload, binaries, [owner])
            self.assertEqual((destination / 'owner-note').read_bytes(), b'existing')
            composition['payloads']['../escape'] = '0' * 64
            with self.assertRaisesRegex(RuntimeError, 'relative provenance'):
                p.immutable_publish(composition, payload, binaries, [owner])
            self.assertFalse((owner / '.work/escape').exists())

    def test_changed_frozen_source_stops_supervisor_before_any_child(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary); (directory / 'source.rs').write_bytes(b'changed')
            plan = dict(owner=str(directory), status='not-executed', tool_key=None,
                tool_sources={'source.rs': '0' * 64}, workspace_sources={}, harness={}, commands=[])
            with patch.object(p, 'retained_command') as command:
                with self.assertRaisesRegex(RuntimeError, 'frozen build input differs'):
                    p.run_plan_commands(plan, inherited={})
                command.assert_not_called()

    def test_registry_source_drift_is_rejected_without_running_cargo(self):
        driver = build_driver()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); package = root / 'registry/src/registry-id/fixture-1.0.0'
            package.mkdir(parents=True)
            archive = root / 'registry/cache/registry-id/fixture-1.0.0.crate'
            archive.parent.mkdir(parents=True)
            content = b'[package]\nname="fixture"\nversion="1.0.0"\n'
            manifest = package / 'Cargo.toml'; manifest.write_bytes(content)
            with tarfile.open(archive, 'w:gz') as bundle:
                member = tarfile.TarInfo(package.name + '/Cargo.toml'); member.size = len(content)
                bundle.addfile(member, io.BytesIO(content))
            checksum = driver.file_digest(archive)
            (package / '.cargo-ok').write_text('installed')
            with patch.object(driver, 'retained_command') as command:
                self.assertEqual(set(driver.registry_files(package, {'checksum': checksum})),
                                 {manifest, package / '.cargo-ok', archive})
                with self.assertRaisesRegex(RuntimeError, 'archive differs from lockfile'):
                    driver.registry_files(package, {'checksum': '0' * 64})
                manifest.write_bytes(content + b'# drift\n')
                with self.assertRaisesRegex(RuntimeError, 'source differs from archive'):
                    driver.registry_files(package, {'checksum': checksum})
                manifest.write_bytes(content)
                (package / 'unexpected.rs').write_text('')
                with self.assertRaisesRegex(RuntimeError, 'file inventory differs'):
                    driver.registry_files(package, {'checksum': checksum})
                command.assert_not_called()

    def test_cargo_config_wrapper_override_fails_before_any_command(self):
        driver = build_driver()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); cargo_home = root / 'cargo-home'; cargo_home.mkdir()
            (cargo_home / 'config.toml').write_text('[build]\nrustc-wrapper="/unreviewed/wrapper"\n')
            with patch.object(driver, 'ROOT', root), patch.object(driver, 'retained_command') as command:
                with self.assertRaisesRegex(RuntimeError, 'unreviewed compiler'):
                    driver.configuration({'CARGO_HOME': str(cargo_home)})
                command.assert_not_called()


if __name__ == '__main__':
    unittest.main()
