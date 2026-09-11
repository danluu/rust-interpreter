#!/usr/bin/env python3
"""Qualify fresh observer exports and collect exact matching execution profiles."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from build import ROOT, environment, sha, write
from verify_repeated_workflow import require
from interpreter import installed_tools


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--build-run', required=True)
    args = parser.parse_args()
    for value in [args.run_id, args.build_run]:
        require(Path(value).name == value and value not in ('.', '..'), 'invalid run ID')
    work = ROOT / '.work' / args.run_id
    work.mkdir(exist_ok=False)
    status = dict(owner=str(ROOT), status='waiting for benchmark lock', pid=os.getpid(),
        parent_pid=os.getppid(), cwd=str(ROOT), started_at=time.time())
    receipt = work / 'status.json'
    write(receipt, status)
    lock = (ROOT / '.work/benchmark.lock').open('a')
    deadline = time.monotonic() + 600
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() >= deadline:
                status.update(status='failed', error='benchmark lock wait expired', finished_at=time.time())
                write(receipt, status)
                raise
            time.sleep(1)
    try:
        build_work = ROOT / '.work' / args.build_run
        build = read(build_work / 'summary.json')
        proof = read(build_work / 'provenance.json')
        require(read(build_work / 'status.json')['status'] == 'finished' and build['exporter_tests'] == 15, 'build not qualified')
        tool, _ = installed_tools(build['tool_key'])
        parent, _ = installed_tools(build['parent_tool_key'])
        require(sha(tool / 'rust-interp-vm') == sha(parent / 'rust-interp-vm'), 'VM differs from parent')
        frozen = dict(proof['root_frozen'])
        for path in [Path(__file__), build_work / 'summary.json', build_work / 'provenance.json']:
            frozen[str(path.relative_to(ROOT))] = sha(path)
        source = ROOT / '.work/sources/fre'
        marker = source / '.rust-interp-owned.json'
        owner = read(marker)
        require(owner['owner'] == str(ROOT), 'unexpected source owner')

        def verify():
            require(read(marker) == owner, 'source owner changed')
            require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == owner['revision'], 'source pin changed')
            require(not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source, text=True).strip(), 'source edited')
            require(all(sha(ROOT / p) == h for p, h in frozen.items()), 'frozen input changed')
            require(all(sha(ROOT / proof['source'] / p) == h for p, h in proof['copied_inputs'].items()), 'copied source changed')
            require(all(sha(tool / p) == h for p, h in build['binaries'].items()), 'installed diagnostic binary changed')

        cases = []
        for label in ['folded-literal-trie', 'token-phrase']:
            records = ROOT / '.work/runs' / ('persistent-e2e-01-' + label) / 'records.json'
            frozen[str(records.relative_to(ROOT))] = sha(records)
            old = next(r for r in read(records) if r['cycle'] == 0 and r['state'] == 0 and r['mode'] == 'candidate')
            require(len(old['calls']) == len(old['artifacts']) == 1, 'expected one original batch')
            call = old['calls'][0]
            command = call['command'].copy()
            require(command[command.index('--tool-key') + 1] == build['parent_tool_key'], 'reference tool differs')
            command[0] = sys.executable
            command[command.index('--tool-key') + 1] = build['tool_key']
            command[command.index('--cache-namespace') + 1] = args.run_id + ':' + label
            original = ROOT / old['artifacts'][0]['path']
            require(sha(original) == old['artifacts'][0]['sha256'], 'original artifact changed')
            frozen[str(original.relative_to(ROOT))] = sha(original)
            cases.append(dict(label=label, export_command=command, guest_rustflags=call['rustflags'],
                original_artifact=str(original.relative_to(ROOT)), original_sha256=sha(original)))
        write(work / 'plan.json', dict(build_run=args.build_run, tool_key=build['tool_key'],
            parent_tool_key=build['parent_tool_key'], frozen=frozen, cases=cases, performance_measurement=False))
        verify()
        commands = []

        def invoke(label, command, env):
            verify()
            with (work / (label + '.stdout')).open('x') as out, (work / (label + '.stderr')).open('x') as err:
                child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err)
                status.update(status='running', label=label, child_pid=child.pid, command=command, child_started_at=time.time())
                write(receipt, status)
                code = child.wait()
            record = dict(label=label, pid=child.pid, parent_pid=os.getpid(), cwd=str(ROOT), command=command,
                started_at=status['child_started_at'], finished_at=time.time(), returncode=code,
                files={str((work / (label + suffix)).relative_to(ROOT)): sha(work / (label + suffix)) for suffix in ['.stdout', '.stderr']})
            commands.append(record)
            write(work / 'commands.json', commands)
            require(code == 0 and (work / (label + '.stdout')).read_text().strip() == '0', 'original batch failed: ' + label)
            verify()
            return (work / (label + '.stderr')).read_text()

        output = []
        for case in cases:
            label = case['label']
            env = environment()
            env.update(RUST_INTERP_LAUNCH_STATS='1', RUSTFLAGS=case['guest_rustflags'])
            if label == 'token-phrase':
                env.update(CARGO_PROFILE_DEV_BUILD_OVERRIDE_OPT_LEVEL='0', CARGO_PROFILE_TEST_BUILD_OVERRIDE_OPT_LEVEL='0')
            errors = invoke(label + '-export', case['export_command'], env)
            inventories = [json.loads(line.split(': ', 1)[1]) for line in errors.splitlines()
                if line.startswith('rust-interp-aggregate-reuse: ')]
            launches = [json.loads(line.split(': ', 1)[1]) for line in errors.splitlines() if line.startswith('rust-interp-launch: ')]
            require(inventories and len(launches) == 1, 'missing observer/launch output')
            require(len({r['id'] for r in inventories}) == len(inventories), 'duplicate compiler instance ID')
            launch = launches[0]
            require(launch['tool_key'] == build['tool_key'] and all(launch[k] for k in
                ['jit_native_calls', 'jit_native_call_stubs', 'jit_persistent_registers']), 'launched wrong runtime')
            artifact = Path(launch['artifact_path'])
            require(sha(artifact) == launch['artifact_sha256'] == case['original_sha256'], 'fresh bytecode differs from original')
            saved = work / (label + '.rbc')
            shutil.copy2(artifact, saved)
            frozen[str(saved.relative_to(ROOT))] = sha(saved)
            inventory = work / (label + '-inventory.json')
            write(inventory, inventories)
            profile = work / (label + '-profile.json')
            env = environment()
            env['RUST_INTERP_VM_STATS'] = '1'
            command = [str(parent / 'rust-interp-vm'), '--engine', 'jit', '--jit-native-calls',
                '--jit-native-call-stubs', '--jit-persistent-registers', '--instruction-limit', '100000000000']
            if '--allocation-limit' in case['export_command']:
                command += ['--allocation-limit', case['export_command'][case['export_command'].index('--allocation-limit') + 1]]
            command += ['--profile', str(profile), str(saved)]
            errors = invoke(label + '-profile', command, env)
            stats = {k: int(v) for k, v in re.findall(r'\b([a-z_]+)=(\d+)\b', errors)}
            require(stats.get('jit_register_functions', 0) > 0 and stats.get('instructions', 0) > 0, 'empty profile execution')
            result = dict(label=label, artifact=str(saved.relative_to(ROOT)), artifact_sha256=sha(saved),
                profile=str(profile.relative_to(ROOT)), profile_sha256=sha(profile),
                inventory=str(inventory.relative_to(ROOT)), inventory_sha256=sha(inventory),
                inventories=len(inventories), statistics=stats, bytecode_identical=True, original_assertions_pass=True,
                source_revision=owner['revision'], guest_rustflags=case['guest_rustflags'])
            output.append(result)
            write(work / 'cases.json', output)
            print(json.dumps(dict(label=label, inventories=len(inventories), bytecode_identical=True,
                hypothetical_static_bytes_saved=sum(r['additional_bytes_saved'] for r in inventories))), flush=True)
        verify()
        report = dict(status='passed', cases=output, tool_key=build['tool_key'], parent_tool_key=build['parent_tool_key'],
            binaries=build['binaries'], source_unchanged=True, performance_measurement=False,
            plan_sha256=sha(work / 'plan.json'), frozen=frozen, commands=commands)
        write(work / 'summary.json', report)
        out = ROOT / 'results' / args.run_id
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', report)
        status.update(status='finished', returncode=0, finished_at=time.time())
        write(receipt, status)
    except BaseException as error:
        status.update(status='failed', error=repr(error), finished_at=time.time())
        write(receipt, status)
        raise


if __name__ == '__main__':
    main()
