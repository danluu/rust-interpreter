#!/usr/bin/env python3
"""Build two D/B2 tools bound to installed R; retain the adopted VM unchanged."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import sys
import time

OWNER = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
HERE = OWNER / 'experiments/runtime-exporter/build-01'
WORK = OWNER / '.work/runtime-exporter-build-01'
sys.path.insert(0, str(OWNER / 'experiments/runtime-exporter/metadata-02'))
import metadata as m

require, sha, read = m.require, m.sha, m.read


def check_build_diagnostics(stderr):
    require(not any(text in stderr for text in (b'stripping debug info', b'SIGABRT',
            b'Library not loaded:', b'internal compiler error')), 'Cargo helper/strip/native compiler failure')


def cargo_compiles(stderr, binding, source_root, frozen_sources):
    result = []
    d = binding['build']['executable']['path']
    for line in stderr.decode().splitlines():
        match = re.fullmatch(r'\s*Running `(.*)`', line)
        if not match:
            continue
        argv = shlex.split(match[1])
        if '--crate-name' not in argv:
            continue
        require(argv.count(d) == 1, 'actual Cargo compiler is not exact D')
        at = argv.index(d); command = argv[at:]; prefix = argv[:at]
        if prefix[:1] == ['env']:
            prefix = prefix[1:]
        require(all('=' in word for word in prefix), 'unexpected compiler command prefix')
        require(all(flag in command for flag in binding['build_rustflags'])
                and sum(word.startswith('--sysroot') for word in command) == 1, 'actual D/B2/R compiler flags differ')
        require(not any('RUSTC_FORCE_RUSTC_VERSION=' in word or 'RUSTC_OVERRIDE_VERSION_STRING=' in word for word in argv),
                'compiler version override appeared')
        sources = [word for word in command if word.endswith('.rs')]
        require(len(sources) == 1, 'ambiguous actual compiler source')
        source = Path(sources[0]); source = source if source.is_absolute() else source_root / source
        source = str(source.resolve(strict=True))
        require(source in frozen_sources, 'Cargo compiled an unfrozen source')
        result.append(dict(command=command, environment_assignments=argv[:at], source=source))
    require({'rust_interp_mir_export', 'rust_interp_rustc_wrapper'} <=
            {row['command'][row['command'].index('--crate-name') + 1] for row in result}, 'both actual tool compiles required')
    return result


class Build(m.Stage):
    def __init__(self, args):
        self.args = args
        require(sha(HERE / 'inputs.json') == args.inputs_sha256, 'build freeze differs')
        self.frozen = read(HERE / 'inputs.json')
        require(sha(HERE / 'plan.json') == self.frozen['plan_sha256'], 'build plan differs')
        self.build_plan = read(HERE / 'plan.json')
        self.data = read(self.build_plan['metadata_plan']['path'])
        self.plan = read(m.BHERE / 'plan.json')
        self.current = read(m.BETA / '.work/beta-auxiliary-readmission-01/current-inputs.json')
        self.previous = m.load('exporter_build_b2_prior', m.readmit.BASE / '.work/beta-auxiliary-metadata-source-01/check.py')
        self.stock = m.load('exporter_build_stock', self.previous.STOCK_CODE)
        self.comp = m.load('exporter_build_compositor', self.previous.COMPOSITOR)
        self.stage2 = m.load('exporter_build_native_guard', self.stock.STAGE2 / 'experiments/hir-stage2-package/check.py')
        self.parser = m.load('exporter_build_cargo_parser', m.OLD / '.work/exporter-split-role-source-04/cargo_output.py')
        self.runtime = m.runtime_compiler.load_runtime_compiler(m.ROWNER, m.RKEY)
        self.environment = dict(os.environ)
        expected = self.frozen['launch_environment']; extra = set(self.environment) - set(expected)
        require(all(self.environment.get(k) == v for k, v in expected.items()) and extra <= {'__CF_USER_TEXT_ENCODING'},
                'unexpected build environment')
        if extra:
            cf = self.environment['__CF_USER_TEXT_ENCODING'].split(':')
            require(len(cf) == 3 and all(re.fullmatch(r'(?:0[xX][0-9a-fA-F]{1,8}|[0-9]{1,10})', v) for v in cf)
                    and int(cf[0], 16 if cf[0].lower().startswith('0x') else 10) == os.getuid() == 501, 'unexpected Darwin context')
        require(not WORK.exists() and not m.TARGET.exists(), 'fresh build output and target required')
        WORK.mkdir()
        self.outputs = {}
        self.record = dict(schema_version=1, policy='runtime-exporter-build-v1', status='waiting', owner=str(OWNER),
            runtime_owner=str(m.ROWNER), runtime_key=m.RKEY, source_checkpoint=m.CHECKPOINT,
            pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(), commands=[],
            inputs_sha256=args.inputs_sha256, plan_sha256=self.frozen['plan_sha256'], compiler_builds=0,
            exporter_builds=0, VM_builds=0, guest_execution=False, application_qualified=False,
            publication=False, benchmark=False, environment=self.environment, capacity=dict(entry_gib=16, stop_gib=9, floor_gib=8))
        self.save()

    def save(self):
        m.owned.write(WORK / 'receipt.json', self.record)

    def sources(self):
        require(sha(HERE / 'inputs.json') == self.args.inputs_sha256
                and m.loaders.platform_identity() == self.data['platform'] and dict(os.environ) == self.environment,
                'build source/platform/environment changed')
        require(str(Path(sys.executable).resolve()) == self.frozen['python']['resolved']
                and sha(sys.executable) == self.frozen['python']['sha256'], 'build Python changed')
        for path, expected in self.frozen['files'].items():
            require(m.file_record(path)['sha256'] == expected, 'frozen build source/proof changed: ' + path)
        for module in list(sys.modules.values()):
            path = getattr(module, '__file__', None)
            if path and path.startswith('/Users/danluu/dev/rust-interp'):
                require(str(Path(path).resolve()) in self.frozen['files'], 'unfrozen build import: ' + path)
        require({str(p) for p in m.ordinary_files(OWNER / 'crates')} == set(self.data['crate_files']), 'crate membership changed')
        require(m.configuration() == self.data['configuration'] and not any(m.configuration().values()), 'Cargo config changed')
        for path, row in self.outputs.items():
            require(m.file_record(path) == row, 'completed tool/binding output changed')

    def command(self, argv, *, cwd=None, env=None):
        self.sources(); self.barrier(); m.owned.disk(OWNER, 9)
        wanted = self.build_plan['children'][len(self.record['commands'])]
        cwd, env = str(cwd or OWNER), env or self.data['environment']
        require(argv == wanted['argv'] and cwd == wanted['cwd'] and env == wanted['environment'], 'unreviewed build child')
        executor = '/usr/bin/git' if argv[0] == 'git' else str(Path(argv[0]).resolve(strict=True))
        expected = (self.outputs[executor]['sha256'] if executor in self.outputs else self.data['records'][executor]['sha256'])
        require(sha(executor) == expected, 'build executor changed')
        out = WORK / 'commands' / f'{len(self.record["commands"]):03d}'
        try:
            result = m.owned.run(argv, cwd=cwd, env=env, out=out, capacity_root=OWNER)
        finally:
            if (out / 'receipt.json').exists():
                result = read(out / 'receipt.json')
                self.record['commands'].append(dict(path=str(out / 'receipt.json'), sha256=sha(out / 'receipt.json'),
                    command=result['command'], pid=result.get('pid'), returncode=result.get('returncode')))
                self.save()
        require(sha(executor) == expected, 'executor changed during build child')
        self.barrier(); self.sources()
        return dict(receipt=result, path=str(out / 'receipt.json'), stdout=(out / 'stdout').read_bytes(), stderr=(out / 'stderr').read_bytes())

    def metadata_receipts(self):
        terminal = read(self.build_plan['metadata_receipt']['path'])
        require(terminal['status'] == 'passed' and terminal['current_D_B2_R_and_source_guards_passed']
                and terminal['planned_sha256'] == self.build_plan['metadata_plan']['sha256']
                and terminal['compiler_roles_sha256'] == self.data['compiler_roles_sha256'], 'exact passed metadata required')
        require(len(terminal['commands']) == len(self.data['children']) == 53, 'all metadata children required')
        for ref, expected in zip(terminal['commands'], self.data['children'], strict=True):
            path = Path(ref['path']); child = read(path)
            require(sha(path) == ref['sha256'] and child['status'] == 'finished' and child['returncode'] == 0
                    and child['command'] == ref['command'] == expected['argv'] and child['cwd'] == expected['cwd']
                    and child['environment'] == expected['environment'] and child['pid'] == ref['pid']
                    and child['supervisor_pid'] == terminal['pid'] and child['parent_pid'] == terminal['parent_pid']
                    and terminal['admitted_at'] <= child['started_at'] <= child['finished_at'] <= terminal['finished_at'],
                    'metadata child association changed')
            for stream in ('stdout', 'stderr'):
                require(sha(path.parent / stream) == child[stream + '_sha256'], 'metadata raw output changed')
        require(read(self.data['compiler_roles_path']) == self.data['binding'], 'actual metadata role binding changed')
        m.runtime_tools.runtime_binding(self.runtime, self.data['binding'])

    def run(self):
        self.sources(); self.metadata_receipts(); self.barrier(full=True)
        snapshots = WORK / 'source-snapshots'; snapshots.mkdir(); retained = {}
        for path, expected in dict(self.frozen['files'], **{str(HERE / 'inputs.json'): self.args.inputs_sha256}).items():
            target = snapshots / expected
            if not target.exists():
                self.comp.write_new(target, Path(path).read_bytes(), lambda: m.owned.disk(OWNER, 9))
            require(sha(target) == expected, 'build source snapshot differs')
            retained[path] = dict(path=str(target), sha256=expected)
        m.owned.write(WORK / 'source-snapshots.json', retained)
        self.checkout(); m.readmit.Stage.source_guard(self)
        built = self.command(self.data['future_build'], env=self.data['build_environment'])
        check_build_diagnostics(built['stderr'])
        parsed = self.parser.parse_cargo_output(built['stdout'], self.data['dependencies']['packages'])
        compiles = cargo_compiles(built['stderr'], self.data['binding'], OWNER,
                                 set(self.data['crate_files']) | set(self.data['registry_files']))
        names = ['rust-interp-mir-export', 'rust-interp-rustc-wrapper']
        binaries = {name: m.TARGET / 'release' / name for name in names}
        actual = {row.get('executable') for row in parsed['messages'] if row.get('reason') == 'compiler-artifact'
                  and 'bin' in row.get('target', {}).get('kind', []) and row.get('executable')}
        require(actual == {str(p) for p in binaries.values()}, 'actual Cargo executable set differs')
        generated = []
        for message in parsed['messages']:
            if message.get('reason') == 'build-script-executed' and message.get('out_dir'):
                path = Path(message['out_dir']) / 'compiler_roles.rs'
                if path.is_file():
                    require(path.is_relative_to(m.TARGET), 'generated binding escaped target')
                    generated.append(m.file_record(path))
        require(len(generated) == 1, 'one actual generated role binding required')
        self.outputs = {str(path): m.file_record(path) for path in binaries.values()}
        self.outputs[generated[0]['path']] = generated[0]
        self.record['exporter_builds'] = 1; self.save()
        exporter = str(binaries['rust-interp-mir-export'])
        capabilities = self.command([exporter, '--rust-interp-capabilities'], env=self.data['environment'] | {'DYLD_PRINT_LIBRARIES': '1'})
        allowed = {row['resolved'] for row in self.data['actual_roles']['runtime']['closure']['identity']['libraries']} | {exporter}
        loaded = self.stock.parse_dyld(capabilities['stderr'].decode(), capabilities['receipt']['pid'], allowed,
                                      self.data['binding']['runtime_driver']['path'])
        caps = json.loads(capabilities['stdout'])
        require(caps['schema_version'] == 1 and caps['bytecode_version'] == 5
                and caps['compiler_sysroot'] == str(m.R) and caps['compiler_roles'] == self.data['binding'],
                'built exporter runtime/capability binding differs')
        wrapper = self.command([str(binaries['rust-interp-rustc-wrapper']), '--rust-interp-compiler-roles'])
        require(not wrapper['stderr'], 'wrapper role probe diagnostics')
        all_binaries = {name: self.outputs[str(path)]['sha256'] for name, path in binaries.items()}
        vm = self.data['future_VM']['binary']; require(m.file_record(vm['path']) == vm, 'adopted VM changed')
        all_binaries['rust-interp-vm'] = vm['sha256']
        m.runtime_tools.bind_recorded_wrapper(caps, all_binaries, self.runtime, wrapper['stdout'])
        m.owned.write(WORK / 'cargo-build-evidence.json', dict(compilers=compiles, parsed=parsed, generated=generated,
            strip_failures=0, cargo_receipt=built['path'], cargo_receipt_sha256=sha(built['path'])))
        m.owned.write(WORK / 'built-tools.json', dict(binaries=all_binaries, built_files=self.outputs, VM=self.data['future_VM'],
            capabilities=caps, exporter_loader=loaded, exporter_probe=capabilities['path'], wrapper_probe=wrapper['path'],
            runtime_owner=str(m.ROWNER), runtime_key=m.RKEY, compiler_roles=self.data['binding'],
            actual_build_receipt=built['path'], application_qualified=False, published=False))
        m.readmit.Stage.source_guard(self); self.checkout()
        self.barrier(full=True); self.sources()
        require(len(self.record['commands']) == len(self.build_plan['children']) == 19, 'exact nineteen build children required')
        self.record.update(status='passed', finished_at=time.time(), source_unchanged=True, D_B2_R_unchanged=True,
            adopted_VM_unchanged=True, proper_strip_build_qualified=True, actual_exporter_loaded_installed_R=True,
            actual_wrapper_bound_installed_R=True, built_tools_sha256=sha(WORK / 'built-tools.json'),
            cargo_evidence_sha256=sha(WORK / 'cargo-build-evidence.json'), free_bytes_after=m.owned.disk(OWNER))
        self.save()

    def execute(self):
        try:
            with m.owned.workload_lock(m.owned.CANONICAL_LOCK, 600):
                self.record.update(status='running', admitted_at=time.time(), free_bytes_before=m.owned.disk(OWNER, 16)); self.save()
                self.run()
        except BaseException as error:
            self.record.update(status='failed', error=repr(error), finished_at=time.time(), free_bytes_after=shutil.disk_usage(OWNER).free)
            self.save()
            raise


def main():
    require(sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd() == OWNER, 'fixed build Python -B/cwd required')
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--inputs-sha256', required=True)
    Build(parser.parse_args()).execute()


if __name__ == '__main__':
    main()
