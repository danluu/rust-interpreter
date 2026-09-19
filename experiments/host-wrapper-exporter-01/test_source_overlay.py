"""Owned filesystem controls for source238 overlay admission; no tool processes."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('_tested_host_exporter_common',HERE/'common.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,sort_keys=True)+'\n')


class Overlay(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.R=self.root/'root';self.X=self.root/'x'
        self.X.mkdir();self.R.mkdir();self.retained=self.root/'retained';self.retained.mkdir()
        self.names=['crates/mir-export/src/'+n for n in
                    ('host_proc_macro.rs','wrapper_route.rs','wrapper_main.rs','main.rs')]
        self.names += ['crates/mir-export/tests/compiler_roles.rs']
        self.names += ['unchanged/%03d.rs'%i for i in range(233)]
        sizes=[2150761//238]*238;sizes[-1]+=2150761-sum(sizes)
        rows={}
        for index,(name,size) in enumerate(zip(self.names,sizes,strict=True)):
            p=self.retained/str(index);p.write_bytes(bytes([65+index%26])*size)
            rows[name]=dict(path=str(self.X/name),frozen_sha256=sha(p),frozen_bytes=size,
                            retained_snapshot=dict(path=str(p),sha256=sha(p)))
        self.census=dict(source_checkpoint=c.CHECKPOINT,files=238,logical_bytes=2150761,
                        all_exact_git_blobs_and_retained_snapshots_match=True,rows=rows)
        self.cp=self.root/'census.json';write(self.cp,self.census)
        self.overlay=dict(policy='host-wrapper-exporter-source-overlay-v1',
                          baseline_census=dict(path=str(self.cp),sha256=sha(self.cp)),
                          baseline_files=238,baseline_checkpoint=c.CHECKPOINT,files={})
        for i,name in enumerate(self.names[:5]):
            p=self.R/'experiments/host-wrapper-opt-01'/name;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes(('new host source %d\n'%i).encode())
            self.overlay['files'][name]=dict(original_sha256=rows[name]['frozen_sha256'],
                                            path=str(p),sha256=sha(p),bytes=p.stat().st_size)
        self.op=self.root/'overlay.json';self.prefix=self.X/'new-prefix';self.target=self.X/'new-target'
        self.patch=patch.multiple(c,ROOT=self.R,X=self.X,CENSUS=self.cp,OVERLAY=self.op,
                                  PREFIX=self.prefix,TARGET=self.target,PINS={})
        self.patch.start();self.addCleanup(self.patch.stop);self.seal()

    def seal(self):
        write(self.op,self.overlay);c.PINS.update({str(self.cp):sha(self.cp),str(self.op):sha(self.op)})

    def test_complete_238_independent_copies_only_five_changed(self):
        before={n:sha(Path(v['retained_snapshot']['path'])) for n,v in self.census['rows'].items()}
        rows=c.source_rows();actual=c.materialize(rows)
        self.assertEqual(set(actual),set(self.names))
        changed={n for n,r in actual.items() if r['sha256']!=before[n]}
        self.assertEqual(changed,set(self.names[:5]))
        for n,r in actual.items():
            source=Path(rows[n]['retained_snapshot']['path'])
            self.assertNotEqual(r['identity'][:2],c.stamp(source)[:2])
            self.assertEqual(r['identity'][6],1)
        self.assertEqual(before,{n:sha(Path(v['retained_snapshot']['path'])) for n,v in self.census['rows'].items()})

    def test_wrong_original_hash_rejected(self):
        self.overlay['files'][self.names[0]]['original_sha256']='0'*64;self.seal()
        with self.assertRaisesRegex(RuntimeError,'qualified source238 donor'):c.source_rows()
        self.assertFalse(self.prefix.exists())

    def test_original_snapshot_change_rejected_before_copy(self):
        Path(self.census['rows'][self.names[0]]['retained_snapshot']['path']).write_bytes(b'changed')
        with self.assertRaisesRegex(RuntimeError,'SHA differs'):c.source_rows()
        self.assertFalse(self.prefix.exists())

    def test_missing_or_extra_replacement_rejected(self):
        old=self.overlay['files'].pop(self.names[0]);self.seal()
        with self.assertRaisesRegex(RuntimeError,'overlay required'):c.source_rows()
        self.overlay['files'][self.names[0]]=old
        self.overlay['files'][self.names[5]]=old;self.seal()
        with self.assertRaisesRegex(RuntimeError,'overlay required'):c.source_rows()

    def test_external_replacement_route_rejected(self):
        p=self.root/'outside.rs';p.write_bytes(b'not the selected source')
        row=self.overlay['files'][self.names[0]];row.update(path=str(p),sha256=sha(p),bytes=p.stat().st_size);self.seal()
        with self.assertRaisesRegex(RuntimeError,'qualified source238 donor'):c.source_rows()

    def test_replacement_symlink_rejected(self):
        row=self.overlay['files'][self.names[0]];p=Path(row['path']);data=p.read_bytes();p.unlink()
        destination=self.root/'elsewhere.rs';destination.write_bytes(data);p.symlink_to(destination)
        with self.assertRaisesRegex(RuntimeError,'ordinary canonical input'):c.source_rows()

    def test_replacement_size_and_bool_rejected(self):
        row=self.overlay['files'][self.names[0]]
        for size in (True,999999):
            row['bytes']=size;self.seal()
            with self.assertRaisesRegex(RuntimeError,'length differs'):c.source_rows()

    def test_changed_unselected_source_rejects_before_prefix_write(self):
        rows=c.source_rows();Path(rows[self.names[-1]]['retained_snapshot']['path']).write_bytes(b'changed')
        with self.assertRaisesRegex(RuntimeError,'SHA differs'):c.materialize(rows)
        self.assertFalse(self.prefix.exists())


if __name__=='__main__':unittest.main(verbosity=2)
