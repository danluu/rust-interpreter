"""Synthetic allocation/race controls; no child process or compiler execution."""
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import bounded_command_v2 as b


class AllocationControls(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='hir-options-budget-control-')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        self.namespace=self.root/'namespace'; self.namespace.mkdir()
        self.evidence=self.root/'evidence'; self.evidence.mkdir()
        self.addCleanup(patch.stopall)
        patch.object(b,'NAMESPACE',self.namespace).start()
        patch.object(b,'EVIDENCE',self.evidence).start()

    def test_directory_blocks_hardlinks_and_external_symlink(self):
        directory=self.namespace/'child'; directory.mkdir()
        file=directory/'one'; file.write_bytes(b'x'*8192)
        os.link(file,directory/'two')
        external=self.root/'external';external.mkdir();(external/'large').write_bytes(b'y'*65536)
        link=self.namespace/'link';link.symlink_to(external,target_is_directory=True)
        expected=sum(p.lstat().st_blocks*512 for p in [self.namespace,directory,file,link])
        observed=b.allocated(self.namespace)
        self.assertEqual(observed['bytes'],expected)
        self.assertEqual(observed['raced_entries'],0)

    def test_vanished_entry_is_recorded_and_scan_continues(self):
        real_scan=os.scandir
        file=self.namespace/'keep';file.write_bytes(b'z'*4096)
        class Gone:
            def stat(self,**kwargs):raise FileNotFoundError('concurrent unlink')
        class Racy:
            def __init__(self,fd):self.actual=real_scan(fd)
            def __enter__(self):return iter([Gone(),*self.actual])
            def __exit__(self,*args):self.actual.close()
        with patch.object(b.os,'scandir',Racy):
            row=b.allocated(self.namespace)
        self.assertEqual(row['raced_entries'],1)
        self.assertEqual(row['bytes'],sum(p.stat().st_blocks*512 for p in [self.namespace,file]))

    def test_removed_directory_during_scandir_is_a_recorded_race(self):
        with patch.object(b.os,'scandir',side_effect=FileNotFoundError('directory removed after open')):
            row=b.allocated(self.namespace)
        self.assertEqual(row['raced_entries'],1)
        self.assertEqual(row['bytes'],self.namespace.stat().st_blocks*512)

    def test_exact_budget_boundaries(self):
        row=dict(free_bytes=9*b.GIB,namespace_allocated_bytes=14*b.GIB,
            evidence_allocated_bytes=256*2**20,allocation_errors=[])
        self.assertIsNone(b.rejection(row))
        self.assertIn('free space',b.rejection(dict(row,free_bytes=9*b.GIB-1)))
        self.assertIn('14 GiB',b.rejection(dict(row,namespace_allocated_bytes=14*b.GIB+1)))
        self.assertIn('256 MiB',b.rejection(dict(row,evidence_allocated_bytes=256*2**20+1)))

    def test_allocation_error_retains_independent_free_space_checks(self):
        values=[SimpleNamespace(free=10*b.GIB),SimpleNamespace(free=9*b.GIB+1)]
        with (patch.object(b,'allocated',side_effect=PermissionError('unexpected unreadable directory')),
              patch.object(b.shutil,'disk_usage',side_effect=values) as disk):
            row=b.sample()
        self.assertEqual(disk.call_count,2)
        self.assertEqual(row['free_bytes'],9*b.GIB+1)
        self.assertEqual(len(row['allocation_errors']),2)
        self.assertIn('inventory unavailable',b.rejection(row))
        self.assertIn('free space',b.rejection(dict(row,free_bytes=9*b.GIB-1)))


if __name__=='__main__':
    unittest.main(verbosity=2)
