#!/usr/bin/env python3
"""Source-only B3 discovery/preparation, gated on actual successful continuation.

No compiler/provider probe, extraction, B3 copy or launch is performed. The
eventual invocation is itself a separately reviewed read/hash operation under
canonical admission. Files are created exclusively; partial proposals remain.
"""
import argparse
import ast
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import tomllib

import compose as c
import history
import producer
import provider_observations

HERE, X, S, N = c.HERE, c.X, c.S, c.N
SOURCE = X/'experiments/hir-options-hash/compiler-build-continuation-03'
PREVIOUS_SOURCE = X/'experiments/hir-options-hash/compiler-build-continuation-01'
BUILD = X/'.work/hir-options-hash-compiler-build-continuation-03'
ORIGINAL = X/'experiments/hir-options-hash/compiler-build-02'


def write(path, value):
    with path.open('xb') as stream:
        stream.write(c.comp.encoded(value)); stream.flush(); os.fsync(stream.fileno())


class Discovery:
    def __init__(self, audit, audit_sha256):
        self.files, self.links, self.routes = {}, {}, {}
        self.snapshot_inputs = set()
        self.audit = Path(audit)
        c.require(self.audit.parent == X/'.work' and self.audit.name.endswith('.json'), 'owned exact compiler audit required')
        c.require(c.owned.sha(self.audit) == audit_sha256, 'independent compiler audit hash differs')
        self.add(self.audit, snapshot=True)
        self.audit_record = dict(path=str(self.audit), sha256=audit_sha256)
        self.m = c.load_metadata()
        self.metadata_freeze = c.read(c.METADATA_SOURCE/'inputs.json')

    def add(self, path, *, snapshot=False):
        path = Path(path)
        c.require(path.resolve(strict=True) == path and path.is_file() and not path.is_symlink(), 'ordinary discovery input required: '+str(path))
        row = c.comp.check_file(dict(path=str(path), sha256=c.owned.sha(path)))
        record = {k: row[k] for k in ['sha256', 'size', 'identity']}
        c.require(str(path) not in self.files or self.files[str(path)] == record, 'input changed during discovery')
        self.files[str(path)] = record
        if snapshot:
            c.require(record['size'] <= 64*2**20, 'source snapshot exceeds individual bound')
            self.snapshot_inputs.add(str(path))
        c.owned.disk(c.OWNER, 9)
        return path

    def inherited(self, path, row):
        """Historical source inputs must retain their exact old identity/bytes."""
        self.add(path)
        c.require(self.files[str(path)]['sha256'] == row['sha256'] and self.m.stamp(path) == row['stamp'],
                  'historical immutable input changed: '+str(path))

    def actual_files(self, rows):
        for name, row in rows.items():
            path = Path(name)
            if row.get('kind') == 'directory':
                continue
            if row.get('kind') == 'link' or ('target' in row and 'sha256' not in row):
                c.require(path.is_symlink() and self.m.stamp(path) == row['stamp']
                        and os.readlink(path) == row['target'], 'qualified link differs')
                resolved = str(path.resolve(strict=True))
                if 'resolved' in row:
                    c.require(resolved == row['resolved'], 'qualified link resolution differs')
                value = dict(stamp=row['stamp'], target=row['target'], resolved=resolved)
                c.require(name not in self.links or self.links[name] == value, 'conflicting qualified link')
                self.links[name] = value
                if Path(resolved).is_file():
                    self.add(resolved)
            else:
                self.inherited(path, row)

    def inventory(self, root):
        values = self.m.inventory(root, True)
        result = {name: row for name, row in values.items() if row['kind'] != 'directory'}
        self.actual_files({str(root/name): row for name, row in result.items()})
        return result

    def read_history(self):
        for path in [SOURCE/'plan.json', SOURCE/'inputs.json', PREVIOUS_SOURCE/'test_source.py', ORIGINAL/'plan.json', ORIGINAL/'inputs.json']:
            self.add(path, snapshot=True)
        spec = importlib.util.spec_from_file_location('b3_discovered_test_source', PREVIOUS_SOURCE/'test_source.py')
        tests = importlib.util.module_from_spec(spec); sys.modules[spec.name] = tests; spec.loader.exec_module(tests)
        value = history.validate(owner=X, source=S, evidence=BUILD, source_directory=SOURCE,
                                 frozen=lambda path: self.add(path, snapshot=True), sha=c.owned.sha, derive_tests=tests.derive)
        audit = c.read(self.audit)
        c.require(audit['status'] == 'verified' and audit['receipt_sha256'] == c.owned.sha(BUILD/'receipt.json'),
                  'actual completed compiler independent audit required')
        return value

    def discover(self):
        actual = self.read_history()
        continued, original, compiled = actual['plan'], actual['original_plan'], actual['compiled']
        c.require(compiled['candidate_revision'] == c.REVISION, 'candidate differs')
        c.workspace.historical_controls(original, X, ORIGINAL,
            lambda path: self.add(path, snapshot=True), c.owned.sha)
        self.add(X/'.work/hir-options-hash-compiler-build-01/receipt.json', snapshot=True)
        self.add(X/'experiments/hir-options-hash/compiler-build-01/inputs.json', snapshot=True)
        self.m.guard(original['metadata_plan'], self.metadata_freeze, True)
        # Retain the full metadata/current source/provider guard closure. Current
        # candidate-owned alias changes come exclusively from compiled.providers;
        # they never rewrite these historical immutable inputs.
        for name, row in self.metadata_freeze['files'].items():
            self.inherited(name, row)
        self.links.update(self.metadata_freeze['links'])
        for name, row in c.read(SOURCE/'inputs.json')['files'].items():
            self.inherited(name, row)
        self.actual_files(compiled['providers'])
        self.actual_files({str(c.E/name): row for name, row in compiled['stage1'].items()})
        for name in ['stage1-inventory.json', 'stage1-native-loader.json', 'stage1-final-loader-state.json',
                     'run-make-support-inventory.json', 'run-make-support-producer.json']:
            self.add(BUILD/name, snapshot=True)
        runtime = c.read(BUILD/'stage1-inventory.json')
        closure = runtime['closure']
        for row in closure['identity']['libraries']:
            self.add(row['resolved'])
            c.require(self.files[row['resolved']]['sha256'] == row['sha256'], 'E2 loader bytes differ')
        c.require(self.m.loaders.library_state(closure['identity']) == c.read(BUILD/'stage1-final-loader-state.json')['state'],
                  'E2 final loader state differs')
        driver_names = [name for name in compiled['stage1'] if Path(name).parent == Path('lib')
                        and Path(name).name.startswith('librustc_driver-') and name.endswith('.dylib')]
        c.require(len(driver_names) == 1, 'unique actual E2 driver required')
        driver = self.add(c.E/driver_names[0])
        tree = S/'build'/c.H/'stage1-rustc'
        stamp = self.add(tree/c.H/'release/.librustc-stamp', snapshot=True)
        c.require(stamp.stat().st_size <= c.comp.MAX_STAMP_BYTES, 'bounded actual private stamp required')
        entries = c.comp.parse_stamp(stamp.read_bytes(), tree=tree)
        approved = {}
        for entry in entries:
            path = self.add(entry['source'])
            approved[str(path)] = self.files[str(path)]
        archives = []
        for name, seed in original['metadata_plan']['seeds'].items():
            if Path(name).name in c.comp.BETA:
                self.add(name)
                c.require(seed['active'] and self.files[name]['sha256'] == seed['sha256'] == c.comp.BETA[Path(name).name][0],
                          'beta archive/provider identity differs')
                archives.append(dict(path=name, sha256=seed['sha256']))
        c.require(len(archives) == 2, 'actual beta provider pair required')
        proofs = [BUILD/'receipt.json', BUILD/'compiled.json', SOURCE/'plan.json', SOURCE/'inputs.json', self.audit]
        composition = c.comp.inspect_inputs(source=S, tree=tree, archives=archives,
            stamp=dict(path=str(stamp), **self.files[str(stamp)]), approved_private_files=approved,
            build_compiler=dict(path=str(c.D/'bin/rustc'), **self.files[str(c.D/'bin/rustc')]),
            runtime_source_commit=c.REVISION, runtime_driver=dict(path=str(driver), **self.files[str(driver)]),
            proofs=[dict(path=str(path), **self.files[str(path)]) for path in proofs], archive_copies=[c.COPY])
        config = self.add(S/'bootstrap.toml', snapshot=True)
        proof = producer.discover(composition, actual['streams'], tomllib.loads(config.read_text()))
        shim = self.add(S/'build/bootstrap/debug/rustc')
        build_std = S/'build'/c.H/'stage0-sysroot'
        proof.update(bootstrap_shim=dict(path=str(shim), **self.files[str(shim)]),
                     build_sysroot=dict(root=str(build_std), files=self.inventory(build_std)),
                     compiler_environment=original['tests']['assertions']['build_compiler_std']['compiler_commit_environment'])
        loader_dirs = []
        for name in producer.test_loader_paths(S):
            root = Path(name)
            c.require(root.resolve(strict=True) == root and root.is_dir(), 'ordinary loader search directory required')
            entries = {}
            for path in root.iterdir():
                stamp = self.m.stamp(path)
                if path.is_symlink():
                    target = str(path.resolve(strict=True)); self.add(target)
                    entries[path.name] = dict(kind='link', stamp=stamp, target=os.readlink(path), resolved=target,
                                              resolved_file=self.m.file(target))
                elif path.is_file():
                    self.add(path); entries[path.name] = dict(kind='file', **self.m.file(path))
                else:
                    c.require(path.is_dir(), 'special loader directory entry')
                    entries[path.name] = dict(kind='directory', stamp=stamp)
            loader_dirs.append(dict(path=name, entries=entries))
        proof['loader_directories'] = loader_dirs
        producer.validate(proof, composition, actual['streams'], c.REVISION, tomllib.loads(config.read_text()))
        # Planning reads the actual admitted D2 copies of these exact archive
        # bytes. B3's own subsequent -L/-l/loader/strip observations remain required.
        auxiliary = {}
        for destination, source in [(c.TOOL, c.D/c.TOOL), (c.COPY['destination'], c.D/'lib/libLLVM.dylib')]:
            self.add(source)
            c.require(self.files[str(source)]['sha256'] == composition['files'][destination]['sha256'],
                      'auxiliary plan not based on exact current beta archive bytes')
            auxiliary[destination] = provider_observations.macho_declarations(source)
        version_rows = [row for row in compiled['command_history'] if row['command'] == [str(c.E/'bin/rustc'), '-vV']]
        c.require(version_rows, 'actual E2 version observation required')
        versions = [Path(row['path']).parent/'stdout' for row in version_rows]
        for path in versions:
            self.add(path, snapshot=True)
        c.require(len({path.read_bytes() for path in versions}) == 1, 'actual E2 version observations disagree')
        metadata_history = X/'.work/hir-options-hash-compiler-metadata-03/commands/012'
        otool_receipt = c.read(self.add(metadata_history/'receipt.json', snapshot=True))
        otool_raw = self.add(metadata_history/'stdout', snapshot=True)
        c.require(otool_receipt['status'] == 'finished' and otool_receipt['returncode'] == 0
                  and otool_receipt['command'] == ['/usr/bin/xcrun', '--sdk', 'macosx', '--find', 'otool']
                  and c.owned.sha(otool_raw) == otool_receipt['stdout_sha256'], 'actual selected otool discovery differs')
        otool = otool_raw.read_text().strip()
        self.add(Path(otool).resolve(strict=True)); self.routes[otool] = str(Path(otool).resolve(strict=True))
        environment = dict(continued['environment'], TMPDIR=str(c.WORK/'tmp'))
        roots = set()
        for owner in c.bounded.shared.EVIDENCE_OWNERS:
            for path in (owner/'.work').iterdir():
                if path.name.startswith(c.bounded.shared.EVIDENCE_PREFIXES) and (path.is_dir() or path.is_symlink()):
                    c.require(not path.is_symlink(), 'candidate evidence symlink'); roots.add(path)
        roots.add(c.WORK)
        plan = dict(status='prepared-unrun', candidate_revision=c.REVISION, source_identity=compiled['source_identity'],
            actual_build=dict(source=str(SOURCE), evidence=str(BUILD), audit=self.audit_record,
                unavailable_contemporaneous_cwd_children=actual['unavailable_contemporaneous_cwd_children']),
            metadata_plan=original['metadata_plan'], composition=composition,
            composition_sha256=c.comp.digest(c.comp.encoded(composition)), producer=proof,
            runtime_version=versions[0].read_text(), otool=otool, otool_query_output=otool_raw.read_text(),
            auxiliary_declarations=auxiliary, environment=environment, evidence_roots=sorted(map(str, roots)),
            executor_routes=self.routes, canonical_lock=str(c.owned.CANONICAL_LOCK), wait_seconds=600,
            capacity=dict(entry_gib=24, stop_gib=9, floor_gib=8, namespace_bytes=14*2**30, evidence_bytes=256*2**20),
            interpretation='assembly and strip only; compiler roles/hash/run-make/application remain separate')
        plan['children'] = c.desired_commands(plan)
        for row in plan['children']:
            path = Path(row['argv'][0])
            if path == c.B3/c.TOOL:
                continue
            resolved = path.resolve(strict=True); self.add(resolved); self.routes[str(path)] = str(resolved)
        self.add(S/'src/stage0', snapshot=True)
        self.add(ORIGINAL/'ancestor-Cargo.before.toml', snapshot=True)
        for name, row in original['ancestor_manifests'].items():
            if row is not None:
                self.add(name)
        for directory in [HERE, c.OWNER/'experiments/hir-options-hash-stage-monitor']:
            for path in directory.iterdir():
                c.require(path.is_file() and not path.is_symlink(), 'ordinary source-only controller closure required')
                self.add(path, snapshot=True)
                if path.suffix == '.py':
                    ast.parse(path.read_bytes())
        bindings = c.read(HERE/'source-bindings.json')
        for group in ['references', 'predecessor_draft', 'timing_sources', 'provider_grammar_references']:
            for row in bindings[group].values():
                self.add(row['path'], snapshot=True)
                c.require(self.files[row['path']]['sha256'] == row['sha256']
                          and self.files[row['path']]['size'] == row['size'], 'bound source/reference differs')
        for path in [c.OWNER/'scripts/supervise_experiment.py', X/'experiments/stable-cgu/owned_stage.py',
                     c.METADATA_SOURCE/'inputs.json', self.m.ACQUIRED]:
            self.add(path, snapshot=True)
        for imported in list(sys.modules.values()):
            value = getattr(imported, '__file__', None)
            if value and value.startswith('/Users/danluu/dev/'):
                self.add(Path(value).resolve(strict=True), snapshot=True)
        python = Path(sys.executable).resolve(strict=True); self.add(python)
        for route in ['/opt/homebrew/bin/python3', '/bin/ps', '/usr/sbin/lsof']:
            resolved = Path(route).resolve(strict=True); self.add(resolved); self.routes[route] = str(resolved)
        self.m.guard(original['metadata_plan'], self.metadata_freeze, True)
        c.comp.recheck_inputs(composition)
        return plan, dict(files=self.files, links=self.links, python=str(python), launch_environment=environment,
            snapshot_inputs=sorted(self.snapshot_inputs), absent_paths=[name for name, value in original['ancestor_manifests'].items() if value is None])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--actual-audit', required=True)
    parser.add_argument('--actual-audit-sha256', required=True)
    args = parser.parse_args()
    c.require(Path.cwd() == c.OWNER and sys.dont_write_bytecode and not sys.flags.optimize, 'explicit preparation owner/Python required')
    c.require(not any((HERE/name).exists() for name in ['plan.json', 'inputs.json', 'launch.json'])
              and not c.WORK.exists() and not c.B3.exists(), 'fresh proposal and B3 required')
    with c.owned.workload_lock(c.owned.CANONICAL_LOCK, 600):
        c.owned.disk(c.OWNER, 16)
        plan, freeze = Discovery(args.actual_audit, args.actual_audit_sha256).discover()
        write(HERE/'plan.json', plan)
        row = c.comp.check_file(dict(path=str(HERE/'plan.json'), sha256=c.owned.sha(HERE/'plan.json')))
        freeze['files'][str(HERE/'plan.json')] = {k: row[k] for k in ['sha256', 'size', 'identity']}
        freeze['snapshot_inputs'].append(str(HERE/'plan.json'))
        freeze['plan_sha256'] = row['sha256']
        write(HERE/'inputs.json', freeze)
        launch = dict(status='prepared-unrun-awaiting-review', owner=str(c.OWNER), environment=plan['environment'],
            command=[freeze['python'], '-B', str(c.OWNER/'scripts/supervise_experiment.py'), '--run-id',
                     'hir-options-hash-beta-composition-supervisor-06', '--', freeze['python'], '-B', str(HERE/'compose.py'),
                     '--inputs-sha256', c.owned.sha(HERE/'inputs.json')],
            inputs_sha256=c.owned.sha(HERE/'inputs.json'), plan_sha256=c.owned.sha(HERE/'plan.json'),
            expected_children=19, capacity=plan['capacity'], actual_composition=False)
        write(HERE/'launch.json', launch)
        c.owned.disk(c.OWNER, 9)
        print(json.dumps(dict(status='prepared-unrun', launch_sha256=c.owned.sha(HERE/'launch.json'),
                             inputs=len(freeze['files']), private_entries=len(plan['composition']['private']))))


if __name__ == '__main__':
    main()
