"""Shared supervision for explicit runtime application correctness controls."""
import argparse
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import runtime_platform

OWNER = Path(__file__).resolve().parents[2]
R_OWNER = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
sys.path.insert(0, str(R_OWNER / 'scripts'))
from custom_compiler import file_digest, require
from runtime_compiler import load_runtime_compiler
from runtime_tools import validate_tool_runtime
from interpreter import installed_tools
from std_mir_source_paths import load as load_std, namespace_for, tree_files
from workflow_compiler import runtime_receipt, verify_flags, verify_runtime_call


def read(path):
    return json.loads(Path(path).read_bytes())


def hir_flags(mode):
    require(mode in ('off', 'on'), 'unknown HIR policy')
    enabled = 'true' if mode == 'on' else 'false'
    return ['-Zmir-opt-level=3', '-Zhir-body-cache-capture=' + enabled,
            '-Zhir-body-cache-reuse=' + enabled]


def validate_hir_flags(argv, mode):
    unstable = []
    for index, arg in enumerate(argv):
        require(not arg.startswith('@'), 'unexpected response file in compiler record')
        if arg == '-Z':
            require(index + 1 < len(argv), 'missing unstable argument')
            unstable.append('-Z' + argv[index + 1].replace('_', '-'))
        elif arg.startswith('-Z'):
            unstable.append('-Z' + arg[2:].replace('_', '-'))
    for expected in hir_flags(mode):
        name = expected.split('=')[0]
        require([arg for arg in unstable if arg.split('=')[0] == name] == [expected],
                'actual HIR compiler arguments differ: ' + name)
    require(not any(arg.split('=')[0] in ['-Zthreads', '-Zcache-proc-macros',
                '-Zproc-macro-execution-strategy', '-Zstable-mono-cgu-partitioning'] for arg in unstable),
            'mixed compiler policy in runtime correctness control')


def validate_runtime_launch(row, compiler, key, std, cache, flags):
    reports = [json.loads(line.removeprefix('rust-interp-launch: '))
               for line in row['stderr'].splitlines() if line.startswith('rust-interp-launch: ')]
    require(row['returncode'] == 0 and len(reports) == 1, 'launcher did not complete exactly once')
    report = reports[0]
    call = dict(row, launch=report)
    verify_runtime_call(call, runtime_receipt(compiler), std)
    verify_flags(call, flags, launcher=True)
    require(report['tool_key'] == key and report['toolchain_lookup'] ==
            dict(mode='cached', outcome='owned-manifest'), 'tools or standard lookup differs')
    workspace, artifact = Path(report['workspace_path']), Path(report['artifact_path'])
    require(workspace.resolve(strict=True) == workspace and workspace.is_relative_to(cache)
            and artifact.resolve(strict=True) == artifact and artifact.is_relative_to(workspace / 'target')
            and file_digest(artifact) == report['artifact_sha256'], 'selected bytecode escaped its owned cache')
    return report, artifact


class RuntimeAdmission:
    def __init__(self, name, policy):
        parser = argparse.ArgumentParser()
        parser.add_argument('--plan', type=Path, required=True)
        parser.add_argument('--freeze', type=Path, required=True)
        parser.add_argument('--freeze-sha256', required=True)
        args = parser.parse_args()
        require(Path.cwd() == OWNER and sys.dont_write_bytecode and sys.flags.optimize == 0,
                'runtime admission requires its owner and unoptimized Python -B')
        self.plan_path, self.freeze_path = args.plan, args.freeze
        require(all(path.is_absolute() and path.resolve(strict=True) == path and path.is_relative_to(OWNER)
                    for path in [args.plan, args.freeze]), 'admission plan paths must be ordinary and owned')
        require(file_digest(args.freeze) == args.freeze_sha256, 'admission freeze differs')
        self.freeze_sha = args.freeze_sha256
        self.plan, self.freeze = read(args.plan), read(args.freeze)
        require(self.plan['policy'] == policy and self.plan['owner'] == str(OWNER)
                and self.plan['runtime_owner'] == str(R_OWNER) and self.plan['name'] == name,
                'runtime admission policy or ownership differs')
        self.work = OWNER / '.work' / name
        self.environment = self.plan['child_environment']
        self.source_files = self.plan['producer_sources']
        require(dict(os.environ) == self.plan['launch_environment'], 'admission launch environment differs')
        self.guard_sources()
        path = OWNER / 'experiments/stable-cgu/owned_stage.py'
        spec = importlib.util.spec_from_file_location('runtime_application_owned', path)
        self.owned = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.owned)
        self.compiler = load_runtime_compiler(R_OWNER, self.plan['runtime_key'])
        self.tools, self.key = installed_tools(self.plan['tool_key'])
        self.standard = load_std(R_OWNER, self.plan['std_key'], self.compiler,
            namespace_for('source-paths-v2-shared', 'unused-shared-policy'), rehash=True)
        require(not self.work.exists() and not self.work.is_symlink(), 'runtime admission work must be fresh')
        self.work.mkdir(parents=True)
        self.record = dict(schema_version=1, status='waiting', owner=str(OWNER), runtime_owner=str(R_OWNER),
            policy=policy, pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(),
            plan_sha256=file_digest(self.plan_path), freeze_sha256=self.freeze_sha, children=[],
            benchmark=False, performance_qualified=False,
            platform_identity=self.plan['platform_identity'],
            platform_context=[dict(observed_at=time.time(), uname=self.observed_platform)])
        self.save()

    def arguments(self):
        return SimpleNamespace(runtime_compiler_key=self.plan['runtime_key'], tool_key=self.plan['tool_key'],
            std_mir_key=self.plan['std_key'], std_mir_policy='source-paths-v2-shared', run_id=self.plan['name'])

    def save(self):
        self.owned.write(self.work / 'supervision.json', self.record)

    def guard_sources(self):
        require(file_digest(self.freeze_path) == self.freeze_sha, 'runtime admission freeze changed')
        require(str(self.plan_path) in self.freeze['files'], 'admission plan was not frozen')
        for name, digest in self.freeze['files'].items():
            path = Path(name)
            require(path.resolve(strict=True) == path and path.is_file() and file_digest(path) == digest,
                    'runtime admission input changed: ' + name)
        require(str(Path(sys.executable).resolve()) == self.freeze['python']['resolved'] and
                file_digest(Path(sys.executable)) == self.freeze['python']['sha256'], 'admission Python differs')
        self.observed_platform = runtime_platform.validate(list(os.uname()), self.plan['platform_identity'])
        if hasattr(self, 'record'):
            self.record['platform_context'].append(dict(observed_at=time.time(), uname=self.observed_platform))
        for module in list(sys.modules.values()):
            name = getattr(module, '__file__', None)
            if name and name.startswith('/Users/danluu/dev/rust-interp'):
                require(str(Path(name).resolve()) in self.freeze['files'], 'unfrozen admission import: ' + name)
        for name, expected in self.source_files.items():
            require(self.freeze['files'].get(name) == expected, 'producer source was not frozen')
        for name, expected in self.plan['executor_routes'].items():
            path = Path(name)
            require(str(path.resolve(strict=True)) == expected['resolved'] and
                    (os.readlink(path) if path.is_symlink() else None) == expected['link_text'] and
                    file_digest(path) == expected['sha256'], 'executor route changed: ' + name)

    def guard(self):
        self.guard_sources()
        require(load_runtime_compiler(R_OWNER, self.compiler.key) == self.compiler, 'installed runtime changed')
        tools, key = installed_tools(self.key)
        require(tools == self.tools and key == self.key, 'installed tool selection changed')
        validate_tool_runtime(tools, key, self.compiler)
        require(read(tools / 'compiler.json') == self.plan['runtime_composition'], 'tool composition differs')
        require(load_std(R_OWNER, self.plan['std_key'], self.compiler,
                    namespace_for('source-paths-v2-shared', 'unused-shared-policy')) == self.standard,
                'shared source-containing standard library changed')
        for name, expected in self.plan['configuration'].items():
            path = Path(name)
            require(not path.is_symlink() and path.exists() == expected['exists'], 'configuration route changed')
            if expected['exists']:
                require(file_digest(path) == expected['sha256'], 'configuration changed: ' + name)

    def full_artifacts(self):
        require(tree_files(self.compiler.sysroot) == self.compiler.identity['files'], 'runtime bytes changed')
        require(tree_files(self.standard[0]) == self.standard[3]['sysroot_files'], 'shared standard bytes changed')
        for name, digest in read(self.tools / 'ready.json').items():
            require(file_digest(self.tools / name) == digest, 'installed tool bytes changed')

    def budget(self):
        free = self.owned.disk(OWNER, 9)
        allocated = 0
        for directory, dirs, files in os.walk(self.work, followlinks=False):
            for name in [*dirs, *files]:
                allocated += (Path(directory) / name).lstat().st_blocks * 512
        require(allocated <= self.plan['allocated_byte_limit'], 'runtime correctness work exceeded its finite allocation bound')
        return dict(free_bytes=free, allocated_bytes=allocated)

    @contextmanager
    def admitted(self):
        with self.owned.workload_lock(self.plan['canonical_lock'], 600):
            self.record.update(status='running', admitted_at=time.time(), free_bytes_before=self.owned.disk(OWNER, 16))
            self.save()
            self.guard()
            self.full_artifacts()
            total = 0
            for name, digest in self.freeze['files'].items():
                self.owned.disk(OWNER, 9)
                path = Path(name)
                require(path.stat().st_size <= 32 * 2**20, 'retained runtime correctness input exceeds file bound')
                data = path.read_bytes()
                total += len(data)
                require(total <= 96 * 2**20, 'retained runtime correctness inputs exceed bound')
                target = self.work / 'inputs' / name.lstrip('/')
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as output:
                    output.write(data)
                require(file_digest(target) == digest and target.stat().st_nlink == 1, 'retained input differs')
            self.record['retained_input_bytes'] = total
            self.save()
            yield

    def invoke(self, label, command, *, cwd, expected=0, environment=None):
        self.guard()
        self.budget()
        command, cwd = list(map(str, command)), Path(cwd)
        environment = self.environment if environment is None else environment
        index = len(self.record['children'])
        declaration = dict(label=label, command=command, cwd=str(cwd), expected_returncode=expected)
        planned = self.plan['commands'][index]
        require({key: value for key, value in planned.items() if key != 'environment'} == declaration,
                'runtime correctness command differs from reviewed recipe')
        require(environment == planned.get('environment', self.environment),
                'unexpected runtime correctness child environment')
        out = self.work / 'raw' / f'{index:03d}-{label}'
        try:
            receipt = self.owned.run(command, cwd=cwd, env=environment, out=out,
                                     capacity_root=OWNER, expected=(expected,))
        finally:
            if (out / 'receipt.json').exists():
                self.record['children'].append(dict(label=label, path=str(out), receipt=read(out / 'receipt.json')))
                self.save()
        self.guard()
        self.budget()
        require(all((out / name).stat().st_size <= 64 * 2**20 for name in ['stdout', 'stderr']),
                'runtime correctness command output exceeded bound')
        return dict(declaration, returncode=receipt['returncode'], pid=receipt['pid'],
            receipt=str(out / 'receipt.json'), stdout=(out / 'stdout').read_text(), stderr=(out / 'stderr').read_text())

    def finish(self, result):
        self.guard()
        self.full_artifacts()
        require(len(self.record['children']) == len(self.plan['commands']) == result['commands'],
                'runtime correctness command count differs')
        self.record.update(status='passed', finished_at=time.time(), commands=result['commands'],
            result=dict(path=str(self.work / 'result.json'), sha256=file_digest(self.work / 'result.json')),
            capacity=self.budget())
        self.save()

    def failed(self, error):
        self.record.update(status='failed', finished_at=time.time(), error=repr(error))
        self.save()
