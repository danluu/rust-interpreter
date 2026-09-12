"""Reject plausible zero-store lookalikes before attributing sampled PCs."""
import importlib.util
from pathlib import Path
import struct
import unittest

path = Path(__file__).resolve().parents[1] / 'benchmarks/experiments/frame-initialization/fixed_profile.py'
spec = importlib.util.spec_from_file_location('fixed_profile', path)
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


def code(*words):
    return struct.pack('<' + 'I' * len(words), *words)


class FixedClearAttribution(unittest.TestCase):
    def test_pair_and_scalar_tail_decode(self):
        # stp xzr,xzr,[x11]; str xzr,[x11,#16]; str wzr,[x11,#24]; strb wzr,[x11,#28]
        words = [0xa9007d7f, 0xf900097f, 0xb900197f, 0x3900717f]
        self.assertEqual([profile.zero_store(w) for w in words], [(0, 16), (16, 8), (24, 4), (28, 1)])
        payload = code(profile.END_POINTER, *words, profile.LOAD_PEAK)
        self.assertEqual(profile.fixed_span(payload, 29), (4, 20))
        with self.assertRaises(RuntimeError):
            profile.fixed_span(payload, 28)

    def test_wrong_base_value_and_writeback_rejected(self):
        for word in [0xa9007d5f, 0xa9007d60, 0xa8817d7f, 0xf800857f, 0x39007160]:
            self.assertIsNone(profile.zero_store(word))

    def test_holes_overlap_missing_context_and_ambiguous_sites(self):
        valid = code(profile.END_POINTER, 0xf900017f, profile.LOAD_PEAK)
        self.assertEqual(profile.fixed_span(valid, 8), (4, 8))
        for payload, size in [
            (code(profile.END_POINTER, 0xf900057f, profile.LOAD_PEAK), 8),
            (code(profile.END_POINTER, 0xf900017f, 0xf900017f, profile.LOAD_PEAK), 16),
            (code(0xf900017f, profile.LOAD_PEAK), 8),
            (code(profile.END_POINTER, 0xf900017f), 8),
            (valid + valid, 8),
        ]:
            with self.subTest(payload=payload):
                with self.assertRaises(RuntimeError):
                    profile.fixed_span(payload, size)


if __name__ == '__main__':
    unittest.main()
