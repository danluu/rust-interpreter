"""Saved installation fixtures; all provider and diagnostic callbacks are fake.

These cases exercise the audit's metadata, independent-copy and ordered-recipe
contracts. They do not qualify the real loader parser or Rust diagnostics.
No fixture constructs a compiler, touches a provider, or starts a process.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import stat
import types
import unittest


def load(name):
    path = Path(__file__).with_name(name+'.py')
    spec = importlib.util.spec_from_file_location('audit04_final_fixture_'+name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reader, recipe = load('final_runtime'), load('recipe')
encode = lambda v: (json.dumps(v, sort_keys=True, separators=(',', ':'))+'\n').encode()
sha = lambda data: hashlib.sha256(data).hexdigest()
digest = lambda value: sha(encode(value))


def unavailable(*args, **kwargs):
    raise AssertionError('fixture requested constructor, installer or workload')


def relative(value):
    p = PurePosixPath(value)
    if p.is_absolute() or str(p) != value or '..' in p.parts:
        raise ValueError('unsafe fixture relative path')
    return value


def stamp(i):
    return [i[k] for k in ['dev', 'ino', 'mode', 'size', 'mtime_ns', 'ctime_ns', 'nlink']]


class Fixture:
    def __init__(self):
        self.owner = Path('/fixture/owner'); self.work = self.owner/'.work/install'
        self.source_work = self.work/'source-probe'
        self.source_prefix = 'lib/rustlib/src/rust/library/'
        self.payloads = {'core/src/panic.rs': b'core source\n', 'std/src/macros.rs': b'std source\n'}
        self.source_files = {k: sha(v) for k, v in self.payloads.items()}
        self.compiler = 'fixture compiler\n'; self.commit = '1'*40
        self.capability = {'policy': 'fixture source paths', 'commit': self.commit}
        self.loader = {'bin/rustc': {'fixture_loader': 'rustc'}, 'lib/libdriver.dylib': {'fixture_loader': 'driver'}}
        self.options = {'fixture_option': True}
        self.runtime = types.SimpleNamespace(NAMESPACE='runtime-compilers', SOURCE=self.source_prefix,
            OVERRIDES=('RUST_SYSROOT', 'RUSTC_FORCE_RUSTC_VERSION'), relative=relative, digest=digest,
            RuntimeCompiler=unavailable, install_runtime_compiler=unavailable,
            macho_commands=json.loads, option_proof=json.loads)
        self.q = types.SimpleNamespace(runtime=self.runtime, PREFLIGHT='fixture-preflight-v1',
            FINAL='fixture-final-v1', PROBE=b'fixture probe\n', preflight=unavailable,
            final_validator=unavailable, run_pair=unavailable,
            std=types.SimpleNamespace(source_capability=lambda commit: copy.deepcopy(self.capability)))
        self.runtime.qualification_policy = lambda spec: self.q.FINAL
        self.q.probe_commands = lambda rustc, sysroot, work: [
            [str(rustc), str(work/'source.rs'), '--sysroot', str(sysroot), 'fixture-local'],
            [str(rustc), str(work/'source.rs'), '--sysroot', str(sysroot), 'fixture-virtual']]
        self.q.validate_observation = self.observe
        self.ids = {}; self.raw = {}; self.documents = {}; self.tree = {}; self.next_inode = 100
        self.accesses = []; self.observations = []; self.guards = 0; self.inventory_calls = 0
        runtime_payloads = {'bin/rustc': b'compiler', 'lib/libdriver.dylib': b'driver'}
        components = []
        for role, root, destination, payloads in [
                ('runtime', '/fixture/provider', '', runtime_payloads),
                ('source', '/fixture/source', self.source_prefix.rstrip('/'), self.payloads)]:
            files = {}
            for name, data in payloads.items():
                mode = 0o755 if name.startswith('bin/') else 0o644
                files[name] = dict(sha256=sha(data), size=len(data), mode=mode)
                self.raw[str(Path(root)/name)] = data
                self.ids[str(Path(root)/name)] = self.new_identity(stat.S_IFREG|mode, len(data))
            self.ids[root] = self.new_identity(stat.S_IFDIR|0o755, 0)
            components.append(dict(role=role, root=root, destination=destination, files=files, links={}))
        all_files = {**{n: sha(d) for n, d in runtime_payloads.items()},
                     **{self.source_prefix+n: h for n, h in self.source_files.items()}}
        previous = dict(status='passed', policy=self.q.PREFLIGHT, full_current_guard_passed=True,
            exact_source_paths_observed=True, finished_at=0, commands=[{}, {}], compiler=self.compiler,
            runtime_rustc_sha256=all_files['bin/rustc'], files_sha256=digest(all_files),
            source_sha256='2'*64, source_commit=self.commit)
        self.previous_path = '/fixture/previous/result.json'
        self.documents[self.previous_path] = previous
        reference = dict(path=self.previous_path, sha256=digest(previous))
        self.identity_document = dict(files=all_files, compiler=self.compiler, source_sha256='2'*64,
            provenance=dict(source_commit=self.commit, std_source_paths=self.capability,
                            source_preflight_sha256=reference['sha256']))
        self.runtime.identity_for = lambda spec: copy.deepcopy(self.identity_document)
        self.spec = dict(components=components, loader=copy.deepcopy(self.loader),
                         compiler=self.compiler, unstable_options=copy.deepcopy(self.options))
        original = dict(PATH='/usr/bin:/bin', TMPDIR=str(self.work/'tmp'))
        self.key, self.sysroot, declarations = recipe.installation_commands(
            self.q, self.spec, self.owner, self.work, original)
        self.prefix = self.sysroot.parent
        self.plan = dict(phase='installation', owner=str(self.owner), work=str(self.work),
            runtime_key=self.key, sysroot=str(self.sysroot), environment=original, children=declarations,
            source_preflight=reference, source_preflight_readback=dict(reference=reference, result=copy.deepcopy(previous)))
        self.terminal = dict(phase='installation', status='passed', runtime_key=self.key,
            installed_runtime_key=self.key, sysroot=str(self.sysroot), pid=50, parent_pid=40,
            admitted_at=1, started_at=1, finished_at=100, children=[{} for _ in declarations],
            application_qualified=False, performance_measurement=False, exporter_qualified=False,
            std_mir_prepared=False)
        self.children = []; command_refs = []
        stdout = [encode(self.loader[n]) for n in sorted(self.loader)]
        stdout += [self.compiler.encode(), (str(self.sysroot)+'\n').encode(), encode(self.options), b'', b'']
        for index, (declaration, output) in enumerate(zip(declarations, stdout, strict=True)):
            source_probe = index >= len(declarations)-2
            receipt = dict(returncode=1 if source_probe else 0,
                           started_at=10+index*2, finished_at=11+index*2)
            path = Path(declaration['output'])/'receipt.json'; self.documents[str(path)] = receipt
            self.children.append(dict(declaration=copy.deepcopy(declaration), receipt=receipt, stdout=output,
                stderr=encode(dict(code='E0080', fixture_virtual=index == len(declarations)-1)) if source_probe else b''))
            if source_probe:
                command_refs.append(dict(path=str(path), sha256=digest(receipt),
                    observed=self.expected_observation(index == len(declarations)-1)))
        self.result = dict(status='passed', schema_version=1, policy=self.q.FINAL, key=self.key,
            owner=str(self.owner), work=str(self.source_work), sysroot=str(self.sysroot), runtime_sysroot=str(self.sysroot),
            compiler=self.compiler, source_commit=self.commit, runtime_rustc_sha256=all_files['bin/rustc'],
            files_sha256=digest(all_files), source_sha256='2'*64, pid=50, parent_pid=40,
            exact_source_paths_observed=True, full_presentation_qualified=False, application_qualified=False,
            std_mir_prepared=False, started_at=2, finished_at=90, commands=command_refs,
            preflight_reference=reference, environment=declarations[-1]['environment'],
            retained_sources={n: dict(path=str(self.source_work/'sources'/n), sha256=h) for n, h in self.source_files.items()})
        self.result_path = self.source_work/'result.json'
        self.documents[str(self.result_path)] = self.result
        self.documents[str(self.prefix/'qualification.json')] = self.result
        self.ids[str(self.result_path)] = self.new_identity(stat.S_IFREG|0o644, 0)
        self.raw[str(self.source_work/'source.rs')] = self.q.PROBE
        for name, data in self.payloads.items():
            p = self.source_work/'sources'/name
            self.raw[str(p)] = data; self.ids[str(p)] = self.new_identity(stat.S_IFREG|0o644, len(data))
        wanted_dirs = {'.', 'sysroot'}
        for component in components:
            for name, row in component['files'].items():
                output = component['destination']+'/'+name if component['destination'] else name
                rel = 'sysroot/'+output; data = self.raw[str(Path(component['root'])/name)]
                self.raw[str(self.prefix/rel)] = data
                self.tree[rel] = dict(kind='file', sha256=row['sha256'],
                    identity=self.new_identity(stat.S_IFREG|(row['mode'] & ~0o222), len(data)))
                wanted_dirs.update(str(p) for p in PurePosixPath(rel).parents)
        for name in wanted_dirs:
            self.tree[name] = dict(kind='directory', identity=self.new_identity(stat.S_IFDIR|0o555, 0))
        for name in ['ready.json', 'admission.json', 'qualification.json']:
            self.tree[name] = dict(kind='file', identity=self.new_identity(stat.S_IFREG|0o444, 0), sha256='0'*64)
        self.admission = dict(identity=copy.deepcopy(self.identity_document), snapshots=[
            dict(files={n: stamp(self.ids[str(Path(c['root'])/n)]) for n in c['files']}, links={},
                 directories={'.': stamp(self.ids[c['root']])}) for c in components])
        self.ready = dict(identity=copy.deepcopy(self.identity_document), status='installed',
            application_qualified=False, owner=str(self.owner), key=self.key, sysroot=str(self.sysroot),
            stamps={n.removeprefix('sysroot/'): stamp(v['identity'])[:6] for n, v in self.tree.items() if n.startswith('sysroot/')},
            probes=dict(loader=copy.deepcopy(self.loader), compiler=self.compiler, sysroot=str(self.sysroot)+'\n', options=self.options))
        self.ready['stamps']['.'] = stamp(self.tree['sysroot']['identity'])[:6]
        self.documents[str(self.prefix/'ready.json')] = self.ready
        self.documents[str(self.prefix/'admission.json')] = self.admission
        self.refresh_publication()

    def new_identity(self, mode, size):
        self.next_inode += 1
        return dict(dev=1, ino=self.next_inode, mode=mode, nlink=1, size=size, mtime_ns=1000, ctime_ns=1000)

    def refresh_publication(self):
        """Keep checksums coherent so forged semantic facts reach their checks."""
        data = encode(self.result)
        self.ids[str(self.result_path)]['size'] = len(data)
        self.tree['qualification.json']['identity']['size'] = len(data)
        self.ready['prepublication_qualification'] = dict(policy=self.q.FINAL, receipt='qualification.json',
            sha256=sha(data), stamp=stamp(self.tree['qualification.json']['identity']))
        for name in ['ready.json', 'admission.json', 'qualification.json']:
            data = encode(self.documents[str(self.prefix/name)])
            self.tree[name]['sha256'] = sha(data); self.tree[name]['identity']['size'] = len(data)

    def expected_observation(self, virtual):
        return dict(sources=sorted(self.source_files), fixture_virtual=virtual)

    def observe(self, records, *, application, local_roots, virtual_root, files, payload_for, virtual):
        if records != [dict(code='E0080', fixture_virtual=virtual)]:
            raise ValueError('fixture diagnostic code/local-virtual mismatch')
        assert application == self.source_work/'source.rs'
        assert local_roots == (self.sysroot/self.source_prefix,)
        assert virtual_root == Path('/rustc')/self.commit/'library' and files == self.source_files
        for name, data in self.payloads.items():
            if payload_for(name) != data:
                raise ValueError('fixture source bytes differ')
        self.observations.append(virtual)
        return self.expected_observation(virtual)

    def read_json(self, p):
        self.accesses.append(str(p)); return copy.deepcopy(self.documents[str(p)])

    def read_bytes(self, p):
        self.accesses.append(str(p)); name = str(p)
        return encode(self.documents[name]) if name in self.documents else self.raw[name]

    def identity(self, p):
        self.accesses.append(str(p)); return copy.deepcopy(self.ids[str(p)])

    def inventory(self, p):
        assert p == self.prefix
        self.inventory_calls += 1
        result = copy.deepcopy(self.tree)
        if getattr(self, 'change_second_inventory', False) and self.inventory_calls == 2:
            result['sysroot/bin/rustc']['identity']['mtime_ns'] += 1
        return result

    def guard(self):
        self.guards += 1

    def validate(self, *, refresh=True):
        if refresh:
            self.refresh_publication()
        return reader.validate(plan=self.plan, spec=self.spec, terminal=self.terminal, children=self.children,
            runtime=self.runtime, q=self.q, recipe=recipe, read_json=self.read_json, read_bytes=self.read_bytes,
            sha=lambda p: sha(self.read_bytes(p)), identity=self.identity, inventory=self.inventory, guard=self.guard)


class FinalRuntime(unittest.TestCase):
    def setUp(self):
        self.f = Fixture()

    def test_complete_final_recipe_without_constructor_or_native_execution(self):
        result = self.f.validate()
        self.assertEqual(result['direct_children'], len(self.f.loader)+5)
        self.assertEqual(result['ordinary_files_independently_hashed'], 4)
        self.assertEqual(self.f.observations, [False, True])
        self.assertEqual(self.f.inventory_calls, 2)
        self.assertGreater(self.f.guards, 0)
        self.assertFalse(any(p.endswith('/install/result.json') for p in self.f.accesses))
        for name in ['native_reexecution', 'application_qualified', 'std_mir_prepared', 'exporter_qualified', 'performance_measurement']:
            self.assertIs(result[name], False)

    def test_reordered_or_missing_actual_children_rejected(self):
        self.f.children[0], self.f.children[1] = self.f.children[1], self.f.children[0]
        with self.assertRaisesRegex(RuntimeError, 'complete loader'): self.f.validate()
        self.f = Fixture(); self.f.children.pop()
        with self.assertRaisesRegex(RuntimeError, 'complete loader'): self.f.validate()

    def test_inherited_compiler_or_loader_override_rejected(self):
        for name in ['RUSTC', 'RUSTDOC', 'DYLD_LIBRARY_PATH']:
            with self.subTest(name=name):
                f = Fixture(); f.plan['environment'][name] = '/foreign'
                with self.assertRaises(RuntimeError): f.validate()

    def test_extra_or_missing_installed_payload_rejected(self):
        self.f.tree['unexpected'] = copy.deepcopy(self.f.tree['sysroot/bin/rustc'])
        with self.assertRaisesRegex(RuntimeError, 'missing or extra'): self.f.validate()
        self.f = Fixture(); del self.f.tree['sysroot/bin/rustc']
        with self.assertRaisesRegex(RuntimeError, 'missing or extra'): self.f.validate()

    def test_writable_or_hardlinked_published_payload_rejected(self):
        for key, value in [('mode', stat.S_IFREG|0o755), ('nlink', 2)]:
            with self.subTest(key=key):
                f = Fixture(); f.tree['sysroot/bin/rustc']['identity'][key] = value
                with self.assertRaises(RuntimeError): f.validate()

    def test_installed_payload_must_have_independent_inode(self):
        source = self.f.ids['/fixture/provider/bin/rustc']
        self.f.tree['sysroot/bin/rustc']['identity']['ino'] = source['ino']
        self.f.ready['stamps']['bin/rustc'] = stamp(self.f.tree['sysroot/bin/rustc']['identity'])[:6]
        with self.assertRaisesRegex(RuntimeError, 'independent inode'): self.f.validate()

    def test_ready_stamps_and_source_admission_remain_exact(self):
        self.f.ready['stamps']['bin/rustc'][4] += 1
        with self.assertRaisesRegex(RuntimeError, 'complete stamps'): self.f.validate()
        self.f = Fixture(); self.f.admission['snapshots'][0]['files']['bin/rustc'][4] += 1
        with self.assertRaisesRegex(RuntimeError, 'component identity'): self.f.validate()

    def test_installed_hash_and_size_match_admitted_payload(self):
        self.f.tree['sysroot/bin/rustc']['sha256'] = 'f'*64
        with self.assertRaisesRegex(RuntimeError, 'payload bytes'): self.f.validate()

    def test_wrong_loader_or_cli_raw_rejected(self):
        for index, data in [(0, encode({'wrong': True})), (2, b'wrong compiler\n'),
                            (3, b'/foreign/sysroot\n'), (4, encode({'wrong': True}))]:
            with self.subTest(index=index):
                f = Fixture(); f.children[index]['stdout'] = data
                with self.assertRaisesRegex(RuntimeError, 'loader/CLI proof'): f.validate()

    def test_failed_loader_or_unexpected_cli_stderr_rejected(self):
        self.f.children[0]['receipt']['returncode'] = 1
        with self.assertRaisesRegex(RuntimeError, 'loader probe'): self.f.validate()
        self.f = Fixture(); self.f.children[2]['stderr'] = b'unexpected warning'
        with self.assertRaisesRegex(RuntimeError, 'CLI probe'): self.f.validate()

    def test_schema_bool_or_wrong_source_owner_rejected(self):
        for key, value in [('schema_version', True), ('pid', 99), ('source_commit', 'f'*40)]:
            with self.subTest(key=key):
                f = Fixture(); f.result[key] = value
                with self.assertRaisesRegex(RuntimeError, 'source result association'): f.validate()

    def test_unearned_application_qualification_rejected(self):
        self.f.terminal['application_qualified'] = True
        with self.assertRaisesRegex(RuntimeError, 'unearned'): self.f.validate()

    def test_source_result_is_independent_of_published_qualification(self):
        self.f.ids[str(self.f.result_path)]['ino'] = self.f.tree['qualification.json']['identity']['ino']
        with self.assertRaisesRegex(RuntimeError, 'source qualification'): self.f.validate()

    def test_stale_preflight_or_false_guard_rejected(self):
        self.f.documents[self.f.previous_path]['full_current_guard_passed'] = False
        with self.assertRaisesRegex(RuntimeError, 'preceding source preflight'): self.f.validate()
        self.f = Fixture(); self.f.plan['source_preflight_readback']['result']['finished_at'] = 200
        with self.assertRaisesRegex(RuntimeError, 'preflight readback'): self.f.validate()

    def test_local_virtual_observation_or_error_code_mismatch_rejected(self):
        self.f.children[-1]['stderr'] = self.f.children[-2]['stderr']
        with self.assertRaises(ValueError): self.f.validate()
        self.f = Fixture(); self.f.children[-2]['stderr'] = encode(dict(code='E9999', fixture_virtual=False))
        with self.assertRaises(ValueError): self.f.validate()

    def test_forged_retained_source_route_or_bytes_rejected(self):
        self.f.result['retained_sources']['core/src/panic.rs']['path'] = '/foreign/copy.rs'
        with self.assertRaisesRegex(RuntimeError, 'source route'): self.f.validate()
        self.f = Fixture(); self.f.raw[str(self.f.source_work/'sources/core/src/panic.rs')] = b'changed\n'
        with self.assertRaisesRegex(RuntimeError, 'source bytes'): self.f.validate()

    def test_retained_source_cannot_alias_installed_source(self):
        p = str(self.f.source_work/'sources/core/src/panic.rs')
        self.f.ids[p]['ino'] = self.f.tree['sysroot/'+self.f.source_prefix+'core/src/panic.rs']['identity']['ino']
        with self.assertRaisesRegex(RuntimeError, 'source is aliased'): self.f.validate()

    def test_source_child_time_cannot_escape_saved_result(self):
        self.f.children[-2]['receipt']['started_at'] = 0
        self.f.result['commands'][0]['sha256'] = digest(self.f.children[-2]['receipt'])
        with self.assertRaisesRegex(RuntimeError, 'source child association'): self.f.validate()

    def test_extra_retained_source_and_mutated_final_inventory_rejected(self):
        self.f.result['retained_sources']['extra.rs'] = dict(path='/foreign/extra.rs', sha256='f'*64)
        with self.assertRaisesRegex(RuntimeError, 'retention omits or adds'): self.f.validate()
        self.f = Fixture(); self.f.change_second_inventory = True
        with self.assertRaisesRegex(RuntimeError, 'changed during audit'): self.f.validate()


if __name__ == '__main__':
    unittest.main(verbosity=2)
