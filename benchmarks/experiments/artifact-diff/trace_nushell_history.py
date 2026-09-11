#!/usr/bin/env python3
"""Capture allocation origins across original/wrong/API/restored Nushell source."""
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
from qualify_trace_launcher import TOOL, lines
from std_mir import checked_std_mir
from verify_repeated_workflow import require
from workflow_case_file import load, source_file
from workflow_controls import native_command, native_environment
from workflow_io import SourceEdit, capture, require_space, write_json


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['', '.', '..'], 'invalid run ID')
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require_space(ROOT / '.work', 18)
        qualification = ROOT / 'results/allocation-trace-launcher-02/summary.json'
        q = json.loads(qualification.read_text())
        regression = ROOT / 'results/allocation-trace-launcher-regression-01/summary.json'
        regression_report = json.loads(regression.read_text())
        require(q['status'] == 'passed' and q['tool_key'] == TOOL and
                q['sources_sha256']['scripts/interpreter.py'] == sha(ROOT / 'scripts/interpreter.py') and
                regression_report['status'] == 'passed' and regression_report['tool_key'] == TOOL and
                regression_report['original_suite_checks'] == 99 and
                regression_report['frozen']['scripts/interpreter.py'] == sha(ROOT / 'scripts/interpreter.py'),
                'current trace launcher lacks qualification')
        tool, key = installed_tools(TOOL)
        require_export_option(tool, key, 'allocation-trace')
        binaries = json.loads((tool / 'ready.json').read_text())
        require(binaries == q['binaries']['traced'] == regression_report['binaries'], 'qualified tools differ')
        std_key = checked_std_mir(TOOLCHAIN)[2]
        spec = ROOT / 'benchmarks/experiments/interface-edits/nushell-generic-list.json'
        revision = '9d3157963241cf89447119d34d6e887859f5e7e8'
        case, proof = load(spec, 'nushell', revision)
        require(len(case['tests']) == 14 and len(case['edits']) == 1, 'diagnostic case changed')
        source = ROOT / '.work/sources/nushell'
        owner = json.loads((source / '.rust-interp-owned.json').read_text())
        require(owner['owner'] == str(ROOT) and owner['revision'] == revision, 'snapshot ownership changed')
        require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == revision and
                not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source, text=True).strip(),
                'snapshot revision or source changed')
        path = source_file(source, case)
        original = subprocess.check_output(['git', 'show', revision + ':' + case['file']], cwd=source)
        require(path.read_bytes() == original, 'original source differs')
        marker = b'\n#[cfg(test)]\nmod tests {'
        require(original.count(marker) == 1, 'original tests cannot be isolated')
        tests = original.split(marker)[1]
        states = [('original', original)]
        for label, before, after in [case['negative'], case['edits'][0]]:
            require(original.count(before.encode()) == 1, 'edit no longer matches exactly once')
            payload = original.replace(before.encode(), after.encode())
            require(payload.count(marker) == 1 and payload.split(marker)[1] == tests, 'original assertions changed')
            states.append((label, payload))
        states.append(('restored-original', original))
        raw, out = [ROOT / parent / args.run_id for parent in ['.work/runs', 'results']]
        require(not raw.exists() and not out.exists(), 'diagnostic already exists')
        raw.mkdir()
        (raw / 'artifacts').mkdir()
        (raw / 'case.json').write_bytes(spec.read_bytes())
        helpers = ['interpreter.py', 'allocation_trace.py', 'std_mir.py', 'workflow_io.py',
                   'workflow_controls.py', 'workflow_case_file.py', 'verify_repeated_workflow.py']
        inputs = [Path(__file__), Path(__file__).with_name('check_allocation_trace.py'),
                  Path(__file__).with_name('qualify_trace_launcher.py'), spec, raw / 'case.json', qualification, regression,
                  *(ROOT / 'scripts' / helper for helper in helpers), tool / 'ready.json', tool / 'capabilities.json']
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                             'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET']}
        env.update(CARGO_TERM_COLOR='never', RUST_INTERP_LAUNCH_STATS='1')
        manifest = source / 'Cargo.toml'
        custom = [sys.executable, ROOT / 'scripts/interpreter.py', '--manifest-path', manifest,
                  '--package', case['package'], '--tool-key', key, '--jobs', '4', '--test-body',
                  '--engine', 'jit', '--instruction-limit', '1000000000', '--inline-leaves', '--std-mir',
                  '--allocation-trace', '--cache-namespace', args.run_id,
                  *[arg for test in case['tests'] for arg in ['--entry', test]]]
        native = native_command(TOOLCHAIN, manifest, case['package'], raw / 'native', 18, 'default', case['tests'])
        rows, snapshots = [], []
        write_json(raw / 'plan.json', dict(tool_key=key, binaries=binaries, std_key=std_key, revision=revision,
            states=[dict(label=label, source_sha256=hashlib.sha256(payload).hexdigest()) for label, payload in states],
            tests=case['tests'], case=proof, sources_sha256=frozen, note='Allocation identity diagnostic; no performance inference.'))
        with SourceEdit(path, original) as edit:
            for index, (label, payload) in enumerate(states):
                if index:
                    edit.replace(payload)
                require(path.read_bytes() == payload and all(sha(ROOT / p) == d for p, d in frozen.items()),
                        'diagnostic source or inputs changed')
                wrong = index == 1
                for mode, command in [('native', native), ('custom', custom)]:
                    require_space(raw, 8)
                    command = list(map(str, command))
                    child, stdout, stderr = capture(command, cwd=source,
                        env=native_environment(env, 'o0-incremental', []) if mode == 'native' else env,
                        receipt_path=raw / 'active-command.json', receipt=dict(state=label, mode=mode))
                    row = dict(state=label, mode=mode, command=command, pid=child.pid, returncode=child.returncode,
                        source_sha256=sha(path), stdout=stdout, stderr=stderr)
                    rows.append(row)
                    write_json(raw / 'records.json', rows)
                    require(child.returncode == int(wrong) and 'internal compiler error' not in stderr,
                            'diagnostic command outcome differs: ' + label + '/' + mode)
                    if mode == 'native':
                        if wrong:
                            require('12 passed; 2 failed' in stdout and 'assertion failed: ty.is_subtype_of(&Type::Any)' in stdout,
                                    'wrong native edit did not reach original assertions')
                        else:
                            require('14 passed; 0 failed' in stdout and all('test ' + t + ' ... ok' in stdout for t in case['tests']),
                                    'native selected tests did not all pass')
                        continue
                    if wrong:
                        require('guest trap: core::panicking::panic' in stderr and
                                'ty::tests::subtype_relation::test_any_is_top_type' in stderr,
                                'wrong custom edit did not reach original assertion')
                    else:
                        require(stdout.strip() == '0', 'custom batch did not pass')
                    launches, traces = lines(stderr, 'rust-interp-launch: '), lines(stderr, 'rust-interp-allocation-trace: ')
                    require(len(launches) == len(traces) == 1, 'selected diagnostic receipt missing')
                    launch, receipt = launches[0], traces[0]
                    require(launch['tool_key'] == key and launch['engine'] == 'jit' and launch['inline_leaves'] and
                            not any(launch.get(k, False) for k in ['jit_persistent_registers', 'jit_resumable_calls',
                                'jit_native_calls', 'jit_native_call_stubs', 'trap_unsupported_calls', 'run_try_callbacks']) and
                            launch['allocation_trace'] == receipt and receipt['exporter_sha256'] == binaries['rust-interp-mir-export'],
                            'unexpected tool, runtime settings or diagnostic receipt')
                    artifact = Path(launch['artifact_path'])
                    require(artifact.is_relative_to(ROOT / '.work/interpreter-workspaces' / key), 'selected artifact owner differs')
                    checked = selected_trace(artifact)
                    require(all(receipt.get(k) == v for k, v in checked.items()), 'selected trace changed after execution')
                    saved = raw / 'artifacts' / (label + '.rbc')
                    saved_trace = Path(str(saved) + '.allocations.jsonl')
                    saved.write_bytes(artifact.read_bytes())
                    saved_trace.write_bytes(Path(checked['path']).read_bytes())
                    require(sha(saved) == checked['artifact_sha256'] and sha(saved_trace) == checked['sha256'],
                            'snapshot differs from executed artifact or trace')
                    details = verify_trace(saved_trace, saved)
                    snapshots.append(dict(state=label, artifact=str(saved.relative_to(ROOT)),
                        trace=str(saved_trace.relative_to(ROOT)), selected=checked, verification=details))
                    write_json(raw / 'snapshots.json', snapshots)
                print(json.dumps(dict(state=label, commands=len(rows), snapshots=len(snapshots))), flush=True)
        require(path.read_bytes() == original and all(sha(ROOT / p) == d for p, d in frozen.items()),
                'source restoration or frozen inputs differ')
        installed_tools(key)
        out.mkdir()
        write_json(out / 'summary.json', dict(status='passed', tool_key=key, binaries=binaries, std_key=std_key,
            revision=revision, commands=len(rows), tests=case['tests'], original_assertions_unchanged=True,
            wrong_original_assertions_verified_both_modes=True, source_restored=True, snapshots=snapshots,
            sources_sha256=frozen, records_sha256=sha(raw / 'records.json'), raw=str(raw.relative_to(ROOT)),
            note='Four-state strict frontend and custom JIT diagnostic with native assertion controls. Tracing adds work; timings are not performance evidence. Allocation equivalence and causes require separate origin analysis.'))
        print(json.dumps(dict(status='passed', commands=len(rows), snapshots=len(snapshots))))


if __name__ == '__main__':
    main()
