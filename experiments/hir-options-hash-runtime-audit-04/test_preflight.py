"""In-memory first-audit contract fixtures, with no prior audit document.

The tiny diagnostic callback exercises source/copy plumbing and local/virtual
association. It is explicitly a fixture callback, not qualification of the real
Rust diagnostic renderer. The actual runner must authenticate and use q's full
existing validate_observation implementation after complete frozen-input checks.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import types
import unittest


def load(name):
    path = Path(__file__).with_name(name+'.py')
    spec = importlib.util.spec_from_file_location('audit04_preflight_fixture_'+name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reader, recipe = load('preflight'), load('recipe')


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'))+'\n').encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def unavailable(*args, **kwargs):
    raise AssertionError('a constructor, preceding audit, or workload was requested')


def relative(value):
    path = Path(value)
    if path.is_absolute() or str(path) != value or '..' in path.parts:
        raise ValueError('unsafe fixture source')
    return value


class Fixture:
    def __init__(self):
        self.owner = Path('/fixture/owner'); self.work = self.owner/'.work/preflight'
        self.probe = self.work/'source-probe'; self.checkout = Path('/fixture/checkout')
        self.sysroot = Path('/fixture/provider'); self.source_prefix = 'lib/rustlib/src/rust/library/'
        self.payloads = {'core/src/panic.rs': b'core fixture source\n', 'std/src/macros.rs': b'std fixture source\n'}
        self.files = {name: hashlib.sha256(data).hexdigest() for name, data in self.payloads.items()}
        self.identity_document = dict(provenance=dict(source_checkout=str(self.checkout), source_commit='1'*40),
            compiler='fixture compiler\n', source_sha256='2'*64,
            files={'bin/rustc': '3'*64, **{self.source_prefix+k: v for k, v in self.files.items()}})
        self.runtime = types.SimpleNamespace(identity_for=lambda spec: copy.deepcopy(self.identity_document),
            digest=digest, relative=relative, NAMESPACE='runtime-compilers',
            OVERRIDES=('RUST_SYSROOT', 'RUSTC_FORCE_RUSTC_VERSION', 'RUSTC_OVERRIDE_VERSION_STRING', 'FORCE_RUSTC_VERSION'),
            RuntimeCompiler=unavailable, install_runtime_compiler=unavailable)
        self.q = types.SimpleNamespace(runtime=self.runtime, std=types.SimpleNamespace(SOURCE=self.source_prefix),
            PREFLIGHT='native-runtime-source-preflight-v1', PROBE=b'fixture source probe\n',
            preflight=unavailable, run_pair=unavailable, final_validator=unavailable)
        self.q.probe_commands = lambda rustc, sysroot, work: [
            [str(rustc), str(work/'source.rs'), '--sysroot', str(sysroot), 'fixture-local'],
            [str(rustc), str(work/'source.rs'), '--sysroot', str(sysroot), 'fixture-virtual']]
        self.q.validate_observation = self.observe
        self.spec = dict(components=[dict(role='runtime', root=str(self.sysroot))])
        self.plan = dict(phase='preflight', owner=str(self.owner), work=str(self.work),
            specification=dict(path='/fixture/packet/specification.json', sha256=digest(self.spec)),
            environment=dict(PATH='/usr/bin:/bin', TMPDIR=str(self.work/'tmp'), SDKROOT='/fixture/sdk'))
        self.plan['children'] = recipe.preflight_commands(self.q, self.spec, self.owner, self.probe, self.plan['environment'])
        self.terminal = dict(phase='preflight', status='passed', pid=50, parent_pid=40,
            runtime_key=digest(self.identity_document), admitted_at=1, finished_at=8, children=[{}, {}])
        self.raw = {str(self.probe/'source.rs'): self.q.PROBE}
        self.ids = {}; self.documents = {self.plan['specification']['path']: self.spec}
        self.accesses = []; self.observations = []; self.guards = 0
        for i, (name, data) in enumerate(self.payloads.items()):
            for j, path in enumerate([self.checkout/'library'/name, self.probe/'sources'/name]):
                self.raw[str(path)] = data
                self.ids[str(path)] = dict(dev=1, ino=100+2*i+j, mode=stat.S_IFREG|0o644,
                    nlink=1, size=len(data), mtime_ns=1000, ctime_ns=1000)
        self.children = []
        proofs = []
        for i, declaration in enumerate(self.plan['children']):
            path = self.probe/'commands'/str(i)/'receipt.json'
            receipt = dict(returncode=1, started_at=3+i*2, finished_at=4+i*2)
            self.documents[str(path)] = receipt
            self.children.append(dict(declaration=copy.deepcopy(declaration), receipt=receipt, stdout=b'',
                stderr=encoded(dict(code='E0080', fixture_virtual=bool(i)))))
            proofs.append(dict(path=str(path), sha256=digest(receipt), observed=self.expected_observation(bool(i))))
        self.result = dict(status='passed', schema_version=1, policy=self.q.PREFLIGHT,
            full_current_guard_passed=True, candidate_sha256=digest(self.spec), candidate_is_not_installation=True,
            capability_added=False, exact_source_paths_observed=True, full_presentation_qualified=False,
            application_qualified=False, std_mir_prepared=False, commands=proofs,
            owner=str(self.owner), work=str(self.probe), pid=50, parent_pid=40, runtime_sysroot=str(self.sysroot),
            compiler=self.identity_document['compiler'], source_commit='1'*40, runtime_rustc_sha256='3'*64,
            files_sha256=digest(self.identity_document['files']), source_sha256='2'*64,
            started_at=2, finished_at=7, environment=self.plan['children'][0]['environment'],
            retained_sources={name:dict(path=str(self.probe/'sources'/name), sha256=h) for name,h in self.files.items()})
        self.documents[str(self.probe/'result.json')] = self.result

    def expected_observation(self, virtual):
        return dict(sources=sorted(self.files), fixture_virtual=virtual)

    def observe(self, records, *, application, local_roots, virtual_root, files, payload_for, virtual):
        if records != [dict(code='E0080', fixture_virtual=virtual)]:
            raise ValueError('fixture code/local-virtual association differs')
        if application != self.probe/'source.rs' or local_roots != (self.sysroot/'lib/rustlib/src/rust/library', self.checkout/'library'):
            raise ValueError('fixture diagnostic roots differ')
        if virtual_root != Path('/rustc')/('1'*40)/'library' or files != self.files:
            raise ValueError('fixture admitted source map differs')
        for name in sorted(files):
            if payload_for(name) != self.payloads[name]: raise ValueError('fixture source bytes differ')
        self.observations.append(virtual)
        return self.expected_observation(virtual)

    def read_bytes(self, path):
        name = str(path); self.accesses.append(name)
        return encoded(self.documents[name]) if name in self.documents else self.raw[name]

    def read_json(self, path):
        self.accesses.append(str(path)); return copy.deepcopy(self.documents[str(path)])

    def sha(self, path):
        return hashlib.sha256(self.read_bytes(path)).hexdigest()

    def identity(self, path):
        self.accesses.append(str(path)); return copy.deepcopy(self.ids[str(path)])

    def guard(self):
        self.guards += 1

    def validate(self):
        self.terminal['source_preflight_sha256'] = self.sha(self.probe/'result.json')
        return reader.validate(plan=self.plan, spec=self.spec, terminal=self.terminal, children=self.children,
            runtime=self.runtime, q=self.q, recipe=recipe, read_json=self.read_json, read_bytes=self.read_bytes,
            sha=self.sha, identity=self.identity, inventory=unavailable, guard=self.guard)


class FirstPreflight(unittest.TestCase):
    def setUp(self): self.f = Fixture()

    def test_first_audit_needs_no_prior_audit_or_runtime_constructor(self):
        result = self.f.validate()
        self.assertEqual(result['direct_children'], 2)
        self.assertEqual(result['result_sha256'], self.f.sha(self.f.probe/'result.json'))
        self.assertEqual(self.f.observations, [False, True])
        self.assertFalse(any('audit' in path for path in self.f.accesses))
        self.assertTrue(all(result[name] is False for name in ['capability_added', 'application_qualified',
            'std_mir_prepared', 'exporter_qualified', 'performance_measurement']))

    def test_wrong_or_boolean_schema_rejected(self):
        self.f.result['schema_version'] = True
        with self.assertRaises(RuntimeError): self.f.validate()

    def test_missing_full_guard_or_added_capability_rejected(self):
        for key,value in [('full_current_guard_passed',False), ('capability_added',True), ('application_qualified',True)]:
            with self.subTest(key=key):
                f=Fixture(); f.result[key]=value
                with self.assertRaises(RuntimeError): f.validate()

    def test_candidate_identity_mismatch_rejected(self):
        self.f.result['candidate_sha256'] = 'f'*64
        with self.assertRaises(RuntimeError): self.f.validate()

    def test_wrong_result_owner_or_pid_rejected(self):
        self.f.result['pid'] = 999
        with self.assertRaises(RuntimeError): self.f.validate()

    def test_missing_second_child_rejected(self):
        self.f.children.pop()
        with self.assertRaises(RuntimeError): self.f.validate()

    def test_changed_frozen_recipe_or_environment_rejected(self):
        self.f.plan['children'][0]['argv'].append('foreign')
        with self.assertRaises(RuntimeError): self.f.validate()

    def test_inherited_compiler_override_is_not_assumed_absent(self):
        self.f.plan['environment']['RUSTC'] = '/fixture/provider/bin/rustc'
        with self.assertRaises(RuntimeError): self.f.validate()

    def test_nonempty_stdout_or_wrong_error_code_rejected(self):
        self.f.children[0]['stdout'] = b'unexpected'
        with self.assertRaises(RuntimeError): self.f.validate()
        self.f.children[0]['stdout'] = b''
        self.f.children[0]['stderr'] = encoded(dict(code='E9999', fixture_virtual=False))
        with self.assertRaises(ValueError): self.f.validate()

    def test_swapped_local_virtual_or_saved_observation_rejected(self):
        self.f.children[1]['stderr'] = self.f.children[0]['stderr']
        with self.assertRaises(ValueError): self.f.validate()
        self.f = Fixture(); self.f.result['commands'][1]['observed']['fixture_virtual'] = False
        with self.assertRaises(RuntimeError): self.f.validate()

    def test_retained_source_route_and_bytes_rejected(self):
        self.f.result['retained_sources']['core/src/panic.rs']['path'] = '/fixture/foreign'
        with self.assertRaises(RuntimeError): self.f.validate()
        self.f = Fixture(); self.f.raw[str(self.f.probe/'sources/core/src/panic.rs')] = b'changed\n'
        with self.assertRaises(RuntimeError): self.f.validate()

    def test_aliased_or_hardlinked_source_copy_rejected(self):
        name = 'core/src/panic.rs'; path = str(self.f.probe/'sources'/name)
        self.f.ids[path] = copy.deepcopy(self.f.ids[str(self.f.checkout/'library'/name)])
        with self.assertRaises(RuntimeError): self.f.validate()
        self.f = Fixture(); self.f.ids[path]['nlink'] = 2
        with self.assertRaises(RuntimeError): self.f.validate()

    def test_extra_retained_source_or_child_time_outside_result_rejected(self):
        self.f.result['retained_sources']['extra.rs'] = dict(path='/fixture/extra',sha256='e'*64)
        with self.assertRaises(RuntimeError): self.f.validate()
        self.f = Fixture(); self.f.children[0]['receipt']['started_at'] = 1
        with self.assertRaises(RuntimeError): self.f.validate()


if __name__ == '__main__':
    unittest.main(verbosity=2)
