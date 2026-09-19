"""Source-only pure adapter controls; execution requires a separate frozen harness.

All native images are small in-memory bytes. Filesystem observations are mocked;
the monitor stops at an injected canonical-admission sentinel before any output
creation. Process, signal and write APIs are forbidden throughout every test.
These controls do not execute the unchanged production R installation recipe.
"""
import copy
from contextlib import ExitStack
import importlib.util
import os
from pathlib import Path
import struct
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


HERE = Path(__file__).resolve().parent
ARM64 = 0x100000c
X86_64 = 0x1000007
GIB = 2**30


def load_source(name, *, owned=None):
    """Fresh private modules; restore the predecessor's import state exactly."""
    assert sys.dont_write_bytecode, 'controls require explicit Python -B'
    alias = '_runtime_adapter_control_'+name
    missing = object()
    previous = sys.modules.get(alias, missing)
    previous_owned = sys.modules.get('owned_stage', missing)
    old_path = list(sys.path)
    spec = importlib.util.spec_from_file_location(alias, HERE/(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    try:
        sys.modules[alias] = module
        if owned is not None:
            sys.modules['owned_stage'] = owned
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path[:] = old_path
        for key, value in [(alias, previous), ('owned_stage', previous_owned)]:
            if value is missing:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


def loader_command(kind, text):
    offset = 24 if kind in {0xc, 0xd, 0x80000018, 0x8000001f, 0x20, 0x80000023} else 12
    value = text.encode()+b'\0'
    width = (offset+len(value)+7)//8*8
    return struct.pack('<III', kind, width, offset)+bytes(offset-12)+value+bytes(width-offset-len(value))


def thin(commands, *, cpu=ARM64):
    payload = b''.join(commands)
    return struct.pack('<8I', 0xfeedfacf, cpu, 0, 2, len(commands), len(payload), 0, 0)+payload


def fat(images, *, wide=False):
    """Return valid disjoint bounded FAT32/FAT64 slices and their table slots."""
    width = 32 if wide else 20
    result = bytearray(128+256*len(images))
    result[:8] = struct.pack('>II', 0xcafebabf if wide else 0xcafebabe, len(images))
    for index, (cpu, image) in enumerate(images):
        assert len(image) <= 256
        offset = 128+index*256
        entry = (struct.pack('>IIQQII', cpu, 0, offset, len(image), 3, 0) if wide
                 else struct.pack('>IIIII', cpu, 0, offset, len(image), 3))
        result[8+index*width:8+(index+1)*width] = entry
        result[offset:offset+len(image)] = image
    return bytes(result)


def replaced(raw, offset, value, fmt='<I'):
    result = bytearray(raw)
    struct.pack_into(fmt, result, offset, value)
    return bytes(result)


class PureAdapterControls(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        # Source loading may read these Python files; no fixture or output write
        # and no external process/signal is allowed even on an unexpected path.
        self.forbidden = []
        for owner, names in [(subprocess, ['Popen', 'run', 'call', 'check_call', 'check_output']),
                             (os, ['kill', 'killpg', 'system', 'open']),
                             (Path, ['open', 'mkdir', 'write_bytes', 'write_text', 'unlink', 'rmdir'])]:
            for name in names:
                value = self.stack.enter_context(patch.object(owner, name,
                    side_effect=AssertionError('forbidden external/write API: '+name)))
                self.forbidden.append(value)
        self.discovery = load_source('discovery')
        self.controller = load_source('controller')
        self.owned = SimpleNamespace(CANONICAL_LOCK=Path('/fixture/canonical.lock'), workload_lock=Mock())
        self.monitor = load_source('monitor', owned=self.owned)

    def tearDown(self):
        for forbidden in self.forbidden:
            forbidden.assert_not_called()

    def rejected_image(self, raw):
        with self.assertRaises((RuntimeError, UnicodeDecodeError)):
            self.discovery.macho(raw)

    def sample_row(self, **changes):
        result = dict(namespace_allocated_bytes=123, evidence_allocated_bytes=456,
                      free_bytes=12*GIB, allocation_errors=[])
        result.update(changes)
        return result

    def private_monitor(self, row=None):
        original = self.sample_row() if row is None else row
        return SimpleNamespace(EVIDENCE_OWNERS=(Path('/fixture/X'), Path('/fixture/A')),
            EVIDENCE_PREFIXES=('existing-',), sample=Mock(side_effect=lambda **kw: copy.deepcopy(original)),
            allocated=Mock(return_value=dict(bytes=789, entries_visited=2)),
            shutil=SimpleNamespace(disk_usage=Mock(return_value=SimpleNamespace(free=11*GIB))))

    def install_directory(self):
        return self.controller.R/'.work/runtime-compilers'/('a'*64)

    def test_thin_load_kinds_order_and_self_identity(self):
        kinds = [(0xc, 'LC_LOAD_DYLIB'), (0x80000018, 'LC_LOAD_WEAK_DYLIB'),
                 (0x8000001f, 'LC_REEXPORT_DYLIB'), (0x20, 'LC_LAZY_LOAD_DYLIB'),
                 (0x80000023, 'LC_LOAD_UPWARD_DYLIB'), (0xe, 'LC_LOAD_DYLINKER')]
        commands = [loader_command(0xd, '@rpath/self.dylib'), loader_command(0x8000001c, '@loader_path'),
                    *[loader_command(kind, '/image/'+str(index)) for index, (kind, _) in enumerate(kinds)],
                    loader_command(0x8000001c, '@executable_path/../lib')]
        result = self.discovery.macho(thin(commands))
        self.assertEqual(result, dict(rpaths=['@loader_path', '@executable_path/../lib'],
            loads=[[name, '/image/'+str(index)] for index, (_, name) in enumerate(kinds)]))

    def test_fat32_and_fat64_select_exact_arm64_slice(self):
        image = thin([loader_command(0xc, '@rpath/selected.dylib')])
        for wide in [False, True]:
            with self.subTest(wide=wide):
                foreign = thin([loader_command(0xc, 'foreign')], cpu=X86_64)
                self.assertEqual(self.discovery.macho(fat([(X86_64, foreign), (ARM64, image)], wide=wide)),
                                 self.discovery.macho(image))

    def test_image_magic_cpu_and_minimum_bounds(self):
        image = thin([loader_command(0xc, 'x')])
        for raw in [b'', image[:31], b'ABCD'+image[4:], replaced(image, 4, X86_64)]:
            with self.subTest(raw=raw[:32]): self.rejected_image(raw)

    def test_fat_count_table_missing_and_duplicate_arm64(self):
        image = thin([loader_command(0xc, 'x')])
        valid = fat([(ARM64, image)])
        cases = [replaced(valid, 4, 0, '>I'), replaced(valid, 4, 32, '>I'),
                 replaced(valid[:32], 4, 2, '>I'), fat([(X86_64, image)]),
                 fat([(ARM64, image), (ARM64, image)])]
        for raw in cases:
            with self.subTest(size=len(raw)): self.rejected_image(raw)

    def test_fat_declared_slice_limits_contain_header_and_commands(self):
        image = thin([loader_command(0xc, '@rpath/selected.dylib')])
        for wide in [False, True]:
            valid = fat([(ARM64, image)], wide=wide)
            size_offset, fmt = (24, '>Q') if wide else (20, '>I')
            for size in [0, 1, 31, len(image)-1, len(valid)]:
                with self.subTest(wide=wide, size=size):
                    self.rejected_image(replaced(valid, size_offset, size, fmt))
            with self.subTest(wide=wide, outside_offset=True):
                self.rejected_image(replaced(valid, 16, len(valid), '>Q' if wide else '>I'))

    def test_fat_header_alignment_and_reserved_fields(self):
        image = thin([loader_command(0xc, 'x')])
        for wide in [False, True]:
            valid = fat([(ARM64, image)], wide=wide)
            align_offset = 32 if wide else 24
            for raw in [replaced(valid, 16, 8, '>Q' if wide else '>I'),
                        replaced(valid, align_offset, 32, '>I'),
                        replaced(valid, align_offset, 8, '>I')]:
                with self.subTest(wide=wide): self.rejected_image(raw)
        self.rejected_image(replaced(fat([(ARM64, image)], wide=True), 36, 1, '>I'))

    def test_load_table_count_and_extent_bounds(self):
        image = thin([loader_command(0xc, 'x')])
        for raw in [replaced(image, 16, 0), replaced(image, 16, 4096), replaced(image, 16, 2),
                    replaced(image, 20, 0), replaced(image, 20, len(image)),
                    replaced(image, 20, len(image)-33), image+b'ignored trailing bytes']:
            if raw == image+b'ignored trailing bytes':
                self.assertEqual(self.discovery.macho(raw), self.discovery.macho(image))
            else:
                with self.subTest(raw=raw[:32]): self.rejected_image(raw)

    def test_load_command_width_and_string_offsets(self):
        image = thin([loader_command(0xc, 'x')])
        width = len(image)-32
        for raw in [replaced(image, 36, 7), replaced(image, 36, width+8),
                    replaced(image, 40, 0), replaced(image, 40, 11), replaced(image, 40, width)]:
            with self.subTest(raw=raw[32:44]): self.rejected_image(raw)

    def test_string_empty_unterminated_and_invalid_utf8(self):
        for payload in [b'\0'+b'x'*7, b'x'*8, b'\xff\0'+b'x'*6]:
            command = struct.pack('<III', 0x8000001c, 20, 12)+payload
            with self.subTest(payload=payload): self.rejected_image(thin([command]))

    def test_embedded_loader_environment_always_refused(self):
        self.rejected_image(thin([loader_command(0x27, 'DYLD_LIBRARY_PATH=/foreign')]))

    def test_preflight_counts_only_existing_namespace_and_adds_evidence_owner(self):
        monitor = self.private_monitor(); original_sample = monitor.sample
        self.assertIs(self.controller.configure_monitor(monitor, installation_directory=None), monitor)
        result = monitor.sample(evidence_root=Path('/fixture/work'), evidence_roots=[Path('/fixture/work')])
        self.assertEqual(result['compiler_namespace_allocated_bytes'], 123)
        self.assertEqual(result['namespace_allocated_bytes'], 123)
        self.assertEqual(result['evidence_allocated_bytes'], 456)
        self.assertEqual(result['runtime_installation_allocation_sample'], dict(bytes=0, absent=True))
        self.assertEqual(result['free_bytes'], 11*GIB)
        self.assertEqual(monitor.EVIDENCE_OWNERS, (Path('/fixture/X'), Path('/fixture/A'), self.controller.R))
        self.assertEqual(monitor.EVIDENCE_PREFIXES, ('existing-', self.controller.PREFIX))
        original_sample.assert_called_once_with(evidence_root=Path('/fixture/work'), evidence_roots=[Path('/fixture/work')])
        monitor.allocated.assert_not_called()

    def test_present_installation_is_counted_once_in_shared_namespace_cap(self):
        monitor = self.private_monitor(); directory = self.install_directory()
        self.controller.configure_monitor(monitor, installation_directory=directory)
        with patch.object(Path, 'exists', return_value=True):
            first = monitor.sample(evidence_root=Path('/fixture/work'), evidence_roots=[])
            second = monitor.sample(evidence_root=Path('/fixture/work'), evidence_roots=[])
        self.assertEqual(first['namespace_allocated_bytes'], 123+789)
        self.assertEqual(second['namespace_allocated_bytes'], 123+789)
        self.assertEqual(first['evidence_allocated_bytes'], 456)
        self.assertEqual(monitor.allocated.call_args_list[0].args, (directory, (directory,)))
        self.assertEqual(monitor.allocated.call_count, 2)

    def test_absent_installation_adds_no_bytes_or_walk(self):
        monitor = self.private_monitor()
        self.controller.configure_monitor(monitor, installation_directory=self.install_directory())
        with patch.object(Path, 'exists', return_value=False), patch.object(Path, 'is_symlink', return_value=False):
            result = monitor.sample(evidence_root=Path('/fixture/work'), evidence_roots=[])
        self.assertEqual(result['namespace_allocated_bytes'], 123)
        monitor.allocated.assert_not_called()

    def test_unavailable_or_indirect_allocation_rejects_without_zero_credit(self):
        for error in [OSError('unavailable'), AssertionError('indirect root')]:
            monitor = self.private_monitor(); monitor.allocated.side_effect = error
            self.controller.configure_monitor(monitor, installation_directory=self.install_directory())
            with patch.object(Path, 'exists', return_value=False), patch.object(Path, 'is_symlink', return_value=True):
                result = monitor.sample(evidence_root=Path('/fixture/work'), evidence_roots=[])
            self.assertTrue(result['runtime_installation_allocation_sample']['unavailable'])
            self.assertEqual(len(result['allocation_errors']), 1)
            self.assertIn('unavailable', self.monitor.rejection(result))

    def test_allocation_preserves_prior_error_and_lowest_free_sample(self):
        old_error = dict(root='/fixture/N', error='original missing inventory')
        monitor = self.private_monitor(self.sample_row(allocation_errors=[old_error], free_bytes=10*GIB))
        self.controller.configure_monitor(monitor, installation_directory=None)
        result = monitor.sample(evidence_root=Path('/fixture/work'), evidence_roots=[])
        self.assertEqual(result['allocation_errors'], [old_error])
        self.assertEqual(result['free_bytes'], 10*GIB)
        self.assertIsNotNone(self.monitor.rejection(result))

    def test_only_exact_keyed_installation_scope_is_allowed(self):
        parent = self.install_directory().parent
        for directory in [Path('/fixture')/('a'*64), parent/('a'*63), parent/('A'*64),
                          parent/('g'*64), parent/'..'/('a'*64), Path('relative')/('a'*64)]:
            with self.subTest(directory=str(directory)):
                monitor = self.private_monitor()
                with self.assertRaises(RuntimeError):
                    self.controller.configure_monitor(monitor, installation_directory=directory)
                monitor.allocated.assert_not_called()

    def test_private_instance_reuse_and_historical_monitor_are_rejected(self):
        private = self.private_monitor()
        self.controller.configure_monitor(private, installation_directory=None)
        with self.assertRaisesRegex(RuntimeError, 'already adapted'):
            self.controller.configure_monitor(private, installation_directory=None)
        historical = self.private_monitor(); historical.owned = self.owned
        plan = dict(work=str(self.controller.R/'.work/hir-options-hash-runtime-preflight-test'),
            phase='preflight', owner=str(self.controller.R), capacity=dict(entry_gib=24, stop_gib=9,
                floor_gib=8, combined_namespace_bytes=14*GIB, evidence_bytes=256*2**20))
        with self.assertRaisesRegex(RuntimeError, 'historical shared monitor'):
            self.controller.Controller(plan=plan, inputs_sha256='0'*64, q=None, recipe=None,
                reader=SimpleNamespace(reader=SimpleNamespace(monitor=historical)), monitor=historical,
                check_frozen=Mock(), read_json=Mock(), read_bytes=Mock(), sha=Mock())
        self.assertFalse(getattr(historical, '_runtime_configured', False))

    def test_existing_owners_not_duplicated_and_caps_not_reset(self):
        private = self.private_monitor()
        private.EVIDENCE_OWNERS += (self.controller.R,)
        self.controller.configure_monitor(private, installation_directory=None)
        self.assertEqual(private.EVIDENCE_OWNERS.count(self.controller.R), 1)
        for changes in [dict(namespace_allocated_bytes=14*GIB+1),
                        dict(evidence_allocated_bytes=256*2**20+1), dict(free_bytes=9*GIB-1)]:
            with self.subTest(changes=changes): self.assertIsNotNone(self.monitor.rejection(self.sample_row(**changes)))
        self.assertIsNone(self.monitor.rejection(self.sample_row(namespace_allocated_bytes=14*GIB,
            evidence_allocated_bytes=256*2**20, free_bytes=9*GIB)))

    def test_relocated_monitor_keeps_original_evidence_owners_and_empty_cwd_policy(self):
        expected = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
        self.assertEqual(self.monitor.CONTROLLER_OWNER, expected)
        self.assertIn(expected, self.monitor.EVIDENCE_OWNERS)
        self.assertEqual(len(set(self.monitor.EVIDENCE_OWNERS)), 4)
        self.assertEqual(self.monitor.ALLOWED_CWDS, frozenset())

    def test_exact_allowed_cwds_reach_inherited_fd_gate_only(self):
        class ReachedCanonicalGate(Exception): pass
        root = self.controller.R/'.work/hir-options-hash-runtime-control'
        for cwd in [self.controller.R, root/'source-probe']:
            self.monitor.ALLOWED_CWDS = frozenset({cwd})
            self.owned.workload_lock.reset_mock()
            self.owned.workload_lock.side_effect = ReachedCanonicalGate
            with patch.object(Path, 'resolve', autospec=True, side_effect=lambda path, **kw: path):
                with self.assertRaises(ReachedCanonicalGate):
                    self.monitor.run(['/fixture/compiler'], cwd=cwd, environment={}, output=root/'command',
                        canonical_fd=37, evidence_root=root, evidence_roots=[root])
            self.owned.workload_lock.assert_called_once_with(self.owned.CANONICAL_LOCK, 600, inherited_fd=37)

    def test_missing_or_aliased_cwd_is_refused_before_admission(self):
        root = self.controller.R/'.work/hir-options-hash-runtime-control'
        cwd = root/'source-probe'
        for allowed, indirect in [(frozenset(), False), (frozenset({self.controller.R}), False),
                                  (frozenset({cwd}), True)]:
            self.monitor.ALLOWED_CWDS = allowed
            self.owned.workload_lock.reset_mock()
            def resolve(path, **kw): return Path('/fixture/foreign') if indirect and path == cwd else path
            with patch.object(Path, 'resolve', autospec=True, side_effect=resolve):
                with self.assertRaises(AssertionError):
                    self.monitor.run(['/fixture/compiler'], cwd=cwd, environment={}, output=root/'command',
                        canonical_fd=37, evidence_root=root, evidence_roots=[root])
            self.owned.workload_lock.assert_not_called()


if __name__ == '__main__':
    unittest.main()
