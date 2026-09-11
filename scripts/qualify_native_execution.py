#!/usr/bin/env python3
"""Run the existing full native differential validator on one immutable tool."""
import argparse
import ast
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from interpreter import ROOT, installed_tools
from audit_validation_counts import count_commands

OPTIONS = ['jit_native_calls', 'jit_native_call_stubs', 'jit_persistent_registers', 'jit_resumable_calls']


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def stage_validator(source, tool, flags):
    original = source.read_text()
    replacements = [
        ("ROOT = Path(__file__).resolve().parents[1]", 'ROOT = Path(' + repr(str(ROOT)) + ')'),
        ("BUILD = ROOT / '.work/interpreter-build/release'", 'BUILD = Path(' + repr(str(tool)) + ')'),
        ("(ROOT / 'results/interpreter-validation.json').write_text", "(work / 'summary.json').write_text"),
        ('        p = subprocess.run(list(map(str, command)),',
         "        if list(map(str, command[:3])) == [str(BUILD / 'rust-interp-vm'), '--engine', 'jit']:\n"
         '            command = [*command[:3], *' + repr(flags) + ', *command[3:]]\n'
         '        p = subprocess.run(list(map(str, command)),'),
    ]
    text = original
    for old, new in replacements:
        require(text.count(old) == 1, 'validator staging anchor changed')
        text = text.replace(old, new)
    def assertions(code):
        return [ast.dump(n, include_attributes=False) for n in ast.walk(ast.parse(code)) if isinstance(n, ast.Assert)]
    require(assertions(text) == assertions(original), 'validator assertions changed')
    compile(text, 'staged-validator', 'exec')
    return text, replacements


def verify_vm_options(path, tool, options, require_statistics=False):
    counts = dict(jit=0, interpreter=0, default_rejection=0)
    statistics = dict(resumable_calls=0, resumable_returns=0, maximum_generated_bytes=0,
                      executions_with_declines=0)
    with path.open() as rows:
        for line in rows:
            row = json.loads(line)
            command = row['command']
            if Path(command[0]).name != 'rust-interp-vm':
                continue
            require(command[0] == str(tool / 'rust-interp-vm'), 'validator used another VM')
            engine = command[command.index('--engine') + 1] if '--engine' in command else 'default_rejection'
            require(engine in counts, 'unknown captured engine')
            counts[engine] += 1
            for option, enabled in options.items():
                flag = '--' + option.replace('_', '-')
                require(command.count(flag) == int(engine == 'jit' and enabled), 'captured VM option differs')
            if engine == 'jit' and row['returncode'] == 0:
                stats = {k: int(v) for k, v in re.findall(r'\b([a-z_]+)=(\d+)\b', row['stderr'])}
                if require_statistics:
                    require('instructions' in stats and 'jit_entries' in stats, 'missing successful JIT statistics')
                statistics['resumable_calls'] += stats.get('jit_resumable_calls', 0)
                statistics['resumable_returns'] += stats.get('jit_resumable_returns', 0)
                statistics['maximum_generated_bytes'] = max(statistics['maximum_generated_bytes'], stats.get('jit_bytes', 0))
                statistics['executions_with_declines'] += int(stats.get('jit_declined_functions', 0) > 0)
    require(counts['jit'] == counts['interpreter'] == 11119 and counts['default_rejection'] == 1,
            'full validator VM command count changed')
    if require_statistics and options['jit_resumable_calls']:
        require(statistics['resumable_calls'] > 0 and statistics['resumable_returns'] > 0,
                'resumable transitions did not execute')
    return dict(counts=counts, statistics=statistics)


def verify_binary_provenance(rows, tool, binaries, inputs):
    """Match recorded input hashes to binaries actually invoked by the validator.

    The direct validator does not use the Cargo wrapper. The enclosing run
    still checks every installed binary before and after each validation mode.
    """
    invoked = {}
    known = {'rust-interp-vm', 'rust-interp-mir-export', 'rust-interp-rustc-wrapper'}
    for row in rows:
        executable = Path(row['command'][0])
        if executable.parent != tool and executable.name not in known:
            continue
        require(executable.name in binaries and executable == tool / executable.name,
                'validator invoked an unexpected tool binary')
        invoked[executable.name] = invoked.get(executable.name, 0) + 1
    require({'rust-interp-vm', 'rust-interp-mir-export'} <= set(invoked),
            'validator did not invoke both required binaries')
    captured = {Path(path).name: digest for path, digest in inputs.items()
                if Path(path).parent == tool.relative_to(ROOT)}
    require(set(captured) == set(invoked), 'recorded tool inputs differ from invoked binaries')
    require(all(captured[name] == binaries[name] for name in invoked),
            'validator binary provenance differs')
    return dict(directly_invoked_binaries=captured, direct_invocation_counts=invoked,
                other_installed_binaries={name: digest for name, digest in binaries.items()
                                          if name not in invoked})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--tool-key', required=True)
    parser.add_argument('--wait-for-lock', type=int, default=600)
    for option in OPTIONS:
        parser.add_argument('--' + option.replace('_', '-'), action='store_true')
    args = parser.parse_args()
    if not __debug__ or sys.flags.optimize:
        parser.error('the full validator requires enabled Python assertions')
    if Path(args.run_id).name != args.run_id or args.run_id in ['.', '..']:
        parser.error('invalid run ID')
    if not 0 <= args.wait_for_lock <= 3600:
        parser.error('invalid lock wait')
    options = {key: getattr(args, key) for key in OPTIONS}
    if args.jit_native_call_stubs and not args.jit_native_calls:
        parser.error('native stubs require native calls')
    if args.jit_resumable_calls and (args.jit_native_calls or args.jit_native_call_stubs):
        parser.error('resumable calls exclude native tree/stub calls')
    work = ROOT / '.work' / args.run_id
    work.mkdir(exist_ok=False)
    status = dict(status='waiting for benchmark lock', pid=os.getpid(), parent_pid=os.getppid(),
                  cwd=str(ROOT), started_at=time.time())
    receipt = work / 'status.json'
    write(receipt, status)
    lock = (ROOT / '.work/benchmark.lock').open('a')
    deadline = time.monotonic() + args.wait_for_lock
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            require(time.monotonic() < deadline, 'benchmark lock unavailable')
            time.sleep(1)
    tool, key = installed_tools(args.tool_key)
    binaries = json.loads((tool / 'ready.json').read_text())
    source = ROOT / 'scripts/validate_interpreter.py'
    flags = ['--' + k.replace('_', '-') for k, v in options.items() if v]
    text, substitutions = stage_validator(source, tool, flags)
    script = work / 'validate_selected_tool.py'
    script.write_text(text)
    paths = [Path(__file__), source, script, ROOT / 'scripts/interpreter.py', ROOT / 'scripts/std_mir.py',
             ROOT / 'scripts/audit_validation_counts.py', ROOT / 'Cargo.toml', ROOT / 'Cargo.lock',
             ROOT / 'rust-toolchain.toml', *sorted((ROOT / 'tests').glob('*.rs')),
             *sorted((ROOT / 'crates').rglob('*.rs'))]
    frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    write(work / 'plan.json', dict(tool_key=key, binaries=binaries, options=options,
        modes=['default', 'inline'], substitutions=substitutions, assertions_unchanged=True,
        frozen=frozen, expected_commands_per_mode=23502, performance_measurement=False))

    def verify():
        require(all(sha(ROOT / p) == digest for p, digest in frozen.items()), 'frozen validator input changed')
        require(all(sha(tool / p) == digest for p, digest in binaries.items()), 'installed tool changed')

    env = os.environ.copy()
    for name in list(env):
        if name.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_')) or name in [
            'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
            'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET', 'PYTHONOPTIMIZE']:
            env.pop(name)
    env['PYTHONPATH'] = str(ROOT / 'scripts')
    env['RUST_INTERP_VM_STATS'] = '1'
    runs = {}
    try:
        for mode in ['default', 'inline']:
            verify()
            for field in ['child_pid', 'child_returncode', 'child_started_at', 'child_finished_at', 'command']:
                status.pop(field, None)
            command = [sys.executable, str(script)]
            with (work / (mode + '.log')).open('x') as output:
                child = subprocess.Popen(command, cwd=ROOT, env=env | (
                    {'RUST_INTERP_INLINE_LEAVES': '1'} if mode == 'inline' else {}),
                    stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT)
                status.update(status='running', mode=mode, child_pid=child.pid,
                              command=command, child_started_at=time.time())
                write(receipt, status)
                print('START', mode, child.pid, flush=True)
                code = child.wait()
            status.update(child_returncode=code, child_finished_at=time.time())
            write(receipt, status)
            require(code == 0, 'native differential validator failed; log preserved')
            detail = json.loads((work / (mode + '.log')).read_text())
            folder = (ROOT / detail['raw']).resolve()
            require(folder.is_relative_to(ROOT / '.work'), 'unexpected validator archive')
            commands = folder / 'commands.jsonl'
            digest = sha(commands)
            counts = count_commands(commands, folder)
            require(counts['commands'] == detail['completed_commands'] == 23502, 'incomplete validator run')
            selected = verify_vm_options(commands, tool, options, require_statistics=True)
            with commands.open() as rows:
                provenance = verify_binary_provenance((json.loads(line) for line in rows),
                    tool, binaries, detail['inputs_sha256'])
            require(sha(commands) == digest, 'validator archive changed')
            runs[mode] = dict(detail=detail, classification=counts, vm_options_verified=selected,
                              binary_provenance=provenance, commands_sha256=digest)
            write(work / 'completed.json', runs)
            verify()
            print('PASS', mode, counts['commands'], flush=True)
        out = ROOT / 'results' / args.run_id
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', dict(status='passed', tool_key=key, binaries=binaries, options=options,
            runs=runs, commands=sum(r['classification']['commands'] for r in runs.values()), frozen=frozen,
            assertions_unchanged=True, performance_measurement=False,
            scope='Full existing native differential and rejection validator, two inlining modes. Commands include builds, exports and executions; they are not unique cases. No new FFI, unwind or thread support is implied.'))
        status.update(status='finished', returncode=0, finished_at=time.time())
        write(receipt, status)
    except Exception as error:
        status.update(status='failed', error=str(error), finished_at=time.time())
        write(receipt, status)
        raise


if __name__ == '__main__':
    main()
