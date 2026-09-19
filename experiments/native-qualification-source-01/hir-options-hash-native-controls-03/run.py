#!/usr/bin/env python3
"""Source-only native roles controller; no plan/freeze/launch exists yet.

Admission must freeze a successful source08 composition and its complete input
closure after the real compiler continuation. A partial build cannot satisfy
this interface. This stage neither constructs B3 nor executes a hash driver.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time

import recipe
import observations as observed
import stock_source
import previous_attempt
import stock_controls
import loader_controls

HERE = Path(__file__).resolve().parent
A = HERE.parents[1]
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
N = X/'.work/hir-options-hash-compiler-01'
WORK = A/'.work/hir-options-hash-native-controls-03'
COMPOSITION = A/'experiments/hir-options-hash-beta-composition-08'
ASSEMBLY = A/'.work/hir-options-hash-beta-composition-08'
REVISION = '4de35bdacef0e3cd18a66bc30b5459c19e09b118'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


# Shared pure file copier remains unchanged from reviewed source03. Source08
# and all selected imports still have to occur in the eventual native freeze.
comp = module('native_compose_files', A/'experiments/hir-options-hash-beta-composition-03/compose_sysroot.py')
monitor = module('native_stage_monitor', A/'experiments/hir-options-hash-stage-monitor/monitor.py')
owned, require = monitor.owned, observed.require


def read(path):
    require(Path(path).stat().st_size <= 256*2**20, 'bounded JSON input required')
    return json.loads(Path(path).read_bytes(), object_pairs_hook=observed.unique_object)


SNAPSHOT_SOURCE = ROOT/'experiments/bounded-proof-snapshots/proof_snapshots.py'
SNAPSHOT_CONTROLS = ROOT/'experiments/bounded-proof-snapshot-controls-01'
SNAPSHOT_CONTROL_WORK = ROOT/'.work/bounded-proof-snapshot-controls-01'
SNAPSHOT_AUDIT = A/'.work/proof-snapshot-controls-independent-verification-01.json'
SNAPSHOT_LIMITS = dict(maximum_files=1024, maximum_file_bytes=64*2**20, maximum_logical_bytes=512*2**20,
                       maximum_compressed_bytes=128*2**20, maximum_manifest_bytes=4*2**20)
REMAINING_EVIDENCE_RESERVATION = 32*2**20


def load_snapshots(freeze):
    require(str(SNAPSHOT_SOURCE) in freeze['files'], 'snapshot helper omitted from frozen closure')
    expected = dict(path=str(SNAPSHOT_SOURCE), **freeze['files'][str(SNAPSHOT_SOURCE)])
    require(comp.check_file(expected) == expected, 'snapshot helper changed before import')
    spec = importlib.util.spec_from_file_location('b3_verified_proof_snapshots', SNAPSHOT_SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def snapshot_records(freeze, inputs_path, inputs_sha256):
    names = freeze['snapshot_inputs']
    require(len(names) == len(set(names)) and str(inputs_path) not in names, 'exact unique snapshot inputs')
    records = [dict(path=name, **freeze['files'][name]) for name in sorted(names)]
    records.append(comp.check_file(dict(path=str(inputs_path), sha256=inputs_sha256)))
    return records


def snapshot_reservation(projection, records):
    # One block of rounding per logical file is conservative even when aliases
    # share a single compressed payload. The manifest and reviewed projection
    # are reserved separately; ordinary command evidence keeps its existing cap.
    return (projection['compressed_bytes'] + 4096*len(records)
            + 2*SNAPSHOT_LIMITS['maximum_manifest_bytes'] + REMAINING_EVIDENCE_RESERVATION)


def snapshot_qualification(freeze):
    paths = [SNAPSHOT_SOURCE, SNAPSHOT_SOURCE.with_name('test_proof_snapshots.py'),
             SNAPSHOT_CONTROLS/'inputs.json', SNAPSHOT_CONTROLS/'launch.json', SNAPSHOT_AUDIT,
             *[SNAPSHOT_CONTROL_WORK/name for name in ['receipt.json', 'result.json', 'command/receipt.json', 'command/stdout', 'command/stderr']]]
    for path in paths:
        require(str(path) in freeze['files'] and owned.sha(path) == freeze['files'][str(path)]['sha256'],
                'frozen snapshot qualification proof missing or changed')
    controls = read(SNAPSHOT_CONTROLS/'inputs.json')
    for path in [SNAPSHOT_SOURCE, SNAPSHOT_SOURCE.with_name('test_proof_snapshots.py')]:
        require(controls['files'][str(path)]['sha256'] == freeze['files'][str(path)]['sha256'], 'snapshot source differs from tested source')
    terminal, audit = read(SNAPSHOT_CONTROL_WORK/'receipt.json'), read(SNAPSHOT_AUDIT)
    result = read(SNAPSHOT_CONTROL_WORK/'result.json')
    require(terminal['status'] == 'passed' and terminal['controls_passed'] == 7
            and terminal['inputs_sha256'] == owned.sha(SNAPSHOT_CONTROLS/'inputs.json')
            and terminal['result_sha256'] == audit['result_sha256'] == owned.sha(SNAPSHOT_CONTROL_WORK/'result.json')
            and audit['status'] == 'verified' and audit['controls'] == 7
            and audit['receipt_sha256'] == owned.sha(SNAPSHOT_CONTROL_WORK/'receipt.json')
            and result['status'] == 'passed' and result['tests_run'] == 7
            and all(result[key] == 0 for key in ['failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes', 'child_processes', 'compiler_calls']),
            'actual seven-control snapshot qualification required')



class Stage:
    def __init__(self, inputs_sha256, snapshot_plan_sha256):
        require(owned.sha(HERE/'inputs.json') == inputs_sha256, 'reviewed native freeze required')
        self.freeze = read(HERE/'inputs.json')
        self.snapshot_plan_file = comp.check_file(dict(path=str(HERE/'snapshot-plan.json'), sha256=snapshot_plan_sha256))
        require(self.snapshot_plan_file['size'] <= SNAPSHOT_LIMITS['maximum_manifest_bytes'], 'bounded native snapshot projection')
        self.snapshot_plan = read(HERE/'snapshot-plan.json')
        require(self.snapshot_plan['inputs_sha256'] == inputs_sha256 and self.snapshot_plan['limits'] == SNAPSHOT_LIMITS
                and self.snapshot_plan['remaining_evidence_reservation_bytes'] == REMAINING_EVIDENCE_RESERVATION
                and self.snapshot_plan['helper'] == dict(path=str(SNAPSHOT_SOURCE), sha256=self.freeze['files'][str(SNAPSHOT_SOURCE)]['sha256']),
                'reviewed native snapshot projection differs')
        self.snapshots = load_snapshots(self.freeze)
        require(owned.sha(HERE/'plan.json') == self.freeze['plan_sha256'], 'native plan differs')
        self.plan = read(HERE/'plan.json')
        require(Path.cwd() == A and sys.dont_write_bytecode and not sys.flags.optimize, 'explicit owner/Python mode required')
        require(str(Path(sys.executable).resolve(strict=True)) == self.freeze['python'], 'Python route differs')
        require(self.plan['namespace'] == str(N) and self.plan['candidate_revision'] == REVISION, 'wrong native candidate')
        require(self.plan['children'] == recipe.desired_commands(self.plan), 'native command allowlist differs')
        self.paths = recipe.paths(N)
        self.inputs_sha256 = inputs_sha256
        self.environment = dict(os.environ)
        expected = self.freeze['launch_environment']
        extra = set(self.environment)-set(expected)
        require(all(self.environment.get(k) == v for k, v in expected.items())
                and extra <= {'__CF_USER_TEXT_ENCODING'}, 'controller environment differs')
        if extra:
            value = self.environment['__CF_USER_TEXT_ENCODING'].split(':')
            require(len(value) == 3 and all(re.fullmatch(r'(?:0[xX][0-9a-fA-F]{1,8}|[0-9]{1,10})', v) for v in value)
                    and int(value[0], 16 if value[0].lower().startswith('0x') else 10) == os.getuid() == 501,
                    'unproved Darwin context')
        require(self.plan['environment'].get('RUSTUP_DIST_SERVER') == 'file:///dev/null',
                'pinned offline distribution policy required')
        require(not any((k.startswith(('RUST', 'DYLD_', 'LD_')) and k != 'RUSTUP_DIST_SERVER')
                        or k in ['CARGO_ENCODED_RUSTFLAGS'] for k in self.plan['environment']),
                'ambient compiler/loader override')
        self.evidence_roots = tuple(comp.absolute(p) for p in self.plan['evidence_roots'])
        require(WORK in self.evidence_roots and ASSEMBLY in self.evidence_roots, 'native/composition budget omitted')
        require(not WORK.exists() and not WORK.is_symlink() and WORK.parent.resolve(strict=True) == WORK.parent,
                'fresh native evidence required')
        WORK.mkdir(); (WORK/'commands').mkdir(); (WORK/'artifacts').mkdir(); (WORK/'tmp').mkdir()
        self.stock = None
        self.stock_source = None
        self.record = dict(status='waiting', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(),
            inputs_sha256=inputs_sha256, snapshot_plan_sha256=snapshot_plan_sha256, candidate_revision=REVISION, commands=[], fixture_compilations=[],
            native_executions=[], hits=[], source_restored=False, hash_driver_qualified=False,
            application_qualified=False, runtime_installation=False, benchmark=False)
        self.require = require
        self.save()

    def save(self):
        owned.write(WORK/'receipt.json', self.record)

    def budget(self):
        value = monitor.sample(evidence_root=WORK, evidence_roots=self.evidence_roots)
        require(monitor.rejection(value) is None, str(monitor.rejection(value)))
        return value

    def frozen(self, path):
        path = Path(path)
        require(str(path) in self.freeze['files'], 'unfrozen prior/native input: '+str(path))
        row = dict(path=str(path), **self.freeze['files'][str(path)])
        require(comp.check_file(row) == row, 'frozen input bytes differ')
        return path

    def guard(self, full=False):
        require(comp.check_file(self.snapshot_plan_file) == self.snapshot_plan_file, 'native snapshot projection changed')
        require(dict(os.environ) == self.environment and owned.sha(HERE/'inputs.json') == self.inputs_sha256,
                'native controller environment/freeze changed')
        for name, row in self.freeze['files'].items():
            require(comp.ordinary(name) == row['identity'], 'frozen input stamp changed: '+name)
            if full:
                self.frozen(name)
        for name, row in self.freeze['links'].items():
            path = Path(name)
            info = path.lstat()
            stamp = [info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink]
            require(path.is_symlink() and stamp == row['stamp']
                    and os.readlink(path) == row['target'] and str(path.resolve(strict=True)) == row['resolved'],
                    'frozen input route changed')
        for name in self.freeze['absent_paths']:
            require(not Path(name).exists() and not Path(name).is_symlink(), 'admitted absence changed')
        for name, resolved in self.plan['executor_routes'].items():
            require(str(Path(name).resolve(strict=True)) == resolved, 'executor route changed')
        for imported in list(sys.modules.values()):
            path = getattr(imported, '__file__', None)
            if path and path.startswith('/Users/danluu/dev/'):
                require(str(Path(path).resolve(strict=True)) in self.freeze['files'], 'unfrozen local imported source')
        if self.stock_source is not None:
            require(self.file(self.paths['stock_source']) == self.stock_source, 'private stock source changed')
        if self.stock is not None:
            require(comp.ordinary(self.paths['stock']) == self.stock['identity'], 'stock executable changed')
            if full:
                require(self.file(self.paths['stock']) == self.stock, 'stock executable bytes changed')

    def predecessor(self):
        """Read back the reviewed successful B3 operation and its exact closure.

        The B3 freeze is a subset of this freeze, including its explicit absent
        routes. No old failure is relabeled passed, and no implicit re-admission
        of a changed provider is available here.
        """
        require(loader_controls.validate(self.frozen, self.freeze['files']) == self.plan['loader_route_controls'], 'actual loader route controls differ')
        require(stock_controls.validate(self.frozen, self.freeze['files']) == self.plan['stock_source_controls'], 'actual derivation controls differ')
        require(previous_attempt.validate(self.frozen, self.freeze['files']) == self.plan['prior_failed_attempts'], 'original native failure proof differs')
        source = self.plan['assembly']['source']
        evidence = self.plan['assembly']['evidence']
        require(source == str(COMPOSITION) and evidence == str(ASSEMBLY), 'source08 B3 route required')
        terminal = read(self.frozen(ASSEMBLY/'receipt.json'))
        prior_freeze = read(self.frozen(COMPOSITION/'inputs.json'))
        prior_plan = read(self.frozen(COMPOSITION/'plan.json'))
        require(terminal['status'] == 'passed' and terminal['assembly_and_auxiliary_strip_qualified'] is True
                and terminal['candidate_revision'] == REVISION and len(terminal['commands']) == 19,
                'actual successful B3 assembly/strip prerequisite required')
        independent = self.plan['assembly']['audit']
        actual_audit = read(self.frozen(independent['path']))
        require(owned.sha(Path(independent['path'])) == independent['sha256']
                and actual_audit['status'] == 'verified'
                and actual_audit['receipt_sha256'] == owned.sha(ASSEMBLY/'receipt.json'),
                'independent B3 audit does not bind actual predecessor')
        require(owned.sha(ASSEMBLY/'receipt.json') == self.plan['assembly']['receipt_sha256']
                and owned.sha(COMPOSITION/'inputs.json') == terminal['inputs_sha256'] == self.plan['assembly']['inputs_sha256']
                and owned.sha(COMPOSITION/'plan.json') == prior_freeze['plan_sha256'], 'B3 source/receipt binding differs')
        require(owned.sha(self.frozen(COMPOSITION/'snapshot-plan.json')) == owned.sha(self.frozen(ASSEMBLY/'snapshot-plan.json'))
                == terminal['snapshot_plan_sha256']
                and owned.sha(self.frozen(ASSEMBLY/'source-snapshots.json')) == terminal['source_snapshots_sha256'],
                'B3 compressed proof projection/manifest differs')
        require(all(self.freeze['files'].get(name) == row for name, row in prior_freeze['files'].items())
                and all(self.freeze['links'].get(name) == row for name, row in prior_freeze['links'].items())
                and set(prior_freeze.get('absent_paths', [])) <= set(self.freeze['absent_paths']),
                'native freeze omits or changes B3 qualification inputs/routes')
        last = terminal['admitted_at']
        for ref, expected in zip(terminal['commands'], prior_plan['children'], strict=True):
            receipt = self.frozen(ref['path']); child = read(receipt)
            require(owned.sha(receipt) == ref['sha256'] and child['status'] == 'finished' and child['returncode'] == 0
                    and child['command'] == ref['command'] == expected['argv'] and child['environment'] == expected['environment']
                    and child['cwd'] == expected['cwd'] == str(self.paths['source']) and child['pid'] == ref['pid']
                    and child['supervisor_pid'] == terminal['pid'] and child['parent_pid'] == terminal['parent_pid']
                    and last <= child['started_at'] <= child['finished_at'] <= terminal['finished_at'],
                    'B3 child/terminal association differs')
            last = child['finished_at']
            for stream in ['stdout', 'stderr']:
                require(owned.sha(self.frozen(receipt.parent/stream)) == child[stream+'_sha256'], 'B3 raw output changed')
        inventory = read(self.frozen(ASSEMBLY/'assembly/output-inventory.json'))
        require(comp.output_inventory(self.paths['beta']) == inventory
                and owned.sha(ASSEMBLY/'assembly/output-inventory.json') == terminal['assembly']['output_inventory_sha256'],
                'complete admitted B3 payload changed')
        require(owned.sha(self.frozen(ASSEMBLY/'strip-proof.json')) == terminal['strip_proof_sha256'], 'B3 strip proof differs')
        require(self.plan['ordered_driver_destinations'] == terminal['producer_proof']['ordered_driver_destinations'],
                'actual ordered B3 driver pair differs')
        for name in self.plan['ordered_driver_destinations']:
            require(name in inventory, 'ordered B3 driver missing')
        require(inventory[self.plan['ordered_driver_destinations'][0]]['sha256'] == self.plan['runtime_driver']['sha256'],
                'B3 driver bytes differ from runtime E2')
        compiler = self.plan['compiler']
        require(compiler == prior_plan['actual_build'], 'native compiler provenance differs from B3')
        compiled = read(self.frozen(Path(compiler['evidence'])/'compiled.json'))
        require(compiled['status'] == 'compiled-awaiting-native-recipe-and-B3-qualification'
                and compiled['candidate_revision'] == REVISION and compiled['source_identity'] == self.plan['source_identity'],
                'native source identity differs')
        runtime = read(self.frozen(Path(compiler['evidence'])/'stage1-inventory.json'))['closure']
        require(runtime['identity'] == self.plan['runtime_closure'], 'runtime loader closure differs')
        for row in runtime['identity']['libraries']:
            require(owned.sha(self.frozen(row['resolved'])) == row['sha256'], 'runtime provider bytes differ')
        for key, value in runtime['identity']['searches'].items():
            require((Path(key).exists() or Path(key).is_symlink()) == value, 'runtime loader search changed')
        platform = os.uname()
        require(runtime['identity']['platform'] == dict(system=platform.sysname, release=platform.release,
                version=platform.version, machine=platform.machine), 'system dyld platform changed')
        require(self.plan['runtime_driver']['path'] in {row['resolved'] for row in runtime['identity']['libraries']},
                'runtime driver absent from complete private closure')
        require(comp.check_file(self.plan['runtime_driver']) == self.plan['runtime_driver'], 'runtime driver identity differs')
        # Wrong-role notes must cite actual beta std files, never a fabricated
        # missing-crate failure. Exactly the complete matching inventory subset.
        beta_std = [str(self.paths['beta']/name) for name in sorted(inventory)
                    if name.startswith('lib/rustlib/'+recipe.HOST+'/lib/lib')
                    and re.fullmatch(r'lib(?:std|core)-[a-f0-9]+\.(?:rlib|rmeta|dylib)', Path(name).name)]
        require(beta_std and self.plan['beta_std_paths'] == beta_std, 'complete beta std diagnostic paths differ')

    def fresh_root(self):
        root = self.paths['root']
        require(not root.exists() and not root.is_symlink() and root.parent.resolve(strict=True) == root.parent,
                'fresh native artifacts required after canonical admission')
        root.mkdir()
        source = self.frozen(self.plan['stock_source_derivation']['source'])
        data, proof = stock_source.derive(source.read_bytes(), source, self.paths['stock_source'])
        require(proof == self.plan['stock_source_derivation'], 'stock source derivation differs')
        with self.paths['stock_source'].open('xb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        self.stock_source = self.file(self.paths['stock_source'])
        require(self.stock_source['sha256'] == proof['derived_sha256'] and self.stock_source['size'] == len(data), 'private stock source readback differs')
        self.record['stock_source_derivation'] = proof
        self.record['stock_source'] = self.stock_source
        self.save()

    def retain_sources(self):
        snapshot_qualification(self.freeze)
        last_sample = [float('-inf')]
        def capacity():
            # Free space is checked on every codec chunk; expensive whole-tree
            # allocation uses the shared monitor's ordinary five-second cadence.
            owned.disk(A, 9)
            if time.monotonic()-last_sample[0] >= 5:
                self.budget(); last_sample[0] = time.monotonic()
        records = snapshot_records(self.freeze, HERE/'inputs.json', self.inputs_sha256)
        projection = self.snapshots.measure(records, SNAPSHOT_LIMITS, capacity)
        require(projection == self.snapshot_plan['projection'], 'native compressed snapshot projection differs')
        current = self.budget(); reservation = snapshot_reservation(projection, records)
        require(current['evidence_allocated_bytes'] + reservation <= 256*2**20,
                'native snapshots plus remaining stage exceed aggregate evidence cap')
        self.record['snapshot_admission'] = dict(existing_evidence_bytes=current['evidence_allocated_bytes'],
            projected_reservation_bytes=reservation, evidence_cap_bytes=256*2**20)
        self.save()
        manifest = self.snapshots.write_verified(records, WORK/'source-snapshots', projection, SNAPSHOT_LIMITS, capacity)
        data = self.snapshots.encoded(manifest)
        require(len(data) <= SNAPSHOT_LIMITS['maximum_manifest_bytes'], 'bounded native snapshot manifest')
        with (WORK/'source-snapshots.json').open('xb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        require(owned.sha(WORK/'source-snapshots.json') == comp.digest(data), 'native snapshot manifest readback differs')
        with (WORK/'snapshot-plan.json').open('xb') as stream:
            comp.check_file(self.snapshot_plan_file, stream, self.budget)
            stream.flush(); os.fsync(stream.fileno())
        require(owned.sha(WORK/'snapshot-plan.json') == self.record['snapshot_plan_sha256'], 'native projection copy differs')
        self.record['source_snapshots_sha256'] = owned.sha(WORK/'source-snapshots.json')
        self.save()
        self.budget()

    def file(self, path):
        path = Path(path)
        require(path.stat().st_size <= 128*2**20, 'bounded native file required')
        return comp.check_file(dict(path=str(path), sha256=owned.sha(path)))

    def command(self, index):
        require(index == len(self.record['commands']), 'native command order differs')
        row = self.plan['children'][index]
        self.guard(); self.budget()
        executable = Path(row['argv'][0]).resolve(strict=True)
        generated = executable in [self.paths['stock'], self.paths['program']]
        bound = self.file(executable) if generated else dict(path=str(executable), **self.freeze['files'][str(executable)])
        out = WORK/'commands'/f'{index:03}'
        try:
            child = monitor.run(row['argv'], cwd=self.paths['source'], environment=row['environment'], output=out,
                canonical_fd=self.lockfd, evidence_root=WORK, evidence_roots=self.evidence_roots, expected=tuple(row['expected']))
        finally:
            if (out/'receipt.json').exists():
                saved = read(out/'receipt.json')
                self.record['commands'].append(dict(path=str(out/'receipt.json'), sha256=owned.sha(out/'receipt.json'),
                    command=row['argv'], pid=saved.get('pid'), role=row['role']))
                self.save()
        require(comp.check_file(bound) == bound, 'executed native input changed')
        self.guard(); self.budget()
        require((out/'stdout').stat().st_size <= 8*2**20 and (out/'stderr').stat().st_size <= 8*2**20,
                'bounded native output required before reading')
        stdout, stderr = (out/'stdout').read_bytes(), (out/'stderr').read_bytes()
        require(len(stdout) <= 8*2**20 and len(stderr) <= 8*2**20, 'bounded native output required')
        return stdout, stderr, child

    def bind_stock(self, raw):
        self.stock = self.file(self.paths['stock'])
        self.record['stock'] = self.stock
        self.record['linker'] = observed.link_command(raw, clang=self.plan['clang'], output=self.paths['stock'],
                                                      runtime_lib=self.paths['runtime']/'lib')
        self.save()

    def static_stock(self, raw):
        self.record['static_loader'] = observed.stock_macho(self.paths['stock'].read_bytes(), raw,
            stock=self.paths['stock'], driver=self.plan['runtime_driver']['path'], runtime_lib=self.paths['runtime']/'lib',
            qualified_private=self.plan['runtime_closure']['libraries'])
        self.save()

    def loaded_stock(self, raw, child):
        # The reviewed parser's observation-only parse is shared with the hash
        # stage. It does not launch a process or qualify a provider by its name.
        directory = ROOT/'experiments/hir-driver-observations'
        self.frozen(directory/'loader_trace.py'); self.frozen(directory/'observations.py')
        # Avoid the unrelated local observations module name during import.
        alias = sys.modules.get('observations')
        try:
            module('observations', directory/'observations.py')
            parser = module('native_loader_trace', directory/'loader_trace.py')
        finally:
            if alias is not None:
                sys.modules['observations'] = alias
        private = {str(self.paths['stock']), *[row['resolved'] for row in self.plan['runtime_closure']['libraries']]}
        self.record['actual_loader'] = parser.parse(raw, pid=child['pid'], allowed_private=private)
        self.save()

    def write_fixture(self, data, label):
        self.paths['fixture'].write_bytes(data)
        copy = WORK/(label+'.rs')
        if copy.exists():
            require(copy.read_bytes() == data, 'retained fixture changed')
        else:
            copy.write_bytes(data)
        self.record['source_restored'] = data == recipe.ORIGINAL
        self.save()

    def compile(self, index, source):
        require(self.paths['fixture'].read_bytes() == source, 'fixture before compile differs')
        previous = self.file(self.paths['program']) if index in [13, 14, 15] else None
        result = self.command(index)
        require(self.paths['fixture'].read_bytes() == source, 'fixture changed during compile')
        if previous is not None:
            require(self.file(self.paths['program']) == previous, 'failed typecheck changed prior executable')
        observed.clean(result[1])
        self.record['fixture_compilations'].append(dict(index=index, source_sha256=comp.digest(source)))
        self.save()
        return result

    def output(self, index):
        artifact = self.file(self.paths['program'])
        copy = WORK/'artifacts'/(str(index)+'.bin')
        with copy.open('xb') as stream:
            comp.check_file(artifact, stream, self.budget)
            stream.flush(); os.fsync(stream.fileno())
        require(owned.sha(copy) == artifact['sha256'], 'executed artifact retention differs')
        out, err, _ = self.command(index)
        require(out == b'42\n' and not err and self.file(self.paths['program']) == artifact, 'native output differs')
        self.record['native_executions'].append(dict(index=index, artifact=artifact, retained=str(copy)))
        self.save()

    def hit(self, result, cold=False):
        self.record['hits'].append(observed.hit(result[1], cold=cold)); self.save()

    def error_pair(self, ordinary, candidate, code):
        self.record['uncalled_error'] = observed.error_pair(ordinary, candidate, code); self.save()

    def wrong_role(self, index):
        require(not self.paths['wrong_output'].exists() and not self.paths['wrong_output'].is_symlink(), 'wrong-role output is not fresh')
        require(self.paths['wrong_source'].read_bytes() == recipe.WRONG, 'wrong-role source differs')
        result = self.command(index)
        require(not self.paths['wrong_output'].exists() and not self.paths['wrong_output'].is_symlink()
                and self.paths['wrong_source'].read_bytes() == recipe.WRONG, 'wrong-role failure mutated source/output')
        return result

    def wrong_pair(self, ordinary, candidate):
        self.record['wrong_B3'] = observed.wrong_pair(ordinary, candidate, self.plan['beta_std_paths']); self.save()

    def finish(self):
        self.guard(True); self.predecessor(); self.budget()
        require(self.record['source_restored'] and len(self.record['native_executions']) == 4
                and len(self.record['hits']) == 4 and len(self.record['fixture_compilations']) == 7,
                'incomplete original/error/restored history')
        result = dict(status='native-roles-and-behavior-qualified', candidate_revision=REVISION,
            source_identity=self.plan['source_identity'], assembly=self.plan['assembly'], compiler=self.plan['compiler'],
            stock=self.stock, stock_source=self.stock_source, stock_source_derivation=self.plan['stock_source_derivation'],
            prior_failed_attempts=self.plan['prior_failed_attempts'], loader_route_controls=self.plan['loader_route_controls'], total_actual_native_children=31, qualified_native_children=20,
            ordered_driver_destinations=self.plan['ordered_driver_destinations'],
            static_loader=self.record['static_loader'], actual_loader=self.record['actual_loader'],
            runtime_closure=self.plan['runtime_closure'], source_restored=True,
            history=self.record['commands'][:18], wrong_B3_commands=self.record['commands'][18:],
            uncalled_error=self.record['uncalled_error'], wrong_B3=self.record['wrong_B3'],
            hits=self.record['hits'], native_executions=self.record['native_executions'],
            hash_driver_qualified=False, run_make_qualified=False, application_qualified=False)
        owned.write(WORK/'native-controls.json', result)
        self.record.update(status='passed', native_roles_and_behavior_qualified=True,
                           result_sha256=owned.sha(WORK/'native-controls.json'))

    def execute(self):
        try:
            with owned.workload_lock(owned.CANONICAL_LOCK, 600) as fd:
                self.lockfd = fd
                self.record.update(status='running', admitted_at=time.time(), free_bytes_before=owned.disk(A, 24)); self.save()
                self.guard(True); self.predecessor(); self.budget()
                self.retain_sources()
                recipe.execute(self)
                self.record['free_bytes_after'] = owned.disk(A, 9)
        except BaseException as error:
            self.record.update(status='failed', error=repr(error)); raise
        finally:
            self.record['finished_at'] = time.time(); self.save()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs-sha256', required=True)
    parser.add_argument('--snapshot-plan-sha256', required=True)
    args = parser.parse_args()
    Stage(args.inputs_sha256, args.snapshot_plan_sha256).execute()
