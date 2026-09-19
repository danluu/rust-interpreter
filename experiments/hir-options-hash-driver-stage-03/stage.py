"""Enclosing hash-driver controller draft; no concrete admission exists yet.

Preparation must supply actual completed compiler, B3, native and run-make
evidence. Missing prerequisites fail before the three-command core is called.
This file imports definitions only; main is the sole execution entry point.
"""
import argparse
import ast
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
A = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
O = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
WORK = ROOT/'.work/hir-options-hash-driver-02'
REVISION = '4de35bdacef0e3cd18a66bc30b5459c19e09b118'
NATIVE_SOURCE = A/'experiments/hir-options-hash-native-controls-03'
NATIVE_WORK = A/'.work/hir-options-hash-native-controls-03'
NATIVE_QUALIFICATION_SOURCE = A/'experiments/hir-options-hash-native-reconciliation-01'
NATIVE_QUALIFICATION_WORK = A/'.work/hir-options-hash-native-controls-reconciliation-01'
NATIVE_FAILURE_AUDIT = dict(path=str(A/'.work/native-controls-failure-verification-03.json'),
    sha256='1058d64e64d75748a3da12115a8400a01daa5cd499b39b09c8d29520eaab4f24')
BETA_SOURCE = A/'experiments/hir-options-hash-beta-composition-08'
BETA_WORK = A/'.work/hir-options-hash-beta-composition-08'
RECIPE_SOURCE = O/'experiments/hir-options-hash-run-make-stage-02'
RECIPE_WORK = O/'.work/hir-options-hash-run-make-01'
SNAPSHOT_SOURCE = A/'experiments/bounded-proof-snapshots-v2/proof_snapshots.py'
SNAPSHOT_TESTS = [SNAPSHOT_SOURCE.with_name(name) for name in
                  ['test_proof_snapshots.py', 'test_reference_reuse.py']]
SNAPSHOT_CONTROLS = A/'experiments/bounded-proof-snapshot-controls-v2-01'
SNAPSHOT_CONTROL_WORK = A/'.work/bounded-proof-snapshot-controls-v2-01'
SNAPSHOT_AUDIT = A/'.work/proof-snapshot-controls-v2-independent-verification-01.json'
SNAPSHOT_LIMITS = dict(maximum_files=1024, maximum_file_bytes=64*2**20,
    maximum_logical_bytes=512*2**20, maximum_compressed_bytes=128*2**20,
    maximum_manifest_bytes=4*2**20)
REMAINING_EVIDENCE_RESERVATION = 32*2**20
CONTINUATION_SOURCE = HERE/'continuation_controls.py'
FAILED_READER_SOURCE = HERE/'failed_driver.py'
FAILED_SOURCE = ROOT/'experiments/hir-options-hash-driver-stage-02'
FAILED_WORK = ROOT/'.work/hir-options-hash-driver-01'
FAILED_AUDIT = dict(path=str(ROOT/'.work/hir-options-hash-driver-failure-verification-01.json'),
    sha256='ee81a129d5d1742074619ea31b75ad06512abd110dd102dc0ac8bec8c3eda8b3')
CATALOG_SOURCE = ROOT/'experiments/completed-proof-snapshot-catalog-02/catalog.py'
PLAN_REFERENCE_SOURCE = HERE/'plan_reference.py'
METADATA_PLAN_REFERENCE = dict(path=str(X/'experiments/hir-options-hash/compiler-metadata-03/plan.json'),
    sha256='250b19e48b158efe78e726e78223791cb4ff55b5b5d2b9eaa59b41ba2b1727c2')
FILE_TABLE_SOURCE = ROOT/'experiments/frozen-file-table-delta-01/file_table.py'
FILE_TABLE_TESTS = [FILE_TABLE_SOURCE.with_name('test_file_table.py')]
FILE_TABLE_CONTROLS = ROOT/'experiments/frozen-file-table-delta-controls-01'
FILE_TABLE_CONTROL_WORK = ROOT/'.work/frozen-file-table-delta-controls-01'
FILE_TABLE_AUDIT = ROOT/'.work/frozen-file-table-delta-controls-independent-verification-01.json'
FILE_TABLE_BASE = dict(path=str(NATIVE_SOURCE/'inputs.json'),
    sha256='8569abb81a61e34b6b5a892116af5218557ceb0436ab8dbf8a31f2aec55b1b1d')
DRIVER_ENVIRONMENT_KEYS = frozenset({
    'PATH', 'HOME', 'USER', 'LOGNAME', 'LANG', 'LC_ALL', 'TZ', 'TMPDIR',
    'SDKROOT', 'PYTHONDONTWRITEBYTECODE', 'PYTHONNOUSERSITE', '__CF_USER_TEXT_ENCODING',
})
BOOTSTRAP_ENVIRONMENT_KEYS = frozenset({
    'CARGO_BUILD_JOBS', 'CARGO_HOME', 'CARGO_NET_OFFLINE', 'CARGO_TERM_COLOR',
    'CC', 'CXX', 'GIT_CONFIG_COUNT', 'GIT_CONFIG_GLOBAL', 'GIT_CONFIG_KEY_0',
    'GIT_CONFIG_KEY_1', 'GIT_CONFIG_KEY_2', 'GIT_CONFIG_NOSYSTEM',
    'GIT_CONFIG_VALUE_0', 'GIT_CONFIG_VALUE_1', 'GIT_CONFIG_VALUE_2',
    'GIT_OPTIONAL_LOCKS', 'GIT_TERMINAL_PROMPT', 'RUSTUP_DIST_SERVER',
})


def driver_environment(inherited, temporary):
    """Select the direct-rustc environment; retain every omitted bootstrap key."""
    if set(inherited) - DRIVER_ENVIRONMENT_KEYS != BOOTSTRAP_ENVIRONMENT_KEYS:
        raise RuntimeError('unreviewed predecessor environment keys')
    selected = {key: value for key, value in inherited.items() if key in DRIVER_ENVIRONMENT_KEYS}
    selected['TMPDIR'] = str(temporary)
    omitted = {key: inherited[key] for key in sorted(BOOTSTRAP_ENVIRONMENT_KEYS)}
    return selected, omitted


@contextmanager
def aliases(values):
    missing = object()
    previous = {name: sys.modules.get(name, missing) for name in values}
    old_path = list(sys.path)
    sys.modules.update(values)
    try:
        yield
    finally:
        sys.path[:] = old_path
        for name, value in previous.items():
            if value is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value


def module(name, path, dependencies=None):
    name = '_hash_stage_' + name
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    try:
        with aliases(dependencies or {}):
            spec.loader.exec_module(value)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return value


def dependencies():
    """Keep similarly named diagnostic/recipe modules isolated."""
    deadline = module('deadline', ROOT/'experiments/hir-driver-deadline/deadline.py')
    owned_driver = module('owned_driver', ROOT/'experiments/hir-driver-deadline/owned_driver.py',
                          {'deadline': deadline})
    observations = module('driver_observations', ROOT/'experiments/hir-driver-observations/observations.py')
    trace = module('loader_trace', ROOT/'experiments/hir-driver-observations/loader_trace.py',
                   {'observations': observations})
    core = module('core', HERE/'controls.py', {'owned_driver': owned_driver, 'loader_trace': trace})
    predecessor = module('prerequisites', HERE/'prerequisites.py')
    native_recipe = module('native_recipe', NATIVE_SOURCE/'recipe.py')
    native_observed = module('native_observed', NATIVE_SOURCE/'observations.py')
    wrong_beta = module('wrong_beta', NATIVE_QUALIFICATION_SOURCE/'wrong_beta.py')
    adapter = module('recipe_adapter', RECIPE_SOURCE/'adapter.py')
    bundle = adapter.load_bundle()
    monitor = adapter.monitor()
    metadata = adapter.metadata()
    comp = module('composition', BETA_SOURCE/'compose_sysroot.py')
    snapshot_bindings = module('snapshot_bindings', HERE/'snapshot_bindings.py')
    return dict(core=core, predecessor=predecessor, trace=trace, recipe=native_recipe,
                observed=native_observed, adapter=adapter, bundle=bundle, monitor=monitor,
                metadata=metadata, comp=comp, snapshot_bindings=snapshot_bindings, wrong_beta=wrong_beta)


def snapshot_records(freeze, inputs_sha256, comp):
    names = freeze['snapshot_inputs']
    comp.require(type(names) is list and names == sorted(set(names))
                 and set(names) <= set(freeze['files'])
                 and str(HERE/'inputs.json') not in names, 'exact snapshot selection required')
    return [dict(path=name, **freeze['files'][name]) for name in names] + [
        comp.check_file(dict(path=str(HERE/'inputs.json'), sha256=inputs_sha256))]


def snapshot_reservation(projection, records, bindings):
    if set(projection['files']) != {row['path'] for row in records}:
        raise RuntimeError('physical reservation omits logical source records')
    return bindings.reservation(projection, SNAPSHOT_LIMITS['maximum_manifest_bytes'],
                                REMAINING_EVIDENCE_RESERVATION)


def snapshot_predecessors(audits):
    return [dict(role='beta', source=str(BETA_SOURCE), evidence=str(BETA_WORK), audit=audits['beta']),
            dict(role='native', source=str(NATIVE_SOURCE), evidence=str(NATIVE_WORK), audit=NATIVE_FAILURE_AUDIT,
                 qualification=dict(source=str(NATIVE_QUALIFICATION_SOURCE), evidence=str(NATIVE_QUALIFICATION_WORK),
                                    audit=audits['native']))]


def snapshot_directory(path, snapshots):
    path = Path(path); snapshots.ordinary_route(path)
    before = snapshots.identity(path.lstat()); children = sorted(os.listdir(path))
    if snapshots.identity(path.lstat()) != before:
        raise RuntimeError('snapshot proof directory changed during listing')
    return dict(identity=before, children=children)


def load_snapshots(freeze, comp):
    comp.require(str(SNAPSHOT_SOURCE) in freeze['files'], 'snapshot helper missing from freeze')
    row = dict(path=str(SNAPSHOT_SOURCE), **freeze['files'][str(SNAPSHOT_SOURCE)])
    comp.require(comp.check_file(row) == row, 'snapshot helper changed before import')
    return module('verified_snapshots', SNAPSHOT_SOURCE)


def load_file_table(freeze, comp):
    """Import only the helper bytes already authenticated by this packet."""
    comp.require(str(FILE_TABLE_SOURCE) in freeze['files'], 'file-table helper missing from delta freeze')
    row = dict(path=str(FILE_TABLE_SOURCE), **freeze['files'][str(FILE_TABLE_SOURCE)])
    comp.require(comp.check_file(row) == row, 'file-table helper changed before import')
    return module('file_table', FILE_TABLE_SOURCE)


def expand_file_table(wire, table, guard=lambda: None):
    """Expose all original rows while preserving the actual compact-file hash."""
    table.require(wire.get('file_table_base') == FILE_TABLE_BASE,
                  'exact original native03 file-table base required')
    return table.expand(wire, guard=guard)


def continuation_qualification(*, read_json, read_bytes, sha, file_record):
    file_record(CONTINUATION_SOURCE)
    helper = module('continuation_controls', CONTINUATION_SOURCE)
    return helper.qualify(read_json=read_json, read_bytes=read_bytes, sha=sha, file_record=file_record)


def failed_owner():
    return dict(role='failed-hash-driver-01', source=str(FAILED_SOURCE), evidence=str(FAILED_WORK),
                audit=dict(FAILED_AUDIT))


def continued_catalog(modules, freeze, comp, audits, evidence_roots, snapshots, *,
                      read_json, read_bytes, sha, file_record, directory_record, check_absent, guard):
    """Reuse audited closed failure bytes without qualifying the failed workload."""
    continuation_qualification(read_json=read_json, read_bytes=read_bytes, sha=sha, file_record=file_record)
    file_record(CATALOG_SOURCE); file_record(FAILED_READER_SOURCE)
    catalog = module('closed_catalog', CATALOG_SOURCE)
    failure = module('failed_driver', FAILED_READER_SOURCE)
    prior = modules['snapshot_bindings'].catalog(snapshot_predecessors(audits), evidence_roots,
        SNAPSHOT_LIMITS, read_json=read_json, file_record=file_record, directory_record=directory_record)
    def expand_inputs(wire, input_file):
        table = load_file_table(wire, comp)
        return expand_file_table(wire, table, guard=guard)
    result = catalog.extend_failed(prior, failed_owner(), evidence_roots, SNAPSHOT_LIMITS,
        read_json=read_json, file_record=file_record, directory_record=directory_record,
        expand_inputs=expand_inputs,
        validate_failure=lambda owner, terminal, audit: failure.validate(owner, terminal, audit,
            read_json=read_json, read_bytes=read_bytes, sha=sha, check_absent=check_absent,
            directory_record=directory_record))
    for row in result['records']:
        snapshots.verify_reference(row, result['evidence_roots'], guard)
    return result


def load_plan_reference(freeze, comp):
    """Authenticate this helper before importing it, as for file-table readers."""
    row = dict(path=str(PLAN_REFERENCE_SOURCE), **freeze['files'][str(PLAN_REFERENCE_SOURCE)])
    comp.require(comp.check_file(row) == row, 'plan-reference helper changed before import')
    return module('plan_reference', PLAN_REFERENCE_SOURCE)


def expand_plan(wire, helper, read_bytes):
    """Reconstruct the complete typed plan, retaining the raw wire file hash."""
    helper.require(wire.get('member') == 'metadata_plan', 'exact external metadata member required')
    return helper.expand(wire, expected_reference=METADATA_PLAN_REFERENCE, read_bytes=read_bytes)


class Stage:
    def __init__(self, inputs_sha256, snapshot_plan_sha256):
        self.modules = dependencies()
        self.core = self.modules['core']
        self.monitor = self.modules['monitor']
        self.owned = self.monitor.owned
        self.comp = self.modules['comp']
        self.require = self.core.require
        self.require(Path.cwd() == ROOT and sys.dont_write_bytecode and not sys.flags.optimize,
                     'explicit root and unoptimized Python -B required')
        self.require(self.owned.sha(HERE/'inputs.json') == inputs_sha256, 'reviewed hash freeze required')
        self.inputs_sha256 = inputs_sha256
        wire = self.read_json(HERE/'inputs.json', frozen=False)
        table = load_file_table(wire, self.comp)
        self.freeze = expand_file_table(wire, table, guard=lambda: self.owned.disk(ROOT, 9))
        self.file_table_qualification()
        self.bind_snapshot_plan(snapshot_plan_sha256)
        self.snapshots = load_snapshots(self.freeze, self.comp)
        continuation_proof = continuation_qualification(read_json=self.read_json, read_bytes=self.read_bytes,
            sha=lambda p: self.owned.sha(self.frozen(p)),
            file_record=lambda p: dict(path=str(self.frozen(p)), **self.freeze['files'][str(p)]))
        plan_reference = load_plan_reference(self.freeze, self.comp)
        self.plan = expand_plan(self.read_json(HERE/'plan.json'), plan_reference, self.read_bytes)
        self.require(self.plan['continuation_controls'] == continuation_proof
                     and self.plan['failed_driver'] == failed_owner(), 'actual continuation qualification changed')
        self.require(self.owned.sha(HERE/'plan.json') == self.freeze['plan_sha256'], 'hash plan differs')
        self.require(str(Path(sys.executable).resolve(strict=True)) == self.freeze['python'], 'Python route differs')
        self.require(self.plan['candidate_revision'] == REVISION, 'hash candidate differs')
        self.require(self.plan['children'] == self.core.desired_commands(self.plan), 'hash commands differ')
        self.environment = dict(os.environ)
        expected = self.freeze['launch_environment']
        extra = set(self.environment) - set(expected)
        self.require(all(self.environment.get(k) == v for k, v in expected.items())
                     and extra <= {'__CF_USER_TEXT_ENCODING'}, 'hash controller environment differs')
        if extra:
            parts = self.environment['__CF_USER_TEXT_ENCODING'].split(':')
            self.require(len(parts) == 3 and all(re.fullmatch(r'(?:0[xX][0-9a-fA-F]{1,8}|[0-9]{1,10})', p) for p in parts)
                         and int(parts[0], 16 if parts[0].lower().startswith('0x') else 10) == os.getuid() == 501,
                         'unproved Darwin context')
        self.require(not WORK.exists() and not WORK.is_symlink() and WORK.parent.resolve(strict=True) == WORK.parent,
                     'fresh hash evidence required')
        WORK.mkdir()
        self.record = dict(status='waiting', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(),
            candidate_revision=REVISION, inputs_sha256=inputs_sha256,
            snapshot_plan_sha256=snapshot_plan_sha256, application_qualified=False,
            performance_measurement=False, runtime_installation=False, hash_driver_qualified=False,
            failed_driver=self.plan['failed_driver'], continuation_controls=self.plan['continuation_controls'])
        self.save()

    def save(self):
        self.owned.write(WORK/'receipt.json', self.record)

    def frozen(self, path):
        path = Path(path)
        self.require(str(path) in self.freeze['files'], 'unfrozen hash input: '+str(path))
        row = dict(path=str(path), **self.freeze['files'][str(path)])
        self.require(self.comp.check_file(row) == row, 'hash input identity or bytes changed')
        return path

    def read_bytes(self, path, *, frozen=True):
        path = self.frozen(path) if frozen else Path(path)
        self.require(path.stat().st_size <= 256*2**20, 'bounded readback file required')
        return path.read_bytes()

    def read_json(self, path, *, frozen=True):
        return json.loads(self.read_bytes(path, frozen=frozen),
                          object_pairs_hook=self.modules['observed'].unique_object,
                          parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))

    def guard(self, full=False):
        self.require(dict(os.environ) == self.environment and self.owned.sha(HERE/'inputs.json') == self.inputs_sha256,
                     'hash environment/freeze changed')
        self.require(self.comp.check_file(self.snapshot_plan_file) == self.snapshot_plan_file,
                     'hash snapshot projection changed')
        for name, row in self.freeze['files'].items():
            self.require(self.comp.ordinary(name) == row['identity'], 'hash input stamp changed')
            if full:
                self.frozen(name)
        for name, row in self.freeze['links'].items():
            path = Path(name); info = path.lstat()
            stamp = [info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink]
            self.require(path.is_symlink() and stamp == row['stamp'] and os.readlink(path) == row['target']
                         and str(path.resolve(strict=True)) == row['resolved'], 'hash provider link changed')
        for name in self.freeze['absent_paths']:
            self.require(not Path(name).exists() and not Path(name).is_symlink(), 'hash admitted absence changed')
        for name, resolved in self.plan['executor_routes'].items():
            self.require(str(Path(name).resolve(strict=True)) == resolved, 'hash executor route changed')
        for imported in list(sys.modules.values()):
            path = getattr(imported, '__file__', None)
            if path and path.startswith('/Users/danluu/dev/'):
                self.require(str(Path(path).resolve(strict=True)) in self.freeze['files'], 'unfrozen hash import')
        bundle = self.modules['bundle']
        bundle.support.ancestor_guard(full)
        bundle.support.source_guard()
        metadata_freeze = self.read_json(X/'experiments/hir-options-hash/compiler-metadata-03/inputs.json')
        for name, row in metadata_freeze['files'].items():
            self.require(name in self.freeze['files'] and self.freeze['files'][name]['sha256'] == row['sha256'],
                         'hash freeze omits original metadata input')
        self.modules['metadata'].guard(self.plan['metadata_plan'], metadata_freeze, full)
        if full:
            self.require(set(self.plan['immutable_trees']) == set(map(str, [self.core.D2, self.core.E2, self.core.B3])),
                         'complete build/application/provider trees required')
            for root, catalog in self.plan['immutable_trees'].items():
                self.require(bundle.support.inventory(Path(root)) == self.read_json(catalog),
                             'complete compiler/provider inventory differs')
        platform = os.uname()
        self.require(self.plan['platform'] == dict(system=platform.sysname, release=platform.release,
                     version=platform.version, machine=platform.machine), 'hash platform identity differs')

    def inherited_freeze(self, source):
        prior = self.read_json(source/'inputs.json')
        prior_plan = self.read_json(source/'plan.json')
        self.require(self.owned.sha(source/'plan.json') == prior['plan_sha256'], 'predecessor plan differs')
        if source == NATIVE_QUALIFICATION_SOURCE:
            base = dict(path=str(NATIVE_SOURCE/'inputs.json'), sha256=self.owned.sha(self.frozen(NATIVE_SOURCE/'inputs.json')))
            self.require(prior['base_inputs'] == prior_plan['base_inputs'] == base,
                         'native reconciliation compact base binding differs')
            self.inherited_freeze(NATIVE_SOURCE)
        else:
            self.require('base_inputs' not in prior, 'unreviewed inherited proof base')
        for name, row in prior['files'].items():
            self.require(name in self.freeze['files'] and self.freeze['files'][name]['sha256'] == row['sha256'],
                         'hash freeze omits predecessor input')
        for name, row in prior.get('links', {}).items():
            self.require(self.freeze['links'].get(name) == row, 'hash freeze omits predecessor route')
        self.require(set(prior.get('absent_paths', [])) <= set(self.freeze['absent_paths']),
                     'hash freeze omits predecessor absence')
        return prior_plan

    def audit(self, name, receipt):
        reference = self.plan['independent_audits'][name]
        proof = self.read_json(reference['path'])
        self.require(self.owned.sha(reference['path']) == reference['sha256']
                     and proof['status'] == 'verified' and proof['receipt_sha256'] == self.owned.sha(receipt),
                     'actual independent predecessor audit required')

    def retained_snapshot_proof(self, source, evidence, terminal):
        projection = self.read_json(source/'snapshot-plan.json')
        manifest = self.read_json(evidence/'source-snapshots.json')
        self.require(self.owned.sha(source/'snapshot-plan.json')
                     == self.owned.sha(evidence/'snapshot-plan.json') == terminal['snapshot_plan_sha256']
                     and projection['inputs_sha256'] == self.owned.sha(source/'inputs.json')
                     and self.owned.sha(evidence/'source-snapshots.json') == terminal['source_snapshots_sha256']
                     and manifest['full_logical_readback'] is True and manifest['full_gzip_eof'] is True,
                     'completed compressed predecessor snapshot proof differs')

    def snapshot_reuse(self):
        """Rebuild exact closed predecessor ownership before granting reuse."""
        def file_record(path):
            self.snapshots.ordinary_route(Path(path))
            self.frozen(path)
            return dict(path=str(path), **self.freeze['files'][str(path)])
        def check_absent(path):
            self.require(str(path) in self.freeze['absent_paths'] and not Path(path).exists()
                         and not Path(path).is_symlink(), 'frozen failed output absence changed')
            return True
        bindings = continued_catalog(self.modules, self.freeze, self.comp, self.plan['independent_audits'],
            self.plan['evidence_roots'], self.snapshots, read_json=self.read_json, read_bytes=self.read_bytes,
            sha=lambda path: self.owned.sha(self.frozen(path)), file_record=file_record,
            directory_record=lambda path: snapshot_directory(path, self.snapshots),
            check_absent=check_absent, guard=lambda: self.owned.disk(ROOT, 9))
        self.require(bindings == self.plan['snapshot_reuse'], 'closed snapshot predecessor catalog changed')
        records = snapshot_records(self.freeze, self.inputs_sha256, self.comp)
        catalog = module('closed_catalog', self.frozen(CATALOG_SOURCE))
        selected = catalog.select(records, bindings)
        self.require(selected == self.snapshot_plan['reuse_selection'], 'complete reference selection changed')
        return selected

    def prerequisites(self):
        """All operations are frozen file reads and pure parsing."""
        bundle = self.modules['bundle']
        actual = bundle.support.completed_build(self.frozen)
        compiler = actual['compiled']
        self.require(compiler['candidate_revision'] == REVISION
                     and compiler['source_identity'] == self.plan['source_identity'], 'compiler identity differs')
        compiler_plan = self.read_json(bundle.support.BHERE/'plan.json')
        self.require(compiler_plan['metadata_plan'] == self.plan['metadata_plan'], 'compiler metadata association differs')
        self.audit('compiler', bundle.support.BUILT/'receipt.json')
        beta_plan = self.inherited_freeze(BETA_SOURCE)
        beta = self.read_json(BETA_WORK/'receipt.json')
        self.require(beta['assembly_and_auxiliary_strip_qualified'] is True and len(beta_plan['children']) == 19,
                     'actual B3 qualification required')
        self.require(beta['candidate_revision'] == REVISION
                     and beta['inputs_sha256'] == self.owned.sha(BETA_SOURCE/'inputs.json'),
                     'B3 candidate/freeze association differs')
        self.modules['predecessor'].command_history(beta, beta_plan['children'], evidence=BETA_WORK,
            read_json=self.read_json, read_bytes=self.read_bytes)
        self.require(self.comp.output_inventory(self.core.B3) == self.read_json(BETA_WORK/'assembly/output-inventory.json'),
                     'B3 complete payload differs')
        self.require(self.owned.sha(BETA_WORK/'assembly/output-inventory.json') == beta['assembly']['output_inventory_sha256']
                     and self.owned.sha(self.frozen(BETA_WORK/'strip-proof.json')) == beta['strip_proof_sha256'],
                     'B3 producer inventory/strip proof differs')
        self.audit('beta', BETA_WORK/'receipt.json')
        self.retained_snapshot_proof(BETA_SOURCE, BETA_WORK, beta)
        native_plan = self.inherited_freeze(NATIVE_QUALIFICATION_SOURCE)
        environment, omitted = driver_environment(native_plan['environment'], self.core.ARTIFACTS/'tmp')
        self.require(self.plan['environment'] == environment
                     and self.plan['omitted_bootstrap_environment'] == omitted,
                     'hash environment does not match the qualified native predecessor')
        native = self.read_json(NATIVE_WORK/'receipt.json')
        native_qualification = self.read_json(NATIVE_QUALIFICATION_WORK/'receipt.json')
        result = self.read_json(NATIVE_QUALIFICATION_WORK/'native-controls.json')
        self.require(native['inputs_sha256'] == self.owned.sha(NATIVE_SOURCE/'inputs.json')
                     and native_plan['assembly']['source'] == str(BETA_SOURCE)
                     and native_plan['assembly']['evidence'] == str(BETA_WORK)
                     and native_plan['assembly']['receipt_sha256'] == self.owned.sha(BETA_WORK/'receipt.json')
                     and native_plan['assembly']['inputs_sha256'] == beta['inputs_sha256']
                     and native_plan['compiler'] == beta_plan['actual_build']
                     and native_plan['ordered_driver_destinations'] == beta['producer_proof']['ordered_driver_destinations'],
                     'native-to-B3 predecessor binding differs')
        # The ordinary positive compile has no HIR/JSON parser to call clean
        # implicitly. Repeat the native producer's check for every fixture
        # compile, including that otherwise uncovered first positive row.
        for index in [7, 9, 11, 13, 14, 15, 16]:
            self.modules['observed'].clean(self.read_bytes(NATIVE_WORK/'commands'/f'{index:03}'/'stderr'))
        def verify_beta_provider(row):
            self.frozen(row['path'])
            actual = dict(path=row['path'], **self.freeze['files'][row['path']])
            self.require(actual == row, 'wrong-B3 diagnostic provider differs from frozen bytes')
            return actual
        native_proof = self.modules['predecessor'].native_controls(native_plan, native, result,
            evidence=NATIVE_WORK, read_json=self.read_json, read_bytes=self.read_bytes,
            recipe=self.modules['recipe'], observations=self.modules['observed'], loader_trace=self.modules['trace'],
            qualification_terminal=native_qualification, qualification_evidence=NATIVE_QUALIFICATION_WORK,
            wrong_beta=self.modules['wrong_beta'], beta_providers=native_plan['wrong_beta_providers'],
            verify_provider=verify_beta_provider)
        self.require(native_plan['source_identity'] == self.plan['source_identity']
                     and [str(self.core.B3/name) for name in result['ordered_driver_destinations']]
                         == self.plan['ordered_driver_pair'], 'hash role pair differs from actual native controls')
        self.audit('native', NATIVE_QUALIFICATION_WORK/'receipt.json')
        self.retained_snapshot_proof(NATIVE_SOURCE, NATIVE_WORK, native)
        recipe_plan = self.inherited_freeze(RECIPE_SOURCE)
        recipe = self.read_json(RECIPE_WORK/'receipt.json')
        recipe_result = self.read_json(RECIPE_WORK/'result.json')
        compiler_audit = bundle.prerequisite.audit(actual,
            **recipe_plan['independent_verification'], frozen=self.frozen)
        compiler_reference = bundle.prerequisite.reference(actual, compiler_audit)
        self.require(recipe_plan['compiler_prerequisite'] == compiler_reference
                     and recipe_result['compiler_prerequisite'] == compiler_reference
                     and recipe_plan['source_identity'] == self.plan['source_identity'],
                     'run-make compiler history association differs')
        self.require(self.owned.sha(RECIPE_WORK/'result.json') == recipe['result_sha256']
                     and recipe_result['status'] == 'passed'
                     and recipe_result['policy'] == 'unchanged-hir-body-cache-run-make-v1'
                     and recipe_result['source_identity'] == self.plan['source_identity']
                     and recipe_result['inputs_sha256'] == self.owned.sha(RECIPE_SOURCE/'inputs.json')
                     and recipe_result['plan_sha256'] == self.owned.sha(RECIPE_SOURCE/'plan.json')
                     and recipe_result['actual_commands'] == recipe['commands'],
                     'run-make result/history binding differs')
        self.require(recipe_result['native_recipe_qualified'] is True
                     and all(recipe_result[key] is False for key in
                         ['performance_measurement', 'application_qualified', 'hash_driver_qualified'])
                     and [recipe_result[key] for key in ['recipe_compilations', 'recipe_executions',
                         'nested_commands', 'compiler_commands', 'native_runs', 'expected_compiler_failures']]
                         == [1, 1, 230, 144, 86, 39], 'run-make result scope differs')
        self.require(recipe['native_recipe_qualified'] is True and recipe['recipe_compilations'] == 1
                     and recipe['recipe_executions'] == 1 and recipe['nested_commands'] == 230,
                     'completed run-make recipe required')
        self.require(len(recipe_plan['children']) == 2, 'run-make command count differs')
        history = self.modules['predecessor'].command_history(recipe, recipe_plan['children'], evidence=RECIPE_WORK,
            read_json=self.read_json, read_bytes=self.read_bytes)
        self.require(not history['rows'][1]['stdout'], 'unexpected run-make stdout')
        nested = bundle.history.audit(history['rows'][1]['stderr'], out=str(bundle.support.OUT),
            rustc=str(self.core.E2/'bin/rustc'), target=self.core.H,
            recipe_dyld=recipe_plan['children'][1]['environment']['DYLD_LIBRARY_PATH'], e2=str(self.core.E2))
        self.require(nested == self.read_json(RECIPE_WORK/'nested-history.json')
                     and self.owned.sha(RECIPE_WORK/'nested-history.json') == recipe['nested_history_sha256'],
                     'actual nested run-make history differs')
        self.require(bundle.support.inventory(bundle.support.BASE) == self.read_json(RECIPE_WORK/'final-output-inventory.json'),
                     'retained recipe outputs differ')
        self.require(self.owned.sha(RECIPE_WORK/'final-output-inventory.json') == recipe['final_outputs_sha256'],
                     'run-make producer inventory differs')
        for filename, key in [('nested-history.json', 'nested_history_sha256'),
                              ('final-output-inventory.json', 'final_outputs_sha256'),
                              ('compiler-loader-closures.json', 'compiler_loader_closures_sha256'),
                              ('recipe-loader-closure.json', 'recipe_loader_closure_sha256'),
                              ('retained-inputs.json', 'retained_inputs_sha256')]:
            self.require(self.owned.sha(self.frozen(RECIPE_WORK/filename)) == recipe_result[key],
                         'run-make result proof digest differs')
        self.require(set(recipe_plan['outputs']) == set(map(str,
                     [self.core.D2, self.core.E2, bundle.support.TOOLS])), 'run-make provider roots differ')
        for root, inventory in recipe_plan['outputs'].items():
            self.require(bundle.support.inventory(Path(root)) == inventory, 'run-make provider tree changed')
        def recipe_closure(path, cwd, dyld):
            return bundle.loader.closure(path, cwd=cwd, dyld=dyld,
                admitted=recipe_plan['admitted_provider_files'], macho=self.modules['metadata'].macho)
        compile_dyld = recipe_plan['children'][0]['environment']['DYLD_LIBRARY_PATH']
        runtime_dyld = recipe_plan['children'][1]['environment']['DYLD_LIBRARY_PATH']
        closures = dict(D2=recipe_closure(self.core.D2/'bin/rustc', self.core.S, compile_dyld),
            E2=recipe_closure(self.core.E2/'bin/rustc', bundle.support.OUT,
                f'{bundle.support.OUT}:{self.core.E2}/lib:'+runtime_dyld))
        self.require(closures == self.read_json(RECIPE_WORK/'compiler-loader-closures.json')
                     and recipe_closure(bundle.support.BASE/'rmake', bundle.support.OUT, runtime_dyld)
                         == self.read_json(RECIPE_WORK/'recipe-loader-closure.json')
                     and bundle.support.file(bundle.support.BASE/'rmake') == recipe_result['recipe_identity']
                         == recipe['recipe_identity'], 'run-make static loader/recipe bytes changed')
        self.audit('run_make', RECIPE_WORK/'receipt.json')
        return dict(native=native_proof, compiler_actual_children=26, compiler_successful_children=25,
                    beta_commands=19, run_make_top_level_commands=2, run_make_nested_commands=230)

    def budget(self):
        value = self.monitor.sample(evidence_root=WORK, evidence_roots=list(map(Path, self.plan['evidence_roots'])))
        self.require(self.monitor.rejection(value) is None, 'hash aggregate capacity rejected')
        return value

    def closure(self, binary):
        bundle = self.modules['bundle']
        return bundle.loader.closure(binary, cwd=self.core.S, dyld='',
            admitted=self.plan['runtime_private_providers'], macho=self.modules['metadata'].macho)

    def bind_snapshot_plan(self, snapshot_plan_sha256):
        self.snapshot_plan_file = self.comp.check_file(dict(
            path=str(HERE/'snapshot-plan.json'), sha256=snapshot_plan_sha256))
        self.require(self.snapshot_plan_file['size'] <= SNAPSHOT_LIMITS['maximum_manifest_bytes'],
                     'bounded hash snapshot projection required')
        self.snapshot_plan = self.read_json(HERE/'snapshot-plan.json', frozen=False)
        self.require(self.snapshot_plan['inputs_sha256'] == self.inputs_sha256
                     and self.snapshot_plan['limits'] == SNAPSHOT_LIMITS
                     and self.snapshot_plan['remaining_evidence_reservation_bytes'] == REMAINING_EVIDENCE_RESERVATION
                     and self.snapshot_plan['evidence_cap_bytes'] == 256*2**20
                     and self.snapshot_plan['helper'] == dict(path=str(SNAPSHOT_SOURCE),
                         sha256=self.freeze['files'][str(SNAPSHOT_SOURCE)]['sha256']),
                     'hash snapshot projection policy or helper differs')
        selected = self.snapshot_plan['reuse_selection']; projection = self.snapshot_plan['projection']
        self.require(set(selected) == {'records', 'evidence_roots'}
                     and projection['policy'] == 'bounded-gzip-proof-snapshots-v2'
                     and projection['reuse'] == {row['blob']['logical_sha256']: row for row in selected['records']}
                     and len(projection['reuse']) == len(selected['records'])
                     and projection['evidence_roots'] == selected['evidence_roots']
                     and self.snapshot_plan['projected_reservation_bytes'] == snapshot_reservation(projection,
                         snapshot_records(self.freeze, self.inputs_sha256, self.comp), self.modules['snapshot_bindings']),
                     'hash selected references or physical reservation differs')

    def snapshot_qualification(self):
        paths = [SNAPSHOT_SOURCE, *SNAPSHOT_TESTS,
            SNAPSHOT_CONTROLS/'inputs.json', SNAPSHOT_CONTROLS/'launch.json', SNAPSHOT_AUDIT,
            *[SNAPSHOT_CONTROL_WORK/name for name in ['receipt.json', 'result.json',
                'command/receipt.json', 'command/stdout', 'command/stderr']]]
        for path in paths:
            self.frozen(path)
        controls = self.read_json(SNAPSHOT_CONTROLS/'inputs.json')
        for name, row in controls['files'].items():
            self.frozen(name)
            frozen = self.freeze['files'][name]
            self.require(frozen['sha256'] == row['sha256']
                         and [frozen['identity'][key] for key in
                             ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']] == row['stamp'],
                         'snapshot control source/input differs from actual qualification')
        for path in [SNAPSHOT_SOURCE, *SNAPSHOT_TESTS]:
            self.require(controls['files'][str(path)]['sha256'] == self.freeze['files'][str(path)]['sha256'],
                         'snapshot helper differs from tested source')
        terminal, audit = self.read_json(SNAPSHOT_CONTROL_WORK/'receipt.json'), self.read_json(SNAPSHOT_AUDIT)
        result = self.read_json(SNAPSHOT_CONTROL_WORK/'result.json')
        names = []
        for path in SNAPSHOT_TESTS:
            for cls in ast.parse(self.read_bytes(path), filename=str(path)).body:
                if isinstance(cls, ast.ClassDef):
                    names.extend(path.stem+'.'+cls.name+'.'+test.name for test in cls.body
                        if isinstance(test, ast.FunctionDef) and test.name.startswith('test_'))
        self.require(len(names) > 7 and len(names) == len(set(names)), 'explicit original and reuse controls required')
        count = len(names)
        self.require(terminal['status'] == 'passed' and terminal['controls_passed'] == count
                     and terminal['inputs_sha256'] == self.owned.sha(SNAPSHOT_CONTROLS/'inputs.json')
                     and terminal['result_sha256'] == audit['result_sha256'] == self.owned.sha(SNAPSHOT_CONTROL_WORK/'result.json')
                     and audit['status'] == 'verified' and audit['controls'] == count
                     and audit['receipt_sha256'] == self.owned.sha(SNAPSHOT_CONTROL_WORK/'receipt.json')
                     and sorted(names) == controls['expected_names'] == result['expected_names']
                     and sorted(audit['exact_names']) == sorted(names)
                     and result['status'] == 'passed' and result['tests_run'] == count
                     and all(result[key] == 0 for key in ['failures', 'errors', 'skipped',
                         'expected_failures', 'unexpected_successes', 'child_processes', 'compiler_calls']),
                     'actual source-derived v2 snapshot qualification required')
        child_path = SNAPSHOT_CONTROL_WORK/'command/receipt.json'
        child = self.read_json(child_path)
        self.require(terminal['commands'] == [dict(path=str(child_path), pid=child['pid'],
                         sha256=self.owned.sha(child_path))]
                     and child['status'] == 'finished' and child['returncode'] == 0
                     and child['command'] == controls['command']
                     and child['environment'] == controls['environment']
                     and child['cwd'] == str(SNAPSHOT_SOURCE.parent)
                     and child['supervisor_pid'] == terminal['pid'] and child['parent_pid'] == terminal['parent_pid']
                     and terminal['admitted_at'] <= child['started_at'] <= child['finished_at'] <= terminal['finished_at'],
                     'actual snapshot test child recipe/owner differs')
        for stream in ['stdout', 'stderr']:
            path = SNAPSHOT_CONTROL_WORK/'command'/stream
            self.require(self.owned.sha(self.frozen(path)) == child[stream+'_sha256'] == audit['raw_sha256'][stream],
                         'actual snapshot test raw hashes differ')
        stderr = self.read_bytes(SNAPSHOT_CONTROL_WORK/'command/stderr').decode('utf-8', 'strict')
        observed_names = re.findall(r'^test_[A-Za-z0-9_]+ \(([^)]+)\) \.\.\. ok$', stderr, re.M)
        self.require(not self.read_bytes(SNAPSHOT_CONTROL_WORK/'command/stdout')
                     and sorted(observed_names) == sorted(names)
                     and re.search(r'^Ran '+str(count)+r' tests in [0-9.]+s\n\nOK\n$', stderr, re.M),
                     'actual snapshot test names/footer differ')

    def file_table_qualification(self):
        paths = [FILE_TABLE_SOURCE, *FILE_TABLE_TESTS,
            FILE_TABLE_CONTROLS/'inputs.json', FILE_TABLE_CONTROLS/'launch.json', FILE_TABLE_AUDIT,
            *[FILE_TABLE_CONTROL_WORK/name for name in ['receipt.json', 'result.json',
                'command/receipt.json', 'command/stdout', 'command/stderr']]]
        for path in paths:
            self.frozen(path)
        controls = self.read_json(FILE_TABLE_CONTROLS/'inputs.json')
        for name, row in controls['files'].items():
            self.frozen(name)
            frozen = self.freeze['files'][name]
            self.require(frozen['sha256'] == row['sha256']
                         and [frozen['identity'][key] for key in
                             ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']] == row['stamp'],
                         'file-table control source/input differs from actual qualification')
        for path in [FILE_TABLE_SOURCE, *FILE_TABLE_TESTS]:
            self.require(controls['files'][str(path)]['sha256'] == self.freeze['files'][str(path)]['sha256'],
                         'file-table helper differs from tested source')
        terminal, audit = self.read_json(FILE_TABLE_CONTROL_WORK/'receipt.json'), self.read_json(FILE_TABLE_AUDIT)
        result = self.read_json(FILE_TABLE_CONTROL_WORK/'result.json')
        names = []
        for path in FILE_TABLE_TESTS:
            for cls in ast.parse(self.read_bytes(path), filename=str(path)).body:
                if isinstance(cls, ast.ClassDef):
                    names.extend(path.stem+'.'+cls.name+'.'+test.name for test in cls.body
                        if isinstance(test, ast.FunctionDef) and test.name.startswith('test_'))
        self.require(len(names) > 0 and len(names) == len(set(names)), 'explicit source-derived file-table controls required')
        count = len(names)
        self.require(terminal['status'] == 'passed' and terminal['controls_passed'] == count
                     and terminal['inputs_sha256'] == self.owned.sha(FILE_TABLE_CONTROLS/'inputs.json')
                     and terminal['result_sha256'] == audit['result_sha256'] == self.owned.sha(FILE_TABLE_CONTROL_WORK/'result.json')
                     and audit['status'] == 'verified' and audit['controls'] == count
                     and audit['receipt_sha256'] == self.owned.sha(FILE_TABLE_CONTROL_WORK/'receipt.json')
                     and sorted(names) == controls['expected_names'] == result['expected_names']
                     and sorted(audit['exact_names']) == sorted(names)
                     and result['status'] == 'passed' and result['tests_run'] == count
                     and all(result[key] == 0 for key in ['failures', 'errors', 'skipped',
                         'expected_failures', 'unexpected_successes', 'child_processes', 'compiler_calls']),
                     'actual source-derived file-table qualification required')
        child_path = FILE_TABLE_CONTROL_WORK/'command/receipt.json'
        child = self.read_json(child_path)
        self.require(terminal['commands'] == [dict(path=str(child_path), pid=child['pid'],
                         sha256=self.owned.sha(child_path))]
                     and child['status'] == 'finished' and child['returncode'] == 0
                     and child['command'] == controls['command']
                     and child['environment'] == controls['environment']
                     and child['cwd'] == str(FILE_TABLE_SOURCE.parent)
                     and child['supervisor_pid'] == terminal['pid'] and child['parent_pid'] == terminal['parent_pid']
                     and terminal['admitted_at'] <= child['started_at'] <= child['finished_at'] <= terminal['finished_at'],
                     'actual file-table test child recipe/owner differs')
        for stream in ['stdout', 'stderr']:
            path = FILE_TABLE_CONTROL_WORK/'command'/stream
            self.require(self.owned.sha(self.frozen(path)) == child[stream+'_sha256'] == audit['raw_sha256'][stream],
                         'actual file-table test raw hashes differ')
        stderr = self.read_bytes(FILE_TABLE_CONTROL_WORK/'command/stderr').decode('utf-8', 'strict')
        observed_names = re.findall(r'^test_[A-Za-z0-9_]+ \(([^)]+)\) \.\.\. ok$', stderr, re.M)
        self.require(not self.read_bytes(FILE_TABLE_CONTROL_WORK/'command/stdout')
                     and sorted(observed_names) == sorted(names)
                     and re.search(r'^Ran '+str(count)+r' tests in [0-9.]+s\n\nOK\n$', stderr, re.M),
                     'actual file-table test names/footer differ')

        return dict(controls=count, receipt_sha256=self.owned.sha(FILE_TABLE_CONTROL_WORK/'receipt.json'),
                    result_sha256=self.owned.sha(FILE_TABLE_CONTROL_WORK/'result.json'),
                    audit=dict(path=str(FILE_TABLE_AUDIT), sha256=self.owned.sha(FILE_TABLE_AUDIT)),
                    helper=dict(path=str(FILE_TABLE_SOURCE), sha256=self.owned.sha(FILE_TABLE_SOURCE)))

    def retain_sources(self):
        """Retain complete selected bytes within the unchanged physical evidence cap."""
        self.snapshot_qualification()
        last_sample = [float('-inf')]
        def capacity():
            self.owned.disk(ROOT, 9)
            if time.monotonic()-last_sample[0] >= 5:
                self.budget(); last_sample[0] = time.monotonic()
        records = snapshot_records(self.freeze, self.inputs_sha256, self.comp)
        selected = self.snapshot_reuse()
        projection = self.snapshots.measure(records, SNAPSHOT_LIMITS, capacity,
            reuse=selected['records'], evidence_roots=selected['evidence_roots'])
        self.require(projection == self.snapshot_plan['projection'], 'hash snapshot projection differs')
        current = self.budget(); reservation = snapshot_reservation(projection, records, self.modules['snapshot_bindings'])
        self.require(reservation == self.snapshot_plan['projected_reservation_bytes']
                     and current['evidence_allocated_bytes'] + reservation <= 256*2**20,
                     'hash snapshots and remaining stage exceed aggregate evidence cap')
        self.record['snapshot_admission'] = dict(existing_evidence_bytes=current['evidence_allocated_bytes'],
            projected_reservation_bytes=reservation, evidence_cap_bytes=256*2**20)
        self.save()
        manifest = self.snapshots.write_verified(records, WORK/'source-snapshots', projection, SNAPSHOT_LIMITS, capacity,
            reuse=selected['records'], evidence_roots=selected['evidence_roots'])
        data = self.snapshots.encoded(manifest)
        self.require(len(data) <= SNAPSHOT_LIMITS['maximum_manifest_bytes'], 'bounded hash snapshot manifest required')
        with (WORK/'source-snapshots.json').open('xb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        self.require(self.owned.sha(WORK/'source-snapshots.json') == self.comp.digest(data),
                     'hash snapshot manifest readback differs')
        with (WORK/'snapshot-plan.json').open('xb') as stream:
            self.comp.check_file(self.snapshot_plan_file, stream, capacity)
            stream.flush(); os.fsync(stream.fileno())
        self.require(self.owned.sha(WORK/'snapshot-plan.json') == self.record['snapshot_plan_sha256'],
                     'retained hash snapshot projection differs')
        self.record['source_snapshots_sha256'] = self.owned.sha(WORK/'source-snapshots.json')
        self.save(); self.budget()

    def execute(self):
        try:
            with self.owned.workload_lock(self.owned.CANONICAL_LOCK, 600) as fd:
                self.record.update(status='running', admitted_at=time.time(), free_bytes_before=self.owned.disk(ROOT, 24))
                self.save()
                self.guard(True)
                self.record['prerequisites'] = self.prerequisites()
                self.save(); self.budget()
                self.retain_sources()
                result = self.core.execute(self.plan, evidence_root=WORK, canonical_fd=fd,
                    owned=self.owned, monitor=self.monitor, check_inputs=lambda: self.guard(True),
                    inspect_closure=self.closure)
                self.guard(True); self.prerequisites(); self.budget()
                result.update(status='hash-driver-observations-passed-awaiting-independent-audit',
                              candidate_revision=REVISION, source_identity=self.plan['source_identity'],
                              failed_driver=self.plan['failed_driver'], continuation_controls=self.plan['continuation_controls'])
                self.owned.write(WORK/'result.json', result)
                self.record.update(status='passed-awaiting-independent-audit', result_sha256=self.owned.sha(WORK/'result.json'),
                                   free_bytes_after=self.owned.disk(ROOT, 9))
        except BaseException as error:
            self.record.update(status='failed', error=repr(error))
            raise
        finally:
            self.record['finished_at'] = time.time()
            self.save()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs-sha256', required=True)
    parser.add_argument('--snapshot-plan-sha256', required=True)
    args = parser.parse_args()
    Stage(args.inputs_sha256, args.snapshot_plan_sha256).execute()
