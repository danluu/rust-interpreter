#!/usr/bin/env python3
"""Admit a current D/B2/R exporter recipe without compiling or publishing tools."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time

OWNER = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
HERE = OWNER / 'experiments/runtime-exporter'
WORK = OWNER / '.work/runtime-exporter-metadata-01'
TARGET = OWNER / '.work/runtime-exporter-target-01'
BETA = Path('/Users/danluu/dev/rust-interp-beta-auxiliary-readmission-20260918')
BHERE = BETA / 'experiments/beta-auxiliary-readmission'
BWORK = BETA / '.work/beta-auxiliary-sysroot-01'
B2 = BWORK / 'build-sysroot'
ROWNER = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
RKEY = 'eca3d1317ba4c852d64de435aa0f0e5d87ae63bd4eb96cfafacc7b0a85841d03'
R = ROWNER / '.work/runtime-compilers' / RKEY / 'sysroot'
OLD = Path('/Users/danluu/dev/rust-interp-hir-native-controls-evidence-20260913')
OLDWORK = OLD / '.work/exporter-split-role-compatibility-02'
PUBLIC = Path('/Users/danluu/.rustup/toolchains/nightly-2026-09-08-aarch64-apple-darwin')
HOST = 'aarch64-apple-darwin'
CHECKPOINT = '185efda9403389fcb408100e5765306179be2cbe'
sys.path[:0] = [str(OWNER / 'scripts'), str(OWNER / 'experiments/stable-cgu')]
import owned_stage as owned
import runtime_compiler
import runtime_tools
import custom_cargo_libraries as loaders
from custom_compiler import tree_stamps


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


readmit = load('exporter_b2_readmit', BHERE / 'readmit.py')
require, sha, read, identity = readmit.require, readmit.sha, readmit.read, readmit.identity


def ordinary_files(root):
    root = Path(root)
    require(root.resolve(strict=True) == root and root.is_dir(), 'ordinary directory required')
    result = []
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink(), 'unexpected indirect input: ' + str(path))
        if path.is_dir():
            continue
        require(path.is_file() and path.resolve(strict=True) == path, 'ordinary input required')
        result.append(path)
    return result


def configuration():
    directories = {Path('/Users/danluu/.cargo'), *[p / '.cargo' for p in [OWNER, *OWNER.parents]]}
    paths = sorted(p / name for p in directories for name in ('config', 'config.toml'))
    require(not any(p.is_symlink() for path in paths for p in path.parents), 'indirect Cargo config search')
    return {str(p): p.exists() or p.is_symlink() for p in paths}


def file_record(path, expected=None):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.resolve(strict=True) == path, 'ordinary file required')
    before = identity(path)
    value = sha(path)
    require(identity(path) == before and (expected is None or value == expected), 'file bytes/identity changed')
    return dict(path=str(path), sha256=value, identity=before)


class Stage:
    def __init__(self, args):
        self.args = args
        require(sha(HERE / 'inputs.json') == args.inputs_sha256, 'metadata freeze differs')
        self.frozen = read(HERE / 'inputs.json')
        require(sha(HERE / 'plan.json') == self.frozen['plan_sha256'], 'metadata plan differs')
        self.data = read(HERE / 'plan.json')
        self.plan = read(BHERE / 'plan.json')
        self.current = read(BETA / '.work/beta-auxiliary-readmission-01/current-inputs.json')
        self.previous = load('exporter_b2_previous', readmit.BASE / '.work/beta-auxiliary-metadata-source-01/check.py')
        self.stock = load('exporter_stock_proofs', self.previous.STOCK_CODE)
        self.comp = load('exporter_compositor', self.previous.COMPOSITOR)
        self.stage2 = load('exporter_native_guard', self.stock.STAGE2 / 'experiments/hir-stage2-package/check.py')
        self.runtime = runtime_compiler.load_runtime_compiler(ROWNER, RKEY)
        self.environment = dict(os.environ)
        expected = self.frozen['launch_environment']
        extra = set(self.environment) - set(expected)
        require(all(self.environment.get(k) == v for k, v in expected.items()) and extra <= {'__CF_USER_TEXT_ENCODING'},
                'unexpected metadata environment')
        if extra:
            cf = self.environment['__CF_USER_TEXT_ENCODING'].split(':')
            require(len(cf) == 3 and all(re.fullmatch(r'(?:0[xX][0-9a-fA-F]{1,8}|[0-9]{1,10})', v) for v in cf)
                    and int(cf[0], 16 if cf[0].lower().startswith('0x') else 10) == os.getuid() == 501,
                    'unexpected Darwin context')
        require(not WORK.exists() and not TARGET.exists(), 'fresh metadata and future target required')
        WORK.mkdir(); (WORK / 'tmp').mkdir()
        self.record = dict(schema_version=1, policy='runtime-exporter-metadata-v1', status='waiting',
            owner=str(OWNER), runtime_owner=str(ROWNER), runtime_key=RKEY, source_checkpoint=CHECKPOINT,
            pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(), commands=[],
            inputs_sha256=args.inputs_sha256, plan_sha256=self.frozen['plan_sha256'],
            compiler_builds=0, exporter_builds=0, guest_execution=False, publication=False, benchmark=False,
            environment=self.environment, capacity=dict(entry_gib=16, stop_gib=9, floor_gib=8))
        self.save()

    def save(self):
        owned.write(WORK / 'receipt.json', self.record)

    def sources(self):
        require(sha(HERE / 'inputs.json') == self.args.inputs_sha256
                and loaders.platform_identity() == self.data['platform'] and dict(os.environ) == self.environment,
                'source/platform/environment changed')
        require(str(Path(sys.executable).resolve()) == self.frozen['python']['resolved']
                and sha(sys.executable) == self.frozen['python']['sha256'], 'Python changed')
        for path, expected in self.frozen['files'].items():
            require(file_record(path)['sha256'] == expected, 'frozen source/proof changed: ' + path)
        for module in list(sys.modules.values()):
            path = getattr(module, '__file__', None)
            if path and path.startswith('/Users/danluu/dev/rust-interp'):
                require(str(Path(path).resolve()) in self.frozen['files'], 'unfrozen local import: ' + path)
        require({str(p) for p in ordinary_files(OWNER / 'crates')} == set(self.data['crate_files']),
                'crate source membership changed')
        require(configuration() == self.data['configuration'] and not any(configuration().values()), 'Cargo config changed')
        require(not TARGET.exists(), 'metadata produced a future build target')

    def barrier(self, full=False):
        readmit.Stage.current_barrier(self, contents=full)
        self.runtime.revalidate(ROWNER)
        require(tree_stamps(R) == self.data['runtime_stamps'], 'installed R membership/stamps changed')
        for group in ('records', 'b2_files', 'registry_files'):
            for path, row in self.data[group].items():
                require(identity(path) == row['identity'], group + ' input identity changed: ' + path)
                if full:
                    require(file_record(path) == row, group + ' complete bytes changed: ' + path)
        require({str(p) for p in ordinary_files(B2)} == set(self.data['b2_files']), 'B2 membership changed')
        for package in self.data['registry_packages']:
            base = Path(package['manifest_path']).parent
            require({str(p) for p in ordinary_files(base)} == set(package['source_files']), 'registry membership changed')
        for path, expected in self.data['routes'].items():
            require(str(Path(path).resolve(strict=True)) == expected, 'SDK/executor route changed')
        if full:
            for name, expected in self.runtime.identity['files'].items():
                require(sha(R / name) == expected, 'installed R bytes changed: ' + name)
            self.runtime.revalidate(ROWNER)

    def command(self, argv, *, cwd=None, env=None):
        self.sources(); self.barrier(); owned.disk(OWNER, 9)
        wanted = self.data['children'][len(self.record['commands'])]
        cwd, env = str(cwd or OWNER), env or self.data['environment']
        require(argv == wanted['argv'] and cwd == wanted['cwd'] and env == wanted['environment'], 'unreviewed child')
        executor = '/usr/bin/git' if argv[0] == 'git' else str(Path(argv[0]).resolve(strict=True))
        require(sha(executor) == self.data['records'][executor]['sha256'], 'executor bytes changed')
        out = WORK / 'commands' / f'{len(self.record["commands"]):03d}'
        try:
            result = owned.run(argv, cwd=cwd, env=env, out=out, capacity_root=OWNER)
        finally:
            if (out / 'receipt.json').exists():
                result = read(out / 'receipt.json')
                self.record['commands'].append(dict(path=str(out / 'receipt.json'), sha256=sha(out / 'receipt.json'),
                    command=result['command'], pid=result.get('pid'), returncode=result.get('returncode')))
                self.save()
        self.barrier(); self.sources()
        return dict(receipt=result, path=str(out / 'receipt.json'),
                    stdout=(out / 'stdout').read_bytes(), stderr=(out / 'stderr').read_bytes())

    def checkout(self):
        for child in self.data['checkout_children']:
            result = self.command(child['argv'])
            require(not result['stderr'] and hashlib.sha256(result['stdout']).hexdigest() == child['stdout_sha256'],
                    'integrated source checkpoint changed')

    def closure(self, path):
        def inspect(argv, *, text):
            require(text is True, 'unexpected loader inspection')
            result = self.command(argv)
            require(not result['stderr'], 'loader diagnostics')
            return result['stdout'].decode()
        closure, state = loaders.library_closure(path, HOST, inspect=inspect)
        for item in closure['libraries']:
            require(self.data['records'][item['resolved']]['sha256'] == item['sha256'], 'unadmitted library')
        return dict(identity=closure, state=state)

    def role_probe(self, binding):
        path = binding['executable']['path']
        closure = self.closure(Path(path))
        result = self.command([path, '-vV'], env=self.data['environment'] | {'DYLD_PRINT_LIBRARIES': '1'})
        require(result['stdout'].decode() == binding['verbose_version'], 'actual compiler role version differs')
        allowed = {r['resolved'] for r in closure['identity']['libraries']} | {path}
        driver = next(p for p in allowed if '/librustc_driver-' in p)
        loaded = self.stock.parse_dyld(result['stderr'].decode(), result['receipt']['pid'], allowed, driver)
        root = self.command([path, '--print', 'sysroot'])
        require(not root['stderr'] and root['stdout'].decode() == binding['default_sysroot'] + '\n', 'actual role sysroot differs')
        return dict(closure=closure, loaded=loaded, version_receipt=result['path'], sysroot_receipt=root['path'])

    def dependencies(self, metadata):
        prior = read(OLDWORK / 'plan.json')['dependencies']['packages']
        expected = {(p['name'], p['version'], p['source']): p for p in prior}
        packages = metadata['packages']
        require(len(packages) == len(expected) == 30 and metadata['workspace_root'] == str(OWNER), 'resolved workspace differs')
        features = {r['id']: r['features'] for r in metadata['resolve']['nodes']}
        for package in packages:
            old = expected[(package['name'], package['version'], package['source'])]
            require(features[package['id']] == old['features'], 'dependency features changed')
            path = Path(package['manifest_path'])
            if package['source']:
                require(str(path) == old['manifest_path'], 'registry source changed')
            else:
                require(path == OWNER / Path(old['manifest_path']).relative_to(OLDWORK / 'source'), 'workspace source changed')
            for target in package['targets']:
                source = str(Path(target['src_path']).resolve(strict=True))
                require(source in self.data['registry_files'] or source in self.data['crate_files'], 'unfrozen Cargo target source')
        require(set(features) == {p['id'] for p in packages}, 'dependency resolve membership differs')
        return dict(packages=packages, resolve=metadata['resolve'], lock_sha256=sha(OWNER / 'Cargo.lock'))

    def run(self):
        self.sources(); self.barrier(full=True)
        sources = WORK / 'source-snapshots'; sources.mkdir()
        snapshots = {}
        for path, expected in self.frozen['files'].items():
            target = sources / expected
            if not target.exists():
                self.comp.write_new(target, Path(path).read_bytes(), lambda: owned.disk(OWNER, 9))
            require(sha(target) == expected, 'source snapshot readback differs')
            snapshots[path] = dict(path=str(target), sha256=expected)
        owned.write(WORK / 'source-snapshots.json', snapshots)
        self.checkout(); readmit.Stage.source_guard(self)
        for key, argv in self.plan['sdk_queries']:
            result = self.command(argv)
            require(not result['stderr'] and result['stdout'].decode() == self.plan['sdk_outputs'][key], 'SDK selection differs')
        binding = self.data['binding']
        runtime_tools.runtime_binding(self.runtime, binding)
        roles = {name: self.role_probe(binding[name]) for name in ('build', 'runtime')}
        closures = {name: self.closure(Path(path)) for name, path in self.data['support_executables'].items()}
        cargo = self.command([str(PUBLIC / 'bin/cargo'), '-Vv'])
        cargo_version = cargo['stdout'].decode()
        historical = self.data['historical_cargo_version']
        require(not cargo['stderr'] and len([s for s in cargo_version.splitlines() if s.startswith('os: ')]) == 1
                and [s for s in cargo_version.splitlines() if not s.startswith('os: ')]
                == [s for s in historical.splitlines() if not s.startswith('os: ')],
                'Cargo identity changed beyond its explicit current OS reporting field')
        owned.write(WORK / 'compiler-roles.json', binding)
        result = self.command(self.data['cargo_metadata'], env=self.data['build_environment'])
        require(not result['stderr'], 'Cargo metadata diagnostics')
        self.comp.write_new(WORK / 'cargo-metadata.json', result['stdout'], lambda: owned.disk(OWNER, 9))
        dependencies = self.dependencies(json.loads(result['stdout']))
        readmit.Stage.source_guard(self); self.checkout()
        selected = self.command(self.plan['sdk_queries'][-1][1])
        require(not selected['stderr'] and selected['stdout'].decode() == self.plan['sdk_outputs']['otool'], 'SDK route changed afterward')
        self.barrier(full=True); self.sources()
        require(len(self.record['commands']) == len(self.data['children']), 'metadata command count differs')
        result = dict(self.data, status='metadata-passed-build-unexecuted', actual_roles=roles,
            actual_support_closures=closures, dependencies=dependencies,
            actual_cargo_version=cargo_version, cargo_version_receipt=cargo['path'],
            compiler_roles_path=str(WORK / 'compiler-roles.json'), compiler_roles_sha256=sha(WORK / 'compiler-roles.json'),
            metadata_receipt=str(WORK / 'receipt.json'), source_snapshots_sha256=sha(WORK / 'source-snapshots.json'))
        owned.write(WORK / 'planned.json', result)
        self.record.update(status='passed', finished_at=time.time(), current_D_B2_R_and_source_guards_passed=True,
            registry_packages=26, workspace_packages=4, installed_R_files=len(self.runtime.identity['files']),
            source_snapshots=len(snapshots), planned_sha256=sha(WORK / 'planned.json'),
            compiler_roles_sha256=sha(WORK / 'compiler-roles.json'), free_bytes_after=owned.disk(OWNER))
        self.save()

    def execute(self):
        try:
            with owned.workload_lock(owned.CANONICAL_LOCK, 600):
                self.record.update(status='running', admitted_at=time.time(), free_bytes_before=owned.disk(OWNER, 16)); self.save()
                self.run()
        except BaseException as error:
            self.record.update(status='failed', error=repr(error), finished_at=time.time(), free_bytes_after=shutil.disk_usage(OWNER).free)
            self.save()
            raise


def main():
    require(sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd() == OWNER, 'fixed Python -B/cwd required')
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--inputs-sha256', required=True)
    Stage(parser.parse_args()).execute()


if __name__ == '__main__':
    main()
