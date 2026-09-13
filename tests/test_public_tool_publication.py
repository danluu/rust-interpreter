"""Publication failures use dummy bytes only; never execute a tool or workload."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import public_tool_publication as p


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
            def reject(tool, supplied_key, reader):
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


if __name__ == '__main__':
    unittest.main()
