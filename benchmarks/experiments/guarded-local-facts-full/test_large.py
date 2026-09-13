import collections
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

path=Path(__file__).with_name('large_compare.py')
spec=importlib.util.spec_from_file_location('memory_lookup_large_comparison',path)
comparison=importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)


def rows(candidate=.97,duplicate=1.01):
    result=[]
    for cycle in range(3):
        for state in range(1,6):
            for mode in comparison.MODES:
                ratio=candidate if mode=='candidate' else duplicate if mode=='duplicate' else 1
                result.append(dict(cycle=cycle,state=state,mode=mode,source_sha256=str(state),
                    seconds=ratio,cpu=dict(total_seconds=ratio)))
    return result


class ComparisonTests(unittest.TestCase):
    def test_custom_order_balances_positions_and_reverses_adjacent_pairs(self):
        orders=[comparison.order(c,s) for c in range(3) for s in range(1,6)]
        for position in range(3):
            self.assertEqual(collections.Counter(o[position] for o in orders),dict.fromkeys(comparison.CUSTOM,5))
        pairs=collections.Counter((o[i],o[i+1]) for o in orders[:6] for i in range(2))
        self.assertEqual(len(pairs),6)
        self.assertEqual(set(pairs.values()),{2})

    def test_guard_keeps_both_cpu_and_wall_margins(self):
        self.assertTrue(comparison.assessment(rows(candidate=1.02, duplicate=1.02),'nushell')['gate_passed'])
        self.assertFalse(comparison.assessment(rows(candidate=1.04, duplicate=1.02),'nushell')['gate_passed'])
        cpu_rows=rows(candidate=.90)
        for row in cpu_rows:
            if row['mode']=='candidate':row['cpu']['total_seconds']=1.05
        self.assertFalse(comparison.assessment(cpu_rows,'nushell')['gate_passed'])
        self.assertTrue(comparison.assessment(rows(candidate=.94, duplicate=1.06),'nushell')['gate_passed'])

    def test_assessment_rejects_missing_duplicate_and_mixed_source_pairs(self):
        original=rows()
        for broken in [original[:-1],original+[copy.deepcopy(original[0])]]:
            with self.assertRaises(AssertionError):comparison.assessment(broken,'nushell')
        original[0]['source_sha256']='different'
        with self.assertRaises(AssertionError):comparison.assessment(original,'nushell')

    def test_native_parser_requires_original_assertion_failure(self):
        names=['tests::a','tests::b']
        success='test tests::b ... ok\ntest tests::a ... ok\ntest result: ok. 2 passed; 0 failed; 0 ignored;'
        failure='test tests::a ... FAILED\ntest tests::b ... ok\ntest result: FAILED. 1 passed; 1 failed; 0 ignored;'
        self.assertEqual(comparison.native_outcomes(success,names,True),[(n,'passed') for n in names])
        self.assertEqual(comparison.native_outcomes(failure,names,False),[('tests::a','failed'),('tests::b','passed')])
        for text in [success,'compiler failed',failure.replace('tests::a','tests::unrelated')]:
            with self.assertRaises(AssertionError):comparison.native_outcomes(text,names,False)
        for wrapped in ['/path with spaces/report.html','`/path with spaces/report.html`','"/path with spaces/report.html"']:
            self.assertEqual(comparison.timing_path('Timing report saved to '+wrapped),'/path with spaces/report.html')
        for text in ['', 'Timing report saved to /a.html\nTiming report saved to /b.html']:
            with self.assertRaises(AssertionError):comparison.timing_path(text)

    def test_fingerprints_track_directory_and_dangling_link_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'dir').mkdir();link=root/'link';link.symlink_to('dir')
            a=comparison.fingerprint(link);self.assertEqual(a['kind'],'symlink')
            link.unlink();link.symlink_to('missing');b=comparison.fingerprint(link)
            self.assertEqual(b['kind'],'symlink');self.assertNotEqual(a,b)
            link.unlink();link.write_text('missing');self.assertNotEqual(b,comparison.fingerprint(link))


    def test_both_mandatory_guards_use_the_same_five_percent_sum(self):
        for case in ['nushell','rg-aot']:
            self.assertTrue(comparison.assessment(rows(candidate=1.039),case)['gate_passed'])
            self.assertFalse(comparison.assessment(rows(candidate=1.041),case)['gate_passed'])
            self.assertFalse(comparison.assessment(rows(candidate=1,duplicate=1.051),case)['gate_passed'])

    def test_distinct_runtime_composition_uses_the_recorded_pins(self):
        self.assertNotEqual(comparison.BASELINE,comparison.CANDIDATE)
        self.assertEqual(comparison.BASELINE,'b08f39e282ece70b125d23cf1a9b3a22cef5cfd4c03bf5b8cae023701f9b21ff')
        self.assertEqual(comparison.CANDIDATE,'317a0bf16da0f15f562ab457408ab321b12f25211f8169ec8bcd8205a3cb7dfb')
        self.assertEqual(set(comparison.PINS),{'pgrust','rg-aot','nushell'})


if __name__=='__main__':unittest.main()
