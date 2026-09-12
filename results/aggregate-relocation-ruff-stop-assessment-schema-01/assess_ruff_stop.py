#!/usr/bin/env python3
"""Preserve and verify the Ruff comparison stopped before its second cycle."""
import fcntl
import hashlib
import json
import math
import re
import subprocess
import time
from pathlib import Path

from build_relocation import ROOT, HERE, read, sha, require, write
from check_comparison import expected_tools
from heldout_controls import case
from workflow_cases import WORKFLOWS
from workflow_measurements import source_states
from workflow_jobs import verify_command_jobs
from workflow_cache_evidence import option
from bench_e2e_workflow import guest_test_failure

RUN = 'aggregate-relocation-heldout-01-ruff'
OUT = 'aggregate-relocation-ruff-stop-01'


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        experiment, work = ROOT/'.work/experiments'/RUN, ROOT/'.work'/RUN
        raw = ROOT/'.work/runs'/RUN
        supervisor, controller = read(experiment/'status.json'), read(work/'status.json')
        launch, plan = read(experiment/'plan.json'), read(work/'plan.json')
        require(supervisor['status'] == 'finished' and supervisor['returncode'] == 1 and
                supervisor['owner'] == supervisor['cwd'] == launch['owner'] == str(ROOT) and
                supervisor['command'] == launch['command'] ==
                ['python3', 'benchmarks/experiments/aggregate-byte-writes/run_heldout.py', '--case', 'ruff'],
                'unexpected stopped supervisor')
        require(controller['status'] == 'failed' and controller['child_returncode'] == 1 and
                controller['pid'] == supervisor['child_pid'] and
                controller['parent_pid'] == supervisor['supervisor_pid'] and
                controller['command'] == plan['command'] and plan['case'] == case('ruff') and
                plan['expected_tools'] == expected_tools(), 'unexpected stopped controller or tools')
        command = controller['command']
        for flag, value in [('--run-id', RUN), ('--project', 'ruff'), ('--workflow', 'default'),
                            ('--cycles', '3'), ('--jobs', '4'), ('--native-jobs', '18'),
                            ('--native-profile', 'o0-incremental'), ('--native-test-threads', 'default'),
                            ('--minimum-free-gib', '8')]:
            require(option(command, flag) == value, 'stopped command controls differ')
        require(sha(experiment/'plan.json') == supervisor['plan_sha256'] and
                sha(experiment/'command.log') == supervisor['log_sha256'] and
                all(sha(ROOT/p) == h for p, h in plan['frozen'].items()),
                'stopped measured sources or receipts changed')
        log = (work/'command.log').read_text()
        matches = re.findall(r'insufficient free disk: (\d+) bytes; no child started or automatic cleanup attempted', log)
        require(matches == ['7517466624'] and 'No space left on device' not in log,
                'expected one pre-command disk rejection')
        require(not (ROOT/'results'/RUN/'summary.json').exists(), 'stopped history has a success report')
        source = ROOT/'.work/sources/ruff'
        marker = read(source/'.rust-interp-owned.json')
        pin = read(ROOT/'benchmarks/corpus.json')['projects']['ruff']['revision']
        require(marker['owner'] == str(ROOT) and marker['revision'] == pin and
                subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == pin and
                not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source, text=True).strip(),
                'Ruff source is not owned, pinned and restored')
        c = WORKFLOWS['ruff']; original = (source/c['file']).read_bytes()
        samples = list(source_states(original.decode(), c, 3, ['native', 'baseline', 'candidate'], True))
        rows, checks, transitions = (read(raw/n) for n in ['records.json', 'check-records.json', 'source-transitions.json'])
        require(len(rows) == 21 and len(checks) == 7 and len(transitions) == 8,
                'stopped prefix length differs')
        require([(r['cycle'], r['state'], r['mode']) for r in rows] ==
                [(s['cycle'], s['state'], m) for s in samples[:7] for m in s['modes']],
                'stopped primary command order differs')
        require([(r['cycle'], r['state']) for r in checks] == [(s['cycle'], s['state']) for s in samples[:7]],
                'stopped check order differs')
        previous = dict.fromkeys(['native', 'baseline', 'candidate'])
        snapshots = {}; tools = expected_tools()
        for mode, tool in tools.items():
            for binary, key in [('rust-interp-vm', 'vm_sha256'), ('rust-interp-mir-export', 'exporter_sha256'),
                                ('rust-interp-rustc-wrapper', 'wrapper_sha256')]:
                require(sha(ROOT/'.work/interpreter-tools'/tool['tool_key']/binary) == tool[key], 'immutable tool differs')
        for index, sample in enumerate(samples[:8]):
            digest = hashlib.sha256(sample['source']).hexdigest(); t = transitions[index]
            require(all(t[k] == sample[k] for k in ['cycle', 'state', 'phase']) and
                    t['source_sha256'] == digest and t['previous_mode_sources'] == previous and
                    t['content_changed'] == (index != 0), 'source transition differs')
            if index == 7:
                require(sample['cycle'] == 1 and sample['state'] == 0, 'unexpected rejected next sample')
                break
            for row in rows[index*3:index*3+3]:
                mode = row['mode']; call = row['calls'][0]
                require(len(row['calls']) == 1 and row['tests'] == c['tests'] and
                        row['source_sha256'] == digest and row['previous_source_sha256'] == previous[mode] and
                        (call['returncode'] == 0) == (sample['state'] != -1), 'partial command outcome/source differs')
                require(all(math.isfinite(row[k]) and row[k] > 0 for k in ['seconds', 'cpu_seconds']) and
                        abs(row['cpu_seconds']-call['cpu']['total_seconds']) < 1e-8,
                        'partial timing or CPU accounting differs')
                require(call['rustflags'] is None and call['encoded_rustflags'] is None, 'unexpected compiler flags')
                verify_command_jobs(call['command'], 18 if mode == 'native' else 4)
                require(option(call['command'], '--manifest-path') == str(source/'Cargo.toml') and
                        option(call['command'], '--package') == c['package'], 'partial crate selection differs')
                if mode == 'native':
                    require(option(call['command'], '--target-dir') == str(raw/'native') and
                            not any(a.startswith('--test-threads=') for a in call['command']), 'native target/concurrency differs')
                    require(('test result: FAILED.' in call['stdout'] and
                             'test registry::tests::check_code_serialization ... FAILED' in call['stdout'])
                            if sample['state'] == -1 else '6 passed' in call['stdout'], 'native original assertions differ')
                else:
                    require(guest_test_failure(call['stderr']) if sample['state'] == -1 else
                            call['stdout'].strip() == '0', 'custom original assertions differ')
                    launched = call['launch']; key = tools[mode]['tool_key']
                    require(row['engine'] == launched['engine'] == option(call['command'], '--engine') == 'jit' and
                            row['tool_key'] == launched['tool_key'] == option(call['command'], '--tool-key') == key and
                            launched['compiler_wrapper']['sha256'] == tools[mode]['wrapper_sha256'], 'executed tool differs')
                    for field, flag, value in [('jit_persistent_registers', '--jit-persistent-registers', True),
                            ('jit_resumable_calls', '--jit-resumable-calls', True), ('inline_leaves', '--inline-leaves', True),
                            ('jit_native_calls', '--jit-native-calls', False), ('jit_native_call_stubs', '--jit-native-call-stubs', False),
                            ('trap_unsupported_calls', '--trap-unsupported-calls', False), ('run_try_callbacks', '--run-try-callbacks', False)]:
                        require(launched[field] is value and (flag in call['command']) == value, 'executed runtime option differs')
                    require('--std-mir' in call['command'] and len(row['artifacts']) == 1, 'missing standard MIR or artifact')
                    item = row['artifacts'][0]; path = ROOT/item['path']
                    require(path.resolve(strict=True) == path and path.is_relative_to(raw/'artifacts'/mode) and
                            sha(path) == item['sha256'] == launched['artifact_sha256'] and
                            path.stat().st_size == item['bytes'] == launched['artifact_bytes'] and
                            item['path'] not in snapshots, 'executed artifact differs or was overwritten')
                    snapshots[item['path']] = item['sha256']
                require(('Compiling ' if mode == 'native' else 'Checking ')+c['package'] in call['stderr'],
                        'selected crate did not compile')
                previous[mode] = digest
            check = checks[index]
            require(check['source_sha256'] == digest and check['returncode'] == 0 and
                    check['command'][2] == 'check' and option(check['command'], '--profile') == 'test' and
                    option(check['command'], '--target-dir') == str(raw/'check') and
                    'test result:' not in check['stdout'], 'independent check differs')
            verify_command_jobs(check['command'], 18)
        require(sha(source/c['file']) == rows[0]['source_sha256'], 'source restoration differs')
        active = read(raw/'active-command.json')
        require(active['status'] == 'finished' and active['returncode'] == 0 and
                active['command'] == checks[-1]['command'] and active['pid'] == checks[-1]['pid'] and
                active['parent_pid'] == controller['child_pid'], 'last check is not terminal')
        pids = [supervisor['supervisor_pid'], supervisor['child_pid'], controller['child_pid'], active['pid']]
        process = subprocess.run(['ps', '-p', ','.join(map(str, pids)), '-o', 'pid,ppid,lstart,tty,command'], capture_output=True, text=True)
        require(process.returncode in [0, 1] and not process.stderr and
                not any(RUN in line for line in process.stdout.splitlines()[1:]), 'stopped process remains live')
        out = ROOT/'results'/OUT; out.mkdir(exist_ok=False)
        paths = [experiment/n for n in ['plan.json', 'status.json', 'command.log', 'supervisor.log']]
        paths += [work/n for n in ['plan.json', 'status.json', 'admission.json', 'command.log']]
        paths += [raw/n for n in ['records.json', 'check-records.json', 'source-transitions.json', 'active-command.json']]
        evidence = {}
        for i, path in enumerate(paths):
            payload = path.read_bytes(); name = 'evidence-%02d%s' % (i, path.suffix)
            (out/name).write_bytes(payload)
            evidence[str(path.relative_to(ROOT))] = dict(snapshot=name, sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload))
        result = dict(status='incomplete: pre-command disk guard', run_id=RUN, assessed_at=time.time(),
            primary_records=21, check_records=7, completed_cycles=1, planned_cycles=3,
            measured_successful_edit_pairs=5, snapshots=snapshots, source_pin=pin,
            source_restored=True, restored_source_sha256=sha(source/c['file']), completed_workflows=0,
            retained=False, included_in_performance_gate=False, observed_guard_free_bytes=int(matches[0]),
            admitted_free_bytes=plan['admission']['observed_free_bytes'], running_floor_bytes=8*1024**3,
            evidence=evidence, frozen=plan['frozen'], expected_tools=tools,
            original_records_unchanged=True, cache_cleanup_performed=False, process_signals_sent=False,
            process_check=dict(command=process.args, returncode=process.returncode, stdout=process.stdout),
            assessor_sha256=sha(Path(__file__)))
        write(out/'summary.json', result)
        (out/'assessment.md').write_text('# Ruff stopped before its second cycle\n\n'
            'One complete cycle verifies: 21 primary commands, seven independent checks, five real-edit pairs and 14 executed artifacts. '
            'All original assertions, the wrong-edit failures, exact tool/runtime controls and pinned source restoration verify. '
            'The next cycle reached its original-source transition, then the 8 GiB guard stopped before another compiler child.\n\n'
            'The guard observed 7,517,466,624 free bytes. This partial history is preserved and excluded from the planned 15-pair performance decision. '
            'No cache cleanup or process signal occurred. Available-space observations alone do not identify the cause of the transient shortage. '
            'Any retry requires an explicit new identity and unchanged benchmark controls.\n')
        print(dict(status=result['status'], primary_records=21, check_records=7, edited_pairs=5, artifacts=14, source_restored=True))


if __name__ == '__main__':
    main()
