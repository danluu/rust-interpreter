#!/usr/bin/env python3
"""Prepare owned Cargo/std inputs and emit a separate 27-command screen plan."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, lock_wait_seconds
from custom_cargo import install_qualified_cargo, load_cargo, validate_matched_pair
from custom_compiler import validate_tool_compiler
from interpreter import TOOLCHAIN, installed_tools, require_export_option
from std_mir import FLAGS, POLICY
from workflow_io import capture, require_space, write_json


def require(condition, message):
    if not condition:raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def std_path(cargo):
    binding = cargo.identity['pinned_compiler']
    identity = dict(policy=POLICY, compiler=binding['compiler'], target=binding['host'], flags=FLAGS,
        lock_sha256=sha(Path(binding['sysroot']) / 'lib/rustlib/src/rust/library/Cargo.lock'), cargo=cargo.receipt())
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return ROOT / '.work/std-mir' / key / 'ready.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--screen-run-id', required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--qualified-report', type=Path, required=True)
    parser.add_argument('--tool-key', required=True)
    parser.add_argument('--lock-wait-seconds', type=lock_wait_seconds, default=45)
    args = parser.parse_args()
    require(all(re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', value)
                for value in [args.run_id, args.screen_run_id]) and args.run_id != args.screen_run_id,
            'invalid or duplicate run IDs')
    require(not (ROOT / '.work' / args.screen_run_id).exists(), 'screen history already exists')
    work = ROOT / '.work' / args.run_id; work.mkdir(exist_ok=False)
    screen_path = ROOT / 'benchmarks/experiments/strict-warm-build/screen.py'
    spec = importlib.util.spec_from_file_location('cargo_setup_screen', screen_path)
    screen = importlib.util.module_from_spec(spec); spec.loader.exec_module(screen)
    summary = dict(status='waiting', owner=str(ROOT), started_at=time.time(), supervisor_pid=os.getpid(),
                   performance_measurement=False, commands=[], expected_cache_growth_gib=8,
                   minimum_free_gib=8, screen_started=False)
    write_json(work / 'summary.json', summary)
    try:
        with (ROOT / '.work/benchmark.lock').open('a') as lock:
            acquire_lock(lock, args.lock_wait_seconds)
            # Reserve the projected screen growth above the ordinary 8GiB floor.
            require_space(ROOT, 16)
            env = screen.environment()
            revision, marker, changed, original = screen.validate_source(args.source.absolute())
            tools, key = installed_tools(args.tool_key)
            validate_tool_compiler(tools, key, None)
            for option in ['entry-catalog', 'function-cache-auto', 'inline-leaves',
                           'trap-unsupported-calls', 'run-try-callbacks']:
                require_export_option(tools, key, option)
            frozen = {str(p): sha(p) for p in [Path(__file__), screen_path, *sorted((ROOT / 'scripts').glob('*.py'))]}
            summary.update(status='running', lock_acquired_at=time.time(), source=str(args.source.absolute()),
                           source_revision=revision, original_source_sha256=hashlib.sha256(original).hexdigest(),
                           harness=frozen, tools=key)
            write_json(work / 'summary.json', summary)
            cargos = [install_qualified_cargo(ROOT, args.qualified_report.resolve(strict=True), mode, TOOLCHAIN)
                      for mode in ['stock', 'candidate']]
            summary['cargo_comparison'] = validate_matched_pair(*cargos)
            stds = []
            for mode, cargo in zip(['baseline', 'candidate'], cargos):
                cargo.environment(env, TOOLCHAIN)
                ready = std_path(cargo)
                initial = 'ready' if ready.exists() else 'partial' if ready.parent.exists() else 'absent'
                require(initial != 'partial', 'incomplete std setup requires explicit recovery: ' + str(ready.parent))
                require(all(sha(Path(p)) == digest for p, digest in frozen.items()), 'setup harness changed')
                command = [sys.executable, str(ROOT / 'scripts/std_mir.py'), '--cargo-key', cargo.key]
                child, out, err = capture(command, cwd=ROOT, env=env,
                    receipt_path=work / (mode + '-std-process.json'),
                    receipt=dict(phase='std-setup', mode=mode, cargo_key=cargo.key, initial_namespace=initial))
                (work / (mode + '.stdout')).write_text(out); (work / (mode + '.stderr')).write_text(err)
                summary['commands'].append(dict(command=command, pid=child.pid, returncode=child.returncode,
                    cargo=cargo.receipt(), initial_namespace=initial, stdout_sha256=hashlib.sha256(out.encode()).hexdigest(),
                    stderr_sha256=hashlib.sha256(err.encode()).hexdigest()))
                write_json(work / 'summary.json', summary)
                require(child.returncode == 0, 'std setup failed; see retained output')
                stds.append(screen.validate_std_ready(ready, env, cargo=cargo))
                require(load_cargo(ROOT, cargo.key) == cargo, 'Cargo changed during std setup')
                require_space(ROOT, 16)
            require(all(sha(Path(p)) == digest for p, digest in frozen.items()), 'setup harness changed')
            require(screen.validate_source(args.source.absolute())[0] == revision, 'project source changed')
            command = [sys.executable, str(screen_path), '--run-id', args.screen_run_id,
                '--source', str(args.source.absolute()), '--candidate-policy', 'cargo-info-cache',
                '--baseline-tool-key', key, '--candidate-tool-key', key,
                '--baseline-cargo-key', cargos[0].key, '--candidate-cargo-key', cargos[1].key,
                '--std-mir-ready', stds[0]['path'], '--candidate-std-mir-ready', stds[1]['path'],
                '--lock-wait-seconds', str(args.lock_wait_seconds)]
            write_json(work / 'screen-command.json', command)
            summary.update(status='passed', std_mir_by_mode=dict(baseline=stds[0], candidate=stds[1], duplicate=stds[0]),
                           screen_command=command, source_restored=True)
    except BaseException as error:
        summary.update(status='failed', error_type=type(error).__name__, error=str(error))
        raise
    finally:
        summary['finished_at'] = time.time(); write_json(work / 'summary.json', summary)
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
