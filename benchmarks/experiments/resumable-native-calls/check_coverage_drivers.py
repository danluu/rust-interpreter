#!/usr/bin/env python3
"""Check explicit replay/TLS options and preservation of the full TLS case matrix."""
import argparse
import ast
import fcntl
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from qualify_native_execution import require, sha, write


def assigned(node, name):
    return isinstance(node, ast.Assign) and any(isinstance(n, ast.Name) and n.id == name for n in node.targets)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['.', '..'], 'invalid run ID')
    lock = (ROOT / '.work/benchmark.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    old_path = ROOT / '.work/validate_local_memory_forwarding_tls_01.py'
    tls = ROOT / 'scripts/validate_tls_destructors.py'
    survey = ROOT / 'scripts/survey_audit_execution.py'
    audit = ROOT / 'scripts/audit_test_lowering.py'
    coordinator = ROOT / 'scripts/qualify_test_bodies.py'
    archived_audit = ROOT / '.work/audit_local_memory_forwarding_01.py'
    def assertions(path):
        return [ast.dump(n, include_attributes=False) for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.Assert)]
    require(assertions(audit) == assertions(archived_audit), 'original audit assertions changed')
    compile(coordinator.read_text(), str(coordinator), 'exec')
    old = ast.parse(old_path.read_text()).body
    new = next(n for n in ast.parse(tls.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == 'main').body
    old_cases = old[next(i for i, n in enumerate(old) if assigned(n, 'seeds')):
                    next(i for i, n in enumerate(old) if assigned(n, 'summary'))]
    new_cases = new[next(i for i, n in enumerate(new) if assigned(n, 'seeds')):
                    next(i for i, n in enumerate(new) if assigned(n, 'vm_counts'))]
    require([ast.dump(n, include_attributes=False) for n in old_cases] ==
            [ast.dump(n, include_attributes=False) for n in new_cases], 'TLS case generation or expectations changed')
    checks = []
    for script, required in [(tls, ['--run-id', 'unused', '--tool-key', 'unused']),
                             (survey, ['--run-id', 'unused', '--collection', 'unused']),
                             (coordinator, ['--run-id', 'unused', '--tool-key', 'unused', '--project', 'fre',
                                 '--package', 'fre-kernels', '--entries', 'unused', '--discovery-record', 'unused'])]:
        cases = [(['--help'], 0, '--jit-resumable-calls'),
                 ([*required, '--jit-resumable-calls', '--jit-native-calls'], 2, 'resumable calls exclude'),
                 ([*required, '--jit-native-call-stubs'], 2, 'native Call stubs require')]
        if script == survey:
            cases.append(([*required, '--allocation-limit', '-1'], 2, 'allocation limit must fit'))
        if script == coordinator:
            cases += [([*required, '--batch-size', '0'], 2, 'batch size must be'),
                      ([*required, '--run-try-callbacks'], 2, 'try callbacks require'),
                      ([*required, '--guest-mir-inline-scale', '8'], 2, 'requires MIR level 3')]
        for flags, code, expected in cases:
            command = [sys.executable, str(script), *flags]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
            require(result.returncode == code and expected in result.stdout + result.stderr, 'coverage driver CLI failed')
            checks.append(dict(command=command, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr))
        command = [sys.executable, '-O', str(script), *required]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
        require(result.returncode == 2 and 'enabled Python assertions' in result.stderr, 'disabled assertions accepted')
        checks.append(dict(command=command, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr))
    for flags, code, expected in [(['--help'], 0, '--tool-key'),
            (['--project', 'fre', '--package', 'fre-kernels', '--entries', 'unused', '--discovery-record', 'unused'],
             2, 'enabled Python assertions')]:
        command = [sys.executable, *(['-O'] if code else []), str(audit), *flags]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
        require(result.returncode == code and expected in result.stdout + result.stderr, 'audit CLI validation failed')
        checks.append(dict(command=command, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr))
    out = ROOT / 'results' / args.run_id
    out.mkdir(exist_ok=False)
    paths = [Path(__file__), old_path, tls, survey, audit, coordinator, archived_audit, ROOT / 'scripts/qualify_native_execution.py']
    write(out / 'summary.json', dict(status='passed', original_tls_case_matrix_unchanged=True,
        cli_checks=checks, frozen={str(p.relative_to(ROOT)): sha(p) for p in paths},
        original_audit_assertions_unchanged=True, actual_coverage_execution=False, performance_measurement=False))
    print(json.dumps(dict(status='passed', cli_checks=len(checks), original_tls_case_matrix_unchanged=True)))


if __name__ == '__main__':
    main()
