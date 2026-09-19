"""Pure parser controls plus two exact retained, already-closed dyld streams."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from dyld_parser import loaded_libraries

PID=71
DRIVER='/owned/lib/librustc_driver-test.dylib'
OTHER='/owned/lib/libLLVM.dylib'
SYSTEM='/usr/lib/libSystem.B.dylib'
UUID='01234567-89AB-CDEF-0123-456789ABCDEF'


def require(ok,message):
    if not ok:raise RuntimeError(message)


def load(path, *, pid=PID, uuid=UUID):
    return f'dyld[{pid}]: <{uuid}> {path}\n'.encode()


def move(name, before='loaded', after='delayed', *, pid=PID):
    return f'dyld[{pid}]: move {before} to {after}: {name}\n'.encode()


def parse(raw, *, pid=PID, allowed=None, driver=DRIVER):
    return loaded_libraries(SimpleNamespace(require=require),raw,pid,
                            {DRIVER,OTHER} if allowed is None else allowed,driver)


class DyldParserTests(unittest.TestCase):
    def test_original_loads_preserve_uuid_pid_and_bytes(self):
        raw=load(DRIVER)+load(SYSTEM)
        value=parse(raw)
        self.assertEqual(value['loaded'],[DRIVER,SYSTEM]);self.assertEqual(value['delayed'],[])
        self.assertEqual(value['images'][0]['uuid'],UUID)
        self.assertEqual(value['pid'],PID);self.assertEqual(value['raw_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(b''.join(bytes.fromhex(r['raw_hex']) for r in value['events']),raw)

    def test_delayed_non_driver_remains_retained_but_not_active(self):
        raw=load(DRIVER)+load(OTHER)+move('libLLVM.dylib')
        value=parse(raw)
        self.assertEqual(value['loaded'],[DRIVER]);self.assertEqual(value['delayed'],[OTHER])
        self.assertEqual(value['images'][1]['state'],'delayed')
        self.assertEqual(value['events'][-1]['path'],OTHER)

    def test_reverse_transition_reactivates_same_prior_image(self):
        raw=load(DRIVER)+move('librustc_driver-test.dylib')+move('librustc_driver-test.dylib','delayed','loaded')
        value=parse(raw)
        self.assertTrue(value['selected_driver_active']);self.assertEqual(value['loaded'],[DRIVER])
        self.assertEqual(len(value['images']),1);self.assertEqual(len(value['events']),3)
        self.assertEqual([r['start'] for r in value['events']],[0,len(load(DRIVER)),len(raw)-len(move('librustc_driver-test.dylib','delayed','loaded'))])

    def test_multiple_legal_state_cycles(self):
        raw=load(DRIVER)+load(OTHER)
        for _ in range(3):raw+=move('libLLVM.dylib')+move('libLLVM.dylib','delayed','loaded')
        self.assertEqual(parse(raw)['loaded'],[DRIVER,OTHER])

    def test_selected_driver_delayed_at_end_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'not active'):
            parse(load(DRIVER)+move('librustc_driver-test.dylib'))

    def test_missing_selected_driver_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'not active'):parse(load(SYSTEM))

    def test_unadmitted_initial_non_system_load_rejected_even_if_later_delayed(self):
        with self.assertRaisesRegex(RuntimeError,'unadmitted'):
            parse(load(DRIVER)+load('/foreign/unsafe.dylib')+move('unsafe.dylib'))

    def test_driver_must_be_explicitly_admitted(self):
        with self.assertRaisesRegex(RuntimeError,'admitted exact driver'):parse(load(DRIVER),allowed=set())

    def test_load_pid_mismatch_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'another process'):parse(load(DRIVER,pid=PID+1))

    def test_transition_pid_mismatch_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'another process'):
            parse(load(DRIVER)+load(OTHER)+move('libLLVM.dylib',pid=PID+1))

    def test_missing_prior_basename_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'missing or ambiguous'):
            parse(load(DRIVER)+move('unknown.dylib'))

    def test_transition_before_future_load_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'missing or ambiguous'):
            parse(load(DRIVER)+move('libLLVM.dylib')+load(OTHER))

    def test_ambiguous_prior_basename_rejected(self):
        alternate='/different/lib/libLLVM.dylib'
        with self.assertRaisesRegex(RuntimeError,'ambiguous'):
            parse(load(DRIVER)+load(OTHER)+load(alternate)+move('libLLVM.dylib'),allowed={DRIVER,OTHER,alternate})

    def test_duplicate_loaded_to_delayed_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'incompatible prior state'):
            parse(load(DRIVER)+load(OTHER)+move('libLLVM.dylib')*2)

    def test_delayed_to_loaded_without_delay_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'incompatible prior state'):
            parse(load(DRIVER)+load(OTHER)+move('libLLVM.dylib','delayed','loaded'))

    def test_duplicate_initial_path_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'duplicate'):parse(load(DRIVER)*2)

    def test_unknown_row_and_transition_direction_rejected(self):
        for suffix in (b'compiler warning\n',b'dyld[71]: unload: libLLVM.dylib\n',move('libLLVM.dylib','loaded','loaded')):
            with self.subTest(suffix=suffix),self.assertRaisesRegex(RuntimeError,'unrecognized'):
                parse(load(DRIVER)+load(OTHER)+suffix)

    def test_malformed_uuid_rejected(self):
        for uuid in ('-'*36,'0'*36,UUID[:-1]+'G'):
            with self.subTest(uuid=uuid),self.assertRaisesRegex(RuntimeError,'unrecognized'):
                parse(load(DRIVER,uuid=uuid))

    def test_transition_requires_basename_not_path(self):
        with self.assertRaisesRegex(RuntimeError,'unrecognized'):
            parse(load(DRIVER)+load(OTHER)+move(OTHER))

    def test_unterminated_crlf_and_empty_rows_rejected(self):
        for raw in (load(DRIVER)[:-1],load(DRIVER).replace(b'\n',b'\r\n'),load(DRIVER)+b'\n'):
            with self.subTest(raw=raw),self.assertRaises(RuntimeError):parse(raw)

    def test_invalid_utf8_and_nul_rejected(self):
        for raw in (load(DRIVER)+b'\xff\n',load(DRIVER)+move('bad\x00name')):
            with self.subTest(raw=raw),self.assertRaises(RuntimeError):parse(raw)

    def test_empty_stream_and_invalid_pid_types_rejected(self):
        with self.assertRaises(RuntimeError):parse(b'')
        for pid in (True,0,-1,'71'):
            with self.subTest(pid=pid),self.assertRaises(RuntimeError):parse(load(DRIVER),pid=pid)

    def test_same_basename_loads_without_transition_are_not_conflated(self):
        a='/owned/a/same.dylib';b='/owned/b/same.dylib'
        result=parse(load(DRIVER)+load(a)+load(b),allowed={DRIVER,a,b})
        self.assertEqual(result['loaded'],[DRIVER,a,b]);self.assertEqual(len(result['images']),3)

    def test_actual_closed_build_and_runtime_streams(self):
        root=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/.work/hir-options-hash-exporter-metadata-01/commands')
        cases=[('025','38d246a87b22ed9f64efc9a52dd1cc90bf8238bcefe7355287b2fe71d01b91c8',
                'fede29331aa274c15ac9c275c46820d36c7457af0c1603e0b4926467003a96a1',80505,
                Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/.work/hir-options-hash-compiler-01/source/build/aarch64-apple-darwin/stage0'),
                'librustc_driver-9ef202210fe39e05.dylib'),
               ('027','845591447242c62e2641508f5d19e1ef6808459bfd3d0b331277448dbcc96d13',
                '6494cf8a01a4bf0f78132918049819fbaf353164a86c557eca018d0ad90793d7',83850,
                Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918/.work/runtime-compilers/f031d981666f450f760ccf303dccba986053ec6b9a143a60f3d26680f9ac7c70/sysroot'),
                'librustc_driver-88dbe03d702a9b6c.dylib')]
        for index,raw_sha,receipt_sha,pid,sysroot,driver_name in cases:
            with self.subTest(index=index):
                raw=(root/index/'stderr').read_bytes();record_raw=(root/index/'receipt.json').read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(),raw_sha)
                self.assertEqual(hashlib.sha256(record_raw).hexdigest(),receipt_sha)
                record=json.loads(record_raw)
                self.assertEqual((record['pid'],record['status'],record['returncode']),(pid,'finished',0))
                self.assertEqual(record['stderr_sha256'],raw_sha)
                driver=str(sysroot/'lib'/driver_name)
                allowed={driver,str(sysroot/'bin/rustc'),str(sysroot/'lib/libLLVM.dylib')}
                result=parse(raw,pid=pid,allowed=allowed,driver=driver)
                self.assertEqual(len(result['images']),548);self.assertEqual(len(result['events']),705)
                self.assertEqual(len(result['loaded']),391);self.assertEqual(len(result['delayed']),157)
                self.assertIn(driver,result['loaded']);self.assertTrue(result['selected_driver_active'])
                self.assertEqual(b''.join(bytes.fromhex(row['raw_hex']) for row in result['events']),raw)


if __name__=='__main__':unittest.main(verbosity=2)
