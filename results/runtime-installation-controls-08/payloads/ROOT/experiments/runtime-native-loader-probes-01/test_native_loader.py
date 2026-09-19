"""Pure source/body controls; no provider modules, processes, or payloads.

Execute exact selected AST function bodies from old/new runtime sources and the
three pure custom_compiler helpers. Read only the pinned saved JSON admission;
no path in its inventory is inspected. Recipe fixtures supply an in-memory
compiler environment adapter, not an installed compiler or loader simulation.
"""
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import types
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
OLD_RUNTIME = R/'scripts/runtime_compiler.py'
CUSTOM = R/'scripts/custom_compiler.py'
OLD_PRODUCER = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/experiments/hir-options-hash/runtime-installation-01/recipe.py')
SPEC_PATH = ROOT/'experiments/runtime-installation-after-preflight05-02/installation-plan-01/specification.json'
SPEC_SHA = '96c228e2b561de69c2d56a8e1364ac349437418a47a5c1935f6e4f14e67ab6b9'
OLD_KEY = 'ac216a6a0962f84ba7a4c4d02f271e531d34e0810e0f537d5b1a5af7857e79b6'
NEW_KEY = 'f031d981666f450f760ccf303dccba986053ec6b9a143a60f3d26680f9ac7c70'
CONSTANTS = {'POLICY','NAMESPACE','LOADER_POLICY','SOURCE','SOURCE_ROOTS','CRATES',
             'REQUIRED_SOURCES','LOAD_KINDS','OVERRIDES','BLOCK'}
FUNCTIONS = {'relative','absolute','under','option_proof','require_runtime',
             'qualification_policy','identity_for','macho_commands','validate_loader',
             'native_loader_probe','loader_probe_policy','loader_command','install_runtime_compiler'}


def selected(path, functions, constants, namespace):
    tree = ast.parse(path.read_text(), filename=str(path))
    nodes = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in functions)
             or (isinstance(n, ast.Assign) and len(n.targets) == 1
                 and isinstance(n.targets[0], ast.Name) and n.targets[0].id in constants)]
    found = {n.name for n in nodes if isinstance(n, ast.FunctionDef)}
    if found != functions:
        raise AssertionError(('missing exact source functions', functions-found))
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)


def runtime(path, *, successor):
    value = dict(Path=Path, PurePosixPath=PurePosixPath, re=re, hashlib=hashlib, json=json, sys=sys)
    selected(CUSTOM, {'require','digest','valid_key'}, set(), value)
    functions = FUNCTIONS if successor else FUNCTIONS-{'native_loader_probe','loader_probe_policy','loader_command'}
    selected(path, functions, CONSTANTS, value)
    return types.SimpleNamespace(**value)


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


old = runtime(OLD_RUNTIME, successor=False)
new = runtime(HERE/'runtime_compiler.py', successor=True)
producer = module(HERE/'producer_recipe.py', 'native_loader_producer_fixture')
historical_producer = module(OLD_PRODUCER, 'native_loader_old_producer_fixture')
audit = module(HERE/'audit_recipe.py', 'native_loader_audit_fixture')
raw = SPEC_PATH.read_bytes()
if hashlib.sha256(raw).hexdigest() != SPEC_SHA:
    raise AssertionError('actual historical admission fixture changed')
SAVED = json.loads(raw)


def forbidden(*args, **kwargs):
    raise AssertionError('unexpected provider, filesystem, or workload operation')


class ExplosiveRoot:
    __fspath__ = forbidden


def explicit():
    spec = copy.deepcopy(SAVED)
    spec['loader_probe'] = new.native_loader_probe(spec)
    return spec


def q_fixture(rt):
    # Only command/context construction is under test. Actual environment policy
    # remains separately qualified; this adapter performs no filesystem checks.
    class InMemoryCompiler:
        def __init__(self, key, sysroot, identity):
            self.rustc, self.sysroot, self.identity = sysroot/'bin/rustc', sysroot, identity
        def environment(self, env):
            return audit.environment(rt, self.identity, self.sysroot, env)
    values = vars(rt).copy()
    values['RuntimeCompiler'] = InMemoryCompiler
    def probes(rustc, sysroot, work):
        return [[str(rustc), str(work/'source.rs'), '--sysroot', str(sysroot), '-o', str(work/'local.rmeta')],
                [str(rustc), str(work/'source.rs'), '--sysroot', str(sysroot), '-o', str(work/'virtual.rmeta')]]
    return types.SimpleNamespace(runtime=types.SimpleNamespace(**values), probe_commands=probes,
        PREFLIGHT='fixture-source-preflight', FINAL=SAVED['prepublication_qualification']['policy'],
        std=types.SimpleNamespace(source_capability=lambda commit: copy.deepcopy(SAVED['provenance']['std_source_paths'])))


class NativeLoader(unittest.TestCase):
    def test_historical_identity_is_exact_and_does_not_mutate(self):
        spec = copy.deepcopy(SAVED); before = copy.deepcopy(spec)
        self.assertEqual(new.identity_for(spec), old.identity_for(spec))
        self.assertEqual(new.digest(new.identity_for(spec)), OLD_KEY)
        self.assertEqual(spec, before)
        self.assertNotIn('loader_probe', spec)

    def test_new_identity_changes_only_admission_declaration(self):
        spec = explicit(); identity = new.identity_for(spec)
        prior = old.identity_for(SAVED)
        self.assertEqual(new.digest(identity), NEW_KEY)
        self.assertNotEqual(NEW_KEY, OLD_KEY)
        restored = copy.deepcopy(identity); del restored['admission']['loader_probe']
        self.assertEqual(restored, prior)
        self.assertEqual(identity['files'], prior['files'])

    def test_host_is_derived_from_exact_qualified_contract(self):
        self.assertEqual(new.native_loader_probe(SAVED),
            {'policy':'darwin-native-loader-probe-v1','host':'aarch64-apple-darwin','architecture':'arm64'})
        for host in ['arm64-apple-darwin','x86_64-apple-darwin','aarch64-unknown-linux-gnu','',None,True]:
            with self.subTest(host=host):
                spec = explicit(); spec['host'] = host
                with self.assertRaises(RuntimeError): new.identity_for(spec)
                with self.assertRaises(RuntimeError): audit.loader_command(spec, '/fixture/image')

    def test_missing_duplicate_or_conflicting_compiler_host_rejected(self):
        base = '\n'.join(line for line in SAVED['compiler'].splitlines() if not line.startswith('host: '))
        for lines in [[], ['aarch64-apple-darwin']*2, ['aarch64-apple-darwin','x86_64-apple-darwin'], ['x86_64-apple-darwin']]:
            with self.subTest(lines=lines):
                spec = explicit(); spec['compiler'] = base+'\n'+''.join('host: '+host+'\n' for host in lines)
                with self.assertRaises(RuntimeError): new.identity_for(spec)
                with self.assertRaises(RuntimeError): audit.loader_command(spec, '/fixture/image')

    def test_closed_probe_declaration_schema_and_values(self):
        declared = explicit()['loader_probe']
        invalid = [None, False, [], {}, dict(declared, extra='field')]
        invalid += [{k:v for k,v in declared.items() if k!=missing} for missing in declared]
        invalid += [dict(declared, **{key:value}) for key in declared for value in [False,0,[],{},'', 'foreign']]
        for declaration in invalid:
            with self.subTest(declaration=declaration):
                spec=copy.deepcopy(SAVED); spec['loader_probe']=declaration
                with self.assertRaises(RuntimeError): new.identity_for(spec)
                with self.assertRaises(RuntimeError): audit.loader_command(spec, '/fixture/image')

    def test_probe_derivation_returns_detached_value(self):
        spec=explicit(); before=copy.deepcopy(spec)
        new.loader_probe_policy(spec)['architecture']='foreign'
        self.assertEqual(spec,before)
        self.assertEqual(new.loader_probe_policy(spec)['architecture'],'arm64')

    def test_legacy_install_rejected_before_root_or_run(self):
        with self.assertRaisesRegex(RuntimeError,'new installation requires an explicit'):
            new.install_runtime_compiler(ExplosiveRoot(), SAVED, run=forbidden, guard=forbidden, environment={})

    def test_malformed_install_rejected_before_root_or_run(self):
        spec=explicit(); spec['loader_probe']['architecture']='x86_64'
        with self.assertRaisesRegex(RuntimeError,'invalid native loader probe'):
            new.install_runtime_compiler(ExplosiveRoot(), spec, run=forbidden, guard=forbidden, environment={})

    def test_native_and_historical_argv_match_independent_reconstruction(self):
        image=Path('/fixture/sysroot/lib/fat.dylib')
        for spec,argv in [(SAVED,['/usr/bin/otool','-l',str(image)]),
                          (explicit(),['/usr/bin/otool','-arch','arm64','-l',str(image)])]:
            with self.subTest(native='loader_probe' in spec):
                self.assertEqual(new.loader_command(spec,image),argv)
                self.assertEqual(audit.loader_command(spec,image),argv)

    def test_installation_body_uses_selected_command_and_keeps_exact_comparison(self):
        tree=ast.parse((HERE/'runtime_compiler.py').read_text())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='install_runtime_compiler')
        assignment=next(n for n in fn.body if isinstance(n,ast.Try))
        loader=next(n for n in assignment.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='loader')
        self.assertEqual(ast.unparse(loader.value), "{name: macho_commands(probe(loader_command(spec, sysroot / name))) for name in sorted(spec['loader'])}")
        self.assertTrue(any(isinstance(n,ast.Compare) and ast.unparse(n)=="loader == spec['loader']" for n in ast.walk(fn)))

    def test_ordered_duplicate_edges_are_preserved(self):
        output='fixture:\nLoad command 0\n cmd LC_LOAD_DYLIB\n name /usr/lib/libSystem.B.dylib (offset 24)\nLoad command 1\n cmd LC_LOAD_DYLIB\n name /usr/lib/libSystem.B.dylib (offset 24)\n'
        result=new.macho_commands(output)
        self.assertEqual(result['loads'],[['LC_LOAD_DYLIB','/usr/lib/libSystem.B.dylib']]*2)
        self.assertEqual(result,old.macho_commands(output))

    def test_all_slice_output_is_not_deduplicated_into_a_false_match(self):
        section='Load command 0\n cmd LC_LOAD_DYLIB\n name /usr/lib/libSystem.B.dylib (offset 24)\n'
        raw=''.join('fixture (architecture '+arch+'):\n'+section for arch in ['x86_64','x86_64h','arm64'])
        expected=new.macho_commands(section)
        self.assertNotEqual(new.macho_commands(raw),expected)
        self.assertEqual(new.macho_commands(raw)['loads'],expected['loads']*3)

    def test_parser_still_rejects_embedded_loader_environment(self):
        with self.assertRaisesRegex(RuntimeError,'embedded loader environment'):
            new.macho_commands('Load command 0\n cmd LC_DYLD_ENVIRONMENT\n')

    def test_complete_new_recipe_matches_independent_recipe(self):
        owner=Path('/fixture/owner'); work=owner/'.work/installation'
        spec=explicit(); q=q_fixture(new); env={'PATH':'/usr/bin:/bin','TMPDIR':str(work/'tmp'),'LANG':'C'}
        before=copy.deepcopy((spec,env))
        produced=producer.installation_commands(q,spec,owner,work,env)
        checked=audit.installation_commands(q,spec,owner,work,env)
        self.assertEqual(produced,checked)
        key,sysroot,rows=produced
        self.assertEqual(key,NEW_KEY); self.assertEqual(len(rows),15)
        self.assertEqual([r['argv'] for r in rows[:10]],
            [['/usr/bin/otool','-arch','arm64','-l',str(sysroot/name)] for name in sorted(spec['loader'])])
        self.assertEqual([r['expected'] for r in rows],[[0]]*13+[[1]]*2)
        self.assertEqual((spec,env),before)

    def test_historical_full_recipe_preserves_old_commands(self):
        owner=Path('/fixture/owner'); work=owner/'.work/installation'; env={'PATH':'/usr/bin:/bin'}
        expected=historical_producer.installation_commands(q_fixture(old),SAVED,owner,work,env)
        self.assertEqual(producer.installation_commands(q_fixture(new),SAVED,owner,work,env),expected)
        self.assertEqual(audit.installation_commands(q_fixture(new),SAVED,owner,work,env),expected)

    def test_new_recipe_changes_only_prefix_key_and_arch_arguments(self):
        owner=Path('/fixture/owner'); work=owner/'.work/installation'; env={'PATH':'/usr/bin:/bin'}
        previous=historical_producer.installation_commands(q_fixture(old),SAVED,owner,work,env)[2]
        expected=json.loads(json.dumps(previous).replace(OLD_KEY,NEW_KEY))
        for row in expected[:10]: row['argv'][1:1]=['-arch','arm64']
        self.assertEqual(producer.installation_commands(q_fixture(new),explicit(),owner,work,env)[2],expected)

    def test_final_specification_adds_only_policy_after_preflight_validation(self):
        candidate=copy.deepcopy(SAVED)
        del candidate['prepublication_qualification']
        preflight_sha=candidate['provenance'].pop('source_preflight_sha256')
        policy_sha=candidate['provenance'].pop('source_policy_proof_sha256')
        before=copy.deepcopy(candidate); q=q_fixture(new)
        preflight={'status':'passed','policy':q.PREFLIGHT,'full_current_guard_passed':True,
            'candidate_sha256':new.digest(candidate),'commands':[{},{}]}
        kwargs=dict(preflight_reference={'sha256':preflight_sha},preflight=preflight,
            policy_reference={'sha256':policy_sha},policy={'source_commit':candidate['provenance']['source_commit'],
            'capability':copy.deepcopy(SAVED['provenance']['std_source_paths'])})
        self.assertEqual(producer.final_specification(q,candidate,**kwargs),explicit())
        self.assertEqual(candidate,before)
        preflight['candidate_sha256']='0'*64
        with self.assertRaisesRegex(RuntimeError,'actual candidate preflight'):
            producer.final_specification(q,candidate,**kwargs)

    def test_identity_loader_validation_is_not_bypassed(self):
        spec=explicit(); del spec['loader']['bin/rustc']
        with self.assertRaisesRegex(RuntimeError,'loader inventory'):
            new.identity_for(spec)


if __name__ == '__main__':
    unittest.main(verbosity=2)
