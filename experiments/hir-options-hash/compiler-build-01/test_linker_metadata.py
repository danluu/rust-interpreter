"""Pure controls for the narrow ld stream and self-ID adapter; no tool probe."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'compiler-metadata-02'))
import metadata as m
import linker_parser

class LinkerControls(unittest.TestCase):
 def fixture(self):
  paths=['/private/linker/ld',*[f'/private/linker/lib{i}.dylib' for i in range(4)]]
  raw=''.join('dyld[123]: <00000000-0000-0000-0000-000000000000> '+p+'\n' for p in paths)
  raw+='dyld[123]: /usr/lib/libSystem.B.dylib\ndyld[123]: move loaded to delayed: libSystem.B.dylib\n'
  raw+='@(#)PROGRAM:ld PROJECT:ld-1266.8\nBUILD 01:30:17 Apr  9 2026\nconfigured to support archs: arm64 x86_64\nLibrary search paths:\n\t/usr/lib\nFramework search paths:\n\t/System/Library/Frameworks/\n'
  return paths,raw.encode()
 def test_valid_report_is_lossless_and_delayed_system_is_not_private(self):
  paths,raw=self.fixture();r=linker_parser.parse(raw,123,paths)
  self.assertEqual(b''.join(bytes.fromhex(x['raw_hex']) for x in r['lines']),raw)
  self.assertEqual(r['private_paths'],sorted(paths));self.assertEqual(len(r['delayed']),1)
 def test_unknown_version_or_malformed_tail_rejected(self):
  paths,raw=self.fixture()
  for variant in [raw+b'unreviewed telemetry\n',raw[:-1],raw.replace(b'ld-1266.8',b'ld-1266.9')]:
   with self.subTest(raw=variant),self.assertRaises(RuntimeError):linker_parser.parse(variant,123,paths)
 def test_exact_pid_private_set_and_system_delay_required(self):
  paths,raw=self.fixture()
  for variant in [raw.replace(b'dyld[123]',b'dyld[124]',1),raw.replace(paths[0].encode(),b'/private/foreign/ld',1),raw.replace(b'move loaded to delayed: libSystem.B.dylib',b'move loaded to delayed: lib0.dylib')]:
   with self.subTest(raw=variant),self.assertRaises(RuntimeError):linker_parser.parse(variant,123,paths)
 def test_self_id_is_removed_only_when_distinct_from_real_loads(self):
  argv=['/usr/bin/otool','-arch','arm64','-L','/private/linker/lib.dylib']
  raw='lib:\n\t@rpath/lib.dylib (compatibility version 1, current version 1)\n\t/usr/lib/libSystem.B.dylib (compatibility version 1, current version 1)\n'
  with patch.object(m,'macho',side_effect=[(['@rpath/lib.dylib','/usr/lib/libSystem.B.dylib'],[]),(['/usr/lib/libSystem.B.dylib'],[])]):
   self.assertNotIn('@rpath/lib.dylib',m.linker_loads(argv,raw))
  dup=raw.replace('\t/usr/lib/libSystem.B.dylib','\t@rpath/lib.dylib')
  with patch.object(m,'macho',side_effect=[(['@rpath/lib.dylib','@rpath/lib.dylib'],[]),(['@rpath/lib.dylib'],[])]),self.assertRaises(AssertionError):m.linker_loads(argv,dup)
 def test_actual_otool_tokens_must_equal_frozen_macho(self):
  argv=['/usr/bin/otool','-arch','arm64','-L','/private/linker/lib.dylib']
  with patch.object(m,'macho',side_effect=[(['/usr/lib/libSystem.B.dylib'],[]),(['/usr/lib/libSystem.B.dylib'],[])]),self.assertRaises(AssertionError):m.linker_loads(argv,'lib:\n\t/private/foreign.dylib (compatibility version 1, current version 1)\n')
if __name__=='__main__':unittest.main()
