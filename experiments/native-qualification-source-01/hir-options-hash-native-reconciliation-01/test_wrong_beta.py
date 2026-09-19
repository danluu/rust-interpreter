"""Saved diagnostic and bounded metadata fixtures; no actual provider reads.

The callback below verifies only fixture metadata against the retained inventory.
It does not qualify live provider bytes. The actual reconciliation must perform
the separate full frozen-byte audit and supply its real byte-verifying callback.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import unittest

import wrong_beta

A = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
N = X/'.work/hir-options-hash-compiler-01'
SOURCE = A/'experiments/hir-options-hash-native-controls-03'
WORK = A/'.work/hir-options-hash-native-controls-03'


def checked(path, expected):
    path = Path(path)
    before = path.stat()
    stamp = lambda s: (s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected or stamp(before) != stamp(path.stat()):
        raise AssertionError('saved fixture binding changed: '+str(path))
    return data


def encoded(records):
    return b''.join(json.dumps(row,sort_keys=True).encode()+b'\n' for row in records)


class WrongBeta(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        proof = json.loads((Path(__file__).parent/'parser-source-proof.json').read_bytes())
        expected_sources = {str(N/'source/compiler/rustc_metadata/src'/name)
                            for name in ['diagnostics.rs','locator.rs']}
        if set(proof['sources']) != expected_sources:
            raise AssertionError('unexpected parser source proof routes')
        for name,row in proof['sources'].items():
            data = checked(name,row['sha256'])
            if len(data) != row['size'] or not all(text in data.decode() for text in row['required_source_text']):
                raise AssertionError('source-defined E0514/provider formatting changed')
        cls.plan = json.loads(checked(SOURCE/'plan.json','37828597c866453a0beba3f22875cea63d03cf1d8a577f93b5987d1bb86bdf49'))
        inventory = json.loads(checked(A/'.work/hir-options-hash-beta-composition-08/assembly/output-inventory.json',
            'adf5ba932880100083448f77a5c8bb508f3d1685ad665a1c58054499f4f9d4f9'))
        cls.stderr = checked(WORK/'commands/018/stderr','a14fd9426d1caf3e049a9088f575aa1995459593fd28abf3f16dd0b61fdcf575')
        cls.other_stderr = checked(WORK/'commands/019/stderr','a14fd9426d1caf3e049a9088f575aa1995459593fd28abf3f16dd0b61fdcf575')
        cls.stdout = checked(WORK/'commands/018/stdout','e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
        cls.other_stdout = checked(WORK/'commands/019/stdout','e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
        checked(SOURCE/'observations.py','5aea2b1b965ee9e95a67513120ca88ab4117c0488c28b320e70c7239aeed241c')
        spec = importlib.util.spec_from_file_location('frozen_native03_observations',SOURCE/'observations.py')
        cls.observed = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.observed
        spec.loader.exec_module(cls.observed)
        cls.beta_lib = str(N/'beta-sysroot/lib/rustlib/aarch64-apple-darwin/lib')
        cls.providers = [dict(path=str(N/'beta-sysroot'/name),size=row['size'],sha256=row['sha256'],identity=row['identity'])
            for name,row in sorted(inventory.items())
            if Path(name).parent == Path('lib/rustlib/aarch64-apple-darwin/lib')
            and re.fullmatch(r'lib(?:std|std_detect|core|compiler_builtins)-[a-f0-9]+\.(?:rmeta|rlib|dylib)',Path(name).name)]
        cls.records = [json.loads(line) for line in cls.stderr.splitlines()]

    def setUp(self):
        self.rows = copy.deepcopy(self.providers)
        self.calls = []
        self.arguments = dict(observed=self.observed,beta_lib=self.beta_lib,
            beta_std_paths=list(self.plan['beta_std_paths']),providers=self.rows,
            beta_version=self.plan['build_version'].splitlines()[0],
            native_version=self.plan['runtime_version'].splitlines()[0],verify_provider=self.metadata_fixture)

    def metadata_fixture(self, row):
        expected = {value['path']:value for value in self.providers}
        self.assertEqual(row,expected[row['path']])
        self.calls.append(row['path'])
        return copy.deepcopy(row)

    def parse(self, records=None, **changes):
        raw = self.stderr if records is None else encoded(records)
        return wrong_beta.wrong_pair((b'',raw),(b'',raw),**(self.arguments|changes))

    def test_real_saved_pair_retains_all_seven_named_provider_bindings(self):
        result = wrong_beta.wrong_pair((self.stdout,self.stderr),(self.other_stdout,self.other_stderr),**self.arguments)
        self.assertEqual(result['coded_crates'],['std','compiler_builtins'])
        self.assertEqual(len(result['provider_files']),7)
        self.assertEqual(len(result['compiler_builtins_paths']),2)
        self.assertEqual(len(result['beta_std_paths']),3)
        self.assertEqual(len(set(self.calls)),7)
        self.assertEqual(result['raw_sha256'],hashlib.sha256(self.stderr).hexdigest())
        self.assertTrue(result['full_raw_parity'])

    def test_original_frozen_parser_rejection_remains_reproducible(self):
        with self.assertRaisesRegex(ValueError,'wrong-B3 failure is not compiler metadata incompatibility'):
            self.observed.wrong_pair((b'',self.stderr),(b'',self.stderr),self.plan['beta_std_paths'])

    def test_existing_std_and_core_primary_roles_still_work(self):
        for crate in ['std','core']:
            with self.subTest(crate=crate):
                row = copy.deepcopy(self.records[0])
                row['message'] = row['message'].replace('`std`','`'+crate+'`')
                paths = [value['path'] for value in self.providers
                         if re.fullmatch(r'lib'+crate+r'-[a-f0-9]+\.(?:rmeta|rlib|dylib)',Path(value['path']).name)]
                row['children'][0]['message'] = 'the following crate versions were found:'+''.join(
                    '\ncrate `'+crate+'` compiled by '+self.arguments['beta_version']+': '+path for path in paths)
                abort = copy.deepcopy(self.records[-2]);abort['message']='aborting due to 1 previous error'
                result = self.parse([row,abort,copy.deepcopy(self.records[-1])])
                self.assertEqual(result['coded_crates'],[crate])
                self.assertEqual(result['beta_std_paths'],sorted(paths))

    def test_builtins_alone_cannot_substitute_for_std_core_rejection(self):
        abort = copy.deepcopy(self.records[-2]);abort['message']='aborting due to 1 previous error'
        with self.assertRaisesRegex(ValueError,'required std/core failure'):
            self.parse([copy.deepcopy(self.records[2]),abort,copy.deepcopy(self.records[-1])])

    def test_unknown_code_and_crate_are_rejected(self):
        for code,crate in [('E0463','std'),('E0514','foreign_crate')]:
            rows=copy.deepcopy(self.records);rows[0]['code']['code']=code
            rows[0]['message']=rows[0]['message'].replace('`std`','`'+crate+'`')
            with self.subTest(code=code,crate=crate),self.assertRaises(ValueError):self.parse(rows)

    def test_foreign_provider_and_wrong_version_notes_are_rejected(self):
        for replacement in ['foreign-path','beta-version','native-version']:
            rows=copy.deepcopy(self.records)
            if replacement=='foreign-path':
                rows[2]['children'][0]['message']=rows[2]['children'][0]['message'].replace(self.beta_lib,'/tmp/foreign')
            elif replacement=='beta-version':
                rows[2]['children'][0]['message']=rows[2]['children'][0]['message'].replace(self.arguments['beta_version'],'rustc foreign')
            else:rows[2]['children'][1]['message']=rows[2]['children'][1]['message'].replace(self.arguments['native_version'],'rustc foreign')
            with self.subTest(replacement=replacement),self.assertRaises(ValueError):self.parse(rows)

    def test_provider_byte_callback_is_mandatory_and_must_match(self):
        with self.assertRaises(ValueError):self.parse(verify_provider=None)
        with self.assertRaises(ValueError):self.parse(verify_provider=lambda row:dict(row,sha256='0'*64))
        def refuse(row):raise ValueError('actual provider hash differs')
        with self.assertRaisesRegex(ValueError,'actual provider hash differs'):self.parse(verify_provider=refuse)

    def test_missing_and_duplicate_provider_rows_are_rejected(self):
        builtin=next(row for row in self.rows if Path(row['path']).name.startswith('libcompiler_builtins-'))
        with self.assertRaises(ValueError):self.parse(providers=[row for row in self.rows if row != builtin])
        with self.assertRaises(ValueError):self.parse(providers=[*self.rows,copy.deepcopy(builtin)])

    def test_full_raw_parity_and_unknown_uncoded_diagnostic_are_rejected(self):
        with self.assertRaises(ValueError):
            wrong_beta.wrong_pair((b'',self.stderr),(b'',self.stderr+b'\n'),**self.arguments)
        rows=copy.deepcopy(self.records);rows[1]['message']='unexpected compiler error'
        with self.assertRaises(ValueError):self.parse(rows)
        rows=copy.deepcopy(self.records);rows[-2]['message']='aborting due to 3 previous errors'
        with self.assertRaises(ValueError):self.parse(rows)

    def test_unsafe_route_or_inconsistent_provider_identity_is_rejected(self):
        for kind in ['escape','size','link']:
            rows=copy.deepcopy(self.rows)
            if kind=='escape':rows[0]['path']=self.beta_lib+'/../lib/'+Path(rows[0]['path']).name
            elif kind=='size':rows[0]['identity']['size']+=1
            else:rows[0]['identity']['nlink']=2
            with self.subTest(kind=kind),self.assertRaises(ValueError):self.parse(providers=rows)

    def test_original_std_core_selection_cannot_be_bypassed(self):
        cores=[name for name in self.plan['beta_std_paths'] if Path(name).name.startswith('libcore-')]
        with self.assertRaisesRegex(ValueError,'original admitted std/core provider'):
            self.parse(beta_std_paths=cores)
        with self.assertRaises(ValueError):self.parse(beta_std_paths=[])


if __name__ == '__main__':
    unittest.main()
