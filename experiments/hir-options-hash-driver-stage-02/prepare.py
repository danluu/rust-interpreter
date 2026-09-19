"""Source-only hash-stage discovery; requires four actual completed audits.

Run only after separate review. This preparer acquires canonical admission for
read-only discovery; it never compiles, probes a provider, or starts a driver.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import time

import stage

HERE = Path(__file__).resolve().parent
CATALOGS = HERE/'catalogs-02'
COMPILER_SOURCE = stage.X/'experiments/hir-options-hash/compiler-build-continuation-03'
COMPILER_WORK = stage.X/'.work/hir-options-hash-compiler-build-continuation-03'
MAX_FILES = 180000
MAX_BYTES = 8*2**30
MAX_FILE_BYTES = 2**30
MAX_JSON_BYTES = 256*2**20


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def read(path):
    path = Path(path)
    require(path.resolve(strict=True) == path and path.is_file() and not path.is_symlink()
            and path.stat().st_size <= MAX_JSON_BYTES, 'bounded ordinary prerequisite JSON required')
    return json.loads(path.read_bytes(), object_pairs_hook=unique,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def stamp(path):
    info = Path(path).lstat()
    return [info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns, info.st_nlink]


def write(path, value):
    data = (json.dumps(value, indent=2, sort_keys=True)+'\n').encode()
    require(len(data) <= MAX_JSON_BYTES, 'discovery JSON exceeds declared bound')
    with Path(path).open('xb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())


class Discovery:
    def __init__(self, modules):
        self.modules = modules
        self.comp = modules['comp']
        self.owned = modules['monitor'].owned
        self.files, self.links, self.routes, self.absent = {}, {}, {}, set()
        self.snapshots = set()
        self.total = 0

    def floor(self):
        return self.owned.disk(stage.ROOT, 9)

    def add(self, path, expected=None, *, snapshot=False):
        self.floor()
        path = Path(path)
        require(path.resolve(strict=True) == path and not path.is_symlink(),
                'ordinary frozen input required: '+str(path))
        require(path.stat().st_size <= MAX_FILE_BYTES, 'oversized frozen input')
        if str(path) in self.files:
            row = self.files[str(path)]
            require(self.comp.check_file(dict(path=str(path), **row)) == dict(path=str(path), **row),
                    'input changed during discovery')
        else:
            row = self.comp.check_file(dict(path=str(path), sha256=sha(path)))
            row = {key: row[key] for key in ['sha256', 'size', 'identity']}
            self.files[str(path)] = row
            self.total += row['size']
            require(len(self.files) <= MAX_FILES and self.total <= MAX_BYTES,
                    'finite input discovery bound exceeded')
        if expected is not None:
            require(row['sha256'] == expected['sha256'], 'historical input bytes changed')
            if 'identity' in expected:
                require(row['identity'] == expected['identity'], 'historical input identity changed')
            if 'stamp' in expected:
                require(stamp(path) == expected['stamp'], 'historical input stamp changed')
        if snapshot:
            require(row['size'] <= stage.SNAPSHOT_LIMITS['maximum_file_bytes'], 'bounded source/proof snapshot required')
            self.snapshots.add(str(path))
        return path

    def link(self, path, expected=None):
        path = Path(path)
        require(path.is_symlink(), 'expected provider symlink')
        row = dict(stamp=stamp(path), target=os.readlink(path), resolved=str(path.resolve(strict=True)))
        if expected is not None:
            require(row == expected, 'historical provider route changed')
        require(str(path) not in self.links or self.links[str(path)] == row, 'link changed during discovery')
        self.links[str(path)] = row
        return row

    def tree(self, root):
        """Only explicit completed evidence/provider roots, never unrelated trees."""
        root = Path(root)
        require(root.resolve(strict=True) == root and root.is_dir() and not root.is_symlink(),
                'ordinary discovery tree required')
        before = set()
        for directory, dirs, names in os.walk(root, followlinks=False):
            self.floor()
            for name in dirs+names:
                path = Path(directory)/name
                before.add(str(path.relative_to(root)))
                require(len(before) <= MAX_FILES, 'tree membership limit')
                if path.is_symlink():
                    self.link(path)
                elif path.is_file():
                    self.add(path)
                else:
                    require(path.is_dir(), 'special discovery entry')
        after = set()
        for directory, dirs, names in os.walk(root, followlinks=False):
            after.update(str((Path(directory)/name).relative_to(root)) for name in dirs+names)
        require(before == after, 'tree membership changed during discovery')

    def inherit(self, source):
        source = Path(source)
        freeze = read(self.add(source/'inputs.json', snapshot=True))
        if 'file_table_base' in freeze:
            require(source == stage.HERE and freeze['file_table_base'] == stage.FILE_TABLE_BASE,
                    'unreviewed compact inherited file table')
            self.add(stage.FILE_TABLE_BASE['path'], stage.FILE_TABLE_BASE, snapshot=True)
            table = stage.load_file_table(freeze, self.comp)
            freeze = stage.expand_file_table(freeze, table, guard=self.floor)
        else:
            require('file_table_integrity' not in freeze, 'partial file-table representation')
        plan = read(self.add(source/'plan.json', snapshot=True))
        if source == stage.NATIVE_QUALIFICATION_SOURCE:
            require(freeze['base_inputs'] == plan['base_inputs']
                    and freeze['base_inputs']['path'] == str(stage.NATIVE_SOURCE/'inputs.json')
                    and freeze['base_inputs']['sha256'] == sha(stage.NATIVE_SOURCE/'inputs.json'),
                    'exact original native proof base required')
            self.inherit(stage.NATIVE_SOURCE)
        else:
            require('base_inputs' not in freeze, 'unreviewed inherited proof base')
        if source in [stage.BETA_SOURCE, stage.NATIVE_SOURCE]:
            self.add(source/'snapshot-plan.json', snapshot=True)
        require(sha(source/'plan.json') == freeze['plan_sha256'], 'predecessor plan hash differs')
        for name, row in freeze['files'].items():
            self.add(name, row)
        for name, row in freeze.get('links', {}).items():
            self.link(name, row)
        for name in freeze.get('absent_paths', []):
            require(not Path(name).exists() and not Path(name).is_symlink(), 'predecessor absence changed')
            self.absent.add(name)
        return plan

    def imports(self):
        for module in list(sys.modules.values()):
            name = getattr(module, '__file__', None)
            if name and name.startswith('/Users/danluu/dev/'):
                path = Path(name).resolve(strict=True)
                self.add(path, snapshot=True)
                if path.suffix == '.py':
                    ast.parse(path.read_bytes(), filename=str(path))


def main():
    parser = argparse.ArgumentParser()
    for role in ['compiler', 'beta', 'native', 'run-make']:
        parser.add_argument('--'+role+'-audit', type=Path, required=True)
        parser.add_argument('--'+role+'-audit-sha256', required=True)
    args = vars(parser.parse_args())
    require(Path.cwd() == stage.ROOT and sys.dont_write_bytecode and not sys.flags.optimize,
            'fixed owner and unoptimized Python -B required')
    # Refuse missing/unsuccessful prerequisites before importing/discovering any
    # provider closure. Every supplied digest must describe actual audit bytes.
    work = dict(compiler=COMPILER_WORK, beta=stage.BETA_WORK,
                native=stage.NATIVE_QUALIFICATION_WORK, run_make=stage.RECIPE_WORK)
    audits = {}
    for role, evidence in work.items():
        path, digest = args[role+'_audit'], args[role+'_audit_sha256']
        require(len(digest) == 64 and all(c in '0123456789abcdef' for c in digest), 'exact audit SHA256 required')
        audit = read(path); terminal = read(evidence/'receipt.json')
        require(sha(path) == digest and audit['status'] == 'verified'
                and audit['receipt_sha256'] == sha(evidence/'receipt.json')
                and terminal['status'] == 'passed', 'actual completed audit/terminal required: '+role)
        audits[role] = dict(path=str(path), sha256=digest)
    modules = stage.dependencies()
    d = Discovery(modules); core = modules['core']; support = modules['bundle'].support
    require(support.BHERE == COMPILER_SOURCE and support.BUILT == COMPILER_WORK,
            'run-make adapter has not adopted the final compiler continuation03')
    targets = [HERE/'plan.json', HERE/'inputs.json', HERE/'snapshot-plan.json', HERE/'launch.json',
               HERE/'metadata-preflight.json', CATALOGS, stage.WORK, core.ARTIFACTS]
    require(all(not path.exists() and not path.is_symlink() for path in targets), 'fresh hash discovery/output paths required')
    with d.owned.workload_lock(d.owned.CANONICAL_LOCK, 600):
        started = time.time(); free_before = d.owned.disk(stage.ROOT, 16)
        require(all(not path.exists() and not path.is_symlink() for path in targets), 'hash output appeared during admission wait')
        for row in audits.values(): d.add(row['path'], row, snapshot=True)
        compiler_plan = d.inherit(COMPILER_SOURCE)
        beta_plan = d.inherit(stage.BETA_SOURCE)
        native_plan = d.inherit(stage.NATIVE_QUALIFICATION_SOURCE)
        recipe_plan = d.inherit(stage.RECIPE_SOURCE)
        for name, row in recipe_plan['admitted_provider_files'].items(): d.add(name, row)
        metadata_source = stage.X/'experiments/hir-options-hash/compiler-metadata-03'
        metadata_plan = d.inherit(metadata_source)
        require(compiler_plan['metadata_plan'] == metadata_plan, 'actual metadata source binding differs')
        for root in work.values(): d.tree(root)
        for root in work.values(): d.add(root/'receipt.json', snapshot=True)
        d.tree(stage.NATIVE_WORK)
        d.add(stage.NATIVE_WORK/'receipt.json', snapshot=True)
        for path in [COMPILER_WORK/'compiled.json', stage.NATIVE_QUALIFICATION_WORK/'native-controls.json',
                     stage.RECIPE_WORK/'result.json']:
            d.add(path, snapshot=True)
        actual = support.completed_build(d.add)
        require(actual['compiled']['candidate_revision'] == stage.REVISION, 'wrong compiled candidate')
        # completed_build explicitly traverses all three original owners. Bind
        # their closed supervisor histories too; no process is queried.
        for name in ['hir-options-hash-compiler-build-supervisor-02',
                     'hir-options-hash-compiler-build-continuation-supervisor-01',
                     'hir-options-hash-compiler-build-continuation-supervisor-03']:
            d.tree(stage.X/'.work/experiments'/name)
        for name, row in compiler_plan['ancestor_manifests'].items():
            if row is None:
                require(not Path(name).exists() and not Path(name).is_symlink(), 'ancestor manifest appeared')
                d.absent.add(name)
            else: d.add(name, row)
        for name, resolved in metadata_plan['routes'].items():
            require(str(Path(name).resolve(strict=True)) == resolved, 'metadata route changed')
            d.routes[name] = resolved
        for executable in [Path(sys.executable), Path('/opt/homebrew/bin/python3'),
                           Path('/bin/ps'), Path('/usr/sbin/lsof'), Path(native_plan['clang'])]:
            resolved = executable.resolve(strict=True); d.routes[str(executable)] = str(resolved); d.add(resolved)
            if executable.is_symlink(): d.link(executable)
        catalogs = {}
        CATALOGS.mkdir()
        for role, root in [('D2', core.D2), ('E2', core.E2), ('B3', core.B3)]:
            d.tree(root)
            inventory = support.inventory(root)
            catalog = CATALOGS/(role+'.json'); write(catalog, inventory); d.add(catalog, snapshot=True)
            catalogs[str(root)] = str(catalog)
        # Retained native and recipe outputs are read by the pure prerequisite
        # readers and must occur in this exact freeze, including binary bytes.
        native_paths = modules['recipe'].paths(native_plan['namespace'])
        d.tree(native_paths['stock'].parent)
        d.tree(support.BASE)
        native_result = read(stage.NATIVE_QUALIFICATION_WORK/'native-controls.json')
        pair = [str(core.B3/name) for name in native_result['ordered_driver_destinations']]
        providers = {}
        for row in native_plan['runtime_closure']['libraries']:
            path = Path(row['resolved']); d.add(path)
            providers[str(path)] = support.file(path)
        roots = {stage.WORK}
        monitor = modules['monitor']
        for owner in monitor.EVIDENCE_OWNERS:
            for path in (owner/'.work').iterdir():
                if path.name.startswith(monitor.EVIDENCE_PREFIXES) and (path.is_dir() or path.is_symlink()):
                    require(path.is_dir() and not path.is_symlink(), 'unexpected candidate evidence route')
                    roots.add(path)
        monitor.evidence_contract(stage.WORK, sorted(roots))
        environment, omitted = stage.driver_environment(native_plan['environment'], core.ARTIFACTS/'tmp')
        plan = dict(status='prepared-unrun', candidate_revision=stage.REVISION,
            source_identity=actual['compiled']['source_identity'], metadata_plan=metadata_plan,
            independent_audits=audits, immutable_trees=catalogs, executor_routes=d.routes,
            runtime_private_providers=providers, ordered_driver_pair=pair,
            roles=dict(build_compiler=str(core.D2), build_sysroot=str(core.B3),
                       runtime_compiler=str(core.E2), application_sysroot=str(core.E2)),
            environment=environment, sdk=environment['SDKROOT'], clang=native_plan['clang'],
            omitted_bootstrap_environment=omitted,
            evidence_roots=sorted(map(str, roots)),
            platform=dict(system=os.uname().sysname, release=os.uname().release,
                          version=os.uname().version, machine=os.uname().machine),
            capacity=dict(entry_gib=24,stop_gib=9,floor_gib=8,namespace_bytes=14*2**30,evidence_bytes=256*2**20),
            qualification_scope='One compile and two hash-driver processes; no application or performance claim.')
        plan['children'] = core.desired_commands(plan)
        for path in [stage.SNAPSHOT_SOURCE, *stage.SNAPSHOT_TESTS,
                     stage.SNAPSHOT_CONTROLS/'inputs.json', stage.SNAPSHOT_CONTROLS/'launch.json', stage.SNAPSHOT_AUDIT,
                     *[stage.SNAPSHOT_CONTROL_WORK/name for name in ['receipt.json', 'result.json',
                         'command/receipt.json', 'command/stdout', 'command/stderr']]]:
            d.add(path, snapshot=True)
        for name, row in read(stage.SNAPSHOT_CONTROLS/'inputs.json')['files'].items():
            d.add(name, row, snapshot=True)
        for path in [stage.FILE_TABLE_SOURCE, *stage.FILE_TABLE_TESTS,
                     stage.FILE_TABLE_CONTROLS/'inputs.json', stage.FILE_TABLE_CONTROLS/'launch.json', stage.FILE_TABLE_AUDIT,
                     *[stage.FILE_TABLE_CONTROL_WORK/name for name in ['receipt.json', 'result.json',
                         'command/receipt.json', 'command/stdout', 'command/stderr']]]:
            d.add(path, snapshot=True)
        for name, row in read(stage.FILE_TABLE_CONTROLS/'inputs.json')['files'].items():
            d.add(name, row, snapshot=True)
        # Actual tested bytes are required before importing the new pure helper.
        qualified = stage.Stage.__new__(stage.Stage)
        qualified.modules, qualified.comp = modules, d.comp
        qualified.owned, qualified.require = d.owned, require
        qualified.freeze = dict(files=d.files)
        file_table_qualification = qualified.file_table_qualification()
        table = stage.load_file_table(dict(files=d.files), d.comp)
        snapshots = stage.load_snapshots(dict(files=d.files), d.comp)
        d.imports()
        for path in [Path(__file__).resolve(), HERE/'stage.py', HERE/'controls.py', HERE/'prerequisites.py',
                     HERE/'snapshot_bindings.py', HERE/'test_snapshot_bindings.py',
                     HERE/'launch.py', HERE/'verify.py',
                     stage.ROOT/'scripts/supervise_experiment.py', *core.SOURCE_HASHES]: d.add(path, snapshot=True)
        def snapshot_file(path):
            snapshots.ordinary_route(Path(path)); d.add(path)
            return dict(path=str(path), **d.files[str(path)])
        # Bind every already-retained old blob and its complete audited catalog
        # before publishing the plan/freeze. The selected logical source list
        # is unchanged; this catalog only supplies alternative physical bytes.
        plan['snapshot_reuse'] = modules['snapshot_bindings'].catalog(
            stage.snapshot_predecessors(audits), plan['evidence_roots'], stage.SNAPSHOT_LIMITS,
            read_json=read, file_record=snapshot_file,
            directory_record=lambda path: stage.snapshot_directory(path, snapshots))
        write(HERE/'plan.json', plan); d.add(HERE/'plan.json', snapshot=True)
        freeze = dict(files=d.files, links=d.links, absent_paths=sorted(d.absent),
            python=str(Path(sys.executable).resolve(strict=True)), plan_sha256=sha(HERE/'plan.json'),
            launch_environment=environment, snapshot_inputs=sorted(d.snapshots))
        # Only the file-table representation changes; all current headers,
        # links, absences and logical snapshot selections remain complete.
        wire = table.split(freeze, base_path=stage.FILE_TABLE_BASE['path'],
                           base_sha256=stage.FILE_TABLE_BASE['sha256'], guard=d.floor)
        require(table.encoded(stage.expand_file_table(wire, table, guard=d.floor)) == table.encoded(freeze),
                'compact file table does not reconstruct the exact complete freeze')
        write(HERE/'inputs.json', wire)
        records = stage.snapshot_records(freeze, sha(HERE/'inputs.json'), d.comp)
        selected = modules['snapshot_bindings'].select(records, plan['snapshot_reuse'])
        projection = snapshots.measure(records, stage.SNAPSHOT_LIMITS, d.floor,
            reuse=selected['records'], evidence_roots=selected['evidence_roots'])
        current = monitor.sample(evidence_root=stage.WORK, evidence_roots=sorted(roots))
        require(monitor.rejection(current) is None, 'hash aggregate evidence admission failed')
        reservation = stage.snapshot_reservation(projection, records, modules['snapshot_bindings'])
        require(current['evidence_allocated_bytes'] + reservation <= 256*2**20,
                'hash compressed proof and remaining stage exceed evidence cap')
        snapshot_plan = dict(inputs_sha256=sha(HERE/'inputs.json'), limits=stage.SNAPSHOT_LIMITS,
            helper=dict(path=str(stage.SNAPSHOT_SOURCE), sha256=freeze['files'][str(stage.SNAPSHOT_SOURCE)]['sha256']),
            projection=projection, remaining_evidence_reservation_bytes=stage.REMAINING_EVIDENCE_RESERVATION,
            reuse_selection=selected,
            measured_existing_evidence_bytes=current['evidence_allocated_bytes'],
            projected_reservation_bytes=reservation, evidence_cap_bytes=256*2**20)
        encoded = snapshots.encoded(snapshot_plan)
        require(len(encoded) <= stage.SNAPSHOT_LIMITS['maximum_manifest_bytes'], 'bounded hash projection required')
        with (HERE/'snapshot-plan.json').open('xb') as stream:
            stream.write(encoded); stream.flush(); os.fsync(stream.fileno())
        require(sha(HERE/'snapshot-plan.json') == hashlib.sha256(encoded).hexdigest(),
                'hash projection publication readback differs')
        # Use the exact controller readers with no __init__/WORK creation and
        # no execute/core invocation. This catches actual schema mismatches.
        probe = stage.Stage.__new__(stage.Stage)
        probe.modules, probe.core, probe.monitor, probe.owned, probe.comp = modules, core, monitor, d.owned, d.comp
        probe.snapshots = snapshots
        probe.require = require; probe.freeze = freeze; probe.plan = plan
        probe.inputs_sha256 = sha(HERE/'inputs.json'); probe.environment = environment
        probe.bind_snapshot_plan(sha(HERE/'snapshot-plan.json'))
        original_environment = dict(os.environ)
        os.environ.clear(); os.environ.update(environment)
        try:
            probe.guard(True); probe.file_table_qualification(); probe.snapshot_qualification(); probe.snapshot_reuse()
            observed = probe.prerequisites(); budget = probe.budget()
        finally:
            os.environ.clear(); os.environ.update(original_environment)
        d.floor()
        write(HERE/'metadata-preflight.json', dict(status='passed', started_at=started,
            finished_at=time.time(), free_bytes_before=free_before, free_bytes_after=d.floor(),
            discovery_entry_gib=16, discovery_live_floor_gib=9, workload_children=0,
            prerequisites=observed, budget=budget, files=len(d.files), input_bytes=d.total,
            file_table_qualification=file_table_qualification, file_table_base=wire['file_table_base'],
            file_table_integrity=wire['file_table_integrity'], delta_files=len(wire['files']),
            inputs_sha256=sha(HERE/'inputs.json'), snapshot_plan_sha256=sha(HERE/'snapshot-plan.json'),
            snapshot_reservation_bytes=reservation, work_created=False))
        launch = dict(status='prepared-unrun-awaiting-review', owner=str(stage.ROOT),
            environment=environment, command=[freeze['python'],'-B',str(stage.ROOT/'scripts/supervise_experiment.py'),
                '--run-id','hir-options-hash-driver-supervisor-01','--',freeze['python'],'-B',str(HERE/'stage.py'),
                '--inputs-sha256',sha(HERE/'inputs.json'), '--snapshot-plan-sha256',sha(HERE/'snapshot-plan.json')],
            inputs_sha256=sha(HERE/'inputs.json'), snapshot_plan_sha256=sha(HERE/'snapshot-plan.json'),
            plan_sha256=sha(HERE/'plan.json'), helper_sha256=sha(HERE/'stage.py'),
            expected_children=3, driver_processes=2, contexts_per_process=8, capacity=plan['capacity'])
        write(HERE/'launch.json', launch)
        print(json.dumps(dict(status='prepared-unrun', launch_sha256=sha(HERE/'launch.json'),
                             inputs_sha256=sha(HERE/'inputs.json'), files=len(d.files), bytes=d.total), indent=2))


if __name__ == '__main__': main()
