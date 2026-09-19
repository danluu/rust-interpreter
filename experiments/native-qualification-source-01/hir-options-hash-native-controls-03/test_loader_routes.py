"""Focused tiny filesystem and saved-route controls; no compiler/provider calls."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest

import observations as observed

A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
PLAN=A/'experiments/hir-options-hash-native-controls-02/plan.json'
DIAGNOSIS=O/'.work/native02-loader-edge-diagnosis-01.json'


def command(kind,text):
    start=24 if kind==0xC else 12
    value=text.encode()+b'\0';width=(start+len(value)+7)//8*8
    return struct.pack('<III',kind,width,start)+bytes(start-12)+value+bytes(width-start-len(value))


class LoaderRoutes(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve(strict=True)
        self.runtime=self.root/'E2';self.lib=self.runtime/'lib';self.lib.mkdir(parents=True)
        (self.runtime/'bin').mkdir()
        self.driver=self.lib/'librustc_driver-abcd.dylib';self.driver.write_bytes(b'fixture driver')
        self.llvm=self.lib/'libLLVM.dylib';self.llvm.write_bytes(b'fixture llvm')
        self.stock=self.root/'stock'
        self.loads=['@rpath/'+self.driver.name,'/usr/lib/libSystem.B.dylib','@rpath/'+self.llvm.name]
        self.rows=[self.row(self.runtime/'bin/../lib'/p.name,p) for p in [self.driver,self.llvm]]
        self.rows.append(self.row(self.lib/'../lib'/self.llvm.name,self.llvm))

    def row(self,logical,resolved):
        return dict(logical=str(logical),resolved=str(resolved),bytes=resolved.stat().st_size,
                    sha256=hashlib.sha256(resolved.read_bytes()).hexdigest())

    def raw(self,loads):
        return (str(self.stock)+':\n'+''.join('\t'+token+' (compatibility version 0.0.0, current version 0.0.0)\n' for token in loads)).encode()

    def check(self,*,loads=None,rows=None,driver=None,runtime=None,raw=None):
        loads=self.loads if loads is None else loads
        chunks=[command(0x8000001C,str(self.lib))]+[command(0xC,p) for p in loads]
        body=b''.join(chunks);data=struct.pack('<8I',0xFEEDFACF,0x100000C,0,2,len(chunks),len(body),0,0)+body
        return observed.stock_macho(data,self.raw(loads) if raw is None else raw,stock=self.stock,
            driver=self.driver if driver is None else driver,runtime_lib=self.lib if runtime is None else runtime,
            qualified_private=self.rows if rows is None else rows)

    def test_saved_actual_alias_shapes_accept_canonical_driver_and_llvm(self):
        raw=PLAN.read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),'a4cf3862479fc357a75a0577fdf3b60bb2b8ba0ced57434a31cd02c9e343c2c4')
        diagnosis=DIAGNOSIS.read_bytes();self.assertEqual(hashlib.sha256(diagnosis).hexdigest(),'dc77f0b49bb29d3f37635ab5f159e3a2cab21b38480c917eb8d443f27774482b')
        plan=json.loads(raw);saved=json.loads(diagnosis);actual=plan['runtime_closure']['libraries']
        base=Path(plan['runtime_driver']['path']).parent.parent
        shapes=[str(Path(row['logical']).relative_to(base).parent) for row in actual]
        self.assertEqual(shapes,['bin/../lib','bin/../lib','lib/../lib'])
        self.assertEqual(saved['actual_loads'],plan['runtime_closure']['nodes']['$CARGO']['dependencies'])
        self.assertEqual([row['literal_key_present'] for row in saved['private_edges']],[False,False])
        # Replay the exact saved alias structure on tiny owned providers only.
        targets={Path(row['resolved']).name:(self.llvm if Path(row['resolved']).name=='libLLVM.dylib' else self.driver) for row in actual}
        rows=[self.row(self.runtime/shape/targets[Path(row['resolved']).name].name,targets[Path(row['resolved']).name]) for shape,row in zip(shapes,actual,strict=True)]
        result=self.check(rows=rows)
        self.assertEqual(result['direct_private'],[str(self.driver),str(self.llvm)])
        self.assertEqual(result['loads'],self.loads)

    def test_canonical_identity_rows_remain_accepted(self):
        rows=[self.row(p,p) for p in [self.driver,self.llvm]]
        result=self.check(rows=rows)
        self.assertEqual(result['direct_private'],[str(self.driver),str(self.llvm)])

    def test_duplicate_logical_rows_reject_before_mapping(self):
        for extra in [self.rows[0],dict(self.rows[0],resolved=str(self.llvm))]:
            with self.subTest(extra=extra),self.assertRaisesRegex(ValueError,'duplicate qualified logical route'):
                self.check(rows=self.rows+[extra])

    def test_same_resolved_provider_requires_identical_byte_identity(self):
        for change in [dict(bytes=123),dict(sha256='0'*64),dict(bytes=True)]:
            rows=[dict(row) for row in self.rows];rows[-1].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):self.check(rows=rows)

    def test_forged_logical_or_canonical_mapping_rejects(self):
        forged=[self.row(self.driver,self.llvm)]
        for rows in [self.rows+forged,[dict(self.rows[0],resolved=str(self.llvm)),*self.rows[1:]]]:
            with self.subTest(rows=rows),self.assertRaises(ValueError):self.check(rows=rows)

    def test_foreign_unadmitted_alias_or_missing_driver_rejects(self):
        alias=self.lib/'libalias.dylib';alias.symlink_to(self.driver)
        foreign=self.root/'libforeign.dylib';foreign.write_bytes(b'foreign')
        for loads,rows in [(self.loads+['@rpath/libalias.dylib'],self.rows),
                           (self.loads+[str(foreign)],self.rows),
                           (self.loads,self.rows+[self.row(foreign,foreign)]),
                           (self.loads[1:],self.rows),
                           (self.loads,self.rows[1:])]:
            with self.subTest(loads=loads,rows=rows),self.assertRaises(ValueError):self.check(loads=loads,rows=rows)

    def test_unsafe_tokens_cannot_be_canonicalized_into_admission(self):
        for token in ['@rpath/../lib/'+self.driver.name,'@rpath//'+self.driver.name,
                      '@rpath/','@loader_path/'+self.driver.name,str(self.lib)+'/../lib/'+self.driver.name,
                      str(self.lib)+'//'+self.driver.name,'/usr/lib/../../foreign.dylib','/usr/lib//libSystem.B.dylib']:
            with self.subTest(token=token),self.assertRaises(ValueError):self.check(loads=[token,*self.loads[1:]])

    def test_wrong_driver_or_runtime_library_route_rejects(self):
        other=self.root/'foreign';other.mkdir()
        for kw in [dict(driver=self.llvm),dict(runtime=other),dict(runtime=self.runtime/'bin/../lib'),dict(driver=self.lib/'missing')]:
            with self.subTest(kw=kw),self.assertRaises(ValueError):self.check(**kw)

    def test_binary_and_complete_otool_order_remain_equal(self):
        for raw in [self.raw(list(reversed(self.loads))),self.raw(self.loads)+b'unknown diagnostic\n',
                    self.raw(self.loads).replace((str(self.stock)+':').encode(),b'/foreign:')]:
            with self.subTest(raw=raw),self.assertRaises(ValueError):self.check(raw=raw)

if __name__=='__main__':unittest.main(verbosity=2)
