#!/usr/bin/env python3
"""Qualify the actual R-bound exporter/wrapper and retained VM before publication."""
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
HERE = OWNER / 'experiments/runtime-exporter/frontend-01'
WORK = OWNER / '.work/runtime-exporter-frontend-01'
FIXTURE = WORK / 'fixture'
OUTPUT = WORK / 'outputs'
SOURCE = OWNER
sys.path.insert(0, str(OWNER / 'experiments/runtime-exporter/build-02'))
import build as b
m = b.m
require, sha, read = m.require, m.sha, m.read
R, B2, TARGET, HOST = m.R, m.B2, m.TARGET, m.HOST
D = Path('/Users/danluu/dev/rustc-hir-capture-check-20260913/build/aarch64-apple-darwin/stage0/bin/rustc')
ERRORS = [('type', 'E0308', b'\nfn uncalled_type_error() -> u32 { "wrong" }\n'),
    ('borrow', 'E0515', b"\nfn uncalled_borrow_error() -> &'static u32 { let value = 3; &value }\n")]


def ordinary(path):
    m.file_record(path)
    return Path(path)


def app_environment(sdk):
    return read(m.WORK / 'planned.json')['environment'] | {'TMPDIR': str(WORK / 'tmp') + '/'}


def application_environment(row, sdk):
    env = app_environment(sdk)
    env['RUST_INTERP_COMPILER_ARGV_RECORD_DIR'] = str(OUTPUT / (row['name'] + '-argv'))
    artifact = OUTPUT / (row['name'] + ('.json' if row['profile'] == 'list' else '.rbc'))
    if row['profile'] != 'native':
        env.update(RUST_INTERP_EXPORT_CRATE='role_test' if row['profile'] in ('test', 'list') else 'role_basic',
                   RUST_INTERP_OUTPUT=str(artifact))
        if row['profile'] in ('test', 'list'):
            env['RUST_INTERP_EXPORT_TEST'] = '1'
        if row['profile'] == 'list':
            env['RUST_INTERP_LIST_TESTS'] = '1'
        else:
            env['RUST_INTERP_ENTRY'] = 'selected' if row['profile'] == 'test' else 'changing_value'
    return env


def application_commands(sdk):
    x, w = [str(TARGET/'release'/name) for name in ['rust-interp-mir-export','rust-interp-rustc-wrapper']]
    def args(test=False, sysroot=R):
        result = ['--crate-name', 'role_test' if test else 'role_basic', '--edition=2024',
            '--crate-type', 'lib' if test else 'bin', '-Copt-level=0', '-Cdebuginfo=0',
            '-Clinker='+sdk['clang'], '--error-format=json', '--emit=metadata']
        if test: result += ['--test','-Zalways-encode-mir=yes']
        if sysroot is not None: result += ['--sysroot',str(sysroot)]
        return result + [str(FIXTURE/('test_export.rs' if test else 'basic.rs'))]
    def row(name, executable, *, test=False, sysroot=R, profile='native', state='original', error=None, wrapper=None):
        argv = [executable] + ([str(wrapper)] if wrapper is not None else [])
        return dict(name=name, argv=argv+args(test,sysroot)+['-o',str(OUTPUT/(name+'.rmeta'))],
            profile=profile, state=state, error=error)
    rows = [dict(name='exporter-capabilities',argv=[x,'--rust-interp-capabilities'],profile='native',state='original',error=None),
        dict(name='wrapper-roles',argv=[w,'--rust-interp-compiler-roles'],profile='native',state='original',error=None),
        row('basic-native',str(R/'bin/rustc')), row('basic-export-explicit-R',x,profile='basic'),
        row('basic-export-default-R',x,profile='basic',sysroot=None),
        row('wrapper-export-R',w,profile='basic',wrapper=R/'bin/rustc'),
        row('wrapper-reject-D',w,profile='basic',wrapper=D,error='wrong-role'),
        row('test-native',str(R/'bin/rustc'),test=True),row('test-export',x,test=True,profile='test'),
        row('test-discovery',x,test=True,profile='list')]
    for state,code,_ in ERRORS:
        rows += [row('uncalled-'+state+'-native',str(R/'bin/rustc'),state=state,error=code),
            row('uncalled-'+state+'-export',x,profile='basic',state=state,error=code)]
    rows += [row('restored-native',str(R/'bin/rustc')),row('restored-export',x,profile='basic'),
        row('reject-build-sysroot-native',str(R/'bin/rustc'),sysroot=B2,error='metadata'),
        row('reject-build-sysroot-export',x,sysroot=B2,profile='basic',error='metadata')]
    require(len(rows)==18, 'fixed application command count differs')
    return rows


class Frontend(b.Build):
    def __init__(self, args):
        self.args = args
        require(sha(HERE / 'inputs.json') == args.inputs_sha256, 'frontend freeze differs')
        self.frozen = read(HERE / 'inputs.json')
        require(sha(HERE / 'plan.json') == self.frozen['plan_sha256'], 'frontend plan differs')
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
        require(not WORK.exists() and not WORK.is_symlink(), 'fresh frontend output required')
        WORK.mkdir(); (WORK / 'tmp').mkdir()
        self.outputs = dict(self.built['built_files'])
        vm = self.data['future_VM']['binary']; self.outputs[vm['path']] = vm
        self.closures = []
        self.record = dict(schema_version=1, policy='runtime-exporter-frontend-v1', status='waiting', owner=str(OWNER),
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

    def check_build(self):
        terminal = read(self.build_plan['build_receipt']['path'])
        plan = read(self.build_plan['build_plan']['path'])
        require(terminal['status'] == 'passed' and terminal['proper_strip_build_qualified']
                and terminal['actual_exporter_loaded_installed_R'] and terminal['actual_wrapper_bound_installed_R']
                and terminal['adopted_VM_unchanged'] and terminal['exporter_builds'] == 1
                and terminal['built_tools_sha256'] == self.build_plan['built_tools']['sha256'], 'qualified actual build required')
        require(len(terminal['commands']) == len(plan['children']) == 19, 'complete build history required')
        for ref, expected in zip(terminal['commands'], plan['children'], strict=True):
            path = Path(ref['path']); child = read(path)
            require(sha(path) == ref['sha256'] and child['status'] == 'finished' and child['returncode'] == 0
                    and child['command'] == ref['command'] == expected['argv'] and child['cwd'] == expected['cwd']
                    and child['environment'] == expected['environment'] and child['pid'] == ref['pid']
                    and child['supervisor_pid'] == terminal['pid'] and child['parent_pid'] == terminal['parent_pid']
                    and terminal['admitted_at'] <= child['started_at'] <= child['finished_at'] <= terminal['finished_at'],
                    'actual build child association changed')
            for stream in ('stdout', 'stderr'):
                require(sha(path.parent / stream) == child[stream + '_sha256'], 'actual build output changed')
        require(self.built['compiler_roles'] == self.data['binding'] and self.built['runtime_key'] == m.RKEY
                and self.built['runtime_owner'] == str(m.ROWNER)
                and self.built['binaries']['rust-interp-vm'] == self.data['future_VM']['binary']['sha256'],
                'built tool composition differs')

    def tool_closures(self):
        old = {}
        for index in range(24, 32):
            path = m.WORK / 'commands' / f'{index:03d}' / 'receipt.json'
            child = read(path); argv = child['command']
            require(argv[:3] == ['/usr/bin/otool', '-arch', 'arm64'] and argv[3] in ('-L', '-l'),
                    'exact prior R closure command required')
            key = (str(Path(argv[-1]).resolve(strict=True)), argv[3])
            old.setdefault(key, dict(path=str(path), child=child))
        driver = self.data['binding']['runtime_driver']['path']
        admitted = {driver, str(R / 'lib/libLLVM.dylib')}
        observations = []
        for name in ('rust-interp-mir-export', 'rust-interp-rustc-wrapper', 'rust-interp-vm'):
            binary = Path(self.data['future_VM']['binary']['path']) if name == 'rust-interp-vm' else TARGET / 'release' / name
            fresh = {}
            for flag in ('-L', '-l'):
                result = self.command(['/usr/bin/otool', '-arch', 'arm64', flag, str(binary)])
                require(not result['stderr'], 'tool Mach-O inspection diagnostics')
                fresh[flag] = result
            reused = []
            def inspect(argv, *, text):
                require(text is True and argv[:3] == ['/usr/bin/otool', '-arch', 'arm64'], 'unexpected closure inspection')
                path, flag = str(Path(argv[-1]).resolve(strict=True)), argv[3]
                if path == str(binary):
                    return fresh[flag]['stdout'].decode()
                require(name == 'rust-interp-mir-export' and path in admitted, 'unadmitted composed tool library')
                prior = old[(path, flag)]
                output = Path(prior['path']).parent / 'stdout'
                require(sha(output) == prior['child']['stdout_sha256'], 'retained R loader output changed')
                reused.append(dict(requested=argv, actual_prior_receipt=prior['path'],
                                   receipt_sha256=sha(prior['path']), stdout_sha256=sha(output)))
                return output.read_text()
            closure, state = m.loaders.library_closure(binary, HOST, inspect=inspect)
            actual = {row['resolved'] for row in closure['libraries']}
            require((driver in actual and actual <= admitted) if name == 'rust-interp-mir-export' else not actual,
                    'unexpected non-system library composition')
            item = dict(name=name, binary=m.file_record(binary), identity=closure, state=state,
                        fresh_binary_inspections={flag: row['path'] for flag, row in fresh.items()},
                        reused_immutable_R_library_inspections=reused)
            self.closures.append(item); observations.append(item)
        m.owned.write(WORK / 'tool-closures.json', observations)

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

    def argv_record(self,row,root):
        paths=m.ordinary_files(root)
        if row['profile']=='native' or row['error']=='wrong-role':
            require(not paths,'unexpected final compiler argv record')
            return None
        require(len(paths)==1 and paths[0].name.startswith('exported-'),'one actual exported compiler argv required')
        data=paths[0].read_bytes();fields=data.split(b'\0')
        require(fields[-1]==b'' and fields[:4]==[b'rust-interp-compiler-argv-v1',b'exported',str(R).encode(),str(FIXTURE).encode()],
            'compiler argv evidence header differs')
        args=[x.decode() for x in fields[4:-1]]
        expected_first=str(R/'bin/rustc') if row['name']=='wrapper-export-R' else str(TARGET/'release/rust-interp-mir-export')
        require(args[0]==expected_first,'actual final compiler route differs')
        roots=[]
        for i,arg in enumerate(args):
            if arg=='--sysroot':require(i+1<len(args),'missing final sysroot');roots.append(args[i+1])
            elif arg.startswith('--sysroot='):roots.append(arg.split('=',1)[1])
        require(roots==[str(B2 if row['error']=='metadata' else R)],'final compiler sysroot differs')
        require(str(FIXTURE/('test_export.rs' if row['name'].startswith('test-') else 'basic.rs')) in args,
            'actual compiler source differs')
        return m.file_record(paths[0])

    def applications(self,plan):
        FIXTURE.mkdir();OUTPUT.mkdir()
        original={name:(SOURCE/'tests/fixtures/borrowck-cache'/name).read_bytes() for name in ['basic.rs','test_export.rs']}
        for name,data in original.items():(FIXTURE/name).write_bytes(data)
        results={};observed=[]
        expected_states={'original':original['basic.rs']} | {name:original['basic.rs']+addition for name,_,addition in ERRORS}
        try:
            for row in plan['application_commands']:
                name=row['name'];raw=expected_states[row['state']]
                (FIXTURE/'basic.rs').write_bytes(raw)
                require((FIXTURE/'test_export.rs').read_bytes()==original['test_export.rs'],'test fixture changed')
                retained=self.work/(name+'.source.rs');retained.write_bytes((FIXTURE/'test_export.rs').read_bytes() if name.startswith('test-') else raw)
                env=application_environment(row,plan['sdk']);record_dir=OUTPUT/(name+'-argv');record_dir.mkdir()
                artifact=OUTPUT/(name+('.json' if row['profile']=='list' else '.rbc'))
                outcome=self.command(row['argv'],env=env,cwd=FIXTURE,expected=(1,2) if row['error'] else (0,),label=name)
                require((FIXTURE/'basic.rs').read_bytes()==raw and (FIXTURE/'test_export.rs').read_bytes()==original['test_export.rs'],
                    'application modified fixture inputs')
                record=self.argv_record(row,record_dir)
                stdout,stderr=outcome['stdout'],outcome['stderr']
                require(b'internal compiler error' not in stderr,'application compiler panicked')
                if row['error']:
                    require(not artifact.exists(),'failed application published bytecode')
                    if row['error']=='wrong-role':
                        require(stderr==b"compiler executable does not match the exporter's runtime toolchain\n" and not stdout,'wrong-role refusal differs')
                    else:
                        diagnostics=[]
                        for line in stderr.splitlines():
                            message=json.loads(line)
                            if message.get('$message_type')=='diagnostic':diagnostics.append(message)
                        require(any(d.get('level')=='error' for d in diagnostics),'ordinary compiler error required')
                        if row['error'] not in ('metadata',):
                            require(any((d.get('code') or {}).get('code')==row['error'] for d in diagnostics),'required uncalled diagnostic missing')
                elif name=='exporter-capabilities':
                    caps=json.loads(stdout)
                    require(not stderr and caps.get('schema_version')==1 and caps.get('bytecode_version')==5
                        and caps.get('compiler_sysroot')==str(R) and caps.get('compiler_roles')==plan['binding'],
                        'actual exporter roles/capabilities differ')
                elif name=='wrapper-roles':
                    require(not stderr and json.loads(stdout)==plan['binding'],'actual wrapper roles differ')
                elif row['profile']=='list':
                    report=read(artifact);tests=report.get('tests')
                    require(report.get('kind')=='test-discovery' and report.get('schema_version')==1
                        and report.get('strict_frontend') is True and report.get('executed') is False
                        and report.get('harness')=='libtest' and report.get('target')==HOST and report.get('count')==1
                        and isinstance(tests,list) and len(tests)==1 and tests[0]['name']=='selected'
                        and tests[0]['status']=='classified' and tests[0]['ordinary_test'] is True,
                        'actual test discovery differs')
                    sidecar=Path(row['argv'][-1]+'.tests.json')
                    require(ordinary(sidecar).read_bytes()==artifact.read_bytes(),'actual test discovery sidecar differs')
                elif row['profile']!='native':
                    require(ordinary(artifact).stat().st_size>0,'successful export lacks actual RBC')
                    sidecar=Path(row['argv'][-1]+'.rbc')
                    require(ordinary(sidecar).read_bytes()==artifact.read_bytes(),'actual RBC metadata sidecar differs')
                results[name]=dict(stdout=stdout,stderr=stderr,artifact=artifact)
                observed.append(dict(name=name,receipt=outcome['path'],source=m.file_record(retained),compiler_argv=record,
                    artifact=m.file_record(artifact) if artifact.is_file() else None))
            for left,right in [('basic-native','basic-export-explicit-R'),('test-native','test-export'),
                ('uncalled-type-native','uncalled-type-export'),('uncalled-borrow-native','uncalled-borrow-export'),
                ('restored-native','restored-export'),('reject-build-sysroot-native','reject-build-sysroot-export'),
                ('basic-native','basic-export-default-R'),('basic-native','wrapper-export-R'),('test-native','test-discovery')]:
                require((results[left]['stdout'],results[left]['stderr'])==(results[right]['stdout'],results[right]['stderr']),
                    'raw native/export diagnostics differ: '+left+'/'+right)
            for name in ['basic-export-default-R','wrapper-export-R','restored-export']:
                require(results[name]['artifact'].read_bytes()==results['basic-export-explicit-R']['artifact'].read_bytes(),
                    'explicit/default/wrapper/restored RBC differs')
            require((results['basic-native']['stdout'],results['basic-native']['stderr'])==
                (results['restored-native']['stdout'],results['restored-native']['stderr']),'restored native diagnostics differ')
        finally:
            (FIXTURE/'basic.rs').write_bytes(original['basic.rs']);(FIXTURE/'test_export.rs').write_bytes(original['test_export.rs'])
            for name,data in original.items():require((FIXTURE/name).read_bytes()==data,'fixture restoration failed')
        m.owned.write(self.work/'application-results.json',dict(children=observed,raw_diagnostic_parity=True,
            bytecode_parity=True,source_restored=True,guest_executions=0))
        return observed


    def run(self):
        self.sources(); self.metadata_receipts(); self.check_build(); self.barrier(full=True)
        snapshots = WORK / 'source-snapshots'; snapshots.mkdir(); retained = {}
        for path, expected in (self.frozen['files'] | {str(HERE / 'inputs.json'): self.args.inputs_sha256}).items():
            target = snapshots / expected
            if not target.exists():
                self.comp.write_new(target, Path(path).read_bytes(), lambda: m.owned.disk(OWNER, 9))
            require(sha(target) == expected, 'frontend source snapshot differs')
            retained[path] = dict(path=str(target), sha256=expected)
        m.owned.write(WORK / 'source-snapshots.json', retained)
        self.checkout(); m.readmit.Stage.source_guard(self)
        self.tool_closures()
        observations = self.applications(self.build_plan)
        m.readmit.Stage.source_guard(self); self.checkout()
        self.barrier(full=True); self.sources()
        require(len(self.record['commands']) == len(self.build_plan['children']) == 40
                and len(observations) == 18, 'exact forty children and eighteen frontend controls required')
        self.record.update(status='passed', finished_at=time.time(), source_unchanged=True, source_restored=True,
            D_B2_R_unchanged=True, adopted_VM_unchanged=True, frontend_qualified=True,
            guest_execution=False, application_qualified=False, publication=False, benchmark=False,
            tool_closures_sha256=sha(WORK / 'tool-closures.json'),
            frontend_results_sha256=sha(WORK / 'application-results.json'), free_bytes_after=m.owned.disk(OWNER))
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
    require(sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd() == OWNER, 'fixed frontend Python -B/cwd required')
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--inputs-sha256', required=True)
    Frontend(parser.parse_args()).execute()


if __name__ == '__main__':
    main()
