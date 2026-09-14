import struct
import subprocess
import sys
import unittest
from pathlib import Path
import attribute_generated_sample as a
import summarize_owned_sample as s

class Contracts(unittest.TestCase):
    def test_bridge_option_is_bound_to_exact_command(self):
        plan=dict(jit_tree_bridge=True,jit_resumable_calls=True,dump_code=True)
        cmd=['--jit-tree-bridge','--jit-resumable-calls']
        self.assertTrue(s.runtime_options(plan,[cmd])['jit_tree_bridge'])
        for bad in [cmd[:1],cmd[1:]]:
            with self.assertRaises(RuntimeError):s.runtime_options(plan,[bad])
        for bad in [dict(plan,jit_resumable_calls=False),dict(plan,jit_tree_bridge='yes'),dict(plan,jit_operation_map=True)]:
            with self.assertRaises(RuntimeError):s.runtime_options(bad,[cmd])

    def test_tree_dump_requires_explicit_compatible_bridge(self):
        dump=dict(resumable_calls=True,ranges=[dict(kind='native_tree')])
        cmd=['--jit-resumable-calls','--jit-tree-bridge']
        self.assertTrue(a.dump_options(dump,cmd))
        for bad in [cmd[:1],cmd+['--jit-operation-map'],cmd+['--jit-native-calls']]:
            with self.assertRaises(RuntimeError):a.dump_options(dump,bad)
        with self.assertRaises(RuntimeError):a.dump_options(dict(dump,resumable_calls=False),cmd[1:])

    def classify(self,words,kinds):
        code=struct.pack('<'+'I'*len(words),*words)
        return a.classify_ranges(code,[dict(offset=i*4,end=(i+1)*4,kind=k) for i,k in enumerate(kinds)],True)[0]

    def test_x20_is_not_a_tree_descriptor(self):
        word=0xf9400289
        self.assertEqual(self.classify([word,word],['resumable_call','native_tree']),
            ['frame_descriptor_load_store','other_generated'])

    def test_budget_debits_require_tree_and_exact_register_operands(self):
        sub=0xd10002d6
        words=[sub|(1<<10),sub|(1024<<10),sub,sub|(1025<<10),0xd10006d5,sub|(1<<10)]
        classes=self.classify(words,['native_tree']*5+['resumable_region'])
        self.assertEqual(classes[:2],['tree_register_budget_debit']*2)
        self.assertEqual(classes[2:],['other_generated']*4)

    def test_cursor_offsets_are_separate_from_register_storage(self):
        words=[0xf9400269|(48//8<<10),0xf9000269|(240//8<<10),0xf9400009]
        self.assertEqual(self.classify(words,['native_tree']*3),
            ['cursor_load_store:call_count','cursor_load_store:tree_depth','direct_register_array_load'])

    def test_bulk_clear_in_tree_and_sequence_boundaries(self):
        code=struct.pack('<'+'I'*len(a.ZERO_BULK),*a.ZERO_BULK)
        ranges=[dict(offset=0,end=len(code),kind='native_tree')]
        classes,counts=a.classify_ranges(code,ranges,True)
        self.assertEqual(counts['native_zero_bulk'],1)
        self.assertEqual(classes[:len(a.ZERO_BULK_PREFIX)],['native_zero_bulk']*len(a.ZERO_BULK_PREFIX))
        split=[dict(offset=0,end=4,kind='native_tree'),dict(offset=4,end=len(code),kind='native_tree')]
        self.assertNotIn('native_zero_bulk',a.classify_ranges(code,split,True)[1])
        for bad in [ranges[:-1],[dict(offset=4,end=len(code),kind='native_tree')],[dict(offset=0,end=len(code)+4,kind='native_tree')]]:
            with self.assertRaises(RuntimeError):a.classify_ranges(code,bad,True)

    def test_sampler_rejects_invalid_bridge_flags_before_opening_artifact(self):
        common=[sys.executable,str(Path(__file__).with_name('sample_owned_vm.py')),'--tool-key','missing',
            '--artifact','missing','--artifact-sha256','missing','--run-id','must-not-start']
        for flags,message in [(['--jit-tree-bridge'],'requires --jit-resumable-calls'),
            (['--jit-tree-bridge','--jit-resumable-calls','--jit-operation-map','--dump-code'],'requires --dump-code and ordinary/resumable execution')]:
            result=subprocess.run(common+flags,capture_output=True,text=True)
            self.assertEqual(result.returncode,2);self.assertIn(message,result.stderr)

if __name__=='__main__':unittest.main()
