#!/usr/bin/env python3
"""Publish the qualified fixed composition under its actual installed R owner."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time

OWNER = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
HERE = OWNER / 'experiments/runtime-exporter/publication-01'
WORK = OWNER / '.work/runtime-exporter-publication-01'
sys.path.insert(0, str(OWNER / 'experiments/runtime-exporter/frontend-01'))
import frontend as f
b, m = f.b, f.m
require, sha, read = m.require, m.sha, m.read


class Publication(f.Frontend):
    @contextmanager
    def tool_lock(self):
        path = m.ROWNER / '.work/interpreter-tools.lock'
        require(path.parent.is_dir() and path.parent.resolve(strict=True) == path.parent,
                'ordinary runtime tool-lock parent required')
        require(not path.is_symlink() and (not path.exists() or path.is_file()), 'indirect runtime tool lock')
        with path.open('a+') as lock:
            before = os.fstat(lock.fileno())
            deadline = time.monotonic() + 600
            while True:
                try:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    require(time.monotonic() < deadline, 'runtime tool publication lock timed out')
                    time.sleep(.25)
            actual = path.stat()
            require((actual.st_dev, actual.st_ino) == (before.st_dev, before.st_ino), 'runtime tool lock replaced')
            yield

    def runtime_source_guard(self):
        for child in self.build_plan['runtime_source_children']:
            result = self.command(child['argv'], cwd=m.ROWNER)
            require(not result['stderr'] and hashlib.sha256(result['stdout']).hexdigest() == child['stdout_sha256'],
                    'runtime launcher source checkpoint changed')

    def frontend_proof(self):
        terminal = read(self.build_plan['frontend_continuation']['path'])
        plan = read(self.build_plan['frontend_continuation_plan']['path'])
        require(terminal['status'] == 'passed' and terminal['frontend_qualified']
                and terminal['prior_failed_attempt_unchanged'] and terminal['completed_compiler_commands_rerun'] == 0
                and terminal['source_restored'] and terminal['D_B2_R_unchanged'] and terminal['adopted_VM_unchanged']
                and len(terminal['commands']) == 8, 'completed saved-frontend continuation required')
        require(len(plan['children']) == 8, 'exact continuation command plan required')
        for ref, expected in zip(terminal['commands'], plan['children'], strict=True):
            path = Path(ref['path']); child = read(path)
            require(sha(path) == ref['sha256'] and child['status'] == 'finished' and child['returncode'] == 0
                    and child['command'] == ref['command'] == expected['argv'] and child['cwd'] == expected['cwd']
                    and child['environment'] == expected['environment'] and child['pid'] == ref['pid']
                    and child['supervisor_pid'] == terminal['pid'] and child['parent_pid'] == terminal['parent_pid']
                    and terminal['admitted_at'] <= child['started_at'] <= child['finished_at'] <= terminal['finished_at'],
                    'frontend continuation child association changed')
            for stream in ('stdout', 'stderr'):
                require(sha(path.parent / stream) == child[stream + '_sha256'], 'frontend continuation raw bytes changed')
        results = read(self.build_plan['frontend_results']['path'])
        require(sha(self.build_plan['frontend_results']['path']) == terminal['frontend_results_sha256']
                and results['raw_compiler_diagnostic_parity'] and results['bytecode_parity']
                and results['telemetry_losslessly_retained'] and len(results['children']) == 18
                and results['guest_executions'] == 0, 'exact qualified frontend result required')

    def write_metadata(self, name, data):
        path = self.directory / name
        raw = (json.dumps(data, indent=2, sort_keys=True) + '\n').encode()
        self.comp.write_new(path, raw, lambda: m.owned.disk(m.ROWNER, 9))
        path.chmod(0o444)
        self.outputs[str(path)] = m.file_record(path)

    def publish(self):
        composition = self.build_plan['composition']
        require(m.runtime_tools.digest(composition) == self.key
                and self.directory == m.ROWNER / '.work/interpreter-tools' / self.key,
                'publication key/destination differs')
        namespace = self.directory.parent
        require(m.ROWNER.resolve(strict=True) == m.ROWNER and namespace.parent.resolve(strict=True) == namespace.parent,
                'ordinary runtime owner required')
        if not namespace.exists():
            namespace.mkdir()
        require(namespace.is_dir() and not namespace.is_symlink() and namespace.resolve(strict=True) == namespace,
                'ordinary runtime tool namespace required')
        require(not self.directory.exists() and not self.directory.is_symlink(), 'fresh final tool destination required')
        self.directory.mkdir()
        copied = {}
        for name in ('rust-interp-mir-export', 'rust-interp-rustc-wrapper', 'rust-interp-vm'):
            source = Path(self.data['future_VM']['binary']['path']) if name == 'rust-interp-vm' else m.TARGET / 'release' / name
            before = m.file_record(source)
            require(before['sha256'] == self.built['binaries'][name], 'qualified tool source changed')
            destination = self.directory / name
            self.comp.write_new(destination, source.read_bytes(), lambda: m.owned.disk(m.ROWNER, 9))
            destination.chmod(0o555)
            after = m.file_record(destination)
            require(after['sha256'] == before['sha256'] and after['identity']['nlink'] == 1
                    and (after['identity']['dev'], after['identity']['ino']) !=
                        (before['identity']['dev'], before['identity']['ino'])
                    and m.file_record(source) == before, 'published tool is changed or shares an input inode')
            copied[name] = dict(source=before, destination=after)
            self.outputs[str(destination)] = after
        exporter = str(self.directory / 'rust-interp-mir-export')
        probe = self.command([exporter, '--rust-interp-capabilities'],
                             env=self.data['environment'] | {'DYLD_PRINT_LIBRARIES': '1'})
        allowed = {row['resolved'] for item in self.closures if item['name'] == 'rust-interp-mir-export'
                   for row in item['identity']['libraries']} | {exporter}
        loaded = self.stock.parse_dyld(probe['stderr'].decode(), probe['receipt']['pid'], allowed,
                                      self.data['binding']['runtime_driver']['path'])
        capabilities = json.loads(probe['stdout'])
        require(capabilities == {key: value for key, value in self.built['capabilities'].items() if key != 'runtime_wrapper'},
                'published exporter capabilities differ from qualified binary')
        wrapper = self.command([str(self.directory / 'rust-interp-rustc-wrapper'), '--rust-interp-compiler-roles'])
        require(not wrapper['stderr'], 'published wrapper probe diagnostics')
        m.runtime_tools.bind_recorded_wrapper(capabilities, self.built['binaries'], self.runtime, wrapper['stdout'])
        capabilities.update(tool_key=self.key, exporter_sha256=self.built['binaries']['rust-interp-mir-export'])
        require(set(self.build_plan['required_export_options']) <= set(capabilities['export_options']),
                'ordinary application route capabilities missing')
        self.write_metadata('compiler.json', composition)
        self.write_metadata('capabilities.json', capabilities)
        self.write_metadata('ready.json', self.built['binaries'])
        self.directory.chmod(0o555)
        validation = self.command(self.build_plan['installed_validation']['argv'], cwd=m.ROWNER)
        require(not validation['stderr'] and json.loads(validation['stdout'])['status'] == 'passed',
                'ordinary installed-tool association validation failed')
        require({path.name for path in self.directory.iterdir()} ==
                {'rust-interp-mir-export', 'rust-interp-rustc-wrapper', 'rust-interp-vm',
                 'compiler.json', 'capabilities.json', 'ready.json'}, 'published membership differs')
        m.owned.write(WORK / 'published-tools.json', dict(tool_key=self.key, directory=str(self.directory),
            composition=composition, copied=copied, capabilities=capabilities, loaded_images=loaded,
            actual_exporter_probe=probe['path'], actual_wrapper_probe=wrapper['path'],
            installed_validation=validation['path'], guest_execution=False, benchmark=False))

    def run(self):
        self.sources(); self.metadata_receipts(); self.check_build(); self.frontend_proof(); self.barrier(full=True)
        snapshots = WORK / 'source-snapshots'; snapshots.mkdir(); retained = {}
        for path, expected in (self.frozen['files'] | {str(HERE / 'inputs.json'): self.args.inputs_sha256}).items():
            target = snapshots / expected
            if not target.exists():
                self.comp.write_new(target, Path(path).read_bytes(), lambda: m.owned.disk(OWNER, 9))
            require(sha(target) == expected, 'publication source snapshot differs')
            retained[path] = dict(path=str(target), sha256=expected)
        m.owned.write(WORK / 'source-snapshots.json', retained)
        self.checkout(); m.readmit.Stage.source_guard(self); self.runtime_source_guard()
        with self.tool_lock():
            self.sources(); self.barrier(full=True); self.publish()
        self.runtime_source_guard(); m.readmit.Stage.source_guard(self); self.checkout()
        self.frontend_proof(); self.barrier(full=True); self.sources()
        require(len(self.record['commands']) == len(self.build_plan['children']) == 23, 'exact twenty-three publication children required')
        self.record.update(status='passed', finished_at=time.time(), source_unchanged=True,
            D_B2_R_unchanged=True, adopted_VM_unchanged=True, frontend_qualified=True,
            tool_key=self.key, published_directory=str(self.directory), publication=True,
            guest_execution=False, application_qualified=False, benchmark=False,
            published_tools_sha256=sha(WORK / 'published-tools.json'), free_bytes_after=m.owned.disk(OWNER))
        self.save()

    def __init__(self, args):
        self.args = args
        require(sha(HERE / 'inputs.json') == args.inputs_sha256, 'publication freeze differs')
        self.frozen = read(HERE / 'inputs.json')
        require(sha(HERE / 'plan.json') == self.frozen['plan_sha256'], 'publication plan differs')
        self.build_plan = read(HERE / 'plan.json')
        self.built = read(self.build_plan['built_tools']['path'])
        self.work = WORK
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
        require(not WORK.exists() and not WORK.is_symlink(), 'fresh publication output required')
        WORK.mkdir(); (WORK / 'tmp').mkdir()
        self.outputs = dict(self.built['built_files'])
        vm = self.data['future_VM']['binary']; self.outputs[vm['path']] = vm
        self.closures = read(self.build_plan['frontend_closures']['path'])
        self.directory = Path(self.build_plan['publication_directory'])
        self.key = self.build_plan['tool_key']
        self.record = dict(schema_version=1, policy='runtime-exporter-publication-v1', status='waiting', owner=str(OWNER),
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
                'publication source/platform/environment changed')
        require(str(Path(sys.executable).resolve()) == self.frozen['python']['resolved']
                and sha(sys.executable) == self.frozen['python']['sha256'], 'publication Python changed')
        for path, expected in self.frozen['files'].items():
            require(m.file_record(path)['sha256'] == expected, 'frozen publication source/proof changed: ' + path)
        for module in list(sys.modules.values()):
            path = getattr(module, '__file__', None)
            if path and path.startswith('/Users/danluu/dev/rust-interp'):
                require(str(Path(path).resolve()) in self.frozen['files'], 'unfrozen publication import: ' + path)
        require({str(p) for p in m.ordinary_files(OWNER / 'crates')} == set(self.data['crate_files']), 'crate membership changed')
        require(m.configuration() == self.data['configuration'] and not any(m.configuration().values()), 'Cargo config changed')
        require({str(path) for path in (m.ROWNER / 'scripts').rglob('*.py')} ==
                set(self.build_plan['runtime_launcher_sources']), 'runtime launcher Python source membership changed')
        for path, row in self.outputs.items():
            require(m.file_record(path) == row, 'completed tool/binding output changed')
        for item in self.closures:
            require(m.loaders.library_state(item['identity']) == item['state'], 'tool library closure changed')

    def command(self, argv, *, cwd=None, env=None, expected=(0,), label=None):
        self.sources(); self.barrier(); m.owned.disk(OWNER, 9)
        wanted = self.build_plan['children'][len(self.record['commands'])]
        cwd, env = str(cwd or OWNER), env or self.data['environment']
        require(argv == wanted['argv'] and cwd == wanted['cwd'] and env == wanted['environment']
                and list(expected) == wanted.get('expected', [0]), 'unreviewed frontend child')
        executor = '/usr/bin/git' if argv[0] == 'git' else str(Path(argv[0]).resolve(strict=True))
        expected_sha = (self.outputs[executor]['sha256'] if executor in self.outputs else self.data['records'][executor]['sha256'])
        require(sha(executor) == expected_sha, 'frontend executor changed')
        out = WORK / 'commands' / f'{len(self.record["commands"]):03d}'
        try:
            result = m.owned.run(argv, cwd=cwd, env=env, out=out, capacity_root=OWNER, expected=expected)
        finally:
            if (out / 'receipt.json').exists():
                result = read(out / 'receipt.json')
                self.record['commands'].append(dict(path=str(out / 'receipt.json'), sha256=sha(out / 'receipt.json'),
                    command=result['command'], pid=result.get('pid'), returncode=result.get('returncode')))
                self.save()
        require(sha(executor) == expected_sha, 'executor changed during frontend child')
        self.barrier(); self.sources()
        return dict(receipt=result, path=str(out / 'receipt.json'), stdout=(out / 'stdout').read_bytes(), stderr=(out / 'stderr').read_bytes())

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
    require(sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd() == OWNER, 'fixed publication Python -B/cwd required')
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--inputs-sha256', required=True)
    Publication(parser.parse_args()).execute()


if __name__ == '__main__':
    main()
