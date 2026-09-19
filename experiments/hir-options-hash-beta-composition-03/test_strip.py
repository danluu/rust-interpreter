import struct
import unittest

import strip_object as assemble


def object_file(sections, kind=1):
    command_size = 72 + len(sections) * 80
    offset = 32 + command_size
    rows, payloads = [], []
    for segment, name, payload in sections:
        rows.append(struct.pack('<16s16sQQIIIIIIII', name.encode(), segment.encode(),
                                0, len(payload), offset, 0, 0, 0, 0, 0, 0, 0))
        payloads.append(payload); offset += len(payload)
    header = struct.pack('<IiiIIIII', 0xfeedfacf, 0x100000c, 0, kind, 1, command_size, 0, 0)
    segment = struct.pack('<II16sQQQQiiII', 0x19, command_size, b'', 0, 0,
                          32 + command_size, sum(map(len, payloads)), 7, 7, len(sections), 0)
    return header + segment + b''.join(rows) + b''.join(payloads)


TEXT = ('__TEXT', '__text', b'actual-code-bytes')
DEBUG = ('__DWARF', '__debug_info', b'actual-debug-bytes')


class StripControls(unittest.TestCase):
    def test_real_debug_removal_preserves_native_section_bytes(self):
        proof = assemble.check_strip(object_file([TEXT, DEBUG]), object_file([TEXT]))
        self.assertEqual(proof['debug_sections'][0]['name'], '__debug_info')
        self.assertEqual(proof['retained_sections'][0]['name'], '__text')
        self.assertLess(proof['after_bytes'], proof['before_bytes'])

    def test_object_without_embedded_debug_cannot_pass(self):
        with self.assertRaises(ValueError):
            assemble.check_strip(object_file([TEXT]), object_file([TEXT]))

    def test_remaining_debug_cannot_pass(self):
        with self.assertRaises(ValueError):
            assemble.check_strip(object_file([TEXT, DEBUG]), object_file([TEXT, DEBUG]))

    def test_native_payload_mutation_cannot_pass(self):
        with self.assertRaises(ValueError):
            assemble.check_strip(object_file([TEXT, DEBUG]), object_file([('__TEXT', '__text', b'changed-code-bytes')]))

    def test_non_object_and_duplicate_sections_are_rejected(self):
        for value in [object_file([TEXT], kind=2), object_file([TEXT, TEXT])]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                assemble.object_sections(value)

    def test_truncated_and_out_of_bounds_sections_are_rejected(self):
        valid = object_file([TEXT, DEBUG])
        invalid = bytearray(valid)
        struct.pack_into('<I', invalid, 32 + 72 + 48, len(invalid) + 1)
        for value in [valid[:16], valid[:64], valid[:-1], invalid]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                assemble.object_sections(value)


if __name__ == '__main__':
    unittest.main()
