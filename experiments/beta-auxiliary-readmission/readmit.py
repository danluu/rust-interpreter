#!/usr/bin/env python3
"""Fresh B2 metadata after an explicitly recorded OS/filesystem transition."""
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
from types import SimpleNamespace

OWNER = Path('/Users/danluu/dev/rust-interp-beta-auxiliary-readmission-20260918')
HERE = OWNER / 'experiments/beta-auxiliary-readmission'
WORK = OWNER / '.work/beta-auxiliary-readmission-01'
OUTPUT = OWNER / '.work/beta-auxiliary-sysroot-01'
B2 = OUTPUT / 'build-sysroot'
BASE = Path('/Users/danluu/dev/rust-interp-beta-auxiliary-sysroot-20260913')
EMBED = Path('/Users/danluu/dev/rust-interp-embedded-frontend-bootstrap-20260913')
POLICY = 'beta-auxiliary-current-platform-metadata-v1'
HOST = 'aarch64-apple-darwin'
COPY = dict(source_destination='lib/libLLVM.dylib', destination=f'lib/rustlib/{HOST}/lib/libLLVM.dylib')
TOOL = f'lib/rustlib/{HOST}/bin/rust-objcopy'
LLVM_SHA = '0d514b73a257a599a433ea7076945639c326cb8483cb06d0dae91d7ceebd842a'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def identity(path):
    info = Path(path).lstat()
    return {key: getattr(info, 'st_' + key) for key in
            ('dev', 'ino', 'size', 'mode', 'nlink', 'mtime_ns', 'ctime_ns')}


def platform():
    value = os.uname()
    return dict(system=value.sysname, release=value.release, version=value.version, machine=value.machine)


def admit_identity(historical, current, transition):
    require(historical['dev'] == transition['historical_device']
            and current['dev'] == transition['current_device']
            and {k: v for k, v in historical.items() if k != 'dev'}
            == {k: v for k, v in current.items() if k != 'dev'},
            'difference beyond the explicit device transition')


def check_composition(old, new, current):
    expected = dict(old['files'])
    require(len(expected) == 334 and COPY['destination'] not in expected
            and expected[COPY['source_destination']]['sha256'] == LLVM_SHA, 'original B334 provider differs')
    expected[COPY['destination']] = dict(expected[COPY['source_destination']])
    require(new['files'] == expected and new['archive_copies'] == [COPY]
            and new['stamp_hex'] == old['stamp_hex']
            and new['runtime_source_commit'] == old['runtime_source_commit'], 'composition payload/roles changed')
    for key in ['build_compiler', 'runtime_driver', 'stamp']:
        require(new[key] == current[old[key]['path']], 'composition input lacks exact current admission')
    require(len(new['private']) == len(old['private']) == 256, 'complete private membership required')
    for before, after in zip(old['private'], new['private'], strict=True):
        require({k: v for k, v in before.items() if k != 'file'}
                == {k: v for k, v in after.items() if k != 'file'}
                and after['file'] == current[before['file']['path']], 'private source/destination/current identity differs')
    for before, after in zip(old['archives'], new['archives'], strict=True):
        require({k: v for k, v in before.items() if k != 'file'}
                == {k: v for k, v in after.items() if k != 'file'}
                and after['file'] == current[before['file']['path']], 'archive membership/current identity differs')


class Stage:
    def __init__(self, args):
        self.args = args
        require(sha(HERE / 'inputs.json') == args.inputs_sha256, 'source freeze differs')
        self.frozen = read(HERE / 'inputs.json')
        self.runtime_environment = dict(os.environ)
        expected_environment = self.frozen['launch_environment']
        extra = set(self.runtime_environment) - set(expected_environment)
        cf = self.runtime_environment.get('__CF_USER_TEXT_ENCODING', '').split(':')
        require(all(self.runtime_environment.get(k) == v for k, v in expected_environment.items())
                and extra <= {'__CF_USER_TEXT_ENCODING'}, 'unexpected helper environment')
        if extra:
            require(len(cf) == 3 and all(re.fullmatch(r'(?:0[xX][0-9a-fA-F]{1,8}|[0-9]{1,10})', p) for p in cf)
                    and int(cf[0], 16 if cf[0].lower().startswith('0x') else 10) == os.getuid() == 501,
                    'unexpected Darwin CF context')
        require(sha(HERE / 'plan.json') == self.frozen['plan_sha256'], 'reviewed admission differs')
        self.plan = read(HERE / 'plan.json')
        for path in self.frozen['import_sources']:
            require(sha(path) == self.frozen['files'][path], 'frozen import differs')
        self.owned = load('b2_readmit_owned', OWNER / 'experiments/stable-cgu/owned_stage.py')
        self.previous = load('b2_prior_metadata', BASE / '.work/beta-auxiliary-metadata-source-01/check.py')
        self.stock = load('b2_prior_stock', self.previous.STOCK_CODE)
        self.comp = load('b2_readmit_compositor', self.previous.COMPOSITOR)
        sys.path.insert(0, str(EMBED / 'scripts'))
        self.libs = load('b2_readmit_libraries', EMBED / 'scripts/custom_cargo_libraries.py')
        self.stage2 = load('b2_readmit_native_source', self.stock.STAGE2 / 'experiments/hir-stage2-package/check.py')
        self.env = self.stock.environment()
        self.current = {}
        self.old = read(self.stock.PLAN)
        self.record = dict(schema_version=1, policy=POLICY, status='waiting', owner=str(OWNER),
            pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(), commands=[],
            inputs_sha256=args.inputs_sha256, admission_plan_sha256=self.frozen['plan_sha256'],
            historical_records_changed=False, assemblies=0, compiler_builds=0, benchmark=False,
            capacity=dict(entry_gib=16, stop_gib=9, floor_gib=8), platform=platform(),
            environment=self.runtime_environment)
        require(not WORK.exists() and not OUTPUT.exists(), 'fresh metadata and future output required')
        WORK.mkdir()
        self.g = SimpleNamespace(args=SimpleNamespace(**self.previous.STOCK_PINS),
            frozen=read(self.previous.STOCK_FREEZE), record=self.record, save=self.save)
        self.g.amendment = lambda: self.stock.Stage.amendment(self.g)
        self.save()

    def save(self):
        self.owned.write(WORK / 'receipt.json', self.record)

    def check_sources(self):
        require(sha(HERE / 'inputs.json') == self.args.inputs_sha256
                and platform() == self.plan['current_platform'] and dict(os.environ) == self.runtime_environment,
                'source freeze/current platform/environment changed')
        require(str(Path(sys.executable).resolve()) == self.frozen['python']['resolved']
                and sha(sys.executable) == self.frozen['python']['sha256'], 'Python identity changed')
        for path, expected in self.frozen['files'].items():
            p = Path(path)
            require(p.is_file() and not p.is_symlink() and p.resolve(strict=True) == p and sha(p) == expected,
                    'frozen source/proof changed: ' + path)
        for module in list(sys.modules.values()):
            path = getattr(module, '__file__', None)
            if path and path.startswith('/Users/danluu/dev/rust-interp'):
                require(str(Path(path).resolve()) in self.frozen['files'], 'unfrozen local import: ' + path)
        require(not OUTPUT.exists(), 'metadata stage created future assembly')

    def current_barrier(self, contents=False):
        for path, record in self.current.items():
            require(identity(path) == record['identity'], 'current admitted input changed: ' + path)
            if contents:
                require(self.comp.check_file(record) == record, 'current input bytes changed')
        for path, expected in self.plan['executors'].items():
            require(identity(path) == expected['identity'], 'executor changed: ' + path)
            if contents:
                require(sha(path) == expected['sha256'], 'executor bytes changed: ' + path)
        current_E = read(self.plan['current_E']['components']['path'])
        require(current_E['components'][0]['root'] == str(self.stock.E), 'fresh E root association differs')
        for kind, entries in current_E['snapshots'][0].items():
            for name, expected in entries.items():
                path = self.stock.E / name
                value = path.lstat()
                require([value.st_dev, value.st_ino, value.st_mode, value.st_size,
                         value.st_mtime_ns, value.st_ctime_ns, value.st_nlink] == expected,
                        'fresh E snapshot changed: ' + name)
                if kind == 'links':
                    link = current_E['components'][0]['links'][name]
                    require(os.readlink(path) == link['text']
                            and str(path.resolve(strict=True)) == link['resolved_target'], 'fresh E source link changed')
        route = self.plan['otool_route']
        selected = Path(route['selected'])
        require(str(selected.resolve(strict=True)) == route['resolved']
                and os.readlink(selected) == route['link_text']
                and identity(selected) == route['link_identity']
                and identity(route['resolved']) == route['resolved_identity']
                and sha(route['resolved']) == route['resolved_sha256'], 'selected otool route changed')
        for path, expected in route['parents'].items():
            require(not Path(path).is_symlink() and identity(path) == expected, 'otool parent route changed')

    def admit_files(self):
        changes = []
        for path, old in self.plan['historical_inputs'].items():
            override = self.plan['changed_system_executors'].get(path)
            expected_hash = override['sha256'] if override else old['sha256']
            actual = self.comp.check_file(dict(path=path, sha256=expected_hash))
            require(actual['identity'] == self.plan['current_input_identities'][path], 'current prelaunch identity changed')
            if override:
                require(actual['identity'] == override['identity'], 'new OS executor admission changed')
            else:
                require(actual['size'] == old['size'], 'historical payload size changed')
                admit_identity(old['identity'], actual['identity'], self.plan['device_transition'])
            changes.append(dict(path=path, historical=old, current=actual,
                                exception='explicit new OS executor' if override else 'device identity only'))
            self.current[path] = actual
            self.owned.disk(OWNER, 9)
        self.owned.write(WORK / 'current-inputs.json', self.current)
        self.owned.write(WORK / 'historical-current-admission.json', changes)
        self.current_barrier()

    def command(self, argv, *, cwd=None, env=None):
        self.check_sources()
        self.current_barrier()
        self.owned.disk(OWNER, 9)
        index = len(self.record['commands'])
        wanted = self.plan['children'][index]
        cwd, env = str(cwd or OWNER), env or self.env
        require(argv == wanted['argv'] and cwd == wanted['cwd'] and env == wanted['environment'],
                'unreviewed native metadata command')
        executor = '/usr/bin/git' if argv[0] == 'git' else argv[0]
        require(sha(executor) == self.plan['executors'][executor]['sha256'], 'selected executor bytes changed')
        out = WORK / 'commands' / f'{index:03d}'
        try:
            child = self.owned.run(argv, cwd=cwd, env=env, out=out, capacity_root=OWNER)
        finally:
            if (out / 'receipt.json').exists():
                child = read(out / 'receipt.json')
                self.record['commands'].append(dict(path=str(out / 'receipt.json'), sha256=sha(out / 'receipt.json'),
                    command=child['command'], pid=child.get('pid'), returncode=child.get('returncode')))
                self.save()
        self.current_barrier()
        require(sha(executor) == self.plan['executors'][executor]['sha256'], 'selected executor changed during command')
        self.check_sources()
        return dict(receipt=child, path=str(out / 'receipt.json'),
                    stdout=(out / 'stdout').read_bytes(), stderr=(out / 'stderr').read_bytes())

    def historical_contracts(self):
        self.g.amendment()
        old = self.old
        require(sha(self.stock.PLAN) == self.previous.STOCK_PINS['plan_sha'], 'old plan changed')
        metadata = read(old['metadata_receipt'])
        assembly = read(self.stock.ROOT / 'stages/assemble-01/receipt.json')
        require(metadata['status'] == assembly['status'] == 'passed'
                and metadata['plan_sha256'] == assembly['plan_sha256'] == self.previous.STOCK_PINS['plan_sha'],
                'historical metadata/assembly association differs')
        smoke = read(self.previous.STOCK_RECEIPT)
        require(sha(self.previous.STOCK_RECEIPT) == self.previous.STOCK_SHA and smoke['status'] == 'passed'
                and smoke['source_unchanged'] and smoke['runtime_unchanged'] and smoke['source_restored']
                and len(smoke['commands']) == 28 and sum(r['role'] == 'smoke-control' for r in smoke['commands']) == 18
                and all(smoke['checks'].values()) and smoke['plan_sha256'] == self.previous.STOCK_PINS['plan_sha'],
                'historical passing stock controls differ')
        for ref in smoke['commands']:
            child = read(ref['path'])
            require(sha(ref['path']) == ref['sha256'] and child['status'] == 'finished'
                    and child['command'] == ref['command'] and child['supervisor_pid'] == smoke['pid']
                    and smoke['admitted_at'] <= child['started_at'] <= child['finished_at'] <= smoke['finished_at'],
                    'historical stock child association differs')
            for name in ['stdout', 'stderr']:
                require(sha(Path(ref['path']).parent / name) == child[name + '_sha256'], 'historical raw stream changed')
        controls = read(self.plan['compositor_controls']['path'])
        require(controls['status'] == 'passed' and controls['controls'] == 10
                and controls['source_commit'] == '95d9501b43848fdbe640fd14c2a88da95da48903', 'compositor controls required')
        e = read(self.plan['current_E']['receipt']['path'])
        require(e['status'] == 'passed' and e['full_current_guard_passed'] and len(e['children']) == 28
                and e['fresh_components'] == self.plan['current_E']['components']
                and e['fresh_metadata'] == self.plan['current_E']['metadata']
                and e['source_commit'] == self.stock.REVISION
                and e['runtime_sysroot'] == str(self.stock.E)
                and e['runtime_rustc_sha256'] == self.old['runtime_compiler']['sha256'], 'fresh E readmission required')
        require(self.stage2.inputs() == self.plan['guard_inputs'], 'current source guard inputs changed')

    def source_guard(self):
        prior = read(self.plan['stage2_plan']['path'])['previous']
        def git(argv, cwd=self.stock.SOURCE):
            result = self.command(argv, cwd=cwd, env=prior['old_plan']['environment'])
            require(not result['stderr'], 'source guard stderr')
            return dict(stdout=result['stdout'].decode(), stderr='')
        self.stage2.engine.source_guard(prior['source'], git, self.plan['old_plan_sha256'])
        require(self.stage2.native.artifacts() == prior['stage1']
                == read(self.stock.INSPECT / 'qualified-runtime.json'), 'current E bytes/source links differ')

    def original_B(self):
        actual = self.comp.output_inventory(self.stock.B)
        expected = {p: {k: r[k] for k in ['sha256', 'size', 'mode']} for p, r in self.old['composition']['files'].items()}
        require({p: {k: r[k] for k in ['sha256', 'size', 'mode']} for p, r in actual.items()} == expected,
                'original B334 complete payload differs')
        manifest = read(self.stock.ROOT / 'composition/private-sysroot.json')
        require(manifest['files'] == {p: r['sha256'] for p, r in actual.items()}, 'B334 manifest changed')
        return actual

    def sdk(self):
        for key, argv in self.plan['sdk_queries']:
            result = self.command(argv)
            require(not result['stderr'] and result['stdout'].decode() == self.plan['sdk_outputs'][key],
                    'current SDK discovery changed: ' + key)

    def probe(self, key):
        old = self.old[key]
        def inspect(argv, text=True):
            require(text, 'text loader inspection required')
            result = self.command(argv)
            require(not result['stderr'], 'Mach-O inspector emitted diagnostics')
            return result['stdout'].decode()
        closure, state = self.libs.library_closure(Path(old['path']), HOST, inspect=inspect)
        require(closure['platform'] == self.plan['current_platform']
                and {k: v for k, v in closure.items() if k != 'platform'}
                == {k: v for k, v in old['closure'].items() if k != 'platform'}, 'compiler loader semantics changed')
        version = self.command([old['path'], '-vV'], env=self.env | {'DYLD_PRINT_LIBRARIES': '1'})
        require(version['stdout'].decode() == old['version'], 'actual compiler version changed')
        allowed = {item['resolved'] for item in closure['libraries']} | {str(Path(old['path']).resolve())}
        parsed = self.stock.parse_dyld(version['stderr'].decode(), version['receipt']['pid'], allowed, old['driver']['resolved'])
        sysroot = self.command([old['path'], '--print', 'sysroot'])
        require(not sysroot['stderr'] and sysroot['stdout'].decode().strip() == old['default_sysroot'], 'sysroot changed')
        return dict(path=old['path'], sha256=old['sha256'], version=old['version'], default_sysroot=old['default_sysroot'],
            closure=closure, state=state, driver=old['driver'], loaded=parsed,
            version_receipt=version['path'], sysroot_receipt=sysroot['path'])

    def metadata(self):
        self.check_sources()
        self.admit_files()
        self.historical_contracts()
        self.source_guard()
        original_B = self.original_B()
        self.owned.write(WORK / 'original-B334-current-inventory.json', original_B)
        self.sdk()
        probes = {key: self.probe(key) for key in ['build_compiler', 'runtime_compiler']}
        snapshots = {}
        directory = WORK / 'input-snapshots'
        directory.mkdir()
        for path in self.frozen['snapshot_inputs'] + [str(HERE / 'inputs.json')]:
            expected = self.args.inputs_sha256 if path == str(HERE / 'inputs.json') else self.frozen['files'][path]
            data = Path(path).read_bytes()
            require(hashlib.sha256(data).hexdigest() == expected, 'snapshot source changed')
            destination = directory / expected
            if not destination.exists():
                self.comp.write_new(destination, data, lambda: self.owned.disk(OWNER, 9))
            require(sha(destination) == expected, 'snapshot readback failed')
            snapshots[str(destination)] = expected
        original = self.old['composition']
        proofs = {row['path']: self.current[row['path']] for row in original['proofs']}
        proofs.update({path: dict(path=path, sha256=value) for path, value in snapshots.items()})
        composition = self.comp.inspect_inputs(archives=[self.current[x['file']['path']] for x in original['archives']],
            stamp=self.current[original['stamp']['path']],
            approved_private_files={x['source']: {k: x['file'][k] for k in ['sha256', 'size']} for x in original['private']},
            build_compiler=self.current[original['build_compiler']['path']], runtime_source_commit=original['runtime_source_commit'],
            runtime_driver=self.current[original['runtime_driver']['path']], proofs=[proofs[p] for p in sorted(proofs)],
            archive_copies=[COPY])
        check_composition(original, composition, self.current)
        auxiliary = {}
        for path in [TOOL, COPY['source_destination']]:
            result = self.command(['/usr/bin/otool', '-arch', 'arm64', '-l', str(self.stock.B / path)])
            require(not result['stderr'], 'auxiliary declaration diagnostics')
            auxiliary[path] = dict(receipt=result['path'], **self.previous.declarations(result['stdout'].decode()))
        tool = auxiliary[TOOL]
        require(any(p in ['@loader_path/../lib', '@executable_path/../lib'] for p in tool['rpaths'])
                and ['LC_LOAD_DYLIB', '@rpath/libLLVM.dylib'] in tool['loads'], 'actual beta auxiliary route differs')
        for path, declaration in auxiliary.items():
            for _, dependency in declaration['loads']:
                require(((path == TOOL and dependency == '@rpath/libLLVM.dylib')
                         or dependency.startswith(('/usr/lib/', '/System/Library/')))
                        and '..' not in Path(dependency).parts, 'unreviewed auxiliary dependency')
        self.source_guard()
        result = self.command(self.plan['sdk_queries'][-1][1])
        require(not result['stderr'] and result['stdout'].decode() == self.plan['sdk_outputs']['otool'], 'selected otool changed')
        require(self.original_B() == original_B, 'original B changed during metadata')
        self.comp.recheck_inputs(composition)
        self.current_barrier(contents=True)
        self.check_sources()
        require(len(self.record['commands']) == len(self.plan['children']) == 39, 'complete 39 metadata commands required')
        plan = dict(schema_version=1, policy=POLICY, status='planned-unexecuted', owner=str(OWNER),
            inputs_sha256=self.args.inputs_sha256, historical_plan_sha256=self.previous.STOCK_PINS['plan_sha'],
            admission_plan_sha256=self.frozen['plan_sha256'], current_inputs_sha256=sha(WORK / 'current-inputs.json'),
            original_B_inventory_sha256=sha(WORK / 'original-B334-current-inventory.json'),
            composition=composition, composition_sha256=self.comp.digest(self.comp.encoded(composition)),
            destination=str(B2), evidence=str(OUTPUT / 'composition'), probes=probes,
            current_sdk=self.plan['sdk_outputs'], current_platform=self.plan['current_platform'],
            actual_original_auxiliary_declarations=auxiliary, future=self.plan['future'],
            current_E_predecessor=self.plan['current_E'], input_snapshots=snapshots,
            copy_payload_bytes=sum(row['size'] for row in composition['files'].values()),
            proof_copy_bytes=sum(row['size'] for row in composition['proofs']),
            capacity=dict(entry_gib=16, stop_gib=9, floor_gib=8), assemblies=0, compiler_builds=0,
            historical_records_changed=False, benchmark=False, publication=False)
        self.owned.write(WORK / 'planned.json', plan)
        self.record.update(status='passed', metadata_only=True, finished_at=time.time(),
            current_inputs_sha256=sha(WORK / 'current-inputs.json'), plan_sha256=sha(WORK / 'planned.json'),
            source_unchanged=True, runtime_unchanged=True, original_B_unchanged=True,
            free_bytes_after=self.owned.disk(OWNER))
        self.save()

    def execute(self):
        try:
            with self.owned.workload_lock(self.owned.CANONICAL_LOCK, 600):
                self.record.update(status='running', admitted_at=time.time(), free_bytes_before=self.owned.disk(OWNER, 16))
                self.save()
                self.metadata()
        except BaseException as exc:
            self.record.update(status='failed', error=repr(exc), finished_at=time.time(),
                               free_bytes_after=shutil.disk_usage(OWNER).free)
            self.save()
            raise


def main():
    require(sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd() == OWNER, 'fixed Python -B/cwd required')
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--inputs-sha256', required=True)
    args = parser.parse_args()
    require(re.fullmatch('[0-9a-f]{64}', args.inputs_sha256), 'exact source digest required')
    Stage(args).execute()


if __name__ == '__main__':
    main()
