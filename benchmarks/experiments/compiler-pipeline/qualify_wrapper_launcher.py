#!/usr/bin/env python3
"""Run the original launcher regression suite with immutable tools and output."""
import argparse
import ast
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from interpreter import installed_tools
from workflow_io import capture, require_space, write_json


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assertions(source):
    return [ast.dump(n, include_attributes=False) for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Assert)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--tool-key', required=True)
    parser.add_argument('--legacy-tool-key', required=True)
    args = parser.parse_args()
    require(not sys.flags.optimize, 'assertions must be enabled')
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['.', '..'], 'invalid run ID')
    lock = (ROOT / '.work/benchmark.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    require_space(ROOT / '.work', 8)
    tool, key = installed_tools(args.tool_key)
    legacy, legacy_key = installed_tools(args.legacy_tool_key)
    manifest = json.loads((tool / 'ready.json').read_text())
    legacy_manifest = json.loads((legacy / 'ready.json').read_text())
    require('rust-interp-rustc-wrapper' in manifest and 'rust-interp-rustc-wrapper' not in legacy_manifest,
            'expected new wrapper versus a historical tool')
    raw = ROOT / '.work/runs' / args.run_id
    out = ROOT / 'results' / args.run_id
    require(not raw.exists() and not out.exists(), 'run already exists')
    raw.mkdir()
    original_path = ROOT / 'scripts/validate_interpreter_launcher.py'
    original = original_path.read_text()
    staged = original
    replacements = [
        ('from interpreter import ROOT, TOOLCHAIN, checked_tools',
         'from interpreter import ROOT, TOOLCHAIN, installed_tools\n'
         f'def checked_tools():\n    return installed_tools({key!r})'),
        ("env=os.environ.copy();env.pop('RUSTFLAGS',None)",
         "env=os.environ.copy();env['RUST_INTERP_LAUNCH_STATS']='1';env.pop('RUSTFLAGS',None)"),
        ("'--package','interpreter-launcher-fixture']",
         f"'--package','interpreter-launcher-fixture','--tool-key',{key!r}]"),
        ("ROOT/'results/interpreter-launcher-validation.json'", repr(str(raw / 'original-suite-summary.json'))),
    ]
    # Keep the expression a Path while changing only the output destination.
    replacements[-1] = (replacements[-1][0], 'Path(' + replacements[-1][1] + ')')
    for before, after in replacements:
        require(staged.count(before) == 1, 'launcher staging source differs: ' + before)
        staged = staged.replace(before, after)
    require(assertions(staged) == assertions(original), 'original launcher assertions changed')
    script = raw / 'validate_selected_launcher.py'
    script.write_text(staged)
    paths = [Path(__file__), original_path, script, ROOT / 'scripts/interpreter.py',
             ROOT / 'scripts/std_mir.py', ROOT / 'scripts/workflow_io.py', ROOT / 'Cargo.toml', ROOT / 'Cargo.lock',
             *sorted((ROOT / 'crates').rglob('*.rs')), *sorted((ROOT / 'tests').glob('*.rs'))]
    frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    write_json(raw / 'plan.json', dict(tool_key=key, legacy_tool_key=legacy_key,
        original_assertions=len(assertions(original)), assertions_unchanged=True, frozen=frozen))
    env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'CARGO_PROFILE_'))
           and k not in ['PYTHONOPTIMIZE', 'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC',
                         'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET']}
    env['PYTHONPATH'] = str(ROOT / 'scripts')
    command = [sys.executable, str(script)]
    child, stdout, stderr = capture(command, cwd=ROOT, env=env,
        receipt_path=raw / 'active-command.json', receipt=dict(phase='original-launcher-suite'))
    write_json(raw / 'suite-command.json', dict(command=command, returncode=child.returncode, stdout=stdout, stderr=stderr))
    require(child.returncode == 0, 'original launcher suite failed; raw output preserved')
    suite = json.loads((raw / 'original-suite-summary.json').read_text())
    records = json.loads((ROOT / suite['raw'] / 'records.json').read_text())
    require(suite['tool_key'] == key and suite['passed'] == [r['label'] for r in records], 'suite identity/records differ')
    traces = []
    for row in records:
        if row['returncode'] != 0:
            continue
        trace = [json.loads(line.split('rust-interp-launch: ', 1)[1]) for line in row['stderr'].splitlines()
                 if line.startswith('rust-interp-launch: ')]
        require(len(trace) == 1 and trace[0]['tool_key'] == key and
            trace[0]['compiler_wrapper'] == dict(name='rust-interp-rustc-wrapper', sha256=manifest['rust-interp-rustc-wrapper']),
            'successful launcher command did not use the verified wrapper')
        traces.append(row['label'])
    # The original suite leaves a valid source, then deletes its own sidecar to
    # check stale-artifact refusal. A historical tool receives a separate cache.
    fixture = ROOT / suite['raw']
    command = [sys.executable, str(ROOT / 'scripts/interpreter.py'), '--manifest-path', str(fixture / 'Cargo.toml'),
        '--package', 'interpreter-launcher-fixture', '--tool-key', legacy_key, '--entry', 'entry', '--', '3']
    legacy_env = dict(env, RUST_INTERP_LAUNCH_STATS='1')
    child, stdout, stderr = capture(command, cwd=ROOT, env=legacy_env,
        receipt_path=raw / 'active-command.json', receipt=dict(phase='historical-two-binary-launcher'))
    write_json(raw / 'legacy-command.json', dict(command=command, returncode=child.returncode, stdout=stdout, stderr=stderr))
    require(child.returncode == 0 and stdout.strip() == '13', 'historical tool execution failed')
    trace = [json.loads(line.split('rust-interp-launch: ', 1)[1]) for line in stderr.splitlines() if line.startswith('rust-interp-launch: ')]
    require(len(trace) == 1 and trace[0]['tool_key'] == legacy_key and trace[0]['compiler_wrapper'] ==
        dict(name='rust-interp-mir-export', sha256=legacy_manifest['rust-interp-mir-export']), 'historical routing changed')
    require(all(sha(ROOT / p) == digest for p, digest in frozen.items()), 'launcher qualification sources changed')
    installed_tools(key)
    installed_tools(legacy_key)
    out.mkdir()
    write_json(out / 'summary.json', dict(status='passed', tool_key=key, binaries=manifest,
        legacy_tool_key=legacy_key, legacy_binaries=legacy_manifest, original_suite_checks=len(records),
        original_assertions=len(assertions(original)), assertions_unchanged=True,
        successful_wrapper_traces=traces, historical_execution_passed=True,
        raw=str(raw.relative_to(ROOT)), fixture=str(fixture.relative_to(ROOT)), frozen=frozen,
        note='Original regression assertions cover source/dependency/feature/flag/selection changes and reverts, wrong edits, missing sidecar, std-MIR host tools and custom test harnesses. Fixture tests are not whole-project performance evidence.'))
    print(json.dumps(dict(original_suite_checks=len(records), successful_wrapper_traces=len(traces), legacy_execution=True)))


if __name__ == '__main__':
    main()
