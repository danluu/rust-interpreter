"""Exact completed public aggregate-relocation histories, with changed exporters."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from verify_repeated_workflow import require
from workflow_cache_evidence import derive
from workflow_cases import WORKFLOWS, WORKFLOW_VARIANTS

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'aggregate-relocation-heldout-01-'
PUBLIC = {'nushell-type-relations', 'ruff', 'nushell', 'forward-anchored-tls',
          'pgrust-sha1-inline8', 'pgrust'}
QUALIFICATION = 'results/aggregate-relocation-heldout-report-check-01/summary.json'
QUALIFICATION_SHA = 'a1fa4c2cb3287ed74670edd5e143a4f34f07996666d7978c2651a4354d17827f'


def selection(run_id, corpus_id, mode):
    require(corpus_id is None and mode in ['native', 'check', 'baseline', 'candidate'],
            'compiler comparison requires a public workflow mode without a corpus')
    require(isinstance(run_id, str) and run_id.startswith(PREFIX) and run_id[len(PREFIX):] in PUBLIC,
            'compiler comparison is outside the fixed completed-public catalog')
    return run_id[len(PREFIX):]


def cache(root, run_id, corpus_id, mode, sha):
    label = selection(run_id, corpus_id, mode)
    require(root == ROOT, 'compiler comparison belongs to another workspace')
    qualification = root/QUALIFICATION
    require(sha(qualification) == QUALIFICATION_SHA, 'compiler receipt qualification changed')
    read = lambda path: json.loads(path.read_text())
    checked = read(qualification)
    require(checked['status'] == 'passed' and len(checked['rejected']) == 15 and
            all(sha(root/p) == h for p, h in checked['evidence'].items()),
            'qualified compiler receipt sources or evidence changed')
    directory = root/'benchmarks/experiments/aggregate-byte-writes'
    sys.path.insert(0, str(directory))
    try:
        from report_heldouts import collect
        result, proofs = collect(label)
    finally:
        sys.path.remove(str(directory))
    proofs[QUALIFICATION] = QUALIFICATION_SHA
    controller = read(root/'.work'/run_id/'status.json')
    pids = [controller['parent_pid'], controller['pid'], controller['child_pid']]
    process = subprocess.run(['ps', '-p', ','.join(map(str, pids)), '-o',
                              'pid,ppid,lstart,tty,command'], capture_output=True, text=True)
    require(process.returncode in [0, 1] and not process.stderr and
            not any(run_id in line for line in process.stdout.splitlines()[1:]),
            'compiler comparison is still live or process inspection failed')
    report = read(root/'results'/run_id/'summary.json')
    source = root/'.work/sources'/report['project']
    marker = source/'.rust-interp-owned.json'
    owner = read(marker)
    require(report['project'] in ['nushell', 'ruff', 'fre', 'pgrust'] and
            owner['owner'] == str(root) and owner['revision'] == report['revision'] and
            subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == report['revision'] and
            not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source, text=True).strip(),
            'compiler comparison source is not owned, pinned and restored')
    case = (WORKFLOWS[report['project']] if report['workflow'] == 'default' else
            WORKFLOW_VARIANTS[report['project'], report['workflow']])
    require(hashlib.sha256(json.dumps(case, sort_keys=True).encode()).hexdigest() == report['case_sha256'],
            'compiler comparison case changed')
    raw = root/'.work/runs'/run_id
    transitions = read(raw/'source-transitions.json')
    restored = source/case['file']
    require(sha(restored) == transitions[0]['source_sha256'], 'original source was not restored')
    rows, checks = read(raw/'records.json'), read(raw/'check-records.json')
    for row in rows:
        for snapshot in row.get('artifacts', []):
            require(sha(root/snapshot['path']) == snapshot['sha256'],
                    'executed compiler-comparison artifact changed')
    target, identity, snapshots = derive(root, run_id, report, rows, checks,
                                         'check' if mode == 'native' else mode)
    if mode == 'native':
        target, identity = raw/'native', dict(mode='native')
    require(target.resolve(strict=True) == target and target.is_dir(), 'noncanonical compiler cache target')
    for path in [marker, restored, raw/'records.json', raw/'check-records.json',
                 raw/'source-transitions.json', raw/'active-command.json', *snapshots]:
        require(path.resolve(strict=True) == path and not path.is_relative_to(target),
                'compiler cache evidence overlaps its retiring target')
        proofs[str(path.relative_to(root))] = sha(path)
    for name, digest in proofs.items():
        relative, path = Path(name), root/name
        require(not relative.is_absolute() and '..' not in relative.parts and
                path.resolve(strict=True) == path and path.is_file() and
                not path.is_relative_to(target) and sha(path) == digest,
                'compiler cache proof changed, is noncanonical, or overlaps target')
    verified = dict(commands=63, check_commands=21, edited_pairs=15,
        exact_artifact_hashes_verified=42, explicit_controls_verified=True,
        compiler_comparison=True, performance_gate_passed=result['passed'],
        source_restored=True, cache_selection=identity)
    return target, proofs, verified
