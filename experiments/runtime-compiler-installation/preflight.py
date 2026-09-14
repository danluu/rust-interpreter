#!/usr/bin/env python3
"""Run the frozen E source observation under the existing canonical supervisor."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time

OWNER = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PLAN = HERE / 'source-preflight-plan-01.json'
FROZEN = OWNER / '.work/runtime-source-preflight-source-01/inputs.json'
WORK = OWNER / '.work/runtime-source-preflight-01'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    path = Path(path)
    require(path.resolve(strict=True) == path and path.is_file() and not path.is_symlink(),
            'nonordinary source/proof input: ' + str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Stage:
    def __init__(self, expected):
        self.expected = expected
        require(sha(FROZEN) == expected, 'preflight source freeze differs')
        self.frozen = read(FROZEN)
        self.check_sources()
        self.plan = read(PLAN)
        require(self.plan['owner'] == str(OWNER) and self.plan['work'] == str(WORK), 'foreign preflight plan')
        self.owned = load('runtime_source_owned', OWNER / 'experiments/stable-cgu/owned_stage.py')
        sys.path.insert(0, str(OWNER / 'scripts'))
        self.q = load('runtime_source_qualification', HERE / 'source_qualification.py')
        self.runtime = self.q.runtime
        self.stage2 = load('runtime_source_stage2_guard', self.plan['guard_script'])
        for module in list(sys.modules.values()):
            filename = getattr(module, '__file__', None)
            if filename and filename.startswith('/Users/danluu/dev/rust-interp'):
                require(str(Path(filename).resolve()) in self.frozen['files'], 'unfrozen local import: ' + filename)
        require(not WORK.exists() and not WORK.is_symlink(), 'preflight work must be fresh')
        WORK.mkdir(parents=True)
        self.record = dict(schema_version=1, status='waiting', owner=str(OWNER), pid=os.getpid(),
            parent_pid=os.getppid(), started_at=time.time(), policy=self.q.PREFLIGHT,
            plan_sha256=sha(PLAN), frozen_sha256=expected, children=[], compiler_commands=0,
            installation=False, capability_added=False, application_qualified=False, benchmark=False)
        self.save()

    def save(self):
        self.owned.write(WORK / 'receipt.json', self.record)

    def capacity(self):
        return self.owned.disk(OWNER, 8)

    def check_sources(self):
        require(sha(FROZEN) == self.expected, 'source freeze changed')
        for path, expected in self.frozen['files'].items():
            require(sha(path) == expected, 'frozen source/proof changed: ' + path)
        python = self.frozen['python']
        require(str(Path(sys.executable).resolve()) == python['resolved']
                and sha(Path(sys.executable).resolve()) == python['sha256'], 'preflight Python changed')

    def quick_guard(self):
        self.capacity()
        self.check_sources()

    def retain_inputs(self):
        for path, expected in self.frozen['files'].items():
            payload = self.q.file_bytes(path, expected, self.capacity)
            dest = WORK / 'inputs' / path.lstrip('/')
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open('xb') as output:
                output.write(payload)
            require(dest.lstat().st_nlink == 1
                    and self.q.file_bytes(dest, expected, self.capacity) == payload, 'input readback differs')

    def components_guard(self, *, rehash):
        for component, snapshot in zip(self.candidate['components'], self.components['snapshots']):
            require(self.runtime.inspect_component(component) == snapshot, 'admitted component identity changed')
            if rehash:
                for name, row in component['files'].items():
                    self.runtime.transfer(Path(component['root']) / name, row, snapshot['files'][name], self.capacity)
                require(self.runtime.inspect_component(component) == snapshot, 'component changed during hashing')

    def execute(self, argv, *, cwd, env, out, capacity_root, expected):
        self.quick_guard()
        argv, cwd = list(map(str, argv)), Path(cwd)
        git = any(argv == r['argv'] and str(cwd) == r['cwd'] for r in self.plan['git_commands'])
        native = argv in self.plan['compiler_commands'] and cwd == WORK / 'probe'
        require(capacity_root == OWNER and ((git and env == self.prior['old_plan']['environment']
                and expected == (0,)) or (native and env == self.plan['compiler_environment'] and expected == (1,))),
                'preflight command is outside the exact allowlist')
        tool = self.plan['git_executor'] if git else self.plan['compiler_executor']
        executable = Path(shutil.which(argv[0], path=env['PATH']) or argv[0]).resolve(strict=True)
        require(str(executable) == tool['path'] and sha(executable) == tool['sha256']
                and self.runtime.stamp(executable.lstat()) == tool['stamp'], 'preflight executor changed')
        if native:
            self.components_guard(rehash=False)
        try:
            return self.owned.run(argv, cwd=cwd, env=env, out=out, capacity_root=OWNER, expected=expected)
        finally:
            if (out / 'receipt.json').exists():
                child = read(out / 'receipt.json')
                self.record['children'].append(dict(path=str(out / 'receipt.json'),
                    sha256=sha(out / 'receipt.json'), command=child['command'], pid=child.get('pid'),
                    returncode=child.get('returncode'), executable=tool))
                self.record['compiler_commands'] += int(native)
                self.save()
            self.quick_guard()
            require(sha(executable) == tool['sha256']
                    and self.runtime.stamp(executable.lstat()) == tool['stamp'], 'executor changed during command')
            if native:
                self.components_guard(rehash=False)

    def source_guard(self):
        require(self.stage2.inputs() == self.plan['guard_inputs'], 'qualified source-guard closure changed')
        def git(argv, cwd=self.stage2.SOURCE):
            out = WORK / 'guards' / str(len(self.record['children']))
            child = self.execute(argv, cwd=cwd, env=self.prior['old_plan']['environment'],
                                 out=out, capacity_root=OWNER, expected=(0,))
            require(not (out / 'stderr').read_bytes(), 'source guard stderr')
            return dict(stdout=(out / 'stdout').read_text(), stderr='')
        self.stage2.engine.source_guard(self.prior['source'], git, self.plan['old_plan_sha256'])
        require(self.stage2.native.artifacts() == self.prior['stage1'], 'qualified E runtime differs')

    def qualify(self):
        self.retain_inputs()
        refs = self.plan['evidence']
        for ref in refs.values():
            require(self.frozen['files'][ref['path']] == ref['sha256'], 'proof omitted from frozen inputs')
        prior_meta, outer = read(refs['metadata']['path']), read(refs['metadata_outer']['path'])
        require(prior_meta['status'] == 'inspected-pending-review' and prior_meta['source_unchanged']
                and prior_meta['runtime_unchanged'] and not prior_meta['std_source_paths_qualified']
                and prior_meta['specification_sha256'] == refs['candidate']['sha256']
                and prior_meta['components_sha256'] == refs['components']['sha256']
                and outer['status'] == 'finished' and outer['returncode'] == 0
                and outer['child_pid'] == prior_meta['pid'] and outer['supervisor_pid'] == prior_meta['parent_pid']
                and outer['started_at'] <= prior_meta['admitted_at'] <= prior_meta['finished_at'] <= outer['finished_at'],
                'accepted metadata predecessor association differs')
        self.prior = read(refs['stage2_plan']['path'])['previous']
        self.candidate = read(refs['candidate']['path'])
        self.components = read(refs['components']['path'])
        require(self.components['components'] == self.candidate['components']
                and len(self.components['snapshots']) == len(self.candidate['components'])
                and self.candidate['provenance']['source_commit'] == self.prior['source']['revision'],
                'source/provider/runtime candidate differs')
        identity = self.runtime.identity_for(self.candidate)
        require(self.runtime.digest(identity) == prior_meta['candidate_key'], 'candidate identity differs')
        self.source_guard()
        self.components_guard(rehash=True)
        observation = self.q.preflight(self.candidate, owner=OWNER, work=WORK / 'probe',
            environment=self.plan['environment'], run=self.execute, guard=self.quick_guard)
        self.source_guard()
        self.components_guard(rehash=True)
        self.quick_guard()
        require(len(self.record['children']) == 12 and self.record['compiler_commands'] == 2,
                'exact ten Git guards and two compiler probes required')
        require(self.candidate == read(refs['candidate']['path']), 'candidate mutated')
        for name in ('compiler', 'source_commit', 'runtime_rustc_sha256', 'files_sha256',
                     'source_sha256', 'runtime_sysroot', 'exact_source_paths_observed', 'commands', 'candidate_sha256'):
            self.record[name] = observation[name]
        self.record.update(status='passed', finished_at=time.time(), full_current_guard_passed=True,
                           free_bytes_after=self.capacity(), source_capability_published=False)
        self.save()


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--frozen-sha', required=True)
    args = parser.parse_args()
    require(sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd() == OWNER,
            'fixed source owner and Python -B required')
    stage = Stage(args.frozen_sha)
    try:
        with stage.owned.workload_lock(stage.owned.CANONICAL_LOCK, 600):
            stage.record.update(status='running', admitted_at=time.time(), free_bytes_before=stage.capacity())
            stage.save()
            stage.qualify()
    except BaseException as error:
        stage.record.update(status='failed', error=repr(error), finished_at=time.time())
        stage.save()
        raise


if __name__ == '__main__':
    main()
