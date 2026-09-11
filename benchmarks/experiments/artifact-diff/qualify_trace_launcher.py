#!/usr/bin/env python3
"""Exercise trace toggles and damaged Cargo sidecars with original assertions."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from allocation_trace import selected_trace
from check_allocation_trace import verify_trace
from interpreter import installed_tools, require_export_option, TOOLCHAIN
from std_mir import checked_std_mir
from verify_repeated_workflow import require
from workflow_io import atomic_bytes, capture, require_space, write_json

TOOL = 'e965f566ac6ba4f8e5f6f174af1258e305b5b0d2acde24017581616fe33f2a06'
LEGACY = '78e60cdd76195c55583651bac6a7f7d349314dd1ea582b6a86335adbee48049d'
PACKAGE = 'allocation-trace-launcher-fixture'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lines(stderr, prefix):
    return [json.loads(line[len(prefix):]) for line in stderr.splitlines() if line.startswith(prefix)]


def identity(path):
    info = path.stat()
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--tool-key', default=TOOL)
    parser.add_argument('--legacy-tool-key', default=LEGACY)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['', '.', '..'], 'invalid run ID')
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require_space(ROOT / '.work', 8)
        tool, key = installed_tools(args.tool_key)
        legacy, legacy_key = installed_tools(args.legacy_tool_key)
        require_export_option(tool, key, 'allocation-trace')
        manifests = {label: json.loads((path / 'ready.json').read_text())
                     for label, path in [('traced', tool), ('legacy', legacy)]}
        require(manifests['traced']['rust-interp-vm'] == manifests['legacy']['rust-interp-vm'],
                'expected the same qualified VM in both tools')
        std_key = checked_std_mir(TOOLCHAIN)[2]
        raw, out = [ROOT / parent / args.run_id for parent in ['.work/runs', 'results']]
        require(not raw.exists() and not out.exists(), 'qualification already exists')
        raw.mkdir()
        fixture = raw / 'fixture'
        fixture.mkdir()
        original = ROOT / 'tests/scalar_constant_fixture.rs'
        source = fixture / 'lib.rs'
        source.write_bytes(original.read_bytes())
        manifest = fixture / 'Cargo.toml'
        manifest.write_text('[package]\nname="' + PACKAGE + '"\nversion="0.0.0"\nedition="2024"\n'
                            '[lib]\npath="lib.rs"\n[workspace]\n')
        helpers = ['interpreter.py', 'allocation_trace.py', 'std_mir.py', 'workflow_io.py',
                   'verify_repeated_workflow.py']
        paths = [Path(__file__), Path(__file__).with_name('check_allocation_trace.py'), original, source, manifest,
                 *(ROOT / 'scripts' / helper for helper in helpers),
                 *(path / name for path in [tool, legacy] for name in ['ready.json', 'capabilities.json'])]
        frozen = {str(path.relative_to(ROOT)): sha(path) for path in paths}
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                             'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET']}
        env['CARGO_TERM_COLOR'] = 'never'
        rows = []

        def run(label, command, expected=0, environment=None):
            require_space(raw, 8)
            command = list(map(str, command))
            child, stdout, stderr = capture(command, cwd=ROOT, env=env if environment is None else environment,
                receipt_path=raw / 'active-command.json', receipt=dict(phase=label))
            row = dict(label=label, command=command, pid=child.pid, returncode=child.returncode,
                       stdout=stdout, stderr=stderr)
            rows.append(row)
            write_json(raw / 'records.json', rows)
            require(child.returncode == expected and 'internal compiler error' not in stderr,
                    'qualification command failed: ' + label)
            return row

        run('cargo-lockfile', ['cargo', '+' + TOOLCHAIN, 'generate-lockfile', '--offline', '--manifest-path', manifest])
        frozen[str((fixture / 'Cargo.lock').relative_to(ROOT))] = sha(fixture / 'Cargo.lock')
        native = raw / 'native'
        run('native-build', ['rustc', '+' + TOOLCHAIN, original, '--edition=2024', '-o', native])
        seeds = [0, 7, 2**64 - 1]
        expected = {seed: run('native-' + str(seed), [native, seed])['stdout'].strip() for seed in seeds}
        base = [sys.executable, ROOT / 'scripts/interpreter.py', '--manifest-path', manifest,
                '--package', PACKAGE, '--tool-key', key, '--cache-namespace', args.run_id,
                '--jobs', '2', '--engine', 'jit', '--inline-leaves', '--std-mir', '--entry', 'rust_interp_entry']
        launch_env = dict(env, RUST_INTERP_LAUNCH_STATS='1')
        artifacts, observations = [], []

        def success(label, enabled, seed=7, environment=launch_env):
            row = run(label, [*base, *(['--allocation-trace'] if enabled else []), '--', seed], environment=environment)
            require(row['stdout'].strip() == expected[seed], 'original native/guest assertion result differs')
            launch = lines(row['stderr'], 'rust-interp-launch: ')
            receipts = lines(row['stderr'], 'rust-interp-allocation-trace: ')
            require(len(receipts) == int(enabled), 'trace receipt presence differs')
            if environment.get('RUST_INTERP_LAUNCH_STATS') == '1':
                require(len(launch) == 1 and launch[0]['tool_key'] == key, 'launch receipt missing')
                artifact = Path(launch[0]['artifact_path'])
                require(sha(artifact) == launch[0]['artifact_sha256'], 'selected artifact digest differs')
            else:
                require(not launch and enabled, 'unexpected timing receipt')
                artifact = Path(receipts[0]['artifact_path'])
            require(artifact.is_relative_to(ROOT / '.work/interpreter-workspaces' / key), 'unexpected artifact owner')
            artifacts.append(sha(artifact))
            if enabled:
                receipt = receipts[0]
                checked = selected_trace(artifact)
                require(all(receipt.get(k) == v for k, v in checked.items()) and receipt['tool_key'] == key and
                        receipt['exporter_sha256'] == manifests['traced']['rust-interp-mir-export'],
                        'trace receipt does not bind the installed exporter and selected file')
                if launch:
                    require(launch[0]['allocation_trace'] == receipt, 'launch and standalone trace receipts differ')
                observations.append(dict(label=label, **verify_trace(Path(receipt['path']), artifact)))
            return artifact

        artifact = success('disabled-initial', False)
        sidecar = Path(str(artifact) + '.allocations.jsonl')
        require(not sidecar.exists(), 'initial disabled export emitted a trace')
        success('enabled-after-disabled', True)
        first = identity(sidecar)
        success('enabled-unchanged', True, seed=0)
        require(identity(sidecar) == first, 'unchanged enabled selection rewrote its trace')
        success('disabled-after-enabled', False, seed=2**64 - 1)
        success('enabled-again', True)
        success('enabled-without-timing-stats', True, environment=env)
        require(len(set(artifacts)) == 1, 'trace toggles changed bytecode')
        saved = sidecar.read_bytes()
        backup = raw / 'saved-selected-trace.jsonl'
        backup.write_bytes(saved)
        program_identity = identity(artifact)
        try:
            events = [json.loads(line) for line in saved.splitlines()]
            events[-1]['artifact_sha256'] = '0' * 64
            damaged = b''.join(json.dumps(event).encode() + b'\n' for event in events)
            atomic_bytes(sidecar, damaged)
            row = run('wrong-footer-refused', [*base, '--allocation-trace', '--', '7'], expected=1, environment=launch_env)
            require(not row['stdout'].strip() and 'no program was run' in row['stderr'] and
                    not lines(row['stderr'], 'rust-interp-launch: ') and identity(artifact) == program_identity,
                    'mismatched cached trace reached execution or was silently reexported')
            atomic_bytes(sidecar, saved)
            standalone = next(p for p in artifact.parents if p.name == 'target').parent / 'program.rbc.allocations.jsonl'
            require(standalone.is_file(), 'standalone diagnostic missing for stale-output probe')
            standalone_hash = sha(standalone)
            sidecar.unlink()
            row = run('missing-selected-trace-refused', [*base, '--allocation-trace', '--', '7'], expected=1, environment=launch_env)
            require(not row['stdout'].strip() and 'no program was run' in row['stderr'] and
                    sha(standalone) == standalone_hash and identity(artifact) == program_identity,
                    'stale standalone trace rescued missing selected sidecar')
        finally:
            atomic_bytes(sidecar, saved)
        success('restored-selected-trace', True)
        old = [str(arg) for arg in base]
        old[old.index('--tool-key') + 1] = legacy_key
        old[old.index('--cache-namespace') + 1] = args.run_id + '-legacy'
        row = run('unsupported-legacy-trace', [*old, '--allocation-trace', '--', '7'], expected=1, environment=launch_env)
        require('does not support --allocation-trace' in row['stderr'] and not row['stdout'].strip(),
                'historical tool did not reject unsupported tracing')
        identity_input = 'shared-entries-v1\0' + str(manifest) + '\0' + PACKAGE + '\0False\0std-mir:' + std_key + '\0' + args.run_id + '-legacy'
        old_workspace = ROOT / '.work/interpreter-workspaces' / legacy_key / hashlib.sha256(identity_input.encode()).hexdigest()[:24]
        require(not old_workspace.exists(), 'unsupported trace created a historical tool workspace')
        selection = raw / 'audit-selection.json'
        write_json(selection, ['rust_interp_entry'])
        audit = base[:-2] + ['--audit-entries', selection, '--test-body', '--allocation-trace']
        row = run('audit-trace-refused', audit, expected=2, environment=launch_env)
        require('--allocation-trace' in row['stderr'] and '--audit-entries' in row['stderr'] and
                not row['stdout'].strip(), 'audit combination did not reject early')
        row = run('legacy-disabled-compatible', [*old, '--', '7'], environment=launch_env)
        require(row['stdout'].strip() == expected[7] and not lines(row['stderr'], 'rust-interp-allocation-trace: '),
                'historical trace-disabled behavior changed')
        require(all(sha(ROOT / path) == digest for path, digest in frozen.items()), 'qualification inputs changed')
        installed_tools(key)
        installed_tools(legacy_key)
        out.mkdir()
        write_json(out / 'summary.json', dict(status='passed', tool_key=key, legacy_tool_key=legacy_key,
            binaries=manifests, commands=len(rows), original_fixture_sha256=sha(original),
            assertions_unchanged=source.read_bytes() == original.read_bytes(), native_inputs=seeds,
            trace_observations=observations, bytecode_identical_across_toggles=True,
            stale_selected_sidecars_rejected=True, selected_trace_restored=sidecar.read_bytes() == saved,
            timing_stats_optional=True, legacy_disabled_compatible=True, sources_sha256=frozen,
            records_sha256=sha(raw / 'records.json'), raw=str(raw.relative_to(ROOT)),
            note='Cargo launcher qualification with original assertions. Diagnostic timings are not performance measurements; allocation equivalence across histories remains unproven.'))
        print(json.dumps(dict(commands=len(rows), trace_observations=len(observations), status='passed')))


if __name__ == '__main__':
    main()
