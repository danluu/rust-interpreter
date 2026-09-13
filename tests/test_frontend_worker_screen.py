"""Prepared pure proof/command tests; no compiler, Cargo, VM or benchmark."""
import copy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/strict-warm-build'))
import frontend_worker_screen as worker
from frontend_workers import CAPABILITY, receipt
import screen
import assess_owned_screen as assess


def sha(data):return hashlib.sha256(data).hexdigest()


class WorkerScreenContracts(unittest.TestCase):
    def capability(self):
        binaries = dict(zip(['rust-interp-vm', 'rust-interp-mir-export', 'rust-interp-rustc-wrapper'],
                            [digit * 64 for digit in '123']))
        return binaries, dict(frontend_workers=CAPABILITY,
            frontend_worker_wrapper=dict(sha256=binaries['rust-interp-rustc-wrapper'], capability=CAPABILITY))

    def test_worker_commands_change_only_explicit_count(self):
        for mode, count in [('baseline', 1), ('candidate', 2), ('duplicate', 1)]:
            args = (mode, 'a' * 64, Path('/owned/source'), Path('/owned/run'), {'index': 3})
            original = screen.command_for(*args, candidate_policy='native-host-mir')
            changed = screen.command_for(*args, candidate_policy='frontend-workers')
            index = changed.index('--frontend-workers')
            self.assertEqual(changed[index:index + 2], ['--frontend-workers', str(count)])
            self.assertEqual(changed[:index] + changed[index + 2:], original)
            self.assertEqual(len([v for v in changed if v == '--entry']), 14)

    def test_worker_selection_requires_same_actual_tool_and_external_qualification(self):
        a, b, q = 'a' * 64, 'b' * 64, Path('/qualification/result.json')
        screen.validate_comparison('frontend-workers', a, a, None, None, worker_qualification=q)
        for change in [dict(candidate_key=b), dict(compiler_key=b), dict(candidate_std=Path('/std/other')),
                       dict(baseline_cargo_key=b), dict(candidate_cargo_key=b), dict(worker_qualification=None),
                       dict(compiler_qualification=q), dict(source_observables=q)]:
            args = dict(policy='frontend-workers', baseline_key=a, candidate_key=a, compiler_key=None,
                        candidate_std=None, worker_qualification=q) | change
            with self.assertRaises(RuntimeError):screen.validate_comparison(**args)

    def test_current_macro_only_public_api_cannot_qualify_worker_tools(self):
        with patch.object(worker.importlib, 'import_module', return_value=SimpleNamespace()):
            with self.assertRaisesRegex(RuntimeError, 'does not yet support'):
                worker.public_build(Path('/tools/key'), 'a' * 64, lambda path: b'{}')

    def test_typed_public_build_boundary_retains_wrapper_and_scope_checks(self):
        binaries, capability = self.capability()
        value = dict(composition=dict(qualification_policy=worker.BUILD_POLICY, binaries=binaries),
                     capability=capability, qualification_scope='public-build-only')
        api = SimpleNamespace(SUPPORTED_QUALIFICATION_POLICIES={worker.BUILD_POLICY})
        api.validate_public_tool = lambda tool, key, read, **kwargs: value
        with patch.object(worker.importlib, 'import_module', return_value=api):
            self.assertEqual(worker.public_build(Path('/tools/key'), 'a' * 64, None), value)
            value['qualification_scope'] = 'worker-qualified'
            with self.assertRaisesRegex(RuntimeError, 'scope'):
                worker.public_build(Path('/tools/key'), 'a' * 64, None)

    def test_worker_launch_requires_exact_bound_count_and_unchanged_other_policies(self):
        _, caps = self.capability()
        expected = screen.launch_settings('candidate', 'a' * 64, 'frontend-workers', worker_capability=caps)
        self.assertEqual(expected['frontend_workers'], receipt(2, caps))
        bad = copy.deepcopy(expected); bad['frontend_workers']['workers'] = 1
        with self.assertRaisesRegex(RuntimeError, 'settings differ'):
            screen.checked_launch('rust-interp-launch: ' + json.dumps(bad), 'candidate', 'a' * 64,
                True, Path('/suite'), Path('/cache'), candidate_policy='frontend-workers', worker_capability=caps)

    def bundle(self):
        owner, run, key = Path('/owned'), Path('/owned/.work/qualification'), 'a' * 64
        tool = owner / '.work/interpreter-tools' / key
        binaries, caps = self.capability()
        std = dict(key='s' * 64, sha256='r' * 64, rustc='/rustup/bin/rustc', rustc_sha256='b' * 64,
                   compiler='rustc pinned\n', sysroot='/owned/std/sysroot', target='aarch64-apple-darwin')
        public = dict(tool_key=key, tool=str(tool), capability=caps,
                      composition=dict(binaries=binaries, source=dict(files={'Cargo.toml': sha(b'[workspace]\n')})))
        data = {}
        def write(path, value):data[str(path)] = json.dumps(value).encode()
        data[str(owner / 'Cargo.toml')] = b'[workspace]\n'
        original = b'pub fn answer() -> u64 { 20 }\n'
        data[str(owner / 'experiments/frontend-workers/fixture/src/lib.rs')] = original
        data[str(owner / 'experiments/frontend-workers/fixture/shared/src/lib.rs')] = b'pub fn value() -> u64 { 3 }\n'
        for relative in ['Cargo.toml','Cargo.lock','build.rs','shared/Cargo.toml','macros/Cargo.toml','macros/src/lib.rs']:
            data[str(owner / worker.FIXTURE_PREFIX / relative)] = ('fixture '+relative+'\n').encode()
        data[str(owner / 'experiments/frontend-workers/qualify.py')] = b'qualifier source\n'
        data[str(owner / 'scripts/interpreter.py')] = b'launcher source\n'
        public['plan'] = dict(harness={str(Path(name).relative_to(owner)):sha(value) for name,value in data.items()
            if name != str(owner/'Cargo.toml')})
        fixture = {name.removeprefix(worker.FIXTURE_PREFIX):value for name,value in public['plan']['harness'].items()
                   if name.startswith(worker.FIXTURE_PREFIX)}
        plan = dict(policy=worker.QUALIFICATION_POLICY, owner=str(owner), tool_key=key,
            lock=str(worker.CAMPAIGN_LOCK), fixture_inputs=fixture,
            tools=binaries, capability=caps, jobs=2, rustc=std['rustc'], rustc_sha256=std['rustc_sha256'],
            std_key=std['key'], std_ready_sha256=std['sha256'], frozen={name: sha(value) for name, value in data.items()})
        labels = ['compiler-path', 'compiler-version']
        labels += [phase + '-' + str(n) for phase in ['cold', 'edited', 'restored'] for n in [1, 2]]
        for error in ['type', 'borrow', 'constant']:
            labels += [phase + '-' + str(n) for phase in [error, error + '-restored', error + '-native-diagnostic'] for n in [1, 2]]
        labels += [phase + '-' + str(n) for phase in ['assembly-rejection', 'assembly-restored'] for n in [1, 2]]
        codes = dict(type='E0308', borrow='E0505', constant='E0080')
        original_bytecode = b'\xfforiginal'
        for index, label in enumerate(labels):
            env, sources, status, stdout, stderr = {}, {}, 0, '', ''
            if label == 'compiler-path':
                command = ['rustup', 'which', '--toolchain', 'nightly-2026-09-08', 'rustc']; stdout = std['rustc'] + '\n'
            elif label == 'compiler-version':
                command = [std['rustc'], '-vV']; stdout = std['compiler']
            else:
                phase, count = label.rsplit('-', 1); count = int(count)
                sources = {'fixture/shared/src/lib.rs': sha(f'pub fn value() -> u64 {{ {7 if phase == "edited" else 3} }}\n'.encode()),
                    'fixture/src/lib.rs': sha(original + worker.ERROR_BODIES.get(phase, '').encode())}
                sources.update({'fixture/'+name:value for name,value in fixture.items() if name not in worker.EDIT_FILES})
                if '-native-diagnostic' in phase:
                    kind = phase.removesuffix('-native-diagnostic')
                    sources['diagnostic.rs'] = sha(('pub fn good() -> u32 { 1 }\n' + worker.ERROR_BODIES[kind]).encode())
                    command = [str(tool / 'rust-interp-rustc-wrapper'), std['rustc'], '--crate-name', 'diagnostic',
                        '--crate-type', 'rlib', '--emit=metadata', '--error-format=json',
                        '-Cincremental=' + str(run / f'diagnostic-{count}'), '-o', str(run / f'diagnostic-{count}.rmeta'), str(run / 'diagnostic.rs')]
                    env['RUST_INTERP_FRONTEND_WORKERS'] = str(count); status = 1
                    stderr = json.dumps(dict(code=dict(code=codes[kind]), level='error', message='rejected', **{'$message_type': 'diagnostic'}))
                else:
                    command = ['/python', str(owner / 'scripts/interpreter.py'), '--manifest-path', str(run / 'fixture/Cargo.toml'),
                        '--package', 'frontend-worker-fixture', '--tool-key', key, '--std-mir', '--jobs', '2',
                        '--function-cache', 'auto', '--frontend-workers', str(count), '--workspace-cache-root', str(run / 'cache'),
                        '--entry', 'assembly' if phase == 'assembly-rejection' else 'answer']
                    if phase in codes or phase == 'assembly-rejection':
                        status = 1; stderr = codes.get(phase,
                            'custom interpreter cannot lower this entry: assembly: unsupported terminator asm!(')
                    else:
                        payload = b'edited' if phase == 'edited' else original_bytecode
                        path = run / 'cache' / str(count)
                        report = dict(tool_key=key, frontend_workers=receipt(count, caps),
                            std_mir={k: std[k] for k in ['key', 'sysroot', 'target']}, workspace_path=str(path),
                            artifact_path=str(path / 'target/output.rbc'), artifact_sha256=sha(payload))
                        stdout = ('32' if phase == 'edited' else '20') + '\n'; stderr = 'rust-interp-launch: ' + json.dumps(report)
                        data[str(run / 'artifacts' / (label + '.rbc'))] = payload
            row = dict(label=label, command=command, returncode=status, stdout=stdout, stderr=stderr, sources=sources)
            child = dict(label=label, command=command, returncode=status, cwd=str(run), status='finished', pid=index+1,
                         started_at=index * 2, finished_at=index * 2 + 1, environment=env, sources=sources)
            write(run / 'logs' / (label + '.json'), row); write(run / 'logs' / (label + '-process.json'), child)
        for relative in fixture:
            data[str(run / 'fixture' / relative)] = data[str(owner / 'experiments/frontend-workers/fixture' / relative)]
        result = dict(status='passed', policy=worker.QUALIFICATION_POLICY, commands=30, tool_key=key,
            workspaces={str(n): str(run / 'cache' / str(n)) for n in [1, 2]}, original_artifact_sha256=sha(original_bytecode),
            logs={str(Path(name).relative_to(run)): sha(value) for name, value in data.items() if name.startswith(str(run / 'logs') + '/')})
        from qualified_public_tools import GUARD_POLICY
        public.update(platform={}, input_records={}, searches={})
        for name in ['before', 'after']:
            write(run / ('public-' + name + '.json'),dict(schema_version=1,policy=GUARD_POLICY,tool_key=key,
                validation='sha256',platform={},files={},searches={}))
        result['public_input_guards'] = {name:sha(data[str(run / ('public-' + name + '.json'))]) for name in ['before','after']}
        write(run / 'result.json', result); write(run / 'plan.json', plan)
        return run / 'result.json', key, public, std, data

    def test_full_synthetic_proof_retains_binary_artifacts_and_requires_all_thirty_controls(self):
        path, key, public, std, data = self.bundle()
        proof = worker.validate_qualification(path, key, public, std, lambda p: data[str(p)])
        self.assertEqual(proof['commands'], 30)
        self.assertIn(str(path.parent / 'artifacts/cold-1.rbc'), proof['files'])
        for field, value in [('commands', 29), ('tool_key', 'b' * 64), ('logs', {})]:
            changed = copy.deepcopy(data); result = json.loads(changed[str(path)]); result[field] = value
            changed[str(path)] = json.dumps(result).encode()
            with self.assertRaises(RuntimeError):
                worker.validate_qualification(path, key, public, std, lambda p: changed[str(p)])

    def test_rehashed_noop_command_and_changed_source_cannot_fake_actual_qualification(self):
        for fault in ['noop', 'source', 'overlap', 'restoration', 'lock', 'harness', 'fixture-copy', 'fixture-child', 'assembly-message']:
            path, key, public, std, data = self.bundle(); run = path.parent
            if fault == 'restoration':
                data[str(run / 'fixture/src/lib.rs')] = b'not restored'
            elif fault == 'fixture-copy':
                data[str(run / 'fixture/build.rs')] = b'fn main() {}\n'
            elif fault in ['lock','harness']:
                plan_path = run/'plan.json'; plan = json.loads(data[str(plan_path)])
                if fault == 'lock':plan['lock'] = '/another/benchmark.lock'
                else:
                    source = '/owned/experiments/frontend-workers/qualify.py'
                    data[source] = b'a self-consistent different qualifier\n'
                    plan['frozen'][source] = sha(data[source])
                data[str(plan_path)] = json.dumps(plan).encode()
            else:
                label = 'assembly-rejection-1' if fault == 'assembly-message' else 'edited-2'
                row_path = run / 'logs' / (label + '.json'); child_path = run / 'logs' / (label + '-process.json')
                row, child = [json.loads(data[str(p)]) for p in [row_path, child_path]]
                if fault == 'noop':row['command'] = child['command'] = ['/usr/bin/true']
                if fault == 'source':row['sources']['fixture/shared/src/lib.rs'] = child['sources']['fixture/shared/src/lib.rs'] = '0' * 64
                if fault == 'fixture-child':row['sources']['fixture/macros/src/lib.rs'] = child['sources']['fixture/macros/src/lib.rs'] = '0' * 64
                if fault == 'overlap':child['started_at'] = 0
                if fault == 'assembly-message':row['stderr'] = 'unsupported terminator InlineAsm'
                result = json.loads(data[str(path)])
                for p, record in [(row_path, row), (child_path, child)]:
                    data[str(p)] = json.dumps(record).encode(); result['logs'][str(p.relative_to(run))] = sha(data[str(p)])
                data[str(path)] = json.dumps(result).encode()
            with self.assertRaises(RuntimeError):
                worker.validate_qualification(path, key, public, std, lambda p: data[str(p)])

    def test_archive_encoding_preserves_exact_binary_and_rejects_ambiguity(self):
        import base64
        raw = b'\xff\x00bytecode'
        self.assertEqual(assess.member_bytes(dict(base64=base64.b64encode(raw).decode(),bytes=len(raw),sha256=sha(raw))), raw)
        with self.assertRaises(RuntimeError):assess.member_bytes(dict(utf8='x', base64='eA=='))


if __name__ == '__main__':
    unittest.main()
