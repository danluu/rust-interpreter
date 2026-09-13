"""Bind actual audit, leaf-inline and audit-parity results; no other scopes."""
from pathlib import Path
import json
import math
import re
import time
from validate_local_export_extra import ROOT, B, KEY, BASE, CONTROLS, read, sha, bind, verify, checked_controls, write_new


def timestamp(value):
    assert type(value) in (int, float) and math.isfinite(value) and value > 0
    return value


controls = checked_controls()
proofs = dict(controls['proofs'])
bind(proofs, CONTROLS)
checks = {}
for mode, public_name in [('audit', 'audit-artifacts'), ('inline', 'leaf-inline'), ('audit-parity', 'audit-parity')]:
    label = 'local-export-' + mode + '-tests'
    execution = read(B / (label + '.json'))
    validation = read(B / ('local-export-' + mode + '-validation.json'))
    assert execution['returncode'] == 0 and execution['owner'] == 'build-general-20260912'
    assert execution['cwd'] == str(ROOT) and execution['command'] == controls['commands'][mode]
    assert type(execution['child_pid']) is int and execution['child_pid'] > 0
    assert validation['controller_pid'] == execution['child_pid'] and validation['status'] == 'passed'
    assert validation['controls_sha256'] == sha(CONTROLS)
    assert timestamp(controls['created_at']) <= timestamp(execution['started_at']) <= timestamp(validation['started_at'])
    assert timestamp(validation['started_at']) <= timestamp(validation['finished_at']) <= timestamp(execution['finished_at'])
    summary = read(B / (label + '.log'))
    assert summary['commands'] == controls['expected_commands'][mode]
    for path in [B / (label + '.json'), B / (label + '.log'), B / ('local-export-' + mode + '-validation.json')]:
        bind(proofs, path)
    if mode == 'audit-parity':
        assert summary['tool_keys'] == {'baseline': BASE, 'candidate': KEY}
        assert summary['retained_artifact_pairs'] == 8 and validation['retained_artifact_pairs'] == 8
        assert len(summary['configurations']) == 4 and all(row['normalized_reports_identical'] is True for row in summary['configurations'])
        raw = B / 'local-export-audit-parity'
    else:
        assert summary['tool_key'] == validation['tool_key'] == KEY
        raw = ROOT / summary['raw'] if mode == 'audit' else Path(summary['work'])
        prefix = 'audit-artifact-validation' if mode == 'audit' else 'leaf-inline-launcher-validation'
        assert raw.parent == ROOT / '.work' and re.fullmatch(prefix + r'-\d+', raw.name)
        if mode == 'audit':
            assert summary['source_restored'] is True and summary['executed_during_collection'] is False
            assert validation['summary'] == summary and validation['prior_top_level_restored'] is True
            retained = B / 'local-export-audit-top-level-validation.json'
            assert read(retained) == summary
            bind(proofs, retained)
            if 'prior_top_level_sha256' in validation:
                bind(proofs, B / 'local-export-audit-prior-top-level.json', validation['prior_top_level_sha256'])
        else:
            assert summary['status'] == 'passed'
    assert raw.resolve(strict=True) == raw
    records_path = raw / 'records.json'
    records = read(records_path)
    assert len(records) == summary['commands']
    bind(proofs, records_path)
    if mode == 'inline':
        assert ('unsupported-old-exporter' in [row['label'] for row in records]) == controls['optional_legacy_exporter_check']
    artifacts = set()
    for row in records:
        if mode == 'audit-parity':
            path = Path(row['report_path'])
            assert path.is_relative_to(raw)
            bind(proofs, path, row['report_sha256'])
            report = read(path)
        else:
            try:
                report = json.loads(row['stdout'])
            except (ValueError, KeyError):
                continue
        if not isinstance(report, dict) or report.get('kind') != 'lowering-audit' or 'artifacts' not in report:
            continue
        directory = Path(report['artifacts']['directory'])
        assert directory.is_relative_to(ROOT / '.work')
        for entry in report['entries']:
            if 'artifact' not in entry:
                continue
            name = entry['artifact']['file']
            assert Path(name).name == name
            path = directory / name
            assert path.stat().st_size == entry['artifact']['bytes']
            bind(proofs, path, entry['artifact']['sha256'])
            artifacts.add(str(path))
    if mode != 'audit-parity':
        for name in ['Cargo.toml', 'Cargo.lock', 'src/lib.rs', 'selection.json']:
            bind(proofs, raw / name)
    else:
        bind(proofs, raw / 'selection.json')
        assert len(artifacts) == 16
    checks[public_name] = dict(status='passed', commands=len(records), raw=str(raw.relative_to(ROOT)),
        retained_artifacts_rehashed=len(artifacts))
    if mode == 'audit-parity':
        checks[public_name]['retained_artifact_pairs'] = 8

checked_controls()
verify(proofs)
receipt = dict(status='passed', tool_key=KEY, baseline_tool_key=BASE,
    source_commit=controls['source_commit'], checks=checks,
    completed_commands=sum(row['commands'] for row in checks.values()),
    optional_legacy_exporter_check=controls['optional_legacy_exporter_check'],
    proofs=proofs, completed_at=time.time(), performance_claim=False,
    scope='Audit artifacts, leaf-inline controls and eight paired audit exports only; panic structural coverage and reuse/cache qualification are separate.')
write_new(B / 'local-export-audit-inline-passed.json', receipt)
print(json.dumps({'status': 'passed', 'tool_key': KEY, 'checks': checks}, indent=2))
