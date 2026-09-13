import collections
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

path=Path(__file__).with_name('edit_compare.py')
spec=importlib.util.spec_from_file_location('toolchain_lookup_comparison',path)
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

    def test_gate_requires_gain_beyond_noise_and_keeps_cpu_guard(self):
        self.assertTrue(comparison.assessment(rows(),'pgrust')['gate_passed'])
        self.assertFalse(comparison.assessment(rows(candidate=.995),'pgrust')['gate_passed'])
        self.assertFalse(comparison.assessment(rows(duplicate=1.05),'pgrust')['gate_passed'])
        noisy_cpu=rows()
        for row in noisy_cpu:
            if row['mode']=='candidate':row['cpu']['total_seconds']=1.0001
        self.assertFalse(comparison.assessment(noisy_cpu,'pgrust')['gate_passed'])
        self.assertTrue(comparison.assessment(rows(candidate=1.04),'nushell')['gate_passed'])
        self.assertFalse(comparison.assessment(rows(candidate=1.06),'nushell')['gate_passed'])

    def test_assessment_rejects_missing_duplicate_and_mixed_source_pairs(self):
        original=rows()
        for broken in [original[:-1],original+[copy.deepcopy(original[0])]]:
            with self.assertRaises(AssertionError):comparison.assessment(broken,'pgrust')
        original[0]['source_sha256']='different'
        with self.assertRaises(AssertionError):comparison.assessment(original,'pgrust')

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


    def test_both_mandatory_guards_retain_the_noise_and_regression_limits(self):
        for case in ['nushell','rg-aot']:
            self.assertTrue(comparison.assessment(rows(candidate=1.04),case)['gate_passed'])
            self.assertFalse(comparison.assessment(rows(candidate=1.06),case)['gate_passed'])
            self.assertFalse(comparison.assessment(rows(duplicate=1.05),case)['gate_passed'])

    def test_control_and_candidate_use_identical_installed_tools(self):
        self.assertEqual(comparison.BASELINE,comparison.CANDIDATE)
        self.assertEqual(set(comparison.PINS),{'pgrust','rg-aot','nushell'})


if __name__=='__main__':unittest.main()
