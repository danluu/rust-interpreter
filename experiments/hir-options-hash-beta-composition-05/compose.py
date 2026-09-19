#!/usr/bin/env python3
"""Source-only B3 composition and auxiliary strip stage.

No plan/inputs/launch exist until the candidate build and producer discovery
actually pass. The separate stock/hash controls qualify compiler roles later.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time
import tomllib

import bounded_stage as bounded
import compose_sysroot as comp
import producer
import ancestor_workspace as workspace
import history
import provider_observations as providers
from strip_object import check_strip

HERE = Path(__file__).resolve().parent
OWNER = HERE.parents[1]
X = bounded.OWNER
N = bounded.NAMESPACE
S = N / 'source'
H = comp.HOST
D = S / 'build' / H / 'stage0'
E = S / 'build' / H / 'stage1'
B3 = N / 'beta-sysroot'
WORK = bounded.EVIDENCE
ASSEMBLY = WORK / 'assembly'
DEBUG = WORK / 'strip'
METADATA_SOURCE = X / 'experiments/hir-options-hash/compiler-metadata-03'
REVISION = '4de35bdacef0e3cd18a66bc30b5459c19e09b118'
TOOL = f'lib/rustlib/{H}/bin/rust-objcopy'
COPY = dict(source_destination='lib/libLLVM.dylib', destination=f'lib/rustlib/{H}/lib/libLLVM.dylib')
STRIP_SOURCE = b'#[inline(never)] fn value() -> u32 { 42 }\nfn main() { println!("{}", value()); }\n'
require, owned = comp.require, bounded.owned


def read(path):
    return json.loads(Path(path).read_bytes())


def load_metadata():
    # Actual retained metadata module; imported source closure must be frozen.
    sys.path.insert(0, str(METADATA_SOURCE))
    spec = importlib.util.spec_from_file_location('b3_candidate_metadata', METADATA_SOURCE / 'metadata.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def desired_commands(plan):
    """Exact 19-child assembly/strip history, without any role/driver run."""
    env = plan['environment']
    traced = env | {'DYLD_PRINT_LIBRARIES': '1'}
    otool = plan['otool']
    rows = []
    def add(argv, environment=env):
        rows.append(dict(argv=list(map(str, argv)), cwd=str(S), environment=environment))
    add(['/usr/bin/git', 'rev-parse', 'HEAD'])
    add(['/usr/bin/git', 'diff', 'HEAD', '--'])
    for root in [D, E]:
        add([root / 'bin/rustc', '-vV'])
        add([root / 'bin/rustc', '--print', 'sysroot'])
    add(['/usr/bin/xcrun', '--sdk', 'macosx', '--find', 'otool'])
    for relative in [TOOL, COPY['destination']]:
        add([otool, '-L', B3 / relative])
        add([otool, '-l', B3 / relative])
    add([B3 / TOOL, '--version'], traced)
    add([D / 'bin/rustc', '--sysroot=' + str(B3), '--emit=obj', '-Cdebuginfo=2',
         '-Cstrip=none', '-Csplit-debuginfo=off', '-Copt-level=0', DEBUG / 'debug.rs',
         '-o', DEBUG / 'before.o'])
    add([otool, '-l', DEBUG / 'before.o'])
    add([B3 / TOOL, '--strip-debug', DEBUG / 'before.o', DEBUG / 'after.o'], traced)
    add([otool, '-l', DEBUG / 'after.o'])
    add(['/usr/bin/xcrun', '--sdk', 'macosx', '--find', 'otool'])
    add(['/usr/bin/git', 'rev-parse', 'HEAD'])
    add(['/usr/bin/git', 'diff', 'HEAD', '--'])
    return rows


def dyld(raw, pid):
    """Retain both qualified dyld forms; require exact B3 private membership."""
    allowed = {str(B3 / TOOL), str(B3 / COPY['destination'])}
    loaded, basenames, lines = set(), {}, []
    require(type(pid) is int and pid > 0 and len(raw) <= 8 * 2**20, 'bounded actual loader trace required')
    for number, line in enumerate(raw.decode('utf-8', errors='strict').splitlines(), 1):
        image = re.fullmatch(rf'dyld\[{pid}\]: (?:<[0-9A-Fa-f-]{{36}}>\s+)?(/.+)', line)
        delayed = re.fullmatch(rf'dyld\[{pid}\]: move loaded to delayed: ([^/\r\n]+)', line)
        if image:
            path = image[1]
            comp.absolute(path)
            basenames.setdefault(Path(path).name, set()).add(path)
            if not path.startswith(('/usr/lib/', '/System/Library/')):
                require(path in allowed, 'foreign B3 auxiliary provider')
                loaded.add(path)
        elif delayed:
            matches = basenames.get(delayed[1], set())
            require(len(matches) == 1 and all(p.startswith(('/usr/lib/', '/System/Library/')) for p in matches),
                    'delayed image was not one previously seen system provider')
        else:
            raise ValueError('unexpected auxiliary loader diagnostic: ' + line)
        lines.append(dict(line=number, raw=line))
    require(loaded == allowed, 'B3 objcopy did not load its matching beta LLVM')
    return dict(loaded_private=sorted(loaded), lines=lines, raw_sha256=comp.digest(raw))


def declarations(raw):
    """Retain raw -l output and distinguish dylib identity from load edges."""
    require(len(raw) <= 8 * 2**20, 'bounded Mach-O declarations required')
    text = raw.decode('utf-8', errors='strict')
    blocks = re.split(r'(?m)^Load command \d+\s*$', text)[1:]
    require(blocks, 'missing Mach-O commands')
    result = dict(rpaths=[], loads=[], identities=[], raw_sha256=comp.digest(raw))
    kinds = {'LC_LOAD_DYLIB', 'LC_LOAD_WEAK_DYLIB', 'LC_REEXPORT_DYLIB',
             'LC_LOAD_UPWARD_DYLIB', 'LC_LAZY_LOAD_DYLIB', 'LC_LOAD_DYLINKER'}
    for block in blocks:
        match = re.search(r'(?m)^\s*cmd (LC_\w+)\s*$', block)
        require(match is not None and match[1] != 'LC_DYLD_ENVIRONMENT', 'unsupported Mach-O command')
        kind = match[1]
        require(not kind.endswith('_DYLIB') or kind in kinds or kind == 'LC_ID_DYLIB', 'unknown Mach-O load kind')
        if kind == 'LC_RPATH':
            match = re.search(r'(?m)^\s*path (.+) \(offset \d+\)\s*$', block)
            require(match is not None, 'malformed Mach-O rpath')
            result['rpaths'].append(match[1])
        elif kind in kinds or kind == 'LC_ID_DYLIB':
            match = re.search(r'(?m)^\s*name (.+) \(offset \d+\)\s*$', block)
            require(match is not None, 'malformed Mach-O dependency')
            (result['identities'] if kind == 'LC_ID_DYLIB' else result['loads']).append([kind, match[1]])
    return result


class Stage:
    def __init__(self, inputs_sha256):
        require(owned.sha(HERE / 'inputs.json') == inputs_sha256, 'reviewed B3 freeze required')
        self.freeze = read(HERE / 'inputs.json')
        require(owned.sha(HERE / 'plan.json') == self.freeze['plan_sha256'], 'B3 plan differs')
        self.plan = read(HERE / 'plan.json')
        require(Path.cwd() == OWNER and sys.dont_write_bytecode and not sys.flags.optimize,
                'explicit controller owner and Python flags required')
        require(str(Path(sys.executable).resolve(strict=True)) == self.freeze['python'], 'controller Python differs')
        require(self.plan['candidate_revision'] == REVISION and self.plan['children'] == desired_commands(self.plan),
                'wrong candidate or child allowlist')
        require(self.plan['composition']['source'] == str(S)
                and self.plan['composition']['runtime_source_commit'] == REVISION
                and self.plan['composition']['archive_copies'] == [COPY], 'B3 source/copy policy differs')
        self.build = comp.absolute(self.plan['actual_build']['evidence'])
        self.build_source = comp.absolute(self.plan['actual_build']['source'])
        require(self.build == X / '.work/hir-options-hash-compiler-build-continuation-03'
                and self.build_source == X / 'experiments/hir-options-hash/compiler-build-continuation-03',
                'actual successful compiler continuation route required')
        self.original_source = X / 'experiments/hir-options-hash/compiler-build-02'
        self.previous_source = X / 'experiments/hir-options-hash/compiler-build-continuation-01'
        self.continuation_plan = read(self.build_source / 'plan.json')
        self.build_plan = read(self.original_source / 'plan.json')
        require(read(self.previous_source/'plan.json')['original_plan'] == self.build_plan, 'original build policy differs')
        self.prior_evidence = tuple(map(comp.absolute, self.plan['evidence_roots']))
        require({WORK, self.build, X / '.work/hir-options-hash-compiler-build-01',
                 X / '.work/hir-options-hash-compiler-build-02',
                 X / '.work/hir-options-hash-compiler-build-continuation-01'} <= set(self.prior_evidence),
                'actual or retained compiler/composition evidence omitted from aggregate budget')
        self.m = load_metadata()
        self.metadata_freeze = read(METADATA_SOURCE / 'inputs.json')
        self.environment = dict(os.environ)
        expected = self.freeze['launch_environment']
        extra = set(self.environment) - set(expected)
        require(all(self.environment.get(k) == v for k, v in expected.items())
                and extra <= {'__CF_USER_TEXT_ENCODING'}, 'unexpected controller environment')
        if extra:
            cf = self.environment['__CF_USER_TEXT_ENCODING'].split(':')
            require(len(cf) == 3 and all(re.fullmatch(r'(?:0[xX][0-9a-fA-F]{1,8}|[0-9]{1,10})', v) for v in cf)
                    and int(cf[0], 16 if cf[0].lower().startswith('0x') else 10) == os.getuid() == 501,
                    'unexpected Darwin CF context')
        require(not any(name in self.plan['environment'] for name in [
            'RUSTC_BOOTSTRAP', 'RUSTC_FORCE_RUSTC_VERSION', 'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS',
            'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'DYLD_LIBRARY_PATH', 'DYLD_FALLBACK_LIBRARY_PATH',
            'DYLD_INSERT_LIBRARIES', 'DYLD_PRINT_LIBRARIES']), 'ambient compiler/loader policy override')
        require(not WORK.exists() and not WORK.is_symlink() and not B3.exists() and not B3.is_symlink(),
                'fresh B3/evidence required')
        require(WORK.parent.resolve(strict=True) == WORK.parent, 'ordinary evidence parent required')
        WORK.mkdir(); (WORK / 'commands').mkdir(); (WORK / 'tmp').mkdir()
        self.installed = None
        self.record = dict(status='waiting', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(),
            candidate_revision=REVISION, inputs_sha256=inputs_sha256, commands=[], assemblies=0,
            debug_object_compilations=0, native_stock_qualified=False, hash_driver_qualified=False,
            application_qualified=False, runtime_installation=False, benchmark=False)
        self.inputs_sha256 = inputs_sha256
        self.last_budget_at = float('-inf')
        self.last_budget = None
        self.save()

    def save(self):
        owned.write(WORK / 'receipt.json', self.record)

    def budget(self, force=False):
        # Free-space checks bracket every copied MiB. The aggregate namespace
        # traversal is sampled at most five seconds apart, like native child
        # supervision, rather than rescanning the compiler cache each MiB.
        free = owned.disk(OWNER, 9)
        now = time.monotonic()
        if force or now - self.last_budget_at >= 5:
            self.last_budget = bounded.sample(self.prior_evidence)
            self.last_budget_at = time.monotonic()
            require(bounded.rejection(self.last_budget) is None, str(bounded.rejection(self.last_budget)))
        return dict(self.last_budget, current_free_bytes=free)

    def guard(self, full=False):
        require(dict(os.environ) == self.environment, 'controller environment changed')
        require(owned.sha(HERE / 'inputs.json') == self.inputs_sha256, 'source freeze changed')
        for name, record in self.freeze['files'].items():
            require(comp.ordinary(name) == record['identity'], 'frozen input identity changed: ' + name)
            if full:
                require(comp.check_file(dict(path=name, **record)) == dict(path=name, **record), 'input bytes changed')
        for name, row in self.freeze['links'].items():
            path = Path(name)
            require(path.is_symlink() and self.m.stamp(path) == row['stamp']
                    and os.readlink(path) == row['target'] and str(path.resolve(strict=True)) == row['resolved'],
                    'frozen route changed')
        for name, resolved in self.plan['executor_routes'].items():
            require(str(Path(name).resolve(strict=True)) == resolved, 'executor route changed')
        self.m.guard(self.plan['metadata_plan'], self.metadata_freeze, full)
        self.workspace_guard(full)
        for module in list(sys.modules.values()):
            path = getattr(module, '__file__', None)
            if path and path.startswith('/Users/danluu/dev/'):
                require(str(Path(path).resolve(strict=True)) in self.freeze['files']
                        or str(Path(path).resolve(strict=True)) in self.metadata_freeze['files'], 'unfrozen imported source')
        if self.installed is not None:
            for name, row in self.installed.items():
                require(comp.ordinary(B3 / name) == row['identity'], 'new B3 file changed')
            if full:
                require(comp.output_inventory(B3) == self.installed, 'complete B3 membership/bytes changed')

    def workspace_guard(self, full):
        controls = X / 'experiments/hir-options-hash/workspace-controls-01/inputs.json'
        before = self.original_source / 'ancestor-Cargo.before.toml'
        required = [self.original_source / 'plan.json', self.original_source / 'inputs.json',
                    before, self.m.ACQUIRED, controls, X / 'Cargo.toml']
        require(all(str(path) in self.freeze['files'] for path in required),
                'workspace transition/source catalog omitted from current freeze')
        require(read(self.original_source / 'plan.json') == self.build_plan,
                'actual build02 ancestor policy changed')
        workspace.contract(self.build_plan, read(self.m.ACQUIRED), X, S,
                           before.read_bytes(), (X / 'Cargo.toml').read_bytes(), read(controls))
        records = self.build_plan['ancestor_manifests']
        require(all(name in self.freeze['files'] for name, row in records.items() if row is not None),
                'current ancestor manifest omitted from B3 freeze')
        workspace.guard_manifests(records, self.m.stamp, owned.sha, full)

    def predecessor(self):
        def frozen(path):
            path = Path(path)
            require(str(path) in self.freeze['files'], 'unfrozen actual predecessor input: ' + str(path))
            require(comp.check_file(dict(path=str(path), **self.freeze['files'][str(path)]))
                    == dict(path=str(path), **self.freeze['files'][str(path)]), 'predecessor input changed')
            return path
        for path in [self.build / 'receipt.json', self.build / 'compiled.json', self.build_source / 'plan.json', self.build_source / 'inputs.json',
                     self.build / 'stage1-native-loader.json', self.build / 'stage1-final-loader-state.json', self.build / 'stage1-inventory.json']:
            frozen(path)
        shim = S / 'build/bootstrap/debug/rustc'
        require(self.plan['producer']['bootstrap_shim']['path'] == str(shim), 'bootstrap shim role differs')
        frozen(shim)
        require(comp.check_file(self.plan['producer']['bootstrap_shim']) == self.plan['producer']['bootstrap_shim'],
                'actual bootstrap shim bytes/identity differ')
        for path in [self.original_source/'plan.json', self.original_source/'inputs.json',
                     self.previous_source/'test_source.py']:
            frozen(path)
        spec = importlib.util.spec_from_file_location('b3_actual_continuation_tests', self.previous_source/'test_source.py')
        tests_module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = tests_module
        spec.loader.exec_module(tests_module)
        actual = history.validate(owner=X, source=S, evidence=self.build, source_directory=self.build_source,
                                  frozen=frozen, sha=owned.sha, derive_tests=tests_module.derive)
        terminal, compiled, build_plan = actual['terminal'], actual['compiled'], actual['original_plan']
        continued = actual['plan']
        require(build_plan == self.build_plan and continued == self.continuation_plan,
                'actual continued compiler policy changed')
        audit_path = frozen(self.plan['actual_build']['audit']['path'])
        audit = read(audit_path)
        require(owned.sha(audit_path) == self.plan['actual_build']['audit']['sha256']
                and audit['status'] == 'verified' and audit['receipt_sha256'] == owned.sha(self.build/'receipt.json'),
                'actual independent compiler continuation audit required')
        require(actual['unavailable_contemporaneous_cwd_children'] == self.plan['actual_build']['unavailable_contemporaneous_cwd_children'],
                'current plan omitted actual fast-probe cwd limitations')
        workspace.historical_controls(build_plan, X, self.original_source, frozen, owned.sha)
        prior = X / '.work/hir-options-hash-compiler-build-01'
        old_source = X / 'experiments/hir-options-hash/compiler-build-01'
        frozen(prior / 'receipt.json'); frozen(old_source / 'inputs.json')
        failure = read(prior / 'receipt.json')
        require(owned.sha(prior / 'receipt.json') == build_plan['prior_build']['receipt_sha256']
                and owned.sha(old_source / 'inputs.json') == build_plan['prior_build']['inputs_sha256']
                and failure['status'] == 'failed' and failure['compiler_stages_completed'] == 0
                and len(failure['commands']) == 3, 'retained pre-compilation workspace failure differs')
        require(terminal['candidate_revision'] == compiled['candidate_revision'] == build_plan['candidate_revision'] == REVISION
                and terminal['source_identity'] == compiled['source_identity'] == build_plan['source_identity'],
                'candidate source identity differs')
        require(compiled['native_loader_sha256'] == owned.sha(self.build / 'stage1-native-loader.json'),
                'actual correctness/loader predecessor binding differs')
        closure = read(self.build / 'stage1-inventory.json')['closure']
        final_loader = read(self.build / 'stage1-final-loader-state.json')
        require(self.m.loaders.library_state(closure['identity']) == final_loader['state'],
                'actual final E2 loader state differs')
        for library in closure['identity']['libraries']:
            require(owned.sha(library['resolved']) == library['sha256'], 'actual E2 loader bytes differ')
        require(build_plan['metadata_plan'] == self.plan['metadata_plan'], 'source/SDK provider policy differs')
        streams = actual['streams']
        native = build_plan['stages'][2]
        require(native['argv'] == ['./x', 'build', '--stage', '1', 'compiler/rustc', 'library', '--jobs', '2', '-vv'],
                'native build producer stage differs')
        # Revalidate all final E2/provider outputs at their saved exact stamps.
        names = set()
        for parent, dirs, files in os.walk(E, followlinks=False):
            for name in dirs + files:
                path = Path(parent) / name
                if path.is_symlink() or path.is_file():
                    names.add(str(path.relative_to(E)))
                else:
                    require(path.is_dir(), 'E2 contains special output')
        require(names == set(compiled['stage1']), 'complete E2 membership changed')
        for name, row in compiled['stage1'].items():
            path = E / name
            if row['kind'] == 'file':
                require(self.m.file(path) == {k: row[k] for k in ['sha256', 'stamp']}, 'E2 output changed')
            else:
                require(path.is_symlink() and os.readlink(path) == row['target']
                        and str(path.resolve(strict=True)) == row['resolved'] and self.m.stamp(path) == row['stamp'],
                        'E2 source route changed')
        for name, row in compiled['providers'].items():
            path = Path(name)
            require(self.m.stamp(path) == row['stamp'], 'actual extracted provider identity changed')
            if 'sha256' in row:
                require(owned.sha(path) == row['sha256'], 'actual extracted provider bytes changed')
            else:
                require(path.is_symlink() and os.readlink(path) == row['target'], 'provider link changed')
        # rustc.rs uses a separate compiler-build std sysroot; do not confuse
        # it with either the downloaded D2 sysroot or E2 application libraries.
        build_sysroot = S / 'build' / H / 'stage0-sysroot'
        expected_sysroot = self.plan['producer']['build_sysroot']
        require(expected_sysroot['root'] == str(build_sysroot), 'bootstrap compiler-build sysroot differs')
        names = set()
        for parent, dirs, files in os.walk(build_sysroot, followlinks=False):
            for name in dirs + files:
                path = Path(parent) / name
                if path.is_symlink() or path.is_file():
                    names.add(str(path.relative_to(build_sysroot)))
                else:
                    require(path.is_dir(), 'compiler-build sysroot has a special file')
        require(names == set(expected_sysroot['files']), 'complete compiler-build sysroot membership differs')
        for name, row in expected_sysroot['files'].items():
            path = build_sysroot / name
            if row['kind'] == 'file':
                frozen(path)
                require(self.m.file(path) == {k: row[k] for k in ['sha256', 'stamp']}, 'compiler-build std input differs')
            else:
                require(row['kind'] == 'link' and path.is_symlink() and os.readlink(path) == row['target']
                        and str(path.resolve(strict=True)) == row['resolved'] and self.m.stamp(path) == row['stamp']
                        and Path(row['resolved']).is_relative_to(S), 'compiler-build source route differs')
        # Test Cargo searches exactly D2/lib, admitted CI LLVM/lib and the
        # build-std lib directory. Freeze every direct search entry, and require
        # file/link membership and bytes to come from the qualified providers or
        # complete build-std inventory above. No path-only loader admission.
        loader_dirs = self.plan['producer']['loader_directories']
        require([row['path'] for row in loader_dirs] == producer.test_loader_paths(S),
                'test Cargo loader search order differs')
        qualified = dict(compiled['providers'])
        qualified.update({str(build_sysroot / name): row for name, row in expected_sysroot['files'].items()})
        for directory in loader_dirs:
            root = Path(directory['path'])
            require(root.resolve(strict=True) == root and root.is_dir(), 'loader search directory aliases another path')
            entries = {entry.name: entry for entry in root.iterdir()}
            require(set(entries) == set(directory['entries']), 'loader search directory membership differs')
            for name, path in entries.items():
                row = directory['entries'][name]
                require(self.m.stamp(path) == row['stamp'], 'loader directory entry identity differs')
                if row['kind'] == 'directory':
                    require(path.is_dir() and not path.is_symlink(), 'ordinary loader subdirectory required')
                    continue
                require(str(path) in qualified, 'loader file outside qualified provider/build-std catalogs')
                prior = qualified[str(path)]
                require(row['stamp'] == prior['stamp'], 'loader file was not the qualified provider')
                if row['kind'] == 'file':
                    frozen(path)
                    require(row['sha256'] == prior['sha256'] == owned.sha(path), 'loader provider bytes differ')
                else:
                    require(row['kind'] == 'link' and path.is_symlink()
                            and row['target'] == prior['target'] == os.readlink(path)
                            and row['resolved'] == str(path.resolve(strict=True)), 'loader provider link differs')
                    resolved = frozen(row['resolved'])
                    require(resolved.is_relative_to(S) and resolved.is_file()
                            and self.m.file(resolved) == row['resolved_file'], 'resolved loader provider bytes differ')
        require(self.plan['producer']['compiler_environment'] == build_plan['tests']['assertions']['build_compiler_std']['compiler_commit_environment'],
                'producer compiler commit environment differs')
        # Bootstrap source/route policy remains an explicit full-byte closure.
        bindings = read(HERE / 'source-bindings.json')['timing_sources']
        for name, row in bindings.items():
            path = S / name; frozen(path)
            require(owned.sha(path) == row['sha256'] and path.stat().st_size == row['size'],
                    'source-bound timing/emitting route changed: ' + name)
        frozen(HERE / 'source-bindings.json')
        config_path = frozen(S / 'bootstrap.toml')
        return producer.validate(self.plan['producer'], self.plan['composition'], streams, REVISION,
                                 tomllib.loads(config_path.read_text()))

    def command(self):
        self.guard(); self.budget()
        index = len(self.record['commands'])
        row = self.plan['children'][index]
        executor = Path(row['argv'][0]).resolve(strict=True)
        if executor == B3 / TOOL:
            expected = self.installed[TOOL]['sha256']
        else:
            expected = self.freeze['files'][str(executor)]['sha256']
        require(owned.sha(executor) == expected, 'child executor differs')
        out = WORK / 'commands' / f'{index:03}'
        try:
            result = bounded.run(row['argv'], cwd=S, environment=row['environment'], output=out, canonical_fd=self.lockfd, prior_evidence=self.prior_evidence)
        finally:
            if (out / 'receipt.json').exists():
                child = read(out / 'receipt.json')
                self.record['commands'].append(dict(path=str(out / 'receipt.json'), sha256=owned.sha(out / 'receipt.json'),
                    pid=child.get('pid'), command=row['argv']))
                self.save()
        require(owned.sha(executor) == expected, 'child executor changed')
        self.guard(); self.budget()
        return (out / 'stdout').read_bytes(), (out / 'stderr').read_bytes(), result

    def execute(self):
        try:
            with owned.workload_lock(owned.CANONICAL_LOCK, 600) as fd:
                self.lockfd = fd
                self.record.update(status='running', admitted_at=time.time(), free_bytes_before=owned.disk(OWNER, 24)); self.save()
                self.guard(True); initial = self.budget(force=True)
                # Reserve ordinary block rounding for every copied B3 member.
                # This is separate from the actual sampled allocation guard.
                planned_blocks = sum(((row['size'] + 4095) // 4096) * 4096
                                     for row in self.plan['composition']['files'].values())
                require(initial['namespace_allocated_bytes'] + planned_blocks + 16 * 2**20 <= 14 * 2**30,
                        'candidate namespace cannot admit complete B3 copy plus directory allowance')
                proof = self.predecessor()
                require(not B3.exists() and not B3.is_symlink() and B3.parent.resolve(strict=True) == B3.parent,
                        'fresh ordinary B3 destination required after admission')
                # Preserve exact source/proof inputs, never entire source/provider payloads.
                snapshots = WORK / 'source-snapshots'; snapshots.mkdir()
                manifest = {}
                for name in self.freeze['snapshot_inputs'] + [str(HERE / 'inputs.json')]:
                    expected = self.inputs_sha256 if name == str(HERE / 'inputs.json') else self.freeze['files'][name]['sha256']
                    path = Path(name)
                    require(path.stat().st_size <= 64 * 2**20, 'bounded source/proof snapshot required')
                    copy = snapshots / expected
                    if not copy.exists():
                        with copy.open('xb') as stream:
                            comp.check_file(dict(path=name, sha256=expected), stream, self.budget)
                            stream.flush(); os.fsync(stream.fileno())
                    require(owned.sha(copy) == expected, 'snapshot readback differs')
                    manifest[name] = dict(path=str(copy), sha256=expected)
                owned.write(WORK / 'source-snapshots.json', manifest)
                # Prefix source/identity/provider probes execute before any B3 copy.
                for index in range(7):
                    raw, err, _ = self.command()
                    require(not err, 'unexpected source/compiler/provider diagnostics')
                    expected = [REVISION + '\n', '', None, str(D) + '\n',
                                self.plan['runtime_version'], str(E) + '\n', self.plan['otool_query_output']][index]
                    if index == 2:
                        self.record['build_version'] = providers.beta_version(raw, (S/'src/stage0').read_text(), H)
                        self.save()
                    else:
                        require(raw.decode() == expected, 'actual source/compiler/provider output differs')
                assembled = comp.assemble(self.plan['composition'], expected_plan_sha256=self.plan['composition_sha256'],
                    destination=B3, evidence=ASSEMBLY, capacity_guard=self.budget)
                self.installed = comp.output_inventory(B3)
                self.record.update(assemblies=1, assembly=assembled, producer_proof=proof); self.save()
                declarations_proof = {}
                for relative in [TOOL, COPY['destination']]:
                    raw_libraries, err, _ = self.command(); require(not err, 'otool -L diagnostics')
                    raw_commands, err, _ = self.command(); require(not err, 'otool -l diagnostics')
                    parsed = declarations(raw_commands)
                    require({k: parsed[k] for k in ['rpaths', 'loads', 'identities']} == self.plan['auxiliary_declarations'][relative],
                            'new auxiliary static loader declarations differ')
                    tokens = [line.strip().split(' (compatibility version ', 1)[0] for line in raw_libraries.decode().splitlines() if line.startswith('\t')]
                    actual_tokens, actual_rpaths = self.m.macho(B3 / relative)
                    require(tokens == actual_tokens and parsed['rpaths'] == actual_rpaths, 'actual -L/-l versus Mach-O bytes differ')
                    declarations_proof[relative] = parsed | dict(libraries_sha256=comp.digest(raw_libraries))
                raw, err, result = self.command()
                self.record['objcopy_version'] = providers.objcopy_version(raw, self.record['build_version']['fields'])
                self.save()
                version_load = dyld(err, result['pid'])
                DEBUG.mkdir()
                comp.write_new(DEBUG / 'debug.rs', STRIP_SOURCE, self.budget)
                raw, err, _ = self.command(); require(not raw and not err, 'debug compilation diagnostics')
                self.record['debug_object_compilations'] = 1; self.save()
                before = comp.check_file(dict(path=str(DEBUG / 'before.o'), sha256=owned.sha(DEBUG / 'before.o')))
                source = comp.check_file(dict(path=str(DEBUG / 'debug.rs'), sha256=comp.digest(STRIP_SOURCE)))
                require(before['size'] <= 16 * 2**20, 'bounded debug object required')
                raw, err, _ = self.command(); require(not err and b'__debug_info' in raw, 'real debug declaration absent')
                require(not (DEBUG / 'after.o').exists(), 'fresh stripped output required')
                raw, err, result = self.command(); require(not raw, 'strip stdout is unexpected')
                strip_load = dyld(err, result['pid'])
                raw, err, _ = self.command(); require(not err and b'__debug_' not in raw, 'debug declarations remain')
                after = comp.check_file(dict(path=str(DEBUG / 'after.o'), sha256=owned.sha(DEBUG / 'after.o')))
                require(after['size'] <= 16 * 2**20 and comp.check_file(before) == before
                        and comp.check_file(source) == source, 'strip mutated input or exceeded object bound')
                strip = check_strip((DEBUG / 'before.o').read_bytes(), (DEBUG / 'after.o').read_bytes())
                owned.write(WORK / 'strip-proof.json', dict(**strip, source=source, before=before, after=after,
                    original_source_and_object_unchanged=True, version_loader=version_load, strip_loader=strip_load,
                    declarations=declarations_proof, object_executed=False))
                for expected in [self.plan['otool_query_output'], REVISION + '\n', '']:
                    raw, err, _ = self.command(); require(not err and raw.decode() == expected, 'final source/provider probe differs')
                self.guard(True); self.predecessor(); self.budget(force=True)
                require(len(self.record['commands']) == len(self.plan['children']) == 19, 'exact 19-child history required')
                self.record.update(status='passed', assembly_and_auxiliary_strip_qualified=True,
                    strip_proof_sha256=owned.sha(WORK / 'strip-proof.json'), source_snapshots_sha256=owned.sha(WORK / 'source-snapshots.json'),
                    free_bytes_after=owned.disk(OWNER, 9))
        except BaseException as error:
            self.record.update(status='failed', error=repr(error)); raise
        finally:
            self.record['finished_at'] = time.time(); self.save()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs-sha256', required=True)
    Stage(parser.parse_args().inputs_sha256).execute()
