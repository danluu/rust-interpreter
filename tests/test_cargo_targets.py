"""A stale sidecar on another Cargo target must never be executed."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from interpreter import artifact_matches_target


def event(name='api-check', kind='test', test=True):
    return dict(reason='compiler-artifact', profile=dict(test=test),
                target=dict(name=name, kind=[kind]))


class CargoTargetTests(unittest.TestCase):
    def test_requested_integration_target(self):
        self.assertTrue(artifact_matches_target(event(), True, 'api-check'))

    def test_other_targets_and_non_test_builds_are_rejected(self):
        for value in [event(name='api_check'), event(name='sibling'),
                      event(kind='lib'), event(kind='bin'), event(test=False)]:
            self.assertFalse(artifact_matches_target(value, True, 'api-check'))

    def test_messages_without_artifacts_are_ignored(self):
        self.assertFalse(artifact_matches_target(dict(reason='compiler-message'), True, 'api-check'))

    def test_existing_library_route_keeps_test_profile_filter(self):
        self.assertTrue(artifact_matches_target(event(kind='lib'), True, None))
        self.assertFalse(artifact_matches_target(event(kind='lib', test=False), True, None))


if __name__ == '__main__':
    unittest.main()
