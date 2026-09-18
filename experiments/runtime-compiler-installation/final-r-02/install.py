#!/usr/bin/env python3
"""Install one reviewed native runtime and qualify its ordinary source root."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import stat
import sys
import time
import tomllib

OWNER = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PLAN = HERE / 'plan.json'
SPEC = HERE / 'specification.json'
FROZEN = HERE / 'inputs.json'
WORK = OWNER / '.work/runtime-installation-r-02'
POLICY = 'native-runtime-installation-with-source-prepublication-v1'


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


class Installation:
    def __init__(self, frozen_sha):
        self.frozen_sha = frozen_sha
        require(sha(FROZEN) == frozen_sha, 'installation freeze differs')
        self.frozen = read(FROZEN)
        self.check_sources()
        self.plan, self.spec = read(PLAN), read(SPEC)
        require(self.plan['owner'] == str(OWNER) and self.plan['work'] == str(WORK)
                and self.plan['policy'] == POLICY, 'foreign installation plan')
        require(dict(os.environ) == self.plan['environment'], 'installation launch environment differs')
        self.owned = load('runtime_installation_owned', OWNER / 'experiments/stable-cgu/owned_stage.py')
        sys.path.insert(0, str(OWNER / 'scripts'))
        self.q = load('runtime_installation_source', HERE.parent / 'source_qualification.py')
        self.runtime = self.q.runtime
        self.stage2 = load('runtime_installation_source_guard', self.plan['guard_script'])
        for module in list(sys.modules.values()):
            path = getattr(module, '__file__', None)
            if path and path.startswith('/Users/danluu/dev/rust-interp'):
                require(str(Path(path).resolve()) in self.frozen['files'], 'unfrozen local import: ' + path)
        self.identity = self.runtime.identity_for(self.spec)
        self.key = self.runtime.digest(self.identity)
        self.sysroot = OWNER / '.work' / self.runtime.NAMESPACE / self.key / 'sysroot'
        require(self.key == self.plan['runtime_key'] and str(self.sysroot) == self.plan['sysroot'],
                'runtime identity or final root differs')
        require(not self.sysroot.parent.exists() and not self.sysroot.parent.is_symlink(),
                'final runtime destination must be fresh')
        require(not WORK.exists() and not WORK.is_symlink(), 'installation evidence must be fresh')
        WORK.mkdir(parents=True)
        self.record = dict(schema_version=1, policy=POLICY, status='waiting', owner=str(OWNER),
            pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(), command=sys.argv,
            cwd=os.getcwd(), environment=dict(os.environ), frozen_sha256=frozen_sha,
            plan_sha256=sha(PLAN), specification_sha256=sha(SPEC), key=self.key,
            sysroot=str(self.sysroot), children=[], application_qualified=False,
            exporter_qualified=False, std_mir_prepared=False, benchmark=False)
        self.save()

    def save(self):
        self.owned.write(WORK / 'receipt.json', self.record)

    def capacity(self):
        # This bounded copy stage preserves the existing 8 GiB running floor.
        # owned.run separately retains its unchanged 9 GiB active-child stop.
        return self.owned.disk(OWNER, 8)

    def check_sources(self):
        require(sha(FROZEN) == self.frozen_sha, 'source freeze changed')
        for path, expected in self.frozen['files'].items():
            require(sha(path) == expected, 'frozen source/proof changed: ' + path)
        python = self.frozen['python']
        require(str(Path(sys.executable).resolve()) == python['resolved']
                and sha(Path(sys.executable).resolve()) == python['sha256'], 'installation Python changed')

    def quick_guard(self):
        self.capacity()
        self.check_sources()

    def retain_inputs(self):
        total = 0
        for path, expected in self.frozen['files'].items():
            payload = self.q.file_bytes(path, expected, self.capacity)
            total += len(payload)
            require(total <= self.plan['bounds']['retained_input_bytes'], 'input retention bound exceeded')
            dest = WORK / 'inputs' / path.lstrip('/')
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open('xb') as output:
                output.write(payload)
            require(dest.lstat().st_nlink == 1
                    and self.q.file_bytes(dest, expected, self.capacity) == payload, 'retained input readback differs')
        self.record['retained_input_bytes'] = total
        self.save()

    def components_guard(self, *, rehash):
        components = self.spec['components']
        snapshots = self.components['snapshots']
        require(len(components) == len(snapshots) == 3, 'component snapshot count differs')
        for component, snapshot in zip(components, snapshots):
            require(self.runtime.inspect_component(component) == snapshot, 'admitted component changed')
            if rehash:
                for name, row in component['files'].items():
                    self.runtime.transfer(Path(component['root']) / name, row, snapshot['files'][name], self.capacity)
                require(self.runtime.inspect_component(component) == snapshot, 'component changed during hashing')

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
                    and self.runtime.stamp(Path(path).lstat()) == stamp, 'Mach-O inspector parent route changed')

    def execute(self, argv, *, cwd, env, out, capacity_root, expected):
        self.quick_guard()
        index = len(self.record['children'])
        require(index < len(self.plan['children']), 'unexpected extra installation child')
        declaration = self.plan['children'][index]
        argv, cwd, out = list(map(str, argv)), Path(cwd), Path(out)
        wanted_env = self.prior['old_plan']['environment'] if declaration['kind'] == 'git' else (
            self.plan['environment'] if declaration['kind'] == 'selection' else self.plan['compiler_environment'])
        require(argv == declaration['argv'] and str(cwd) == declaration['cwd']
                and str(out) == declaration['out'] and env == wanted_env
                and list(expected) == declaration['expected'] and capacity_root == OWNER,
                'installation child differs from ordered argv/cwd/environment allowlist')
        executable = Path(shutil.which(argv[0], path=env['PATH']) or argv[0]).resolve(strict=True)
        if declaration['kind'] in ('identity', 'source'):
            require(executable == self.sysroot / 'bin/rustc', 'final compiler route differs')
            tool = dict(path=str(executable), sha256=self.identity['files']['bin/rustc'],
                        stamp=self.runtime.stamp(executable.lstat()))
            if hasattr(self, 'compiler_stamp'):
                require(tool['stamp'] == self.compiler_stamp, 'installed compiler changed between probes')
            else:
                self.compiler_stamp = tool['stamp']
            self.components_guard(rehash=False)
        else:
            tool = self.plan['executors'][declaration['kind']]
        require(str(executable) == tool['path'] and sha(executable) == tool['sha256']
                and self.runtime.stamp(executable.lstat()) == tool['stamp'], 'child executor changed')
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

    def simple_run(self, argv, env):
        index = len(self.record['children'])
        out = Path(self.plan['children'][index]['out'])
        child = self.execute(argv, cwd=OWNER, env=env, out=out, capacity_root=OWNER, expected=(0,))
        stdout = self.q.file_bytes(out / 'stdout', child['stdout_sha256'], self.capacity)
        stderr = self.q.file_bytes(out / 'stderr', child['stderr_sha256'], self.capacity)
        require(not stderr, 'identity/loader probe emitted stderr')
        return dict(returncode=child['returncode'], stdout=stdout.decode(), stderr=stderr.decode())

    def selection(self):
        row = self.simple_run(['/usr/bin/xcrun', '--find', 'otool'], self.plan['environment'])
        require(row['stdout'] == self.plan['selected_otool']['selected'] + '\n', 'xcrun selected another inspector')

    def source_guard(self):
        require(self.stage2.inputs() == self.plan['guard_inputs'], 'source guard import closure changed')
        def git(argv, cwd=self.stage2.SOURCE):
            out = Path(self.plan['children'][len(self.record['children'])]['out'])
            child = self.execute(argv, cwd=cwd, env=self.prior['old_plan']['environment'],
                out=out, capacity_root=OWNER, expected=(0,))
            stderr = self.q.file_bytes(out / 'stderr', child['stderr_sha256'], self.capacity)
            require(not stderr, 'source guard stderr')
            return dict(stdout=self.q.file_bytes(out / 'stdout', child['stdout_sha256'], self.capacity).decode(), stderr='')
        self.stage2.engine.source_guard(self.prior['source'], git, self.plan['old_plan_sha256'])
        require(self.stage2.native.artifacts() == self.prior['stage1'], 'qualified E native artifacts changed')

    def predecessors(self):
        refs = self.plan['evidence']
        for ref in refs.values():
            require(self.frozen['files'][ref['path']] == ref['sha256'], 'predecessor omitted from freeze')
        self.prior = read(refs['stage2_plan']['path'])['previous']
        self.components = read(refs['components']['path'])
        candidate = read(refs['candidate']['path'])
        metadata, preflight = read(refs['metadata']['path']), read(refs['source_preflight']['path'])
        require(self.components['components'] == candidate['components'] == self.spec['components']
                and metadata['status'] == 'inspected-pending-review'
                and metadata['source_unchanged'] and metadata['runtime_unchanged']
                and metadata['specification_sha256'] == refs['candidate']['sha256']
                and metadata['components_sha256'] == refs['components']['sha256']
                and preflight['status'] == 'passed' and preflight['full_current_guard_passed']
                and preflight['policy'] == self.q.PREFLIGHT
                and preflight['candidate_sha256'] == self.runtime.digest(candidate), 'predecessor binding differs')
        for name, envelope in [('metadata', metadata), ('source_preflight', preflight)]:
            outer = read(refs[name + '_outer']['path'])
            require(outer['status'] == 'finished' and outer['returncode'] == 0
                    and outer['child_pid'] == envelope['pid'] and outer['supervisor_pid'] == envelope['parent_pid']
                    and outer['started_at'] <= envelope['admitted_at'] <= envelope['finished_at'] <= outer['finished_at'],
                    'predecessor process/time association differs')
        proof = read(refs['source_policy']['path'])
        expected = json.loads(json.dumps(candidate))
        expected['provenance'].update(std_source_paths=self.q.std.source_capability(self.prior['source']['revision']),
            source_preflight_sha256=refs['source_preflight']['sha256'], source_policy_proof_sha256=refs['source_policy']['sha256'])
        expected['prepublication_qualification'] = dict(policy=self.q.FINAL)
        require(self.spec == expected, 'runtime spec differs from exact reviewed candidate additions')
        require(proof['source_commit'] == self.prior['source']['revision']
                and proof['capability'] == expected['provenance']['std_source_paths'], 'source capability differs')
        config = tomllib.loads(Path(proof['bootstrap']['path']).read_text())
        require(config == tomllib.loads((OWNER / 'experiments/stable-cgu/bootstrap-production-source-paths.toml').read_text())
                and config['rust']['remap-debuginfo'] is True
                and proof['bootstrap']['sha256'] == candidate['provenance']['bootstrap_sha256'], 'remap configuration differs')
        require(self.prior['source']['files']['src/tools/cargo'] ==
                dict(kind='gitlink', object=self.q.std.CARGO_COMMIT), 'reviewed Cargo policy pin differs')
        build = read(proof['build_receipt']['path'])
        require(build['status'] == 'finished' and build['returncode'] == 0
                and proof['build_receipt']['sha256'] == candidate['provenance']['build_receipt_sha256']
                and build['stdout_sha256'] == proof['build_stdout']['sha256'], 'actual bootstrap command proof differs')
        lines = Path(proof['build_stdout']['path']).read_text().splitlines()
        for row in proof['expanded_commands']:
            line = lines[row['line'] - 1]
            require(hashlib.sha256(line.encode()).hexdigest() == row['sha256'], 'expanded bootstrap command changed')
            tokens = shlex.split(line)
            require(all(token in tokens for token in row['required_tokens']), 'bootstrap remap token missing')
        review = read(proof['cargo_policy_review']['path'])
        require(review['cargo_gitlink_commit'] == self.q.std.CARGO_COMMIT
                and review['cargo_files'] == proof['cargo_recipe_files'], 'historical Cargo recipe review differs')
        for relative, ref in proof['unchanged_remap_sources'].items():
            require(review['rust_files'][relative] == ref['sha256']
                    and self.prior['source']['files'][relative] == dict(kind='file', sha256=ref['sha256']),
                    'remap implementation differs from reviewed source')
        for ref in [proof['bootstrap'], proof['build_receipt'], proof['build_stdout'], proof['cargo_policy_review'],
                    *proof['unchanged_remap_sources'].values()]:
            require(self.frozen['files'][ref['path']] == ref['sha256'], 'source policy proof omitted from freeze')
        require(sum(r['size'] for c in self.spec['components'] for r in c['files'].values()) ==
                self.plan['bounds']['runtime_logical_bytes'] == 650879912
                and [len(c['files']) for c in self.spec['components']] == [64, 3644, 1], 'copy footprint changed')

    def install(self):
        self.retain_inputs()
        self.predecessors()
        self.source_guard()
        self.components_guard(rehash=True)
        self.selection()
        validator = self.q.final_validator(owner=OWNER, work=WORK / 'source-probe',
            expected_identity=self.identity, preflight_reference=self.plan['evidence']['source_preflight'],
            run=self.execute, guard=self.capacity)
        def before_publication(compiler, env):
            reference = validator(compiler, env)
            # All expensive whole-source/input and host-tool checks finish before
            # the installer is permitted to create its ready record.
            self.source_guard()
            self.components_guard(rehash=True)
            self.selection()
            self.quick_guard()
            require(len(self.record['children']) == 28, 'expected all 28 pre-publication children')
            self.record['full_current_guard_passed_before_publication'] = True
            self.record['source_qualification'] = reference
            self.save()
            return reference
        compiler = self.runtime.install_runtime_compiler(OWNER, self.spec, run=self.simple_run,
            guard=self.capacity, environment=self.plan['environment'], validate_before_publication=before_publication)
        require(compiler.identity == self.identity and compiler.key == self.key, 'installed runtime identity differs')
        ready = self.sysroot.parent / 'ready.json'
        qualification = read(ready)['prepublication_qualification']
        require(qualification['sha256'] == self.record['source_qualification']['sha256'], 'published source receipt differs')
        self.record.update(status='passed', finished_at=time.time(), ready=dict(path=str(ready), sha256=sha(ready)),
            source_capability_published=True, free_bytes_after=self.capacity())
        self.save()


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--frozen-sha', required=True)
    args = parser.parse_args()
    require(sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd() == OWNER,
            'fixed installation owner and Python -B required')
    stage = Installation(args.frozen_sha)
    try:
        with stage.owned.workload_lock(stage.owned.CANONICAL_LOCK, 600):
            free = stage.owned.disk(OWNER, 10)
            stage.record.update(status='running', admitted_at=time.time(), free_bytes_before=free)
            stage.save()
            stage.install()
    except BaseException as error:
        stage.record.update(status='failed', error=repr(error), finished_at=time.time())
        stage.save()
        raise


if __name__ == '__main__':
    main()
