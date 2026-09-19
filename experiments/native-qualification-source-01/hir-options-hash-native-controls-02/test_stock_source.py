"""Source-only controls; execution requires a separately reviewed pure packet."""
import unittest
from pathlib import Path
import stock_source as s
SOURCE=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/.work/hir-options-hash-compiler-01/source/compiler/rustc/src/main.rs')
class StockSource(unittest.TestCase):
    def test_exact_saved_source_remove_only_line(self):
        original=SOURCE.read_bytes();derived,proof=s.derive(original,SOURCE,Path('/owned/private-main.rs'))
        self.assertEqual(derived,b''.join(original.splitlines(keepends=True)[:3]+original.splitlines(keepends=True)[4:]))
        self.assertEqual(proof['derived_sha256'],s.DERIVED_SHA256)
        self.assertIn(b'rustc_driver::override_c_allocator_in_binary!();',derived)
        self.assertIn(b'rustc_driver::main()',derived)
    def test_missing_expectation_rejected(self):
        with self.assertRaises(ValueError):s.derive(SOURCE.read_bytes().replace(s.EXPECTATION,b''),SOURCE,'/owned/main.rs')
    def test_duplicate_expectation_rejected(self):
        with self.assertRaises(ValueError):s.derive(SOURCE.read_bytes()+s.EXPECTATION,SOURCE,'/owned/main.rs')
    def test_other_source_change_rejected(self):
        with self.assertRaises(ValueError):s.derive(SOURCE.read_bytes().replace(b'rustc_driver::main()',b'rustc_driver::oops()'),SOURCE,'/owned/main.rs')
if __name__=='__main__':unittest.main()
