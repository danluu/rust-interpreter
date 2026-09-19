"""Enclosing hash-driver controller draft; no concrete admission exists yet.

Preparation must supply actual completed compiler, B3, native and run-make
evidence. Missing prerequisites fail before the three-command core is called.
This file imports definitions only; main is the sole execution entry point.
"""
import argparse
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
WORK = ROOT/'.work/hir-options-hash-driver-01'
REVISION = '4de35bdacef0e3cd18a66bc30b5459c19e09b118'
NATIVE_SOURCE = A/'experiments/hir-options-hash-native-controls-01'
NATIVE_WORK = A/'.work/hir-options-hash-native-controls-01'
BETA_SOURCE = A/'experiments/hir-options-hash-beta-composition-07'
BETA_WORK = A/'.work/hir-options-hash-beta-composition-07'
RECIPE_SOURCE = O/'experiments/hir-options-hash-run-make-stage-02'
RECIPE_WORK = O/'.work/hir-options-hash-run-make-01'
SNAPSHOT_FILE_LIMIT = 64*2**20
SNAPSHOT_TOTAL_LIMIT = 128*2**20
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
    adapter = module('recipe_adapter', RECIPE_SOURCE/'adapter.py')
    bundle = adapter.load_bundle()
    monitor = adapter.monitor()
    metadata = adapter.metadata()
    comp = module('composition', BETA_SOURCE/'compose_sysroot.py')
    return dict(core=core, predecessor=predecessor, trace=trace, recipe=native_recipe,
                observed=native_observed, adapter=adapter, bundle=bundle, monitor=monitor,
                metadata=metadata, comp=comp)


class Stage:
    def __init__(self, inputs_sha256):
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
        self.freeze = self.read_json(HERE/'inputs.json', frozen=False)
        self.plan = self.read_json(HERE/'plan.json')
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
            candidate_revision=REVISION, inputs_sha256=inputs_sha256, application_qualified=False,
            performance_measurement=False, runtime_installation=False, hash_driver_qualified=False)
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
        native_plan = self.inherited_freeze(NATIVE_SOURCE)
        environment, omitted = driver_environment(native_plan['environment'], self.core.ARTIFACTS/'tmp')
        self.require(self.plan['environment'] == environment
                     and self.plan['omitted_bootstrap_environment'] == omitted,
                     'hash environment does not match the qualified native predecessor')
        native = self.read_json(NATIVE_WORK/'receipt.json')
        result = self.read_json(NATIVE_WORK/'native-controls.json')
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
        native_proof = self.modules['predecessor'].native_controls(native_plan, native, result,
            evidence=NATIVE_WORK, read_json=self.read_json, read_bytes=self.read_bytes,
            recipe=self.modules['recipe'], observations=self.modules['observed'], loader_trace=self.modules['trace'])
        self.require(native_plan['source_identity'] == self.plan['source_identity']
                     and [str(self.core.B3/name) for name in result['ordered_driver_destinations']]
                         == self.plan['ordered_driver_pair'], 'hash role pair differs from actual native controls')
        self.audit('native', NATIVE_WORK/'receipt.json')
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

    def retain_sources(self):
        """Copy bounded controller/proof bytes; provider payloads remain inventoried."""
        names = self.freeze['snapshot_inputs']
        self.require(type(names) is list and names == sorted(set(names))
                     and set(names) <= set(self.freeze['files']), 'invalid source snapshot selection')
        rows = {name: dict(path=name, **self.freeze['files'][name]) for name in names}
        freeze_path = HERE/'inputs.json'
        rows[str(freeze_path)] = self.comp.check_file(dict(path=str(freeze_path), sha256=self.inputs_sha256))
        self.require(all(row['size'] <= SNAPSHOT_FILE_LIMIT for row in rows.values())
                     and sum(row['size'] for row in rows.values()) <= SNAPSHOT_TOTAL_LIMIT,
                     'bounded source/proof snapshot budget exceeded')
        directory = WORK/'source-snapshots'
        directory.mkdir()
        manifest = {}
        for name, row in sorted(rows.items()):
            self.budget()
            destination = directory/row['sha256']
            if not destination.exists():
                with destination.open('xb') as stream:
                    self.require(self.comp.check_file(row, stream, self.budget) == row,
                                 'source changed during retained copy')
                    stream.flush(); os.fsync(stream.fileno())
            self.require(self.owned.sha(destination) == row['sha256']
                         and destination.stat().st_size == row['size'], 'retained source readback differs')
            manifest[name] = dict(path=str(destination), sha256=row['sha256'], bytes=row['size'])
        self.owned.write(WORK/'source-snapshots.json', manifest)
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
                              candidate_revision=REVISION, source_identity=self.plan['source_identity'])
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
    Stage(parser.parse_args().inputs_sha256).execute()
