"""Source-only boundary controls; these tests never invoke Cargo or rustc."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_script_baseline', ROOT / 'experiments/interpreted-build-scripts/baseline.py')
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)


class NativeBuildScriptBaselineTests(unittest.TestCase):
    def templates(self):
        return {n: (b.FIXTURE / n).read_bytes() for n in b.inventory(b.FIXTURE)}

    def text(self, failed=None):
        return '\n'.join('test ' + name + ' ... ' + ('FAILED' if name == failed else 'ok') for name in b.TESTS)

    def test_fixed_histories_and_exact_negative_source_restoration(self):
        cases = b.cases(); self.assertEqual(len(cases), 28)
        self.assertEqual([sum(c['group'] == name for c in cases) for name in ['default', 'shared', 'unsupported']], [24, 3, 1])
        self.assertEqual(sum(bool(c['error']) for c in cases), 8)
        self.assertEqual(sum(c['wrong'] for c in cases), 1)
        templates = self.templates()
        for i, case in enumerate(cases):
            command = b.argv(case)
            self.assertEqual(command[command.index('--jobs') + 1], '2')
            self.assertNotIn('--test-threads', command)
            changed = b.sources(case, templates)
            if case['error']:
                target = case['error']['target']
                self.assertIn(templates['controls/' + case['error']['kind'] + '.rs'], changed[target])
                self.assertEqual(b.sources(cases[i+1], templates), {n: templates[n] for n in b.EDITABLE})
            elif case['wrong']:
                self.assertIn(b'transform(input, seed) + 1;', changed['app/build.rs'])
                self.assertEqual(b.sources(cases[i+1], templates), {n: templates[n] for n in b.EDITABLE})
        self.assertEqual(b.sources(cases[0], templates), b.sources(cases[1], templates))

    def test_libtest_and_uncalled_error_cannot_be_substituted(self):
        original, wrong, error = b.cases()[0], b.cases()[6], b.cases()[8]
        b.outcomes(original, [], self.text(), 0)
        b.outcomes(wrong, [], self.text(b.TESTS[1]), 101)
        diagnostics = [{'reason':'compiler-message','message':{'level':'error','code':{'code':'E0308'}}}]
        b.outcomes(error, diagnostics, '', 101)
        for args in [(original, [], self.text() + '\n' + self.text(), 0),
                     (original, [], self.text().replace('ok', 'ignored', 1), 0),
                     (wrong, [], self.text(), 0), (wrong, [], self.text(b.TESTS[0]), 101),
                     (error, diagnostics, self.text(), 101), (error, diagnostics, self.text().replace('ok', 'ignored'), 101),
                     (error, [], '', 101)]:
            with self.subTest(args=args), self.assertRaises(RuntimeError): b.outcomes(*args)
        parsed, text = b.cargo_records(json.dumps(diagnostics[0]) + '\n' + self.text())
        self.assertEqual(parsed, diagnostics); self.assertEqual(text, self.text())

    def test_actual_script_history_and_nested_stdout_are_not_invented(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); target = root / 'target'
            out = target / b.HOST / 'debug/build/ibs-fixture-app/0123456789abcdef/out'; out.mkdir(parents=True)
            run_dir = out.parent / 'run'; run_dir.mkdir()
            (run_dir / 'root-output').write_bytes(os.fsencode(out))
            case = b.cases()[-1]; version = 'rustc actual-pinned-version\n'
            values = {'generated.rs':'pub const GENERATED_VALUE: u64 = 36;\npub const GENERATED_INPUT: u64 = 11;\npub const GENERATED_SEED: u64 = 3;\n',
                'history.txt':'input=11;seed=3;mode=script-only;value=36\n',
                'context.txt':'\n'.join(k+'='+v for k,v in dict(OUT_DIR=str(out),CARGO_MANIFEST_DIR=str(root/'app'),
                    HOST=b.HOST,TARGET=b.HOST,PROFILE='debug',OPT_LEVEL='0',DEBUG='true',NUM_JOBS='2').items())+'\n',
                'before-unsupported.txt':'script already executed\n','child-version.txt':version}
            for n,text in values.items(): (out/n).write_text(text)
            (run_dir/'stdout').write_text('\n'.join(['cargo::rerun-if-changed=build.rs','cargo:rerun-if-changed=input.txt',
                'cargo::rerun-if-env-changed=IBS_FIXTURE_SEED','cargo::rustc-check-cfg=cfg(ibs_seed_even)',
                'cargo::rustc-env=IBS_GENERATED_CONTEXT=input=11;seed=3;mode=script-only'])+'\n')
            (run_dir/'stderr').write_text('build-script input=11 seed=3 mode=script-only value=36\n')
            with patch.object(b, 'APP', root):
                result = b.script_outputs(case, out, target, {}, version)
                self.assertIsNone(result['nested_child']['pid']); self.assertEqual(result['actual_runs'], 1)
                before = b.output_snapshot(out)
                b.script_outputs(b.cases()[1], out, target, before, version)
                (out/'history.txt').write_text(values['history.txt'] * 2)
                with self.assertRaises(RuntimeError): b.script_outputs(b.cases()[1], out, target, before, version)
                (out/'history.txt').write_text(values['history.txt'])
                (out/'child-version.txt').write_text('fabricated version\n')
                with self.assertRaises(RuntimeError): b.script_outputs(case, out, target, {}, version)

    def test_current_cargo_run_files_are_bound_to_actual_unit_out_dir(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary).resolve()
            out = target / b.HOST / 'debug/build/ibs-fixture-app/0123456789abcdef/out'
            out.mkdir(parents=True); run_dir = out.parent / 'run'; run_dir.mkdir()
            for name in ['stdout', 'stderr']: (run_dir / name).write_text('actual-' + name)
            (run_dir / 'root-output').write_bytes(os.fsencode(out))
            # An old-layout decoy is never selected or used as a fallback.
            (out.parent / 'output').write_text('wrong unit output')
            files = b.script_run_files(out, target)
            self.assertEqual(files['stdout'], run_dir / 'stdout')
            self.assertEqual(files['stdout'].read_text(), 'actual-stdout')
            (run_dir / 'root-output').write_bytes(os.fsencode(out.parent / 'other-out'))
            with self.assertRaisesRegex(RuntimeError, 'another OUT_DIR'): b.script_run_files(out, target)
            (run_dir / 'root-output').write_bytes(os.fsencode(out))
            (run_dir / 'stdout').unlink()
            with self.assertRaises((RuntimeError, FileNotFoundError)): b.script_run_files(out, target)
            (run_dir / 'stdout').symlink_to(out.parent / 'output')
            with self.assertRaises(RuntimeError): b.script_run_files(out, target)

    def test_shared_macro_requires_real_link_emission_and_rlib_extern(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary).resolve(); helper=target/'libibs_fixture_helper.rlib'; dylib=target/'libibs_fixture_macros.dylib'
            helper.write_bytes(b'actual-test-artifact'); dylib.write_bytes(b'actual-test-macro')
            compiler=[dict(pid=1,argv=[str(b.RUSTC),'--crate-name','ibs_fixture_helper','--emit=dep-info,link']),
                dict(pid=2,argv=[str(b.RUSTC),'--crate-name','ibs_fixture_macros','--crate-type','proc-macro','--extern','ibs_fixture_helper='+str(helper)]),
                dict(pid=3,argv=[str(b.RUSTC),'--crate-name','ibs_fixture_app','--target',b.HOST,'--extern','ibs_fixture_macros='+str(dylib)])]
            records=[dict(reason='compiler-artifact',target=dict(name='ibs_fixture_helper',kind=['lib']),filenames=[str(helper)]),
                dict(reason='compiler-artifact',target=dict(name='ibs_fixture_macros',kind=['proc-macro']),filenames=[str(dylib)])]
            case=b.cases()[24]; proof=b.native_macro_proof(case,compiler,records,target)
            self.assertEqual(proof['helper']['path'],str(helper))
            mutations=[]
            x=copy.deepcopy(compiler);x[0]['argv'][-1]='--emit=metadata';mutations.append((x,records))
            x=copy.deepcopy(compiler);x[1]['argv'][-1]=str(helper);mutations.append((x,records))
            mutations.append((compiler,records[1:]))
            for actual, artifacts in mutations:
                with self.subTest(actual=actual), self.assertRaises((RuntimeError,KeyError)):
                    b.native_macro_proof(case,actual,artifacts,target)

    def test_explicit_environment_and_fixed_plan_reject_policy_drift(self):
        inherited={'HOME':str(Path.home()),'PATH':'untrusted','RUSTFLAGS':'-Zdanger','CARGO_BUILD_JOBS':'99',
                   'AWS_SECRET_ACCESS_KEY':'excluded','DYLD_INSERT_LIBRARIES':'excluded','IBS_FIXTURE_SEED':'999'}
        with patch.dict(os.environ,inherited,clear=True): env=b.environment()
        for name in ['RUSTFLAGS','CARGO_BUILD_JOBS','AWS_SECRET_ACCESS_KEY','DYLD_INSERT_LIBRARIES','IBS_FIXTURE_SEED']:
            self.assertNotIn(name,env)
        self.assertEqual(env['RUSTC'],str(b.RUSTC));self.assertEqual(env['RUSTC_WRAPPER'],str(Path(b.__file__).resolve()))
        frozen={str(Path(b.__file__).resolve()):'a'*64};public={'files':{str(b.RUSTC):{'sha256':'b'*64}}}
        plan=dict(schema_version=1,owner=str(b.ROOT),work=str(b.WORK),inputs=frozen,environment=env,configurations={},
            cases=b.cases(),commands=[b.argv(c) for c in b.cases()],tests=b.TESTS,fixture=b.inventory(b.FIXTURE),jobs=2,
            canonical_lock=str(b.CANONICAL_LOCK),lock_wait_seconds=600,wrapper_policy='exact-public-rustc-exec-recorder-v1',
            native_baseline_only=True,interpreted_scripts=False,performance_claim=False,public=public,
            environments=[b.case_environment(c,i,env,public,frozen) for i,c in enumerate(b.cases())])
        b.validate_plan(plan,frozen,env,{})
        for field,value in [('jobs',3),('canonical_lock','/tmp/other-lock'),('interpreted_scripts',True),('performance_claim',True)]:
            x=copy.deepcopy(plan);x[field]=value
            with self.subTest(field=field), self.assertRaises(RuntimeError): b.validate_plan(x,frozen,env,{})
        x=copy.deepcopy(plan);x['environments'][0]['RUSTC']='fake-rustc'
        with self.assertRaises(RuntimeError):b.validate_plan(x,frozen,env,{})

    def test_source_snapshot_and_staged_restoration_guard(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve(); source=root/'source.rs'; original=b'fn original() {}\n';source.write_bytes(original)
            expected=b.sha(source); rows=b.freeze_sources(root/'snapshots',{str(source):expected})
            self.assertEqual(Path(rows[str(source)]['copy']).read_bytes(),original)
            with self.assertRaisesRegex(RuntimeError,'simulated child failure'):
                with b.SourceEdit(source,original) as editor:
                    editor.replace(b'fn changed() {}\n')
                    raise RuntimeError('simulated child failure')
            self.assertEqual(source.read_bytes(),original)
            source.write_bytes(b'changed outside controller')
            with self.assertRaises(RuntimeError):b.freeze_sources(root/'changed-snapshots',{str(source):expected})


if __name__ == '__main__': unittest.main()
