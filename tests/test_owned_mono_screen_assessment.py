"""Saved-byte MonoItem assessor contracts; no compiler, Cargo or VM execution."""
import copy
import hashlib
import json
from pathlib import Path
import stat
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'benchmarks/experiments/strict-warm-build'))
import assess_owned_screen as assess
import screen
import custom_compiler as custom
import owned_mono_screen as mono
import std_mir_source_paths as v2
from verified_std_diagnostics import source_span_text
from test_strict_warm_mono_screen import fixture as integration_fixture
from std_source_observables import validate_source_observables
from source_observable_transport import POLICY as OBSERVABLE_POLICY, TRANSPORT, COMMANDS


def encoded(value):
    return json.dumps(value, sort_keys=True).encode()


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def fixture(shared=False):
    owner, files = Path('/owned/project'), {}
    source = b'example source\n'
    sources = {name: sha(source) for name in v2.REQUIRED_SOURCES}
    source_files = {v2.SOURCE + name: h for name, h in sources.items()}
    commit, host = 'c' * 40, 'aarch64-apple-darwin'
    identity = dict(policy=custom.POLICY, host=host, compiler='commit-hash: ' + commit + '\nhost: ' + host + '\n',
        files=source_files | {'bin/rustc': '1' * 64}, source_sha256=custom.digest(source_files),
        provenance=dict(stage=2, source_commit=commit, std_source_paths=v2.source_capability(commit)),
        unstable_options=custom.compiler_options('stable-cgu-partitioning = value\nstable-mono-cgu-partitioning = value\n'))
    compiler = custom.Compiler(custom.digest(identity), owner / '.work/compilers' / custom.digest(identity) / 'sysroot', identity)
    for name in sources:
        files[str(compiler.sysroot / v2.SOURCE / name)] = source
    files[str(compiler.sysroot.parent / 'ready.json')] = encoded(dict(owner=str(owner), key=compiler.key, identity=identity))
    cargo = dict(executable='/public/bin/cargo', sha256='2' * 64, toolchain=v2.TOOLCHAIN,
        version='commit-hash: ' + v2.CARGO_COMMIT + '\nhost: ' + host + '\n', host=host, libraries={}, route={})

    def stamps(mapping):
        entries = {'.': [1, 1, stat.S_IFDIR | 0o555, 0, 1, 1]}
        for name in mapping:
            for parent in Path(name).parents:
                entries[str(parent)] = [1, 1, stat.S_IFDIR | 0o555, 0, 1, 1]
            entries[name] = [1, 2, stat.S_IFREG | 0o444, 10, 1, 1]
        return entries

    def std(mode):
        identity = v2.make_identity(compiler, cargo, v2.SHARED_NAMESPACE if shared else 'stable-mono-cgu:' + mode, {})
        key = custom.digest(identity)
        work = owner / '.work/std-mir' / key
        metadata = {'lib/rustlib/' + host + '/lib/lib' + crate + '-fixture.rmeta': '3' * 64 for crate in v2.CRATES}
        command = v2.command_for(identity, work)
        env = dict(RUSTC=str(compiler.rustc), RUSTFLAGS=v2.FLAGS, RUSTC_WRAPPER='', RUSTC_WORKSPACE_WRAPPER='',
            CARGO_TERM_COLOR='never', __CARGO_RUSTC_BOOTSTRAP_WS_REMAP=identity['virtual_prefix'])
        evidence, commands = {}, []
        def put(name, value):
            evidence[name] = value if isinstance(value, bytes) else encoded(value)
        run_id = 'prepare-' + mode
        for label, code in [('probe-native', 1), ('metadata', 0), ('probe-prepared', 1)]:
            directory = owner / '.work' / run_id / label
            args, cwd, stderr = command, work, ''
            if label != 'metadata':
                sysroot = compiler.sysroot if label == 'probe-native' else work / 'sysroot'
                args = [str(compiler.rustc), str(directory / 'source.rs'), '--crate-type=lib', '--edition=2024',
                    '--emit=metadata', '--error-format=json', '--sysroot', str(sysroot), '-o', str(directory / 'probe.rmeta')]
                spans = []
                for name in ['core/src/panic.rs', 'std/src/macros.rs']:
                    path = sysroot / v2.SOURCE / name
                    files[str(path)] = source
                    span = dict(file_name=str(path), byte_start=0, byte_end=1, line_start=1, line_end=1,
                                column_start=1, column_end=2)
                    spans.append(span | dict(text=source_span_text(span, source)))
                stderr = json.dumps(dict(level='error', code=dict(code='E0080'), spans=spans))
                cwd = directory
                put(label + '/source.rs', b'const UNCALLED: u32 = panic!("std source lookup probe");\n')
            row = dict(label=label, command=args, returncode=code, stderr=stderr, stdout='')
            commands.append(row)
            put(label + '.json', row)
            put(label + '-process.json', dict(command=args, returncode=code, status='finished',
                started_at=1, finished_at=2, cwd=str(cwd)))
        put('commands.json', commands)
        put('plan.json', dict(identity=identity, command=command, environment=env,
                             environment_sha256=identity['build_environment_sha256']))
        put('probe-summary.json', dict(native=['core/src/panic.rs', 'std/src/macros.rs'],
            prepared=['core/src/panic.rs', 'std/src/macros.rs'], full_presentation_qualified=False,
            strict_integration_required=True))
        published = v2.expected_sysroot_files(identity, metadata)
        ready = dict(owner=str(owner), key=key, identity=identity, run_id=run_id, command=command,
            environment=env, cargo_state=dict(route={}), source_sha256=compiler.identity['source_sha256'],
            metadata=metadata, sysroot_files=published, sysroot_stamps=stamps(published),
            snapshot_stamps=stamps(sources), evidence_files={n: sha(p) for n, p in evidence.items()},
            evidence_stamps=stamps(evidence), probes=['native', 'prepared'], full_presentation_qualified=False)
        for name, payload in evidence.items():
            files[str(work / 'evidence' / name)] = payload
        files[str(work / 'owner.json')] = encoded(dict(owner=str(owner), identity=identity, run_id=run_id))
        files[str(work / 'ready.json')] = encoded(ready)
        artifacts = {str(work / 'sysroot' / name): dict(sha256=h, stamp=[1, 2, 10, 1]) for name, h in metadata.items()}
        return dict(path=str(work / 'ready.json'), sha256=sha(encoded(ready)), key=key, artifacts=artifacts,
            compiler=compiler.identity['compiler'], rustc=str(compiler.rustc), rustc_sha256='1' * 64,
            sysroot=str(work / 'sysroot'), target=host, policy=identity['policy'], identity=identity, readiness=ready)

    off = std('off')
    on = copy.deepcopy(off) if shared else std('on')
    plan = dict(owner=str(owner), candidate_policy='stable-mono-cgu', case=json.loads(json.dumps(screen.CASE)),
        source=str(owner / 'source'), states=[dict(index=i) for i in range(9)],
        custom_compiler=dict(key=compiler.key, sysroot=str(compiler.sysroot),
            manifest=str(compiler.sysroot.parent / 'ready.json'), identity=compiler.identity),
        cgu_policy_by_mode=dict.fromkeys(screen.MODES, 'off'),
        mono_cgu_policy_by_mode=dict(baseline='off', candidate='on', duplicate='off'),
        std_mir=off, std_mir_by_mode=dict(baseline=off, candidate=on, duplicate=off),
        cargo_jobs=4, suite_workers=2, instruction_limit=screen.INSTRUCTIONS,
        allocation_limit=screen.ALLOCATIONS, minimum_free_gib=8, guest_rustflags=[],
        profile_overrides={}, final_qualification=False)
    binaries = {name: str(i + 4) * 64 for i, name in enumerate(
        ['rust-interp-vm', 'rust-interp-mir-export', 'rust-interp-rustc-wrapper'])}
    composition = dict(kind=custom.TOOL_POLICY, compiler_key=compiler.key, compiler_sysroot=str(compiler.sysroot),
        binaries=binaries, cargo={k: cargo[k] for k in ['executable', 'sha256', 'toolchain', 'version']})
    key = custom.digest(composition)
    wrapper = dict(policy='stable-mono-cgu-routing-v1', sha256=binaries['rust-interp-rustc-wrapper'],
                   compiler_sysroot=str(compiler.sysroot))
    caps = dict(schema_version=1, bytecode_version=5, tool_key=key, compiler_sysroot=str(compiler.sysroot),
        exporter_sha256=binaries['rust-interp-mir-export'],
        export_options=['stable-cgu-partitioning', 'stable-mono-cgu-partitioning'], stable_mono_cgu_wrapper=wrapper)
    tool = owner / '.work/interpreter-tools' / key
    for name, value in [('compiler.json', composition), ('ready.json', binaries), ('capabilities.json', caps)]:
        files[str(tool / name)] = encoded(value)
    plan.update(tools=dict.fromkeys(screen.MODES, key), binaries=dict.fromkeys(screen.MODES, binaries), mono_wrapper=wrapper)
    return plan, compiler, files


def snapshot(files):
    return lambda path: dict(path=str(path), bytes=len(files[str(path)]), sha256=sha(files[str(path)]),
                             utf8=files[str(path)].decode())


class OwnedMonoAssessmentTests(unittest.TestCase):
    def test_v2_and_tool_selection_use_only_saved_callbacks(self):
        plan, compiler, files = fixture()
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('live read')), \
             patch.object(v2, 'load', side_effect=AssertionError('live loader')):
            self.assertEqual(assess.selection(plan, snapshot(files))[0], compiler)
            assess.tool_identity(plan, plan['tools']['baseline'], compiler, snapshot(files))
        wrong = copy.deepcopy(plan)
        wrong['std_mir_by_mode']['candidate'] = wrong['std_mir_by_mode']['baseline']
        with self.assertRaises(RuntimeError):
            assess.selection(wrong, snapshot(files))

    def test_shared_std_archive_requires_identical_physical_input_and_keeps_mono_modes(self):
        plan, compiler, files = fixture(shared=True)
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('live read')):
            assess.selection(plan, snapshot(files))
        std = plan['std_mir']
        for mode in screen.MODES:
            command = screen.command_for(mode, plan['tools'][mode], Path(plan['source']), Path('/owned/run'),
                plan['states'][0], candidate_policy='stable-mono-cgu', compiler_key=compiler.key,
                prepared_std=std)
            self.assertEqual(command[command.index('--std-mir-policy') + 1], v2.SHARED_SELECTION)
            self.assertEqual(command[command.index('--std-mir-key') + 1], std['key'])
            self.assertEqual(command[command.index('--stable-mono-cgu-partitioning') + 1],
                             'on' if mode == 'candidate' else 'off')
            settings = screen.launch_settings(mode, plan['tools'][mode], 'stable-mono-cgu', compiler,
                mono_wrapper=plan['mono_wrapper'], prepared_std=std)
            self.assertEqual(settings['std_mir_policy'], v2.SHARED_POLICY)
            launch = settings | dict(toolchain_lookup=dict(mode='cached', outcome='owned-manifest'))
            assess.mono_launch_identity(plan, dict(mode=mode, launch=launch), compiler)
            launch['std_mir_policy'] = v2.POLICY
            with self.assertRaises(RuntimeError):
                assess.mono_launch_identity(plan, dict(mode=mode, launch=launch), compiler)
        wrong = copy.deepcopy(plan)
        wrong['std_mir_by_mode']['candidate']['sysroot'] += '-different'
        with self.assertRaises(RuntimeError):
            assess.selection(wrong, snapshot(files))
        wrong = copy.deepcopy(plan)
        old, _, old_files = fixture()
        wrong['std_mir_by_mode']['candidate'] = old['std_mir_by_mode']['candidate']
        with self.assertRaisesRegex(RuntimeError, 'mixed MonoItem std policy'):
            assess.selection(wrong, snapshot(files | old_files))

    def test_v2_rejects_self_consistently_rehashed_missing_real_snippet(self):
        plan, compiler, files = fixture()
        std = plan['std_mir_by_mode']['candidate']
        ready = std['readiness']; work = Path(std['path']).parent
        name = 'probe-prepared.json'; path = work / 'evidence' / name
        row = json.loads(files[str(path)])
        diagnostic = json.loads(row['stderr']); diagnostic['spans'][0]['text'] = []
        row['stderr'] = json.dumps(diagnostic)
        files[str(path)] = encoded(row); ready['evidence_files'][name] = sha(encoded(row))
        history = json.loads(files[str(work / 'evidence/commands.json')])
        history[-1] = row
        files[str(work / 'evidence/commands.json')] = encoded(history)
        ready['evidence_files']['commands.json'] = sha(encoded(history))
        files[std['path']] = encoded(ready); std['sha256'] = sha(encoded(ready))
        with self.assertRaisesRegex(RuntimeError, 'snippet is missing'):
            mono.validate_std(std, plan['owner'], compiler, 'on', lambda p: files[str(p)])

    def test_v2_inventory_and_setup_scope_tampering_is_rejected(self):
        for change in ['missing-source', 'writable', 'scope', 'wrong-artifact', 'path-escape']:
            plan, compiler, files = fixture()
            std = plan['std_mir_by_mode']['candidate']; ready = std['readiness']
            if change == 'missing-source':
                del ready['sysroot_files'][v2.SOURCE + 'core/src/lib.rs']
            elif change == 'writable':
                ready['snapshot_stamps']['core/src/lib.rs'][2] |= 0o200
            elif change == 'scope':
                ready['full_presentation_qualified'] = True
            elif change == 'wrong-artifact':
                std['artifacts'] = {}
            else:
                ready['evidence_files']['../escape'] = 'f' * 64
            files[std['path']] = encoded(ready); std['sha256'] = sha(encoded(ready))
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                mono.validate_std(std, plan['owner'], compiler, 'on', lambda p: files[str(p)])

    def test_27_commands_bind_explicit_std_keys_and_effective_policy(self):
        plan, compiler, files = fixture()
        for index in range(9):
            for mode in screen.MODES:
                command = screen.command_for(mode, plan['tools'][mode], Path(plan['source']), Path('/owned/run'),
                    plan['states'][index], candidate_policy='stable-mono-cgu', compiler_key=compiler.key,
                    prepared_std=plan['std_mir_by_mode'][mode])
                launch = screen.launch_settings(mode, plan['tools'][mode], 'stable-mono-cgu', compiler,
                    mono_wrapper=plan['mono_wrapper']) | dict(toolchain_lookup=dict(mode='cached', outcome='owned-manifest'))
                row = dict(mode=mode, index=index, command=command, launch=launch, seconds=1.0,
                    cpu=dict(user_seconds=.8, system_seconds=.2, total_seconds=1.0))
                assess.command_identity(plan, row, Path('/owned/run'), compiler, None)
                assess.mono_launch_identity(plan, row, compiler)
                wrong = copy.deepcopy(row)
                wrong['command'][command.index('--std-mir-key') + 1] = 'f' * 64
                with self.assertRaisesRegex(RuntimeError, 'timed command differs'):
                    assess.command_identity(plan, wrong, Path('/owned/run'), compiler, None)
        for field, value in [('frontend_workers', {}), ('compiler_argv_record_dir', '/instrument'),
                             ('host_proc_macro_opt', 'on')]:
            wrong = copy.deepcopy(row); wrong['launch'][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                assess.mono_launch_identity(plan, wrong, compiler)

    def test_wrapper_or_compiler_help_cannot_be_inferred_from_the_module_policy(self):
        plan, compiler, files = fixture()
        key = plan['tools']['baseline']; path = Path(plan['owner']) / '.work/interpreter-tools' / key / 'capabilities.json'
        caps = json.loads(files[str(path)]); caps['stable_mono_cgu_wrapper']['sha256'] = 'f' * 64
        files[str(path)] = encoded(caps)
        with self.assertRaisesRegex(RuntimeError, 'exporter/wrapper'):
            assess.tool_identity(plan, key, compiler, snapshot(files))
        wrong = copy.deepcopy(plan); wrong['cgu_policy_by_mode']['candidate'] = 'on'
        with self.assertRaisesRegex(RuntimeError, 'stable-CGU policy'):
            assess.selection(wrong, snapshot(files))

    def test_36_controls_do_not_replace_source_observable_prerequisite(self):
        result, files, put, validate = integration_fixture()
        checked = validate()
        plan = dict(candidate_policy='stable-mono-cgu', owner='/owned/project', tools=dict(baseline='a' * 64),
            std_mir_by_mode=dict(baseline=result['std_mir']['off'], candidate=result['std_mir']['on']),
            compiler_qualification=checked)
        compiler = SimpleNamespace(key='c' * 64, sysroot=Path('/compiler/sysroot'))
        read = lambda path: files[str(path.relative_to(Path('/owned/project/.work/integration')))]
        with self.assertRaisesRegex(RuntimeError, 'source-observable prerequisite'):
            mono.qualification(plan, compiler, read)
        observable = dict(path='/owned/project/.work/observable/result.json', sha256='f' * 64,
                          evidence_files={'/owned/project/.work/observable/result.json': 'f' * 64})
        plan['source_observables'] = observable
        calls = []
        def typed_validator(*args, **kwargs):
            calls.append((args, kwargs)); return observable
        self.assertEqual(mono.qualification(plan, compiler, read,
            source_observables_validator=typed_validator)['source_observables'], observable)
        self.assertIs(calls[0][1]['read_bytes'], read)

    def test_binary_qualification_member_round_trips_and_hash_tampering_fails(self):
        import base64
        payload = b'bytecode\x00\xff\x80'
        item = dict(path='/saved/original.rbc', bytes=len(payload), sha256=sha(payload),
                    base64=base64.b64encode(payload).decode())
        self.assertEqual(assess.member_bytes(item), payload)
        for changes in [dict(sha256='0' * 64), dict(bytes=1), dict(utf8='also present')]:
            with self.subTest(changes=changes), self.assertRaises(RuntimeError):
                assess.member_bytes(item | changes)

    def test_saved_screen_uses_typed_transport_version_gate_after_valid_strict36(self):
        result, files, put, validate = integration_fixture()
        checked = validate()
        owner = Path('/owned/project')
        observable_path = owner / '.work/observable/result.json'
        old = dict(status='passed', policy=OBSERVABLE_POLICY, transport_policy=TRANSPORT,
            guest_negative_controls=4, commands=COMMANDS, owner=str(owner), compiler_key='c'*64,
            tool_key='a'*64, compiler_sysroot='/compiler/sysroot', std_mir=result['std_mir'],
            benchmark=False, diagnostics_rewritten=False, source_restored=True, qualification_only=True,
            unmapped_source_paths='passed', std_only_application_observables='unchanged',
            application_remap_sensitivity='expected-span-file-only-change',
            disposable_source_negatives='rejected-by-raw-source-validator')
        observable = dict(path=str(observable_path))
        plan = dict(candidate_policy='stable-mono-cgu', owner=str(owner), tools=dict(baseline='a'*64),
            std_mir_by_mode=dict(baseline=result['std_mir']['off'], candidate=result['std_mir']['on']),
            compiler_qualification=checked, source_observables=observable)
        compiler = SimpleNamespace(key='c'*64, sysroot=Path('/compiler/sysroot'))
        for change in [dict(policy='std-source-observables-v1'), dict(commands=57),
                       dict(transport_policy='guest-stdout')]:
            payload = encoded(old | change)
            def read(path):
                return payload if path == observable_path else files[str(path.relative_to(owner / '.work/integration'))]
            with self.subTest(change=change), self.assertRaisesRegex(RuntimeError, 'source prerequisite is missing or uses different'):
                mono.qualification(plan, compiler, read, source_observables_validator=validate_source_observables)


if __name__ == '__main__':
    unittest.main()
