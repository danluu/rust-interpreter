"""Restrict whole host-cache retirement to completed, unpublished debug checks."""
import json
from pathlib import Path

from verify_repeated_workflow import require
from workspace_check_evidence import workspace_check


def validate_debug_cache(root, run_id, target, proofs, verified, report, status):
    require(target == root / '.work/diagnostic-builds' / run_id and
            target.resolve(strict=True) == target and target.is_dir(), 'host cache target differs')
    command = report['command']
    require(command[:3] == ['cargo', '+nightly-2026-09-08', 'test'] and
            command.count('--workspace') == 1 and '--release' not in command and
            not any(arg == '--profile' or arg.startswith('--profile=') for arg in command) and
            status['command'] == command, 'expected a completed default-debug workspace test')
    require(verified['kind'] == 'completed host workspace check' and
            verified['installed_tool'] is None and report.get('installed_tool') is None,
            'published host tools are excluded from whole-cache retirement')
    require(bool(proofs), 'host cache has no external evidence')
    for name in proofs:
        relative = Path(name)
        path = root / relative
        require(not relative.is_absolute() and '..' not in relative.parts and
                path.resolve(strict=True) == path and path.is_file() and
                not path.is_relative_to(target), 'host qualification evidence would be retired or is noncanonical')


def debug_workspace_cache(root, run_id, sha):
    target, proofs, verified = workspace_check(run_id, sha)
    report = json.loads((root / 'results' / run_id / 'summary.json').read_text())
    status = json.loads((root / '.work' / run_id / 'status.json').read_text())
    validate_debug_cache(root, run_id, target, proofs, verified, report, status)
    require(all(sha(root / name) == digest for name, digest in proofs.items()),
            'host qualification changed during cache selection')
    return target, proofs, verified
