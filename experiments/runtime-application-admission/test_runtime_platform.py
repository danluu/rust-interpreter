"""Pure uname-policy controls; no host queries or application execution."""
import unittest
import runtime_platform as platform


class PlatformIdentityControls(unittest.TestCase):
    def setUp(self):
        self.raw = ['Darwin', 'MacBook-Pro-2.local', '27.0.0', 'Darwin Kernel Version 27.0.0: source-bound', 'arm64']
        self.expected = platform.identity(self.raw)

    def test_identical_platform_retains_every_context_field(self):
        self.assertEqual(platform.validate(self.raw, self.expected), dict(zip(platform.FIELDS, self.raw)))

    def test_changed_nodename_is_retained_without_changing_identity(self):
        changed = self.raw.copy(); changed[1] = 'Mac'
        self.assertEqual(platform.identity(changed), self.expected)
        self.assertEqual(platform.validate(changed, self.expected)['nodename'], 'Mac')
        self.assertEqual(platform.validate(self.raw, self.expected)['nodename'], 'MacBook-Pro-2.local')

    def test_each_kernel_or_machine_field_change_rejects(self):
        for index in [0, 2, 3, 4]:
            with self.subTest(index=index), self.assertRaises(ValueError):
                changed = self.raw.copy(); changed[index] += '-different'
                platform.validate(changed, self.expected)

    def test_missing_extra_or_wrong_policy_identity_rejects(self):
        for expected in [dict(self.expected, nodename=self.raw[1]), dict(self.expected, policy='other'),
                         {k:v for k,v in self.expected.items() if k != 'version'}, list(self.expected)]:
            with self.subTest(expected=expected), self.assertRaises(ValueError):
                platform.validate(self.raw, expected)

    def test_malformed_or_partial_observations_reject(self):
        for raw in [self.raw[:-1], self.raw+['extra'], dict(zip(platform.FIELDS,self.raw)),
                    [*self.raw[:1], '', *self.raw[2:]], [*self.raw[:1], 'bad\x00name', *self.raw[2:]],
                    [*self.raw[:1], 'x'*4097, *self.raw[2:]], [*self.raw[:1], 1, *self.raw[2:]]]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                platform.validate(raw, self.expected)


if __name__ == '__main__':
    unittest.main()
