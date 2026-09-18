#!/usr/bin/env python3
"""Readmit exact E bytes after a device-identity change; keep history unchanged."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time

OWNER = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PLAN = HERE / 'plan.json'
FROZEN = HERE / 'inputs.json'
WORK = OWNER / '.work/runtime-readmission-01'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    path = Path(path)
    require(path.resolve(strict=True) == path and path.is_file() and not path.is_symlink(),
            'indirect source/proof input: ' + str(path))
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Readmission:
    def __init__(self, frozen_sha):
        self.frozen_sha = frozen_sha
        require(sha(FROZEN) == frozen_sha, 'readmission freeze differs')
        self.frozen = read(FROZEN)
        self.check_sources()
        self.plan = read(PLAN)
        require(self.plan['owner'] == str(OWNER) and self.plan['work'] == str(WORK), 'foreign readmission plan')
        require(dict(os.environ) == self.plan['environment'], 'readmission launch environment differs')
        self.owned = load('runtime_readmission_owned', OWNER / 'experiments/stable-cgu/owned_stage.py')
        sys.path.insert(0, str(OWNER / 'scripts'))
        self.q = load('runtime_readmission_source', HERE.parent / 'source_qualification.py')
        self.runtime = self.q.runtime
        self.stage2 = load('runtime_readmission_source_guard', self.plan['guard_script'])
        for module in list(sys.modules.values()):
            path = getattr(module, '__file__', None)
            if path and path.startswith('/Users/danluu/dev/rust-interp'):
                require(str(Path(path).resolve()) in self.frozen['files'], 'unfrozen local import: ' + path)
        require(not WORK.exists() and not WORK.is_symlink(), 'readmission evidence must be fresh')
        WORK.mkdir(parents=True)
        self.record = dict(schema_version=1, policy=self.q.PREFLIGHT, status='waiting', owner=str(OWNER),
            pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(), command=sys.argv,
            cwd=os.getcwd(), environment=dict(os.environ), frozen_sha256=frozen_sha,
            plan_sha256=sha(PLAN), children=[], application_qualified=False,
            installation=False, capability_added=False, benchmark=False,
            readmission_reason='Current device identity differs; historical receipts remain unchanged.')
        self.save()

    def save(self):
        self.owned.write(WORK / 'receipt.json', self.record)

    def capacity(self):
        return self.owned.disk(OWNER, 8)

    def check_sources(self):
        require(sha(FROZEN) == self.frozen_sha, 'source freeze changed')
        for path, expected in self.frozen['files'].items():
            require(sha(path) == expected, 'frozen source/proof changed: ' + path)
        python = self.frozen['python']
        require(str(Path(sys.executable).resolve()) == python['resolved']
                and sha(Path(sys.executable).resolve()) == python['sha256'], 'readmission Python changed')

    def quick_guard(self):
        self.capacity()
        self.check_sources()

    def retain_inputs(self):
        total = 0
        for path, expected in self.frozen['files'].items():
            payload = self.q.file_bytes(path, expected, self.capacity)
            total += len(payload)
            require(total <= self.plan['retained_input_bound_bytes'], 'input retention bound exceeded')
            dest = WORK / 'inputs' / path.lstrip('/')
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open('xb') as output:
                output.write(payload)
            require(dest.lstat().st_nlink == 1
                    and self.q.file_bytes(dest, expected, self.capacity) == payload, 'retained input readback differs')
        self.record['retained_input_bytes'] = total
        self.save()

    def components_guard(self, *, rehash):
        # These are the exact new snapshots. No field is ignored during this
        # operation, regardless of the historical readmission difference.
        require(len(self.current_snapshots) == len(self.candidate['components']) == 3, 'component count differs')
        for component, snapshot in zip(self.candidate['components'], self.current_snapshots):
            require(self.runtime.inspect_component(component) == snapshot, 'newly admitted component changed')
            if rehash:
                for name, row in component['files'].items():
                    self.runtime.transfer(Path(component['root']) / name, row, snapshot['files'][name], self.capacity)
                require(self.runtime.inspect_component(component) == snapshot, 'component changed during full hashing')

    def readmit_components(self):
        old = read(self.plan['evidence']['components']['path'])
        require(old['components'] == self.candidate['components'] and len(old['snapshots']) == 3,
                'historical component declaration differs')
        self.current_snapshots = []
        changes = []
        declaration = self.plan['observed_device_change']
        for index, (component, previous) in enumerate(zip(self.candidate['components'], old['snapshots'])):
            current = self.runtime.inspect_component(component)
            for kind in ('files', 'links', 'directories'):
                require(set(current[kind]) == set(previous[kind]), 'component membership differs from historical observation')
                for name, stamp in current[kind].items():
                    historical = previous[kind][name]
                    if historical != stamp:
                        changes.append(dict(component=index, kind=kind, path=name,
                                            historical=historical, current=stamp))
            self.current_snapshots.append(current)
        self.owned.write(WORK / 'historical-current-stamp-differences.json', changes)
        require(changes, 'expected an explicitly observed device-identity change')
        require(all(row['historical'][0] == declaration['historical_device']
                    and row['current'][0] == declaration['current_device']
                    and row['historical'][1:] == row['current'][1:] for row in changes),
                'a difference beyond the reviewed device identity requires separate readmission review')
        # Persist both complete observations; historical input is never rewritten.
        self.owned.write(WORK / 'components-initial.json',
            dict(components=self.candidate['components'], snapshots=self.current_snapshots))
        self.components_guard(rehash=True)
        self.record['device_readmission'] = dict(observed_device_change=declaration, changed_entries=len(changes),
            differences=dict(path=str(WORK / 'historical-current-stamp-differences.json'),
                             sha256=sha(WORK / 'historical-current-stamp-differences.json')),
            exact_current_guards=True, all_component_bytes_rehashed=True)
        self.save()

    def host_tool_guard(self):
        route = self.plan['selected_otool']
        selected, resolved = Path(route['selected']), Path(route['resolved'])
        require(selected.is_symlink() and os.readlink(selected) == route['link_text']
                and selected.resolve(strict=True) == resolved
                and self.runtime.stamp(selected.lstat()) == route['link_stamp']
                and self.runtime.stamp(resolved.lstat()) == route['resolved_stamp']
                and sha(resolved) == route['sha256'], 'selected Mach-O inspector changed')
        for path, stamp in route['parents'].items():
            require(Path(path).resolve(strict=True) == Path(path)
                    and self.runtime.stamp(Path(path).lstat()) == stamp, 'inspector parent route changed')

    def execute(self, argv, *, cwd, env, out, capacity_root, expected):
        self.quick_guard()
        index = len(self.record['children'])
        require(index < len(self.plan['children']), 'unexpected extra readmission child')
        declaration = self.plan['children'][index]
        argv, cwd, out = list(map(str, argv)), Path(cwd), Path(out)
        wanted_env = self.prior['old_plan']['environment'] if declaration['kind'] == 'git' else (
            self.plan['environment'] if declaration['kind'] == 'selection' else self.plan['compiler_environment'])
        require(argv == declaration['argv'] and str(cwd) == declaration['cwd']
                and str(out) == declaration['out'] and env == wanted_env
                and list(expected) == declaration['expected'] and capacity_root == OWNER,
                'readmission child differs from ordered argv/cwd/environment allowlist')
        executable = Path(shutil.which(argv[0], path=env['PATH']) or argv[0]).resolve(strict=True)
        tool = self.plan['executors'][declaration['kind']]
        require(str(executable) == tool['path'] and sha(executable) == tool['sha256']
                and self.runtime.stamp(executable.lstat()) == tool['stamp'], 'readmission executor changed')
        if declaration['kind'] in ('identity', 'source', 'loader'):
            self.components_guard(rehash=False)
        if declaration['kind'] in ('selection', 'loader'):
            self.host_tool_guard()
        try:
            return self.owned.run(argv, cwd=cwd, env=env, out=out, capacity_root=OWNER, expected=expected)
        finally:
            if (out / 'receipt.json').exists():
                child = read(out / 'receipt.json')
                self.record['children'].append(dict(path=str(out / 'receipt.json'),
                    sha256=sha(out / 'receipt.json'), command=child['command'], kind=declaration['kind'],
                    pid=child.get('pid'), returncode=child.get('returncode'), executable=tool))
                self.save()
            self.quick_guard()
            require(sha(executable) == tool['sha256']
                    and self.runtime.stamp(executable.lstat()) == tool['stamp'], 'executor changed during child')
            if declaration['kind'] in ('selection', 'loader'):
                self.host_tool_guard()
            if declaration['kind'] in ('identity', 'source', 'loader'):
                self.components_guard(rehash=False)

    def simple_run(self, argv, env):
        out = Path(self.plan['children'][len(self.record['children'])]['out'])
        child = self.execute(argv, cwd=OWNER, env=env, out=out, capacity_root=OWNER, expected=(0,))
        stdout = self.q.file_bytes(out / 'stdout', child['stdout_sha256'], self.capacity)
        stderr = self.q.file_bytes(out / 'stderr', child['stderr_sha256'], self.capacity)
        require(not stderr, 'metadata probe emitted stderr')
        return stdout.decode()

    def selection(self):
        output = self.simple_run(['/usr/bin/xcrun', '--find', 'otool'], self.plan['environment'])
        require(output == self.plan['selected_otool']['selected'] + '\n', 'xcrun selected another inspector')

    def source_guard(self):
        require(self.stage2.inputs() == self.plan['guard_inputs'], 'source guard import closure changed')
        def git(argv, cwd=self.stage2.SOURCE):
            out = Path(self.plan['children'][len(self.record['children'])]['out'])
            child = self.execute(argv, cwd=cwd, env=self.prior['old_plan']['environment'],
                out=out, capacity_root=OWNER, expected=(0,))
            require(not self.q.file_bytes(out / 'stderr', child['stderr_sha256'], self.capacity), 'source guard stderr')
            return dict(stdout=self.q.file_bytes(out / 'stdout', child['stdout_sha256'], self.capacity).decode(), stderr='')
        self.stage2.engine.source_guard(self.prior['source'], git, self.plan['old_plan_sha256'])
        require(self.stage2.native.artifacts() == self.prior['stage1'], 'qualified E artifact bytes or source links changed')

    def predecessors(self):
        refs = self.plan['evidence']
        for ref in refs.values():
            require(self.frozen['files'][ref['path']] == ref['sha256'], 'predecessor omitted from freeze')
        self.prior = read(refs['stage2_plan']['path'])['previous']
        self.candidate = read(refs['candidate']['path'])
        self.identity = self.runtime.identity_for(self.candidate)
        self.sysroot = Path(next(c['root'] for c in self.candidate['components'] if c['role'] == 'runtime'))
        metadata, preflight = read(refs['metadata']['path']), read(refs['source_preflight']['path'])
        require(metadata['status'] == 'inspected-pending-review'
                and metadata['source_unchanged'] and metadata['runtime_unchanged']
                and metadata['specification_sha256'] == refs['candidate']['sha256']
                and metadata['components_sha256'] == refs['components']['sha256']
                and metadata['candidate_key'] == self.runtime.digest(self.identity)
                and preflight['status'] == 'passed' and preflight['full_current_guard_passed']
                and preflight['policy'] == self.q.PREFLIGHT
                and preflight['candidate_sha256'] == self.runtime.digest(self.candidate), 'predecessor binding differs')
        for name, envelope in [('metadata', metadata), ('source_preflight', preflight)]:
            outer = read(refs[name + '_outer']['path'])
            require(outer['status'] == 'finished' and outer['returncode'] == 0
                    and outer['child_pid'] == envelope['pid'] and outer['supervisor_pid'] == envelope['parent_pid']
                    and outer['started_at'] <= envelope['admitted_at'] <= envelope['finished_at'] <= outer['finished_at'],
                    'predecessor process/time association differs')
        require(sum(r['size'] for c in self.candidate['components'] for r in c['files'].values()) == 650879912
                and [len(c['files']) for c in self.candidate['components']] == [64, 3644, 1], 'candidate footprint changed')

    def qualify(self):
        self.retain_inputs()
        self.predecessors()
        self.source_guard()
        self.readmit_components()
        self.selection()
        by_name = {str(Path(c['destination']) / n) if c['destination'] else n: Path(c['root']) / n
                   for c in self.candidate['components'] for n in c['files']}
        loader = {}
        for name in sorted(self.candidate['loader']):
            loader[name] = self.runtime.macho_commands(self.simple_run(
                ['/usr/bin/otool', '-l', str(by_name[name])], self.plan['compiler_environment']))
        require(loader == self.candidate['loader'], 'new E loader observation differs')
        version = self.simple_run([str(self.sysroot / 'bin/rustc'), '-vV'], self.plan['compiler_environment'])
        sysroot = self.simple_run([str(self.sysroot / 'bin/rustc'), '--print', 'sysroot'], self.plan['compiler_environment'])
        options = self.runtime.option_proof(self.simple_run([str(self.sysroot / 'bin/rustc'), '-Zhelp'],
                                                           self.plan['compiler_environment']))
        require(version == self.candidate['compiler'] and sysroot == str(self.sysroot) + '\n'
                and options == self.candidate['unstable_options'], 'new E identity/option observation differs')
        observation = self.q.preflight(self.candidate, owner=OWNER, work=WORK / 'source-probe',
            environment=self.plan['environment'], run=self.execute, guard=self.quick_guard)
        self.source_guard()
        self.components_guard(rehash=True)
        self.selection()
        self.components_guard(rehash=False)
        self.quick_guard()
        require(len(self.record['children']) == 28, 'expected all 28 readmission children')
        require(self.candidate == read(self.plan['evidence']['candidate']['path']), 'original candidate changed')
        self.owned.write(WORK / 'components-and-stamps.json',
                         dict(components=self.candidate['components'], snapshots=self.current_snapshots))
        # Preserve the original candidate bytes as well as its semantic identity.
        candidate_copy = WORK / 'candidate-specification.json'
        with candidate_copy.open('xb') as output:
            output.write(Path(self.plan['evidence']['candidate']['path']).read_bytes())
        require(sha(candidate_copy) == self.plan['evidence']['candidate']['sha256'], 'candidate byte copy differs')
        finished = time.time()
        metadata = dict(self.record, status='inspected-pending-review', finished_at=finished,
            source_unchanged=True, runtime_unchanged=True, candidate_key=self.runtime.digest(self.identity),
            specification_sha256=sha(candidate_copy), components_sha256=sha(WORK / 'components-and-stamps.json'),
            source_capability_published=False, std_source_paths_qualified=False,
            candidate_is_not_installation=True, original_metadata=self.plan['evidence']['metadata'],
            selected_otool=self.plan['selected_otool'])
        self.owned.write(WORK / 'metadata.json', metadata)
        for name in ('compiler', 'source_commit', 'runtime_rustc_sha256', 'files_sha256', 'source_sha256',
                     'runtime_sysroot', 'exact_source_paths_observed', 'commands', 'candidate_sha256'):
            self.record[name] = observation[name]
        self.record.update(status='passed', finished_at=time.time(), full_current_guard_passed=True,
            source_capability_published=False, free_bytes_after=self.capacity(),
            fresh_metadata=dict(path=str(WORK / 'metadata.json'), sha256=sha(WORK / 'metadata.json')),
            fresh_components=dict(path=str(WORK / 'components-and-stamps.json'), sha256=sha(WORK / 'components-and-stamps.json')))
        self.save()


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--frozen-sha', required=True)
    args = parser.parse_args()
    require(sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd() == OWNER,
            'fixed readmission owner and Python -B required')
    stage = Readmission(args.frozen_sha)
    try:
        with stage.owned.workload_lock(stage.owned.CANONICAL_LOCK, 600):
            free = stage.owned.disk(OWNER, 10)
            stage.record.update(status='running', admitted_at=time.time(), free_bytes_before=free)
            stage.save()
            stage.qualify()
    except BaseException as error:
        stage.record.update(status='failed', error=repr(error), finished_at=time.time())
        stage.save()
        raise


if __name__ == '__main__':
    main()
