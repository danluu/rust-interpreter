"""Provenance for one completed host workspace-check target, never guest caches."""
import json
from pathlib import Path
import re
import subprocess

from interpreter import installed_tools
from verify_repeated_workflow import require

ROOT = Path(__file__).resolve().parents[1]


def validate_identity(run_id, plan, status, report):
    require(Path(run_id).name == run_id and run_id not in ['', '.', '..'], 'invalid workspace-check ID')
    work = ROOT / '.work' / run_id
    target = ROOT / '.work/diagnostic-builds' / run_id
    require(plan['owner'] == status['owner'] == status['cwd'] == str(ROOT), 'workspace-check owner differs')
    require(plan['target'] == str(target.relative_to(ROOT)) and
            plan['source_archive'] == report['source_archive'] == str((work / 'source').relative_to(ROOT)),
            'workspace-check target or archive differs')
    require(status['status'] == 'finished' and status['returncode'] == 0 and
            status['report'] == 'results/' + run_id and
            report['status'] == 'passed' and report['returncode'] == 0 and report['frozen_sources_unchanged'],
            'workspace check did not finish successfully')
    require(plan['performance_measurement'] is False and report['performance_measurement'] is False,
            'expected host qualification, not a performance measurement')
    command = plan['command']
    require(command == report['command'] and command[:3] == ['cargo', '+nightly-2026-09-08', 'test'] and
            command[command.index('--target-dir') + 1] == str(target), 'workspace-check command differs')
    command = status['command']
    require(command[:2] == ['cargo', '+nightly-2026-09-08'] and command[2] in ['test', 'build'] and
            command[command.index('--target-dir') + 1] == str(target), 'completed host command names another target')
    require(report['raw_log'] == str((work / 'test.log').relative_to(ROOT)) and
            plan['frozen'] == report['frozen'] and bool(plan['frozen']), 'workspace-check input/log mapping differs')
    require(report['workspace_passed'] > 0 and not any(t['failed'] for t in report['tests']) and
            sum(t['passed'] for t in report['tests']) == report['workspace_passed'] and
            sum(t['ignored'] for t in report['tests']) == report['workspace_ignored'], 'workspace-check test counts differ')
    return work, target


def workspace_check(run_id, sha):
    require(Path(run_id).name == run_id and run_id not in ['', '.', '..'], 'invalid workspace-check ID')
    work = ROOT / '.work' / run_id
    plan_path, status_path = work / 'plan.json', work / 'status.json'
    report_path = ROOT / 'results' / run_id / 'summary.json'
    plan, status, report = [json.loads(p.read_text()) for p in [plan_path, status_path, report_path]]
    work, target = validate_identity(run_id, plan, status, report)
    require(work.resolve(strict=True) == work and target.resolve(strict=True) == target and target.is_dir(),
            'noncanonical workspace-check root or target')
    require(sha(plan_path) == report['source_manifest_sha256'], 'workspace-check plan changed')
    log = ROOT / report['raw_log']
    require(sha(log) == report['raw_log_sha256'], 'workspace-check test log changed')
    counts = [tuple(map(int, match)) for match in re.findall(
        r'test result: .*? (\d+) passed; (\d+) failed; (\d+) ignored;', log.read_text())]
    require(counts == [(t['passed'], t['failed'], t['ignored']) for t in report['tests']],
            'workspace-check log/test totals differ')
    proofs = [plan_path, status_path, report_path, log, Path(__file__).resolve()]
    for name, expected in plan['frozen'].items():
        relative = Path(name)
        require(not relative.is_absolute() and '..' not in relative.parts, 'invalid archived input path')
        path = work / 'source' / relative
        require(path.resolve(strict=True) == path and path.is_file() and sha(path) == expected,
                'workspace-check archived input changed: ' + name)
        proofs.append(path)
    # Only inspect old process identities. PID reuse is not permission to signal.
    process = subprocess.run(['ps', '-p', str(status['pid']) + ',' + str(status['child_pid']),
        '-o', 'pid,ppid,lstart,command'], capture_output=True, text=True)
    require(process.returncode in [0, 1] and not process.stderr and
            not any(run_id in line for line in process.stdout.splitlines()[1:]),
            'workspace check is still live or process inspection failed')
    supervisor_path = ROOT / '.work/experiments' / run_id / 'status.json'
    if supervisor_path.exists():
        supervisor = json.loads(supervisor_path.read_text())
        command = supervisor['command']
        require(supervisor['owner'] == supervisor['cwd'] == str(ROOT) and
                supervisor['status'] == 'finished' and supervisor['returncode'] == 0 and
                Path(command[1]).name == 'check_workspace.py' and
                command[command.index('--run-id') + 1] == run_id,
                'workspace-check supervisor is not successfully terminal')
        supervisor_plan = supervisor_path.with_name('plan.json')
        require(sha(supervisor_plan) == supervisor['plan_sha256'], 'workspace-check supervisor plan changed')
        proofs += [supervisor_path, supervisor_plan]
    installed = report.get('installed_tool')
    if installed:
        directory, _ = installed_tools(installed['tool_key'])
        ready = directory / 'ready.json'
        require(json.loads(ready.read_text()) == installed['binaries'], 'installed host tool differs')
        proofs.append(ready)
        for name, expected in installed['binaries'].items():
            require(sha(target / 'release' / name) == expected, 'host build output differs from installed tool')
            proofs += [directory / name, target / 'release' / name]
        build_log = work / 'build.log'
        require(installed['build_log'] == str(build_log.relative_to(ROOT)) and
                sha(build_log) == installed['build_log_sha256'], 'host build log changed')
        proofs.append(build_log)
    verified = dict(kind='completed host workspace check', tests_passed=report['workspace_passed'],
        tests_ignored=report['workspace_ignored'], archived_inputs=len(plan['frozen']),
        installed_tool=installed, source_commit=plan['source_commit'], performance_measurement=False)
    return target, {str(p.relative_to(ROOT)): sha(p) for p in proofs}, verified
