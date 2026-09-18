#!/usr/bin/env python3
"""Re-evaluate saved frontend outputs losslessly, then finish eight post-guards."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time

OWNER = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
HERE = OWNER / 'experiments/runtime-exporter/frontend-continue-01'
WORK = OWNER / '.work/runtime-exporter-frontend-continue-01'
sys.path.insert(0, str(OWNER / 'experiments/runtime-exporter/frontend-01'))
import frontend as f
import telemetry as t
b, m = f.b, f.m
require, sha, read = m.require, m.sha, m.read


class Continue(f.Frontend):
    def failed_history(self):
        terminal = read(self.build_plan['failed_frontend_receipt']['path'])
        plan = read(self.build_plan['failed_frontend_plan']['path'])
        require(terminal['status'] == 'failed' and terminal['error'] ==
                "RuntimeError('raw native/export diagnostics differ: basic-native/basic-export-explicit-R')"
                and len(terminal['commands']) == 32 and len(plan['children']) == 40,
                'exact retained controller failure required')
        for ref, expected in zip(terminal['commands'], plan['children'][:32], strict=True):
            path = Path(ref['path']); child = read(path)
            require(sha(path) == ref['sha256'] and child['status'] == 'finished'
                    and child['returncode'] in expected.get('expected', [0])
                    and child['command'] == ref['command'] == expected['argv'] and child['cwd'] == expected['cwd']
                    and child['environment'] == expected['environment'] and child['pid'] == ref['pid']
                    and child['supervisor_pid'] == terminal['pid'] and child['parent_pid'] == terminal['parent_pid']
                    and terminal['admitted_at'] <= child['started_at'] <= child['finished_at'] <= terminal['finished_at'],
                    'retained failed-attempt child association changed')
            for stream in ('stdout', 'stderr'):
                require(sha(path.parent / stream) == child[stream + '_sha256'], 'retained frontend raw bytes changed')
        require(not any((f.WORK / 'commands' / f'{index:03d}').exists() for index in range(32, 40)),
                'previously missing guards appeared in failed attempt')
        frozen = read(f.HERE / 'inputs.json'); snapshots = read(f.WORK / 'source-snapshots.json')
        expected_files = frozen['files'] | {str(f.HERE / 'inputs.json'): sha(f.HERE / 'inputs.json')}
        require(set(snapshots) == set(expected_files), 'failed frontend retained source membership differs')
        for path, expected in expected_files.items():
            require(sha(path) == expected == snapshots[path]['sha256'] == sha(snapshots[path]['path']),
                    'failed frontend original/snapshot bytes changed')
        for name in ('basic.rs', 'test_export.rs'):
            require((f.FIXTURE / name).read_bytes() == (OWNER / 'tests/fixtures/borrowck-cache' / name).read_bytes(),
                    'failed attempt did not restore original fixture')
        return terminal, plan

    def reevaluate(self, terminal, plan):
        observations, results = [], {}
        original = {name: (OWNER / 'tests/fixtures/borrowck-cache' / name).read_bytes()
                    for name in ('basic.rs', 'test_export.rs')}
        states = {'original': original['basic.rs']} | {name: original['basic.rs'] + extra for name, _, extra in f.ERRORS}
        for index, row in enumerate(plan['application_commands'], 14):
            name = row['name']; path = Path(terminal['commands'][index]['path'])
            stdout, stderr = [(path.parent / stream).read_bytes() for stream in ('stdout', 'stderr')]
            require(b'internal compiler error' not in stderr, 'retained compiler panic')
            retained = f.WORK / (name + '.source.rs')
            require(retained.read_bytes() == (original['test_export.rs'] if name.startswith('test-') else states[row['state']]),
                    'saved frontend source state differs')
            argv_record = f.Frontend.argv_record(self, row, f.OUTPUT / (name + '-argv'))
            artifact = f.OUTPUT / (name + ('.json' if row['profile'] == 'list' else '.rbc'))
            allow = row['profile'] in ('basic', 'test') and row['error'] is None
            split = None
            if row['error'] == 'wrong-role':
                require(stderr == b"compiler executable does not match the exporter's runtime toolchain\n"
                        and not stdout and not artifact.exists(), 'wrong-role refusal differs')
            else:
                split = t.split_stderr(stderr, allow_telemetry=allow)
                diagnostics = [item['diagnostic'] for item in split['segments'] if item['channel'] == 'compiler']
                if row['error']:
                    require(not artifact.exists() and any(item['level'] == 'error' for item in diagnostics),
                            'failed control lacks diagnostic or published bytecode')
                    if row['error'] != 'metadata':
                        require(any((item.get('code') or {}).get('code') == row['error'] for item in diagnostics),
                                'required uncalled error is missing')
                elif name == 'exporter-capabilities':
                    caps = json.loads(stdout)
                    require(not stderr and caps['schema_version'] == 1 and caps['bytecode_version'] == 5
                            and caps['compiler_sysroot'] == str(m.R) and caps['compiler_roles'] == self.data['binding'],
                            'retained exporter capabilities differ')
                elif name == 'wrapper-roles':
                    require(not stderr and json.loads(stdout) == self.data['binding'], 'retained wrapper roles differ')
                elif row['profile'] == 'list':
                    report = read(artifact); tests = report.get('tests')
                    require(report.get('kind') == 'test-discovery' and report.get('schema_version') == 1
                            and report.get('strict_frontend') is True and report.get('executed') is False
                            and report.get('harness') == 'libtest' and report.get('target') == m.HOST and report.get('count') == 1
                            and isinstance(tests, list) and len(tests) == 1 and tests[0]['name'] == 'selected'
                            and tests[0]['status'] == 'classified' and tests[0]['ordinary_test'] is True,
                            'retained test discovery differs')
                    require(Path(row['argv'][-1] + '.tests.json').read_bytes() == artifact.read_bytes(), 'test sidecar differs')
                elif row['profile'] != 'native':
                    require(artifact.is_file() and artifact.stat().st_size > 0
                            and Path(row['argv'][-1] + '.rbc').read_bytes() == artifact.read_bytes(), 'RBC sidecar differs')
                    telemetry = [item for item in split['segments'] if item['channel'] == 'telemetry']
                    kinds = [item['kind'] for item in telemetry]
                    base = ['aggregate-frames', 'scalar-frames', 'scalar-promotion']
                    require(kinds in (base + ['cfg', 'export'], base + ['forwarding', 'cfg', 'export'])
                            and all(item['values']['stage'] == 'final' for item in telemetry if item['kind'] == 'forwarding')
                            and telemetry[-1]['values']['bytes'] == artifact.stat().st_size,
                            'fixed export telemetry sequence or bytecode size differs')
            results[name] = dict(stdout=stdout, stderr=stderr, artifact=artifact, split=split)
            observations.append(dict(name=name, receipt=str(path), receipt_sha256=sha(path),
                source=m.file_record(retained), compiler_argv=argv_record, stderr_separation=split,
                artifact=m.file_record(artifact) if artifact.is_file() else None))
        pairs = [('basic-native', 'basic-export-explicit-R'), ('test-native', 'test-export'),
            ('uncalled-type-native', 'uncalled-type-export'), ('uncalled-borrow-native', 'uncalled-borrow-export'),
            ('restored-native', 'restored-export'), ('reject-build-sysroot-native', 'reject-build-sysroot-export'),
            ('basic-native', 'basic-export-default-R'), ('basic-native', 'wrapper-export-R'), ('test-native', 'test-discovery')]
        for left, right in pairs:
            require(results[left]['stdout'] == results[right]['stdout'], 'raw compiler stdout differs')
            t.compare_compiler_stderr(results[left]['split'], results[right]['split'])
        for name in ('basic-export-default-R', 'wrapper-export-R', 'restored-export'):
            require(results[name]['artifact'].read_bytes() == results['basic-export-explicit-R']['artifact'].read_bytes(),
                    'explicit/default/wrapper/restored RBC differs')
        require((results['basic-native']['stdout'], results['basic-native']['stderr']) ==
                (results['restored-native']['stdout'], results['restored-native']['stderr']), 'restored native diagnostics differ')
        m.owned.write(WORK / 'frontend-results.json', dict(children=observations, comparison_pairs=pairs,
            raw_compiler_diagnostic_parity=True, whole_stderr_parity=False, telemetry_losslessly_retained=True,
            bytecode_parity=True, source_restored=True, guest_executions=0, prior_failed_attempt_unchanged=True))

    def run(self):
        self.sources(); self.metadata_receipts(); self.check_build(); self.barrier(full=True)
        snapshots = WORK / 'source-snapshots'; snapshots.mkdir(); retained = {}
        for path, expected in (self.frozen['files'] | {str(HERE / 'inputs.json'): self.args.inputs_sha256}).items():
            target = snapshots / expected
            if not target.exists():
                self.comp.write_new(target, Path(path).read_bytes(), lambda: m.owned.disk(OWNER, 9))
            require(sha(target) == expected, 'continuation source snapshot differs')
            retained[path] = dict(path=str(target), sha256=expected)
        m.owned.write(WORK / 'source-snapshots.json', retained)
        terminal, plan = self.failed_history()
        self.reevaluate(terminal, plan)
        m.readmit.Stage.source_guard(self); self.checkout()
        self.failed_history(); self.barrier(full=True); self.sources()
        require(len(self.record['commands']) == len(self.build_plan['children']) == 8, 'exact eight missing post-guards required')
        self.record.update(status='passed', finished_at=time.time(), source_unchanged=True, source_restored=True,
            D_B2_R_unchanged=True, adopted_VM_unchanged=True, frontend_qualified=True, application_qualified=False,
            completed_compiler_commands_rerun=0, prior_failed_attempt_unchanged=True,
            frontend_results_sha256=sha(WORK / 'frontend-results.json'), free_bytes_after=m.owned.disk(OWNER))
        self.save()

    def __init__(self, args):
        self.args = args
        require(sha(HERE / 'inputs.json') == args.inputs_sha256, 'continuation freeze differs')
        self.frozen = read(HERE / 'inputs.json')
        require(sha(HERE / 'plan.json') == self.frozen['plan_sha256'], 'continuation plan differs')
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
        require(not WORK.exists() and not WORK.is_symlink(), 'fresh continuation output required')
        WORK.mkdir(); (WORK / 'tmp').mkdir()
        self.outputs = dict(self.built['built_files'])
        vm = self.data['future_VM']['binary']; self.outputs[vm['path']] = vm
        self.closures = read(self.build_plan['failed_tool_closures']['path'])
        self.record = dict(schema_version=1, policy='runtime-exporter-frontend-continuation-v1', status='waiting', owner=str(OWNER),
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
                'frontend source/platform/environment changed')
        require(str(Path(sys.executable).resolve()) == self.frozen['python']['resolved']
                and sha(sys.executable) == self.frozen['python']['sha256'], 'frontend Python changed')
        for path, expected in self.frozen['files'].items():
            require(m.file_record(path)['sha256'] == expected, 'frozen frontend source/proof changed: ' + path)
        for module in list(sys.modules.values()):
            path = getattr(module, '__file__', None)
            if path and path.startswith('/Users/danluu/dev/rust-interp'):
                require(str(Path(path).resolve()) in self.frozen['files'], 'unfrozen frontend import: ' + path)
        require({str(p) for p in m.ordinary_files(OWNER / 'crates')} == set(self.data['crate_files']), 'crate membership changed')
        require(m.configuration() == self.data['configuration'] and not any(m.configuration().values()), 'Cargo config changed')
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
    require(sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd() == OWNER, 'fixed continuation Python -B/cwd required')
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--inputs-sha256', required=True)
    Continue(parser.parse_args()).execute()


if __name__ == '__main__':
    main()
