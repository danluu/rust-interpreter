import copy
import unittest

import readmit


class AdmissionControls(unittest.TestCase):
    def test_device_transition_preserves_every_other_identity_field(self):
        old = dict(dev=11, ino=7, size=19, mode=33152, nlink=1, mtime_ns=2, ctime_ns=3)
        current = old | dict(dev=12)
        readmit.admit_identity(old, current, dict(historical_device=11, current_device=12))
        for field in set(old) - {'dev'}:
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                readmit.admit_identity(old, current | {field: current[field] + 1},
                                      dict(historical_device=11, current_device=12))
        self.assertEqual(old['dev'], 11)

    def test_unreviewed_device_is_rejected(self):
        with self.assertRaises(RuntimeError):
            readmit.admit_identity(dict(dev=11), dict(dev=13), dict(historical_device=11, current_device=12))

    def fixture(self):
        def record(path, device):
            return dict(path=path, sha256='a' * 64, size=10, identity=dict(dev=device, ino=5))
        files = {f'lib/item{i}': dict(sha256='a' * 64, size=10, mode=420) for i in range(333)}
        files[readmit.COPY['source_destination']] = dict(sha256=readmit.LLVM_SHA, size=10, mode=420)
        old = dict(files=files, stamp_hex='aa', runtime_source_commit='a' * 40,
                   build_compiler=record('/build', 11), runtime_driver=record('/driver', 11),
                   stamp=record('/stamp', 11), archives=[dict(file=record('/archive', 11), members=['member'])],
                   private=[dict(source=f'/private{i}', destination=f'lib/private{i}', tag='t',
                                 file=record(f'/private{i}', 11)) for i in range(256)])
        current = {r['path']: r | dict(identity=r['identity'] | dict(dev=12))
                   for r in [old['build_compiler'], old['runtime_driver'], old['stamp'], old['archives'][0]['file'],
                             *(r['file'] for r in old['private'])]}
        new = copy.deepcopy(old)
        new['files'][readmit.COPY['destination']] = dict(old['files'][readmit.COPY['source_destination']])
        new['archive_copies'] = [readmit.COPY]
        for key in ['build_compiler', 'runtime_driver', 'stamp']:
            new[key] = current[old[key]['path']]
        new['archives'][0]['file'] = current['/archive']
        for row in new['private']:
            row['file'] = current[row['source']]
        return old, new, current

    def test_fresh_composition_accepts_only_admitted_current_records(self):
        old, new, current = self.fixture()
        before = copy.deepcopy(old)
        readmit.check_composition(old, new, current)
        self.assertEqual(old, before)
        new['private'][0]['file'] = old['private'][0]['file']
        with self.assertRaises(RuntimeError):
            readmit.check_composition(old, new, current)

    def test_payload_destination_and_private_membership_cannot_change(self):
        for mutation in ['payload', 'destination', 'private', 'archive']:
            with self.subTest(mutation=mutation):
                old, new, current = self.fixture()
                if mutation == 'payload':
                    new['files']['lib/item0']['sha256'] = 'b' * 64
                elif mutation == 'destination':
                    new['files']['lib/extra'] = new['files'].pop(readmit.COPY['destination'])
                elif mutation == 'private':
                    new['private'].reverse()
                else:
                    new['archives'][0]['members'].append('unrecorded')
                with self.assertRaises(RuntimeError):
                    readmit.check_composition(old, new, current)


if __name__ == '__main__':
    unittest.main()
