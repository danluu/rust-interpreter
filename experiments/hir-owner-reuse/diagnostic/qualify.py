#!/usr/bin/env python3
"""Build only the public coverage driver and run its bounded native controls."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).resolve().parent.parent
PUBLIC = Path('/Users/danluu/.rustup/toolchains/nightly-2026-09-08-aarch64-apple-darwin')
COMMIT = 'cea272fa356e94bd2ee2cadf376630aa0683867a'
LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def require(value, message):
    if not value:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--helpers', type=Path, required=True)
    parser.add_argument('--compiler-inputs', type=Path, required=True)
    parser.add_argument('--compiler-libraries', type=Path, required=True)
    parser.add_argument('--lock-wait-seconds', type=float, default=600)
    args = parser.parse_args()
    require(args.run_id.replace('-', '').isalnum(), 'invalid run id')
    helpers = args.helpers.resolve(strict=True)
    initial_helpers = {str(p): sha(p) for p in helpers.glob("*.py")}
    sys.path.insert(0, str(helpers))
    from owned_stage import workload_lock, disk
    from workflow_io import capture, SourceEdit, write_json
    from custom_cargo_libraries import library_closure, library_state
    from toolchain_lookup import _stamp

    out = ROOT / '.work' / args.run_id
    out.mkdir(parents=True, exist_ok=False)
    logs = out/'logs'; logs.mkdir()
    snapshots = out/'source'; snapshots.mkdir()
    commands = []
    result = dict(status='waiting', pid=os.getpid(), parent_pid=os.getppid(), cwd=str(ROOT),
                  argv=sys.argv, started_at=time.time(), lock=str(LOCK), commands=commands,
                  benchmark=False, project_coverage=False)
    write_json(out/'result.json', result)
    print(json.dumps(dict(status='waiting', pid=os.getpid(), output=str(out))), flush=True)
    env = os.environ.copy()
    rejected = [key for key, value in env.items() if value and
                (key.startswith(('LD_', 'DYLD_', 'HIR_OWNER_COVERAGE_', 'HIR_COVERAGE_')) or
                 key in {'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTDOCFLAGS', 'RUSTC_LOG',
                         'RUSTC_BOOTSTRAP', 'RUSTC_FORCE_RUSTC_VERSION', 'RUSTC_OVERRIDE_VERSION_STRING',
                         'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER'})]
    relevant = {key: value for key, value in env.items() if key in
                {'PATH', 'HOME', 'LANG', 'LC_ALL', 'TERM', 'TMPDIR', 'SDKROOT', 'DEVELOPER_DIR',
                 'MACOSX_DEPLOYMENT_TARGET', 'RUSTUP_HOME', 'CARGO_HOME'}}
    original = None
    edit = None
    source_files = {}
    input_records = []
    closure = None
    tool = out/'hir-owner-coverage'

    def run(label, command, *, cwd=None, command_env=None, expected=0):
        disk(out)
        command = [str(v) for v in command]
        command_env = env if command_env is None else command_env
        receipt = {'label': label, 'relevant_environment': {key: value for key, value in command_env.items()
                   if key in relevant or key.startswith(('HIR_', 'RUSTC_'))},
                   'environment_sha256': hashlib.sha256(json.dumps(command_env, sort_keys=True).encode()).hexdigest()}
        child, stdout, stderr = capture(command, cwd=cwd or out, env=command_env,
                                        receipt_path=logs/f'{label}.process.json', receipt=receipt)
        (logs/f'{label}.stdout').write_text(stdout)
        (logs/f'{label}.stderr').write_text(stderr)
        record = dict(label=label, command=command, cwd=str(cwd or out), pid=child.pid,
                      returncode=child.returncode, stdout_sha256=sha(logs/f'{label}.stdout'),
                      stderr_sha256=sha(logs/f'{label}.stderr'))
        commands.append(record)
        write_json(out/'commands.json', commands)
        require(child.returncode == expected, f'{label}: exit {child.returncode}, expected {expected}')
        return stdout, stderr

    def current_inputs(rehash):
        for record in input_records:
            path = Path(record['path'])
            require(str(path.resolve(strict=True)) == record['resolved'], 'compiler input alias changed')
            require(_stamp(path) == record['stamp'], 'compiler input stamp changed: '+str(path))
            if rehash:
                require(sha(path) == record['sha256'], 'compiler input content changed: '+str(path))
        for name, expected in source_files.items():
            require(sha(Path(name)) == expected, 'frozen source changed: '+name)
        if closure is not None:
            require(library_state(closure['identity']) == closure['state'], 'public compiler loader state changed')

    try:
        require(not rejected, 'inherited compiler override environment: '+', '.join(sorted(rejected)))
        with workload_lock(LOCK, args.lock_wait_seconds) as fd:
            result.update(status='running', lock_acquired_at=time.time(), lock_fd=fd, free_bytes=disk(out))
            write_json(out/'result.json', result)
            print(json.dumps(dict(status='admitted', pid=os.getpid(), output=str(out))), flush=True)
            require(all(sha(Path(p)) == expected for p, expected in initial_helpers.items()),
                    'helper changed while waiting for admission')
            bound = json.loads((SOURCE/'diagnostic/source.json').read_text())
            for name, expected in bound['files'].items():
                require(sha(SOURCE/'diagnostic'/name) == expected, 'diagnostic source manifest differs: '+name)
            # Freeze every real source/include file under the bounded experiment,
            # excluding interpreter cache output; compile exclusively this copy.
            for path in sorted(SOURCE.rglob('*')):
                if not path.is_file() or '__pycache__' in path.parts:
                    continue
                require(not path.is_symlink(), 'source symlink is unsupported')
                dest = snapshots/path.relative_to(SOURCE)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, dest)
                source_files[str(path)] = sha(path)
                require(sha(dest) == source_files[str(path)], 'source copy differs')
            for path in sorted(helpers.glob('*.py')):
                source_files[str(path)] = sha(path)
                dest = out/'helpers'/path.name; dest.parent.mkdir(exist_ok=True)
                shutil.copyfile(path, dest)
            input_bytes = args.compiler_inputs.read_bytes()
            library_bytes = args.compiler_libraries.read_bytes()
            (out/'compiler-inputs.json').write_bytes(input_bytes)
            (out/'compiler-libraries.json').write_bytes(library_bytes)
            input_records = json.loads(input_bytes)['files']
            closure = json.loads(library_bytes)['subjects']['rustc']
            require(closure['executable']['path'] == str(PUBLIC/'bin/rustc'), 'wrong recorded compiler')
            require(all(Path(x['path']).is_relative_to(PUBLIC) for x in input_records), 'mixed compiler inventory')
            current_inputs(True)
            write_json(out/'plan.json', dict(source_files=source_files, public=str(PUBLIC), compiler_commit=COMMIT,
                compiler_inputs_sha256=sha(out/'compiler-inputs.json'),
                compiler_libraries_sha256=sha(out/'compiler-libraries.json'), env=relevant,
                runner_sha256=sha(Path(__file__)), source_snapshot=str(snapshots),
                states=['original', 'body-edit', 'unicode-edit', 'restored'],
                errors=['type_error', 'borrow_error', 'const_error', 'panic_error']))
            version, _ = run('public-version', [PUBLIC/'bin/rustc', '-vV'])
            require('commit-hash: '+COMMIT in version, 'unexpected public compiler commit')
            build_env = dict(env, HIR_COVERAGE_PUBLIC_SYSROOT=str(PUBLIC),
                             HIR_COVERAGE_PUBLIC_RUSTC=str(PUBLIC/'bin/rustc'))
            run('build-driver', [PUBLIC/'bin/rustc', snapshots/'diagnostic/main.rs', '--edition=2024',
                '--crate-name=hir_owner_coverage', '-Copt-level=3', '-Cdebuginfo=1', '-Ccodegen-units=1',
                '-L', 'native='+str(PUBLIC/'lib'), '-C', 'link-arg=-Wl,-rpath,'+str(PUBLIC/'lib'), '-o', tool],
                command_env=build_env)
            ordinal = 0
            def inspect(command, *, text):
                nonlocal ordinal
                require(text is True, 'unexpected library inspection mode')
                label=f'tool-loader-{ordinal:02}'; ordinal += 1
                return run(label, command)[0]
            identity, state = library_closure(tool, 'aarch64-apple-darwin', inspect=inspect)
            require(all(Path(x['resolved']).is_relative_to(PUBLIC) for x in identity['libraries']),
                    'diagnostic links outside the frozen public compiler')
            write_json(out/'driver.json', dict(path=str(tool), sha256=sha(tool), bytes=tool.stat().st_size,
                                             identity=identity, state=state))
            reports=out/'reports'; reports.mkdir()
            fixture=out/'fixture'; fixture.mkdir()
            source=fixture/'fixture.rs'
            original=(snapshots/'diagnostic/fixture.rs').read_bytes()
            source.write_bytes(original)
            (out/'states').mkdir()
            (out/'artifacts').mkdir()
            for arm in ('public', 'diagnostic'):
                (out/arm).mkdir()
            diag_env=dict(env, HIR_OWNER_COVERAGE_OUTPUT=str(reports))
            def compile_one(label, arm, extra=(), expected=0):
                before=set(reports.glob('*.json'))
                binary=out/arm/'fixture'
                cmd=[PUBLIC/'bin/rustc' if arm=='public' else tool, source, '--crate-name=hir_coverage_fixture',
                     '--edition=2024', '--error-format=json', '--sysroot='+str(PUBLIC), '-Copt-level=0',
                     '-Cdebuginfo=2', '-Ccodegen-units=1', '-Cincremental='+str(out/arm/'incremental'),
                     '-o', binary, *extra]
                stdout, stderr=run(label+'-'+arm, cmd, cwd=fixture,
                                   command_env=diag_env if arm=='diagnostic' else env, expected=expected)
                report=None
                if arm=='diagnostic':
                    new=set(reports.glob('*.json'))-before
                    require(len(new)==1, 'expected one separate compiler report')
                    path=new.pop(); report=json.loads(path.read_text())
                    require(report['compiler_argv'][1:]==[str(x) for x in cmd[1:]], 'report compiler argv mismatch')
                    require(not report['problems'], 'gate/visitor instrumentation disagreement')
                    write_json(out/'states'/f'{label}-report.json', dict(path=str(path), sha256=sha(path), report=report))
                if expected==0:
                    require(binary.is_file(), 'successful native compile did not emit binary')
                    shutil.copyfile(binary, out/'artifacts'/f'{label}-{arm}')
                return stdout, stderr, report
            def successful(label, payload):
                edit.replace(payload)
                (out/'states'/f'{label}.rs').write_bytes(payload)
                public=compile_one(label,'public')
                diagnostic=compile_one(label,'diagnostic')
                require(public[:2]==diagnostic[:2], 'successful raw compiler output differs: '+label)
                report=diagnostic[2]
                require(report['coverage_usable'], 'successful coverage is unusable: '+label)
                names={x['owner_name']:x for x in report['owners'] if x['owner_name']}
                require(names['anchor']['input_eligible'], 'ordinary scalar anchor was not accepted')
                for name in ('calls','generic','attributed','expands','main'):
                    require(not names[name]['input_eligible'], 'unsupported function accepted: '+name)
                require(report['counts']['impl-item']['input_eligible']==0, 'associated owner accepted')
                left=run(label+'-public-execute',[out/'public/fixture'],cwd=fixture)
                right=run(label+'-diagnostic-execute',[out/'diagnostic/fixture'],cwd=fixture)
                require(left==right, 'native output differs: '+label)
            with SourceEdit(source, original) as edit:
                successful('original',original)
                changed=original.replace(b'x + 1 }',b'x + 17017 }').replace(b'changed(5), 6',b'changed(5), 17022')
                require(changed!=original, 'body edit absent')
                successful('body-edit',changed)
                successful('unicode-edit','// earlier unequal-width Unicode edit: λ\n'.encode()+changed)
                successful('restored',original)
                for name, code in [('type_error','E0308'),('borrow_error','E0382'),
                                   ('const_error','E0080'),('panic_error','unconditional_panic')]:
                    public=compile_one(name,'public',('--cfg',name),1)
                    diagnostic=compile_one(name,'diagnostic',('--cfg',name),1)
                    require(public[:2]==diagnostic[:2] and code in public[1], 'raw diagnostics differ: '+name)
                    require(not diagnostic[2]['coverage_usable'], 'failed compile qualified coverage')
                    successful(name+'-restored',original)
                for name, extra in [('version',('-vV',)),('dep-info',('--emit=dep-info',))]:
                    before=set(reports.glob('*.json'))
                    cmd=[tool, *extra] if name=='version' else [tool,source,'--crate-name=hir_coverage_probe',
                        '--edition=2024','--sysroot='+str(PUBLIC),'--emit=dep-info','-o',out/'probe.d']
                    output=run('diagnostic-'+name,cmd,cwd=fixture,command_env=diag_env)
                    ordinary=run('ordinary-'+name,[PUBLIC/'bin/rustc',*cmd[1:]],cwd=fixture)
                    require(output==ordinary,'ordinary probe differs: '+name)
                    new=set(reports.glob('*.json'))-before
                    require(len(new)==1 and not json.loads(new.pop().read_text())['coverage_usable'],
                            'probe incorrectly qualified coverage')
            require(source.read_bytes()==original,'fixture source was not restored')
            current_inputs(True)
            require(library_state(identity)==state,'diagnostic loader state changed')
            require(sha(tool)==json.loads((out/'driver.json').read_text())['sha256'],'driver binary changed')
            result.update(status='passed', binary_sha256=sha(tool), source_restored=True,
                          completed_at=time.time(), commands=commands, compiler_inputs_unchanged=True)
            write_json(out/'result.json',result)
            print(json.dumps(dict(status='passed',commands=len(commands),binary_sha256=sha(tool))),flush=True)
    except BaseException as error:
        result.update(status='failed',error=repr(error),completed_at=time.time(),commands=commands)
        if original is not None:
            result['source_restored']=(out/'fixture/fixture.rs').read_bytes()==original
        write_json(out/'result.json',result)
        print(json.dumps(dict(status='failed',error=repr(error),commands=len(commands))),flush=True)
        raise


if __name__=='__main__':
    main()
