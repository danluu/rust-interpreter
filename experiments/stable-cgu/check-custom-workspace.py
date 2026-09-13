#!/usr/bin/env python3
"""Check the workspace with an installed custom toolset's compiler and profile."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_custom_tools import source_identity
from compare_saved_runtime import acquire_lock, lock_wait_seconds
from custom_compiler import digest, file_digest, load_compiler, require, validate_tool_compiler
from interpreter import CURRENT_TOOL_BINARIES, installed_tools
from workflow_io import capture, require_space, write_json

LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')


def command_for(cargo, target):
    return [cargo, 'test', '--workspace', '--release', '--locked', '--offline',
            '--jobs', '2', '--target-dir', str(target)]


def validate_cargo_file(cargo):
    require(file_digest(Path(cargo['executable'])) == cargo['sha256'],
            'workspace Cargo executable changed')


def test_results(returncode, stdout):
    tests = [dict(passed=int(a), failed=int(b), ignored=int(c)) for a, b, c in re.findall(
        r'test result: .*? (\d+) passed; (\d+) failed; (\d+) ignored;', stdout)]
    require(returncode == 0 and tests and sum(t['passed'] for t in tests) > 0
            and all(t['failed'] == 0 for t in tests), 'workspace tests failed or reported no passing tests')
    return dict(passed=sum(t['passed'] for t in tests), ignored=sum(t['ignored'] for t in tests), tests=tests)


def source_files():
    paths = [ROOT / p for p in ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml']]
    paths += [p for p in (ROOT / 'crates').rglob('*')
              if p.is_file() and (p.suffix == '.rs' or p.name == 'Cargo.toml')]
    paths += list((ROOT / 'scripts').glob('*.py')) + [Path(__file__).resolve()]
    configuration = ROOT / '.cargo'
    require(not configuration.is_symlink(), 'repository Cargo configuration directory is indirect')
    if configuration.exists():
        require(configuration.is_dir(), 'repository .cargo is not a directory')
        for path in configuration.rglob('*'):
            require(not path.is_symlink() and (path.is_file() or path.is_dir()),
                    'repository Cargo configuration has an indirect or unsupported entry')
            if path.is_file():
                paths.append(path)
    result = {str(p.relative_to(ROOT)): file_digest(p) for p in sorted(set(paths))}
    # Adding either discovered config after admission must invalidate the
    # snapshot too. Other .cargo files (including local includes) are inventoried.
    for name in ['.cargo/config', '.cargo/config.toml']:
        require(not (ROOT / name).exists() or (ROOT / name).is_file(),
                'repository Cargo discovery path is not a file')
        result.setdefault(name, None)
    return result


def test_environment(compiler, environment):
    # Match build_custom_tools' ordinary release environment; the two explicit
    # additions select matching doctests and bound test execution concurrency.
    compiler.environment(environment)
    require(not any(name in environment for name in
                    ['RUSTDOC', 'RUSTDOCFLAGS', 'CARGO_ENCODED_RUSTDOCFLAGS']),
            'do not inherit a different doctest compiler or doctest flags')
    env = {k: v for k, v in environment.items()
           if not k.startswith(('RUST_INTERP_', 'CARGO_PROFILE_'))
           and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                         'RUSTC_WORKSPACE_WRAPPER', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET',
                         'CARGO_INCREMENTAL']}
    env.update(CARGO_TERM_COLOR='never', RUSTC_WRAPPER='', RUSTC_WORKSPACE_WRAPPER='',
               RUSTDOC=str(compiler.sysroot / 'bin/rustdoc'), RUST_TEST_THREADS='2')
    return compiler.environment(env)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler-key', required=True)
    parser.add_argument('--tool-key', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--workload-lock', type=Path, required=True)
    parser.add_argument('--lock-wait-seconds', type=lock_wait_seconds, default=600)
    args = parser.parse_args()
    require(__debug__ and re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', args.run_id), 'invalid check run')
    require(args.workload_lock == LOCK and LOCK.resolve(strict=True) == LOCK and LOCK.is_file(),
            'supply the existing canonical campaign lock')
    work = ROOT / '.work' / args.run_id
    work.mkdir(exist_ok=False)
    rows = []
    result = dict(status='waiting', owner=str(ROOT), pid=os.getpid(), parent_pid=os.getppid(),
        started_at=time.time(), benchmark=False, lock=str(LOCK), lock_wait_seconds=args.lock_wait_seconds)
    write_json(work / 'result.json', result)
    try:
        with LOCK.open('r+') as lock:
            acquire_lock(lock, args.lock_wait_seconds)
            result.update(status='admitted', admitted_at=time.time())
            write_json(work / 'result.json', result)
            compiler = load_compiler(ROOT, args.compiler_key)
            tools, key = installed_tools(args.tool_key)
            validate_tool_compiler(tools, key, compiler)
            composition = json.loads((tools / 'compiler.json').read_text())
            require(composition['source_files'] == source_identity(), 'tool Rust sources differ from current source')
            settings = composition['settings']
            require(all(settings.get(k) == v for k, v in dict(profile='release', jobs=2,
                locked=True, offline=True, extra_features=[], profile_overrides={}, rustflags=None).items()),
                'toolset was built with another profile or flags')
            target = ROOT / '.work/custom-interpreter-build' / compiler.key
            require(target.resolve(strict=True) == target and target.is_dir(), 'missing owned custom tool target')
            binaries = composition['binaries']
            require(set(binaries) == set(CURRENT_TOOL_BINARIES), 'tool binary set differs')
            rustdoc = compiler.sysroot / 'bin/rustdoc'
            require(compiler.identity['files'].get('bin/rustdoc') == file_digest(rustdoc)
                    and os.access(rustdoc, os.X_OK), 'complete matching rustdoc is required for workspace doctests')
            env = test_environment(compiler, os.environ)
            frozen = source_files()
            for name, expected in frozen.items():
                if expected is None:
                    continue
                destination = work / 'source' / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((ROOT / name).read_bytes())
            cargo = composition['cargo']

            def guard():
                require(load_compiler(ROOT, compiler.key) == compiler, 'installed compiler changed')
                installed_tools(key)
                require(source_files() == frozen, 'workspace source changed')
                validate_cargo_file(cargo)
                require(all(file_digest(target / 'release' / name) == h for name, h in binaries.items()),
                        'custom target tool binaries differ from the installed toolset')

            def invoke(label, command):
                guard()
                require_space(ROOT, 8)
                child, stdout, stderr = capture(command, cwd=ROOT, env=env,
                    receipt_path=work / (label + '-process.json'), receipt=dict(label=label))
                (work / (label + '.stdout')).write_text(stdout)
                (work / (label + '.stderr')).write_text(stderr)
                row = dict(label=label, command=command, returncode=child.returncode,
                    stdout_sha256=file_digest(work / (label + '.stdout')),
                    stderr_sha256=file_digest(work / (label + '.stderr')))
                rows.append(row)
                write_json(work / 'commands.json', rows)
                guard()
                return child.returncode, stdout, stderr

            command = command_for(cargo['executable'], target)
            write_json(work / 'plan.json', dict(owner=str(ROOT), compiler_key=compiler.key, tool_key=key,
                compiler=compiler.identity['compiler'], compiler_provenance=compiler.identity['provenance'],
                tool_composition=composition, command=command, source_files=frozen, target=str(target),
                environment_sha256=digest(env), selected_environment={k: env[k] for k in
                    ['RUSTC', 'RUSTDOC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'PATH', 'RUST_TEST_THREADS']},
                benchmark=False, qualification='custom compiler full workspace release tests'))
            code, version, _ = invoke('cargo-version', [cargo['executable'], '-Vv'])
            require(code == 0 and version == cargo['version'], 'matching Cargo version changed')
            code, version, _ = invoke('rustdoc-version', [str(rustdoc), '-vV'])
            commit = compiler.identity['provenance']['source_commit']
            require(code == 0 and re.findall(r'^commit-hash: (.+)$', version, re.MULTILINE) == [commit],
                    'doctest compiler commit differs')
            code, stdout, _ = invoke('workspace-tests', command)
            counts = test_results(code, stdout)
            require(all((not (work / 'source' / name).exists()) if h is None else
                        file_digest(work / 'source' / name) == h for name, h in frozen.items()),
                    'archived source differs')
            result.update(status='passed', finished_at=time.time(), compiler_key=compiler.key, tool_key=key,
                returncode=code, frozen_sources_unchanged=True, **counts,
                plan_sha256=file_digest(work / 'plan.json'), commands_sha256=file_digest(work / 'commands.json'),
                evidence_files={str(p.relative_to(work)): file_digest(p) for p in sorted(work.rglob('*'))
                                if p.is_file() and p != work / 'result.json'})
            write_json(work / 'result.json', result)
            print(json.dumps(dict(status='passed', compiler_key=compiler.key, tool_key=key,
                                  passed=counts['passed'], ignored=counts['ignored'], benchmark=False)))
    except BaseException as error:
        result.update(status='failed', finished_at=time.time(), error=repr(error), completed_commands=len(rows))
        write_json(work / 'result.json', result)
        raise


if __name__ == '__main__':
    main()
