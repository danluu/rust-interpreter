#!/usr/bin/env python3
"""Check only fixture behavior with the unchanged owned Cmono compiler.

This never enables the proposed index, records no latency result, and cannot
qualify a patched compiler. It catches mistakes in the future native controls.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
COMPILER = 'f9fb3e5f59b8567fffd32c936a9864d0baee77038574236710fbcec75a57d33f'
BASE = '58e1e1f5311f4424ea81def4763081f6da62d9b3'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler-owner', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--lock-wait-seconds', type=float, default=600)
    args = parser.parse_args()
    if not re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', args.run_id):
        raise ValueError('invalid run id')
    if not 0 < args.lock_wait_seconds <= 600:
        raise ValueError('lock admission must be bounded by 600 seconds')
    owner = args.compiler_owner.resolve(strict=True)
    sys.path[:0] = [str(owner/'scripts'), str(owner/'experiments/stable-cgu')]
    from custom_compiler import digest, file_digest, load_compiler, require
    from owned_stage import workload_lock
    from workflow_io import capture, require_space, SourceEdit, write_json

    out = ROOT/'.work'/args.run_id
    out.mkdir(parents=True, exist_ok=False)
    logs = out/'logs'; logs.mkdir()
    state_sources = out/'state-sources'; state_sources.mkdir()
    frozen = {str(p): file_digest(p) for p in (owner/'scripts').glob('*.py')}
    for path in [owner/'experiments/stable-cgu/owned_stage.py', Path(__file__),
                 HERE/'external.rs', HERE/'main.rs']:
        frozen[str(path)] = file_digest(path)
    result = dict(status='waiting', pid=os.getpid(), parent_pid=os.getppid(),
        started_at=time.time(), cwd=str(ROOT), argv=sys.argv, lock=str(LOCK),
        fixture_validation_only=True, benchmark=False, index_enabled=False,
        patched_compiler_qualified=False, source_files=frozen)
    rows = []
    write_json(out/'result.json', result)
    compiler = None
    ready_bytes = None
    source = out/'main.rs'
    original = (HERE/'main.rs').read_bytes()
    environment = os.environ.copy()
    override = {'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'RUSTFLAGS',
        'CARGO_ENCODED_RUSTFLAGS', 'RUST_SYSROOT', 'RUSTC_BOOTSTRAP', 'RUSTC_LOG',
        'RUSTC_FORCE_RUSTC_VERSION', 'RUSTC_OVERRIDE_VERSION_STRING'}
    rejected = sorted(k for k, v in environment.items()
        if k.startswith(('LD_', 'DYLD_')) or (k in override and v))

    def guard(rehash=False):
        require(all(file_digest(Path(p)) == h for p, h in frozen.items()), 'fixture/helper source changed')
        if (out/'external.rs').exists():
            require(file_digest(out/'external.rs') == frozen[str(HERE/'external.rs')],
                    'copied external source changed')
        if compiler is not None:
            require(load_compiler(owner, COMPILER) == compiler, 'compiler installation changed')
            require((owner/'.work/compilers'/COMPILER/'ready.json').read_bytes() == ready_bytes,
                    'compiler readiness changed')
            if rehash:
                require(all(file_digest(compiler.sysroot/p) == h for p, h in compiler.identity['files'].items()),
                        'complete compiler file bytes changed')

    def run(label, command, expected=0):
        guard()
        require_space(out, 8)
        command = list(map(str, command))
        child, stdout, stderr = capture(command, cwd=out, env=environment,
            receipt_path=logs/f'{len(rows):03d}-{label}.process.json',
            receipt=dict(label=label, environment_sha256=digest(environment)))
        stem = logs/f'{len(rows):03d}-{label}'
        Path(str(stem)+'.stdout').write_text(stdout)
        Path(str(stem)+'.stderr').write_text(stderr)
        row = dict(label=label, command=command, pid=child.pid, returncode=child.returncode,
            stdout_sha256=hashlib.sha256(stdout.encode()).hexdigest(),
            stderr_sha256=hashlib.sha256(stderr.encode()).hexdigest(),
            source_sha256=file_digest(source))
        rows.append(row); write_json(out/'commands.json', rows)
        require(child.returncode == expected, f'{label}: unexpected return status')
        guard()
        return stdout, stderr

    try:
        require(not rejected, 'inherited compiler overrides: '+', '.join(rejected))
        with workload_lock(LOCK, args.lock_wait_seconds):
            result.update(status='running', admitted_at=time.time())
            write_json(out/'result.json', result)
            compiler = load_compiler(owner, COMPILER)
            ready_bytes = (owner/'.work/compilers'/COMPILER/'ready.json').read_bytes()
            require(compiler.identity['provenance']['source_commit'] == BASE, 'wrong compiler source')
            environment = compiler.environment(environment)
            guard(True)
            for name in ['main.rs', 'external.rs']:
                shutil.copyfile(HERE/name, out/name)
            (out/'compiler-ready.json').write_bytes(ready_bytes)
            snapshots = out/'frozen-inputs'; snapshots.mkdir()
            for index, (path, expected) in enumerate(frozen.items()):
                payload = Path(path).read_bytes()
                require(hashlib.sha256(payload).hexdigest() == expected, 'snapshot source changed')
                (snapshots/f'{index:03d}-{Path(path).name}').write_bytes(payload)
            flags = [compiler.rustc, '--sysroot', compiler.sysroot, '--edition=2021',
                '-Zunstable-options', '--jobs-backend=2', '-Ccodegen-units=2', '-Cdebuginfo=0',
                '-Zstable-cgu-partitioning=no', '-Zstable-mono-cgu-partitioning=no',
                '--error-format=json']
            run('compiler-version', [compiler.rustc, '-vV'])
            run('external', [*flags, out/'external.rs', '--crate-name=external', '--crate-type=rlib',
                            '-o', out/'libexternal.rlib'])
            external_hash = file_digest(out/'libexternal.rlib')
            binary = out/'native'
            states = []

            def check(label, cfg=(), value='448\n', code=None, warning=None):
                require(file_digest(out/'libexternal.rlib') == external_hash, 'external library changed')
                (state_sources/(label+'.rs')).write_bytes(source.read_bytes())
                args = [*flags, source, '--crate-name=index_fixture', '--extern',
                    'external='+str(out/'libexternal.rlib'), '-Cincremental='+str(out/'incremental'), '-o', binary]
                for item in cfg:
                    args += ['--cfg', item]
                _, stderr = run(label, args, 1 if code else 0)
                diagnostics = [json.loads(line) for line in stderr.splitlines()]
                if code:
                    require(any(d.get('code') and d['code']['code'] == code for d in diagnostics),
                            'required uncalled diagnostic missing: '+code)
                else:
                    binary_hash = file_digest(binary)
                    stdout, runtime_stderr = run(label+'-execute', [binary])
                    require(stdout == value and not runtime_stderr, 'native fixture output differs')
                    require(file_digest(binary) == binary_hash, 'native binary changed during execution')
                    if warning:
                        require(any(d.get('level') == 'warning' and d.get('code')
                            and d['code']['code'] == warning for d in diagnostics), 'required warning missing')
                states.append(dict(label=label, cfg=list(cfg), expected_code=code,
                    expected_stdout=None if code else value, expected_warning=warning,
                    binary_sha256=None if code else binary_hash,
                    source_sha256=file_digest(source)))
                write_json(out/'states.json', states)

            with SourceEdit(source, original) as edit:
                check('original')
                before = b'use external::reexport::nested::Selected;'
                require(original.count(before) == 1, 'import edit anchor differs')
                edit.replace(original.replace(before, b'use external::right::Select as Selected;', 1))
                check('import-edited', value='800\n')
                edit.replace(original); check('import-restored')
                edit.replace(original.replace(b'fn select(', '// Unicode source shift: λ🦀\nfn select('.encode(), 1))
                check('unicode-shifted')
                edit.replace(original); check('unicode-restored')
                check('cfg-right', ('select_right',), value='800\n')
                check('cfg-right-unused', ('select_right', 'unused_import'), value='800\n', warning='unused_imports')
                check('cfg-restored')
                for cfg, code in [('missing_method','E0599'), ('ambiguous','E0034'),
                    ('type_error','E0308'), ('borrow_error','E0382'), ('const_error','E0080')]:
                    check(cfg, (cfg,), code=code)
                    check(cfg+'-restored')
            require(source.read_bytes() == original, 'fixture source not restored')
            guard(True)
            result.update(status='passed', finished_at=time.time(), commands=len(rows),
                states=len(states), source_restored=True, compiler_unchanged=True,
                external_sha256=external_hash)
            write_json(out/'result.json', result)
    except BaseException as error:
        result.update(status='failed', finished_at=time.time(), commands=len(rows), error=repr(error))
        write_json(out/'result.json', result)
        raise


if __name__ == '__main__':
    main()
