"""Pure controls using the saved Cargo005 trace; no native command is run."""
import unittest
from pathlib import Path
import build as b


class BuildControls(unittest.TestCase):
    def setUp(self):
        self.plan = b.read(b.m.WORK / 'planned.json')
        self.binding = self.plan['binding']
        old = b.read(b.m.OLDWORK / 'plan.json')
        self.raw = (b.m.OLDWORK / 'run-03/commands/005/stderr').read_bytes()
        text = self.raw.decode().replace(str(b.m.OLDWORK / 'source'), str(b.OWNER))
        for before, after in zip(old['binding']['build_rustflags'], self.binding['build_rustflags'], strict=True):
            text = text.replace(before, after)
        self.rebound = text.encode()
        self.sources = set(self.plan['crate_files']) | set(self.plan['registry_files'])

    def parse(self, raw, sources=None):
        return b.cargo_compiles(raw, self.binding, b.OWNER, self.sources if sources is None else sources)

    def test_retained_compiler_trace_accepts_exact_rebound_roles(self):
        rows = self.parse(self.rebound)
        self.assertGreaterEqual(len(rows), 2)

    def test_wrong_build_compiler_is_rejected(self):
        raw = self.rebound.replace(self.binding['build']['executable']['path'].encode(),
                                   self.binding['runtime']['executable']['path'].encode())
        with self.assertRaisesRegex(RuntimeError, 'not exact D'):
            self.parse(raw)

    def test_wrong_native_library_route_is_rejected(self):
        raw = self.rebound.replace(self.binding['build_rustflags'][1].encode(), b'-Lnative=/unreviewed')
        with self.assertRaisesRegex(RuntimeError, 'compiler flags differ'):
            self.parse(raw)

    def test_unfrozen_compiled_source_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'unfrozen source'):
            self.parse(self.rebound, set())

    def test_missing_wrapper_compile_is_rejected(self):
        raw = b'\n'.join(line for line in self.rebound.splitlines() if b'--crate-name rust_interp_rustc_wrapper' not in line)
        with self.assertRaisesRegex(RuntimeError, 'both actual tool compiles required'):
            self.parse(raw)

    def test_historical_zero_exit_strip_failures_are_rejected(self):
        warning = b'warning: stripping debug info with `rust-objcopy` failed: signal: 6 (SIGABRT)'
        self.assertEqual(self.raw.count(warning), 13)
        with self.assertRaisesRegex(RuntimeError, 'helper/strip/native compiler failure'):
            b.check_build_diagnostics(self.raw)


if __name__ == '__main__':
    unittest.main()
