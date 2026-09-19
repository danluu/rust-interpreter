"""Focused retry owner/admission controls; no runtime or provider execution.

Owner records live only in Saved callbacks, including real-looking production
path strings. The qualified reader fixture supplies the existing record schema.
Lock cases load the actual old helper into a private module and bind only that
module's CANONICAL_LOCK to an owned TemporaryDirectory file. The real canonical
lock is never opened. These are observed preheld exclusion checks, not an atomic
proof across concurrent changes; production entry retains its owning FD.
"""
import copy
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import audit_owner as owner
import controller
import environment

ORIGINAL_FIXTURE = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/hir-options-hash-runtime-audit-05/test_reader.py')
OWNED_SOURCE = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/experiments/stable-cgu/owned_stage.py')
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
ROUTE_BYTES = (Path(__file__).with_name('routes.json')).read_bytes()
ROUTES = json.loads(ROUTE_BYTES)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(value='0x1F5:0x0:0x52'):
    return RetryFixture(value)


class RetryFixture:
    def __init__(self, value):
        old = load('_retry_saved_owner_fixture', ORIGINAL_FIXTURE)
        self.base = b = old.OwnerFixture('preflight')
        self.s = s = old.Saved()
        aliases = {
            str(b.paths['packet']): ROUTES['packet'],
            str(b.paths['work']): ROUTES['work'],
            str(b.paths['outer']): ROUTES['supervisor'],
            str(b.paths['report']): ROUTES['report'],
            '/fixture/launcher': ROUTES['launcher_execution'],
            str(b.reader.R): str(R),
        }
        ordered = sorted(aliases, key=len, reverse=True)
        def remap(item):
            if isinstance(item, Path):
                return Path(remap(str(item)))
            if isinstance(item, str):
                for before in ordered:
                    if item == before or item.startswith(before + '/'):
                        return aliases[before] + item[len(before):]
                return item
            if isinstance(item, dict):
                return {remap(k): remap(v) for k, v in item.items()}
            if isinstance(item, list):
                return [remap(v) for v in item]
            return item
        for path, raw in b.saved.data.items():
            try:
                s.json(remap(path), remap(json.loads(raw)))
            except (ValueError, UnicodeError):
                s.bytes(remap(path), raw)
        for name in ['plan', 'launch', 'terminal', 'outer', 'launcher', 'expected', 'paths']:
            setattr(b, name, remap(getattr(b, name)))
        b.saved = s
        b.reader.R = R
        self.phase = 'preflight'
        self.paths = b.paths
        b.plan['capacity'] = copy.deepcopy(ROUTES['capacity'])
        b.launch['capacity'] = copy.deepcopy(ROUTES['capacity'])
        b.terminal['free_bytes_before'] = 16 * 2**30
        self.workload = dict(b.plan['environment'], TMPDIR=str(b.paths['work']/'tmp'))
        self.passed = {'PATH': '/fixture/python', 'HOME': '/fixture/home'}
        observed = dict(self.passed)
        if value is not None:
            observed[environment.CF] = value
        observations = {name: dict(observed) for name in environment.OBSERVATIONS}
        derivation = environment.derive(self.workload, self.passed, observations,
                                        platform='darwin', uid=501)
        policy = dict(path=str(owner.STARTUP_SOURCE/'environment.py'),
                      sha256=s.bytes(owner.STARTUP_SOURCE/'environment.py', b'fixture policy'))
        preparer = dict(path=str(owner.ADAPTER/'prepare.py'),
                        sha256=s.bytes(owner.ADAPTER/'prepare.py', b'fixture preparer'))
        self.qualification = dict(controls=39, audit=dict(path='/fixture/startup-audit.json',
            sha256=s.json('/fixture/startup-audit.json', {'status': 'verified', 'controls': 39})))
        self.retry_qualification = dict(controls=1, audit=dict(path='/fixture/retry-audit.json',
            sha256=s.json('/fixture/retry-audit.json', {'status': 'verified', 'fixture': True})))
        s.bytes(owner.ROUTES, ROUTE_BYTES)
        sources = [policy, preparer, dict(path=str(owner.ROUTES), sha256=s.sha(owner.ROUTES))]
        for name in ['entry.py', 'controller.py', 'audit_owner.py', 'prepare_once.py', 'launch.py']:
            path = owner.ADAPTER/name
            sources.append(dict(path=str(path), sha256=s.bytes(path, ('fixture '+name).encode())))
        manifest_value = dict(status='reviewed-runtime-preflight05-startup-source-closure', files={
            row['path']: dict(sha256=row['sha256'], size=s.identity(row['path'])['size'], identity=s.identity(row['path']))
            for row in sources})
        self.manifest_path = '/fixture/retry-sources.json'
        manifest = dict(path=self.manifest_path, sha256=s.json(self.manifest_path, manifest_value))
        self.record_path = Path(ROUTES['preparation_execution'])/'record.json'
        self.proof = dict(derivation=derivation, policy=policy, preparer=preparer,
            qualification=copy.deepcopy(self.qualification), preparation_record=str(self.record_path),
            source_manifest=manifest)
        b.plan.update(environment=dict(self.workload), launch_environment=dict(derivation['launch_environment']),
            startup_environment=self.proof, attempt=dict(path=str(owner.ROUTES), sha256=owner.ROUTES_SHA256),
            retry_qualification=copy.deepcopy(self.retry_qualification))
        b.launch['environment'] = dict(derivation['launch_environment'])
        wrapper = owner.ADAPTER/'prepare_once.py'
        s.bytes(self.record_path.parent/'launcher.py', s.raw(wrapper))
        b.expected['preparation_launcher'] = dict(path=str(wrapper), sha256=s.sha(wrapper))
        invocation = dict(adapter=dict(preparer=preparer, source_manifest=manifest,
            startup_controls=self.qualification['audit'], retry_controls=self.retry_qualification['audit']))
        self.invocation_path = '/fixture/retry-invocation.json'
        self.invocation = dict(path=self.invocation_path, sha256=s.json(self.invocation_path, invocation))
        command = ['/fixture/python', '-B', preparer['path'], '--phase', self.phase,
            '--preparation-record', str(self.record_path), '--preparation-passed-environment-json',
            environment.encoded(self.passed).decode(), '--startup-audit-sha256', self.qualification['audit']['sha256'],
            '--retry-audit-sha256', self.retry_qualification['audit']['sha256'],
            '--startup-source-manifest', manifest['path'], '--startup-source-manifest-sha256', manifest['sha256']]
        self.observation = dict(status='returned', pid=12, parent_pid=11, blocked_events=[], started_at=3,
            finished_at=4, command=command, environments=dict(passed=dict(self.passed),
                before_validation=dict(observed), before_producer_imports=dict(observed), at_return_or_failure=dict(observed)))
        self.record = dict(status='finished', returncode=0, preparation_passed=True, phase=self.phase, cwd=str(R),
            canonical_owner='producer-child', signals=[], runtime_admission=False, compiler_calls=0, provider_probes=0,
            environment=dict(self.passed), producer_command=command, command=['/fixture/python', '-B', str(wrapper)],
            source_sha256=s.sha(wrapper), pid=12, parent_pid=11, started_at=1, child_started_at=2, finished_at=5,
            readback_finished_at=6, invocation=self.invocation)
        self.refresh()

    def refresh(self):
        b, s = self.base, self.s
        packet, work, outer = [b.paths[k] for k in ['packet', 'work', 'outer']]
        b.launch['plan_sha256'] = s.json(packet/'plan.json', b.plan)
        b.terminal['plan_sha256'] = b.launch['plan_sha256']
        b.expected['launch'] = s.json(packet/'launch.json', b.launch)
        b.expected['receipt'] = s.json(work/'receipt.json', b.terminal)
        b.launcher['outer_sha256'] = s.json(outer/'status.json', b.outer)
        b.launcher['environment'] = dict(b.launch['environment'])
        b.launcher['launch_sha256'] = b.expected['launch']
        b.launcher['stdout_sha256'] = s.json(Path(b.expected['launcher_record']).parent/'stdout',
            dict(directory=str(outer), supervisor_pid=b.outer['supervisor_pid']))
        b.expected['launcher_record_sha256'] = s.json(b.expected['launcher_record'], b.launcher)
        self.record['outputs'] = {name: dict(sha256=s.sha(packet/name)) for name in ['plan.json', 'inputs.json', 'launch.json']}
        self.record['child_observation_sha256'] = s.json(self.record_path.parent/'child-observation.json', self.observation)
        b.expected['preparation'] = dict(path=str(self.record_path), sha256=s.json(self.record_path, self.record))

    def check(self, *, startup=None, retry=None):
        b = self.base
        return owner.owner(b.plan, b.launch, b.terminal, b.outer, b.launcher, phase=b.phase,
            expected=b.expected, sha=self.s.sha, read_json=self.s.read, original=b.reader,
            workload_environment=self.workload,
            validate_qualification=startup if startup is not None else lambda proof: b.reader.same(proof, self.qualification),
            validate_retry_qualification=retry if retry is not None else lambda proof: b.reader.same(proof, self.retry_qualification))


class Owner(unittest.TestCase):
    def test_complete_preflight05_keeps_raw_plan_and_16_gib_boundary(self):
        f = fixture(); before = copy.deepcopy(f.base.plan)
        self.assertEqual(f.check(), f.paths)
        self.assertEqual(f.base.plan, before)
        self.assertEqual(f.base.terminal['free_bytes_before'], 16 * 2**30)
        self.assertEqual(ROUTES['installation_entry_gib'], 24)

    def test_exact_plain_startup_without_cf_is_accepted(self):
        f = fixture(None); self.assertEqual(f.check(), f.paths)

    def test_old04_work_and_supervisor_paths_are_rejected(self):
        for field, value in [('work', ROUTES['failed_predecessor']['work']),
                             ('supervisor_work', ROUTES['failed_predecessor']['supervisor'])]:
            f = fixture(); f.base.plan[field] = value; f.refresh()
            with self.subTest(field=field), self.assertRaisesRegex(RuntimeError, 'phase/owner paths'):
                f.check()

    def test_old04_packet_cannot_supply_expected_launch(self):
        f = fixture(); old = Path(ROUTES['failed_predecessor']['packet'])/'launch.json'
        f.base.expected['launch'] = f.s.json(old, dict(f.base.launch, fixture_previous=True))
        with self.assertRaisesRegex(RuntimeError, 'packet/terminal association'): f.check()

    def test_old04_preparation_and_launcher_routes_are_rejected(self):
        f = fixture(); f.proof['preparation_record'] = str(f.record_path).replace('execution-05', 'execution-04'); f.refresh()
        with self.assertRaisesRegex(RuntimeError, 'preparation record reference'): f.check()
        f = fixture(); f.base.expected['launcher_record'] = str(Path(ROUTES['failed_predecessor']['launcher_execution'])/'record.json')
        f.refresh()
        with self.assertRaisesRegex(RuntimeError, 'launcher record/source binding'): f.check()

    def test_installation_cannot_use_preflight_policy(self):
        f = fixture(); f.base.phase = f.base.plan['phase'] = 'installation'
        with self.assertRaisesRegex(RuntimeError, 'preflight-only'): f.check()

    def test_attempt_reference_is_exact(self):
        for value in [None, {}, dict(path=str(owner.ROUTES), sha256='0'*64),
                      dict(path='/fixture/routes.json', sha256=owner.ROUTES_SHA256),
                      dict(path=str(owner.ROUTES), sha256=owner.ROUTES_SHA256, extra=True)]:
            f = fixture(); f.base.plan['attempt'] = value; f.refresh()
            with self.subTest(value=value), self.assertRaisesRegex(RuntimeError, 'retry descriptor'): f.check()

    def test_route_bytes_cannot_be_replaced(self):
        f = fixture(); f.s.json(owner.ROUTES, dict(ROUTES, installation_entry_gib=16))
        with self.assertRaisesRegex(RuntimeError, 'retry descriptor'): f.check()

    def test_preflight_capacity_cannot_be_relabelled(self):
        for field, value in [('entry_gib', 24), ('entry_gib', 16.0), ('stop_gib', 8), ('floor_gib', 7),
                             ('combined_namespace_bytes', 15*2**30), ('evidence_bytes', 257*2**20)]:
            f = fixture(); f.base.plan['capacity'][field] = value; f.refresh()
            with self.subTest(field=field, value=value), self.assertRaisesRegex(RuntimeError, 'phase/capacity'):
                f.check()

    def test_observed_admission_and_exit_floors_are_required(self):
        for field, value in [('free_bytes_before', 16*2**30-1), ('free_bytes_after', 9*2**30-1)]:
            f = fixture(); f.base.terminal[field] = value; f.refresh()
            with self.subTest(field=field), self.assertRaisesRegex(RuntimeError, 'admission/timing'): f.check()

    def test_retry_proof_requires_exact_true_and_is_detached(self):
        for answer in [False, None, 1, 'verified']:
            f = fixture()
            with self.subTest(answer=answer), self.assertRaisesRegex(RuntimeError, 'actual retry controls'):
                f.check(retry=lambda proof: answer)
        f = fixture(); before = copy.deepcopy(f.base.plan['retry_qualification'])
        def mutate(proof): proof['controls'] = 999; return False
        with self.assertRaises(RuntimeError): f.check(retry=mutate)
        self.assertEqual(f.base.plan['retry_qualification'], before)

    def test_old_startup_proof_does_not_replace_retry_proof(self):
        f = fixture(); f.base.plan['retry_qualification'] = copy.deepcopy(f.qualification); f.refresh()
        with self.assertRaisesRegex(RuntimeError, 'actual retry controls'): f.check()
        f = fixture()
        with self.assertRaisesRegex(RuntimeError, 'actual startup controls'): f.check(startup=lambda proof: False)

    def test_recipe_and_raw_startup_observations_remain_exact(self):
        f = fixture(); f.base.plan['environment']['PATH'] = '/foreign'; f.refresh()
        with self.assertRaisesRegex(RuntimeError, 'workload environment'): f.check()
        f = fixture(); f.observation['environments']['at_return_or_failure'][environment.CF] = '501:0:83'; f.refresh()
        with self.assertRaisesRegex(RuntimeError, 'raw preparation'): f.check()

    def test_actual_retry_argument_and_invocation_association_are_required(self):
        f = fixture(); args = f.record['producer_command']; args[args.index('--retry-audit-sha256')+1] = 'f'*64; f.refresh()
        with self.assertRaisesRegex(RuntimeError, 'startup arguments'): f.check()
        f = fixture(); invocation = f.s.read(f.invocation_path); invocation['adapter']['retry_controls'] = f.qualification['audit']
        f.record['invocation']['sha256'] = f.s.json(f.invocation_path, invocation); f.refresh()
        with self.assertRaisesRegex(RuntimeError, 'invoked startup source association'): f.check()

    def test_retry_sources_and_descriptor_are_in_actual_manifest(self):
        for name in ['routes.json', 'entry.py', 'controller.py', 'audit_owner.py', 'prepare_once.py', 'launch.py']:
            f = fixture(); rows = f.s.read(f.manifest_path); del rows['files'][str(owner.ADAPTER/name)]
            digest = f.s.json(f.manifest_path, rows); f.proof['source_manifest']['sha256'] = digest
            invocation = f.s.read(f.invocation_path); invocation['adapter']['source_manifest']['sha256'] = digest
            f.record['invocation']['sha256'] = f.s.json(f.invocation_path, invocation)
            args = f.record['producer_command']; args[args.index('--startup-source-manifest-sha256')+1] = digest; f.refresh()
            with self.subTest(name=name), self.assertRaises((RuntimeError, KeyError)): f.check()

    def test_policy_stays_qualified39_and_preparer_is_new05(self):
        for role, path in [('policy', owner.ADAPTER/'environment.py'), ('preparer', owner.STARTUP_SOURCE/'prepare.py')]:
            f = fixture(); f.proof[role] = dict(path=str(path), sha256=f.s.bytes(path, b'wrong owner')); f.refresh()
            with self.subTest(role=role), self.assertRaisesRegex(RuntimeError, 'startup source association'): f.check()

    def test_source_bytes_and_preparation_output_digests_are_bound(self):
        f = fixture(); f.s.bytes(owner.ADAPTER/'controller.py', b'changed')
        with self.assertRaisesRegex(RuntimeError, 'admission source'): f.check()
        f = fixture(); f.record['outputs']['inputs.json']['sha256'] = 'f'*64
        f.base.expected['preparation']['sha256'] = f.s.json(f.record_path, f.record)
        with self.assertRaisesRegex(RuntimeError, 'preparation output'): f.check()

    def test_preparation_must_be_closed_before_owner_start(self):
        f = fixture()
        for key in ['started_at', 'child_started_at', 'finished_at', 'readback_finished_at']: f.record[key] += 100
        for key in ['started_at', 'finished_at']: f.observation[key] += 100
        f.refresh()
        with self.assertRaisesRegex(RuntimeError, 'preparation chronology'): f.check()

    def test_terminal_closure_and_qualification_scope_remain_required(self):
        for key, value in [('status', 'failed'), ('pid', True), ('application_qualified', True),
                           ('performance_measurement', True), ('exporter_qualified', True), ('std_mir_prepared', True)]:
            f = fixture(); f.base.terminal[key] = value; f.refresh()
            with self.subTest(key=key), self.assertRaises(RuntimeError): f.check()


class LockFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='runtime-retry-lock-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.path = self.root/'canonical.lock'; self.path.write_bytes(b'')
        self.owned = load('_retry_owned_lock_fixture', OWNED_SOURCE)
        self.production_lock = self.owned.CANONICAL_LOCK
        self.assertEqual(self.production_lock, Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock'))
        self.owned.CANONICAL_LOCK = self.path

    def inherited(self, fd):
        return controller.inherited_admission(self.owned, fd)

    def assert_excluded(self):
        with self.path.open('r+') as other:
            with self.assertRaises(BlockingIOError): fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def assert_available(self):
        with self.path.open('r+') as other:
            fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_owner_fd_is_accepted_and_stays_owned_after_nested_scope(self):
        with self.owned.workload_lock(self.path, 1) as fd:
            with self.inherited(fd): self.assert_excluded()
            self.assert_excluded()
        self.assert_available()

    def test_duplicated_owner_description_is_accepted(self):
        with self.owned.workload_lock(self.path, 1) as fd:
            duplicate = os.dup(fd)
            try:
                with self.inherited(duplicate): self.assert_excluded()
            finally: os.close(duplicate)
            self.assert_excluded()

    def test_unheld_open_descriptor_is_rejected_without_taking_ownership(self):
        with self.path.open('r+') as opened:
            with self.assertRaisesRegex(RuntimeError, 'already held|preheld|not held'):
                with self.inherited(opened.fileno()): self.fail('unheld inherited descriptor accepted')
        self.assert_available()

    def test_different_open_description_cannot_inherit_current_owner(self):
        with self.owned.workload_lock(self.path, 1):
            with self.path.open('r+') as other:
                with self.assertRaises(RuntimeError):
                    with self.inherited(other.fileno()): self.fail('foreign description accepted')
            self.assert_excluded()

    def test_wrong_file_descriptor_is_rejected(self):
        foreign = self.root/'foreign.lock'; foreign.write_bytes(b'')
        with self.owned.workload_lock(self.path, 1):
            with foreign.open('r+') as other:
                with self.assertRaises(RuntimeError):
                    with self.inherited(other.fileno()): self.fail('wrong file accepted')
            self.assert_excluded()

    def test_closed_and_invalid_descriptors_are_rejected(self):
        with self.path.open('r+') as opened: closed = opened.fileno()
        for fd in [closed, -1, None, True, '3']:
            with self.subTest(fd=fd), self.assertRaises((RuntimeError, OSError, TypeError, ValueError)):
                with self.inherited(fd): self.fail('invalid descriptor accepted')
        self.assert_available()

    def test_unmodified_old_helper_acquires_unheld_descriptor(self):
        # This documents the original helper contract; the new wrapper adds the
        # preheld observation. Do not relabel the old helper as rejecting this.
        with self.path.open('r+') as opened:
            with self.owned.workload_lock(self.path, 1, inherited_fd=opened.fileno()): self.assert_excluded()
            self.assert_excluded()
        self.assert_available()


class ControllerAdmission(LockFixture):
    def reach(self, fd, *, change=None, observed=None):
        c = controller
        plan = dict(attempt=dict(path=str(c.ROUTES), sha256=c.ROUTES_SHA256), phase='preflight', owner=str(c.R),
            work=ROUTES['work'], supervisor_work=ROUTES['supervisor'], capacity=copy.deepcopy(ROUTES['capacity']),
            launch_environment={'LANG': 'C'}, specification={'path': '/fixture/specification.json'})
        if change is not None: change(plan)
        def read(path):
            if Path(path) == c.ROUTES: return copy.deepcopy(ROUTES)
            self.provider_read.assert_not_called()
            return self.provider_read(path)
        self.provider_read = Mock(side_effect=LookupError('admission passed; stop before providers'))
        monitor = SimpleNamespace(owned=self.owned)
        with patch.object(c, 'os', SimpleNamespace(environ={'LANG': 'C'} if observed is None else observed)), \
             patch.object(c.Path, 'cwd', return_value=c.R):
            c.Controller(plan=plan, inputs_sha256='0'*64, q=None, recipe=None,
                reader=SimpleNamespace(reader=SimpleNamespace(monitor=object())), monitor=monitor,
                check_frozen=Mock(), read_json=read, read_bytes=Mock(), sha=lambda path:c.ROUTES_SHA256,
                canonical_fd=fd)

    def test_current_owner_reaches_specification_without_reacquiring_lock(self):
        with self.owned.workload_lock(self.path, 1) as fd:
            with self.assertRaisesRegex(LookupError, 'stop before providers'): self.reach(fd)
            self.assertEqual(self.provider_read.call_count, 1); self.assert_excluded()

    def test_invalid_descriptor_fails_before_specification(self):
        for fd in [None, True, -1]:
            with self.subTest(fd=fd), self.assertRaises(RuntimeError): self.reach(fd)
            self.provider_read.assert_not_called()

    def test_unheld_descriptor_fails_before_specification(self):
        with self.path.open('r+') as opened:
            with self.assertRaises(RuntimeError): self.reach(opened.fileno())
            self.provider_read.assert_not_called()
        self.assert_available()

    def test_old_attempt_and_phase_routes_fail_before_specification(self):
        changes = [lambda p:p.update(attempt=None), lambda p:p.update(phase='installation'),
                   lambda p:p.update(work=ROUTES['failed_predecessor']['work']),
                   lambda p:p.update(supervisor_work=ROUTES['failed_predecessor']['supervisor'])]
        with self.owned.workload_lock(self.path, 1) as fd:
            for change in changes:
                with self.assertRaises(RuntimeError): self.reach(fd, change=change)
                self.provider_read.assert_not_called()

    def test_24_gib_policy_is_not_silently_used_for_preflight05(self):
        with self.owned.workload_lock(self.path, 1) as fd:
            with self.assertRaisesRegex(RuntimeError, 'bounds'):
                self.reach(fd, change=lambda p:p['capacity'].update(entry_gib=24))
            self.provider_read.assert_not_called()

    def test_undeclared_launch_environment_fails_before_specification(self):
        with self.owned.workload_lock(self.path, 1) as fd:
            with self.assertRaisesRegex(RuntimeError, 'launch context'): self.reach(fd, observed={'LANG':'C', 'EXTRA':'x'})
            self.provider_read.assert_not_called()

    def test_execute_rechecks_preheld_exclusion_before_disk_or_workload(self):
        instance = controller.Controller.__new__(controller.Controller)
        instance.owned = self.owned; instance.record = {}; instance.save = Mock()
        instance.full_guard = Mock(); instance.recipe = SimpleNamespace(execute_preflight=Mock())
        with self.path.open('r+') as opened, patch.object(self.owned, 'disk', side_effect=AssertionError('disk reached')) as disk:
            instance.fd = opened.fileno()
            with self.assertRaises(RuntimeError): instance.execute()
            disk.assert_not_called(); instance.full_guard.assert_not_called(); instance.recipe.execute_preflight.assert_not_called()
        self.assertEqual(instance.record['status'], 'failed'); self.assert_available()
