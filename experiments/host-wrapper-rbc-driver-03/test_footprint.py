"""Deterministic owned-output observation tests; no process/provider calls."""
import errno
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('_footprint_support',HERE/'support.py')
support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support)


class FootprintTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='host-wrapper-footprint-')
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve()
        self.work=self.base/'work';self.out=self.base/'out';self.execution=self.base/'execution'
        for p in (self.work,self.out,self.execution):p.mkdir()
        for name,value in [('WORK',self.work),('OUT',self.out),('EXECUTION',self.execution)]:
            context=patch.object(support,name,value);context.start();self.addCleanup(context.stop)

    def test_regular_bytes_and_allocated_blocks_are_counted_in_all_owned_roots(self):
        files=[]
        for index,root in enumerate((self.work,self.out,self.execution)):
            p=root/'data';p.write_bytes(b'x'*(index+1));files.append(p)
        expected=dict(logical_bytes=6,allocated_bytes=sum(p.stat().st_blocks*512 for p in files),entries=3)
        self.assertEqual(support.footprint(),expected)
        self.assertEqual(support.footprint(active=True),expected)

    def disappearing_walk(self,*args,**kwargs):
        if Path(args[0])==self.work:
            gone=self.work/'atomic-write';gone.write_bytes(b'transient');gone.unlink()
            yield str(self.work),[],['atomic-write','kept']

    def test_active_snapshot_tolerates_an_entry_removed_after_enumeration(self):
        kept=self.work/'kept';kept.write_bytes(b'kept')
        with patch.object(support.os,'walk',side_effect=self.disappearing_walk):
            actual=support.footprint(active=True)
        self.assertEqual(actual,dict(logical_bytes=4,allocated_bytes=kept.stat().st_blocks*512,entries=2))

    def test_default_boundary_and_final_snapshot_rejects_the_same_disappearance(self):
        (self.work/'kept').write_bytes(b'kept')
        with patch.object(support.os,'walk',side_effect=self.disappearing_walk):
            with self.assertRaisesRegex(RuntimeError,'entry lstat.*atomic-write.*FileNotFoundError'):
                support.footprint()

    def walk_failure(self,number):
        def walk(root,*,followlinks,onerror):
            if Path(root)==self.work:onerror(OSError(number,'injected walk error',str(self.work/'vanished-dir')))
            return iter(())
        return walk

    def test_only_active_traversal_tolerates_missing_descendants(self):
        with patch.object(support.os,'walk',side_effect=self.walk_failure(errno.ENOENT)):
            self.assertEqual(support.footprint(active=True),dict(logical_bytes=0,allocated_bytes=0,entries=0))
            with self.assertRaisesRegex(RuntimeError,'traversal.*vanished-dir.*FileNotFoundError'):
                support.footprint()

    def test_root_disappearance_or_unscoped_missing_traversal_is_never_ignored(self):
        for active in (False,True):
            def removed_root(root,*,followlinks,onerror):
                if Path(root)==self.work:
                    self.work.rmdir()
                    onerror(FileNotFoundError(errno.ENOENT,'root vanished',str(root)))
                return iter(())
            with self.subTest(active=active),patch.object(support.os,'walk',side_effect=removed_root):
                with self.assertRaisesRegex(RuntimeError,'traversal.*work.*root vanished'):
                    support.footprint(active=active)
            self.work.mkdir()
        for name in (None,str(self.base/'outside'),'relative',str(self.work/'..'/'outside')):
            def unscoped(root,*,followlinks,onerror):
                if Path(root)==self.work:onerror(FileNotFoundError(errno.ENOENT,'unscoped missing entry',name))
                return iter(())
            with self.subTest(filename=name),patch.object(support.os,'walk',side_effect=unscoped):
                with self.assertRaisesRegex(RuntimeError,'traversal.*unscoped missing entry'):
                    support.footprint(active=True)

    def test_unexpected_entry_errors_preserve_path_and_fail_both_modes(self):
        target=self.work/'denied';target.write_bytes(b'x');original=Path.lstat
        for number in (errno.EACCES,errno.EIO,errno.ENOTDIR):
            for active in (False,True):
                def fail(path,*args,**kwargs):
                    if path==target:raise OSError(number,'injected entry error',str(path))
                    return original(path,*args,**kwargs)
                with self.subTest(errno=number,active=active),patch.object(Path,'lstat',fail):
                    with self.assertRaisesRegex(RuntimeError,'entry lstat.*denied.*injected entry error'):
                        support.footprint(active=active)

    def test_unexpected_traversal_errors_fail_both_modes(self):
        for number in (errno.EACCES,errno.EIO,errno.ENOTDIR):
            for active in (False,True):
                with self.subTest(errno=number,active=active),patch.object(support.os,'walk',side_effect=self.walk_failure(number)):
                    with self.assertRaisesRegex(RuntimeError,'traversal.*vanished-dir.*injected walk error'):
                        support.footprint(active=active)

    def test_missing_owned_root_is_never_a_transient_entry(self):
        self.out.rmdir()
        for active in (False,True):
            with self.subTest(active=active),self.assertRaisesRegex(RuntimeError,'root lstat.*out.*FileNotFoundError'):
                support.footprint(active=active)

    def test_links_remain_rejected_during_live_and_final_snapshots(self):
        (self.work/'link').symlink_to(self.out,target_is_directory=True)
        for active in (False,True):
            with self.subTest(active=active),self.assertRaisesRegex(RuntimeError,'unexpected owned file kind.*link'):
                support.footprint(active=active)

    def test_entry_limit_is_enforced_without_allocating_large_outputs(self):
        actual=self.work/'sample';actual.write_bytes(b'x');saved=actual.lstat();original=Path.lstat
        def observation(path,*args,**kwargs):
            return saved if path.parent==self.work else original(path,*args,**kwargs)
        for count in (65536,65537):
            def walk(root,**kwargs):
                return iter([(str(self.work),[],[f'file-{i}' for i in range(count)])]) if Path(root)==self.work else iter(())
            for active in (False,True):
                with self.subTest(count=count,active=active),patch.object(support.os,'walk',side_effect=walk),patch.object(Path,'lstat',observation):
                    if count==65536:self.assertEqual(support.footprint(active=active)['entries'],count)
                    else:
                        with self.assertRaisesRegex(RuntimeError,'owned entry bound65536 exceeded'):
                            support.footprint(active=active)


if __name__=='__main__':unittest.main(verbosity=2)
