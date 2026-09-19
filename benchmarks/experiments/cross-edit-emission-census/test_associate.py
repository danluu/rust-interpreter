import copy,unittest
from associate import MASKS,associate

def fixture():
    rows=[dict(function=i,previous_name=str(i),previous_operations=7,previous_sha256='a'*64,
        **{key:True for key in MASKS}) for i in range(2)]
    metadata=[dict(function=i,name=str(i),bytecode_operations=7,ordinary_prepared=True,
        ordinary_native_entries=1 if i==0 else 0) for i in range(2)]
    workers=[dict(worker=w,observation=dict(functions=copy.deepcopy(metadata),trace=dict(rows=[
        [0,'ordinary_emission',dict(nanos=10+w)],
        [0,'ordinary_regions',dict(nanos=5+w)],
        [1,'ordinary_emission',dict(nanos=1000+w)]]))) for w in range(2)]
    return dict(functions=rows),workers

class Association(unittest.TestCase):
    def test_owner_intervals_stay_separate_and_no_entry_work_is_excluded(self):
        rows=associate(*fixture())
        self.assertEqual([r['candidates'][MASKS[0]]['original_phase_ns']['ordinary_emission'] for r in rows],[10,11])
        self.assertEqual([r['no_published_entry_phase_ns']['ordinary_emission'] for r in rows],[1000,1001])
        self.assertEqual([r['candidates'][MASKS[0]]['functions'] for r in rows],[1,1])
        self.assertNotIn('saved_seconds',rows[0])

    def test_original_names_counts_and_complete_identity_are_required(self):
        for key,value in [('previous_name','different'),('previous_operations',8),('previous_sha256',None)]:
            row,workers=fixture();row['functions'][0][key]=value
            with self.assertRaises(AssertionError):associate(row,workers)
        row,workers=fixture();row['functions']=row['functions'][:1]
        with self.assertRaises(KeyError):associate(row,workers)

    def test_duplicate_owner_function_or_interval_never_inflates_totals(self):
        for mutate in [lambda r,w:w.append(w[0]),lambda r,w:r['functions'].append(r['functions'][0]),
            lambda r,w:w[0]['observation']['functions'].append(w[0]['observation']['functions'][0]),
            lambda r,w:w[0]['observation']['trace']['rows'].append(w[0]['observation']['trace']['rows'][0])]:
            row,workers=fixture();mutate(row,workers)
            with self.assertRaises(AssertionError):associate(row,workers)

    def test_false_or_invalid_masks_and_unprepared_entries_are_not_candidates(self):
        row,workers=fixture();row['functions'][0][MASKS[0]]=False
        self.assertEqual(associate(row,workers)[0]['candidates'][MASKS[0]]['functions'],0)
        row['functions'][0][MASKS[0]]=1
        with self.assertRaises(AssertionError):associate(row,workers)
        row,workers=fixture();workers[0]['observation']['functions'][0]['ordinary_prepared']=False
        with self.assertRaises(AssertionError):associate(row,workers)

if __name__=='__main__':unittest.main()
