import json
from pathlib import Path
import tempfile
import unittest
from benchmark import environment, run_history, PROBES
from common import SOURCE
from model import FLAGS, KEY, CANDIDATE, TARGET
from evidence import fresh_native_units, validate_options, expected_status, validate_group


class Controller(unittest.TestCase):
    def test_restored_build_sees_final_inode_and_no_later_source_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'source.rs'
            path.write_bytes(b'original')
            observed, probes = [], []
            def probe(label, diagnostic):
                self.assertIn(b'rust_interp_strict_', path.read_bytes())
                probes.append((label, diagnostic))
            def run(state):
                self.assertEqual(path.read_bytes(), b'edit' if state == 1 else b'original')
                observed.append((state, path.stat().st_ino, path.stat().st_mtime_ns))
                if state == 'restored':
                    self.assertEqual(list(Path(directory).glob('.rust-interp-original-*')), [])
            run_history(path, b'original', [(0,'original',b'original'), (1,'edit',b'edit'),
                ('restored','restored-original',b'original')], probe, run)
            self.assertEqual([s for s,_,_ in observed], [0,1,'restored'])
            self.assertEqual(observed[-1][1:], (path.stat().st_ino, path.stat().st_mtime_ns))
            self.assertEqual(probes, [(label,diagnostic) for label,_,diagnostic in PROBES])

    def test_failures_restore_source_without_repeating_a_command(self):
        for stage in ['probe', 0, 1, 'restored']:
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)/'source.rs'
                path.write_bytes(b'original')
                events = []
                def probe(label, diagnostic):
                    events.append(label)
                    if stage == 'probe': raise RuntimeError('injected')
                def run(state):
                    events.append(state)
                    if state == stage: raise RuntimeError('injected')
                with self.assertRaisesRegex(RuntimeError, 'injected'):
                    run_history(path, b'original', [(0,'original',b'original'), (1,'edit',b'edit'),
                        ('restored','restored-original',b'original')], probe, run)
                self.assertEqual(path.read_bytes(), b'original')
                self.assertEqual(len(events),len(set(events)))
                self.assertEqual(events[-1], 'type' if stage == 'probe' else stage)

    def test_external_source_change_is_preserved_with_recovery_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'source.rs'
            path.write_bytes(b'original')
            def probe(label, diagnostic): pass
            def run(state): path.write_bytes(b'external')
            with self.assertRaisesRegex(RuntimeError, 'outside benchmark'):
                run_history(path, b'original', [(1,'edit',b'edit'),
                    ('restored','restored-original',b'original')], probe, run)
            self.assertEqual(path.read_bytes(), b'external')
            backup, = Path(directory).glob('.rust-interp-original-*')
            self.assertEqual(backup.read_bytes(), b'original')

    def test_profile_environment_and_explicit_engine_receipt(self):
        env, guest = environment(dict(PATH='/fixture', RUSTFLAGS='bad', CARGO_INCREMENTAL='0',
            RUST_TEST_THREADS='99', RUST_INTERP_RANDOM_SEED='1', CARGO_PROFILE_TEST_OPT_LEVEL='3'))
        self.assertEqual(env['PATH'], '/fixture')
        self.assertEqual(env['RUST_TEST_THREADS'], '2')
        self.assertNotIn('RUSTFLAGS', env)
        self.assertNotIn('CARGO_INCREMENTAL', env)
        self.assertNotIn('RUST_INTERP_RANDOM_SEED', guest)
        self.assertNotIn('CARGO_PROFILE_TEST_OPT_LEVEL', guest)
        self.assertEqual(guest['RUSTFLAGS'], ' '.join(FLAGS))
        with self.assertRaises(AssertionError): environment({'DYLD_INSERT_LIBRARIES':'unexpected'})
        launch = dict(tool_key=KEY, engine='jit', jit_resumable_calls=True, jit_persistent_registers=True,
            jit_scalar_calls=True, inline_leaves=True, trap_unsupported_calls=True, run_try_callbacks=True,
            jit_indirect_calls=False, jit_native_calls=False, jit_native_call_stubs=False,
            function_cache='auto', borrowck_cache='off', host_proc_macro_opt='off',
            toolchain_lookup=dict(mode='cached',outcome='hit'), isolated_batch='prepared',
            suite_workers_requested=2, suite_workers=2, allocation_limit=150000)
        validate_options(launch)
        validate_options(dict(launch,tool_key=CANDIDATE),'candidate')
        with self.assertRaises(AssertionError):validate_options(launch,'candidate')
        with self.assertRaises(AssertionError):validate_options(dict(launch,tool_key=CANDIDATE),'custom')
        for key,value in [('tool_key','wrong'), ('borrowck_cache','unsafe'), ('engine','foreign'),
                          ('jit_scalar_calls',False), ('suite_workers',1), ('template_session',{})]:
            with self.subTest(key=key), self.assertRaises(AssertionError):
                validate_options(dict(launch, **{key:value}))

    def test_both_library_and_integration_units_must_be_fresh(self):
        rows = [dict(reason='compiler-artifact', fresh=False, profile=dict(test=kind=='test'),
            target=dict(kind=[kind], name=name, src_path=str(SOURCE/'crates/fre-kernels'/suffix)))
            for kind,name,suffix in [('lib','fre_kernels','src/lib.rs'), ('test',TARGET,'tests/'+TARGET+'.rs')]]
        emit = lambda rows:'\n'.join(map(json.dumps, rows))
        fresh_native_units(emit(rows))
        for changed in [rows[:1],rows[1:],rows+rows[:1], [dict(rows[0],fresh=True),rows[1]],
                        [rows[0],dict(rows[1],fresh=True)], [rows[0],dict(rows[1],profile=dict(test=False))]]:
            with self.assertRaises((AssertionError, ValueError)): fresh_native_units(emit(changed))

    def test_wrong_edit_requires_matching_failures_but_check_accepts(self):
        self.assertEqual([expected_status(-1,m) for m in ['native','custom','duplicate','candidate','check']], [101,1,1,1,0])
        group = [dict(mode=m, outcomes=[['original-test','failed']],
            artifact=dict(sha256='same'), catalog=dict(sha256='catalog')) for m in ['native','custom','duplicate','candidate']]+[dict(mode='check')]
        validate_group(group)
        changed = [dict(r) for r in group]
        changed[0]['outcomes'] = [['original-test','passed']]
        with self.assertRaises(AssertionError): validate_group(changed)
        changed = [dict(r) for r in group]
        changed[2]['artifact'] = dict(sha256='different')
        with self.assertRaises(AssertionError): validate_group(changed)


if __name__ == '__main__': unittest.main()
