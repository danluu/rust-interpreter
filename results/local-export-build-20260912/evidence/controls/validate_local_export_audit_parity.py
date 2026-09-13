from pathlib import Path
import hashlib, json, os, subprocess, time
from validate_local_export_extra import checked_controls, CONTROLS

root = Path(__file__).resolve().parents[2]
b = Path(__file__).resolve().parent
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
controls = checked_controls()
bundles = controls['bundles']
work = b / 'local-export-audit-parity'
work.mkdir()
entries = ['unit_ok', 'tagged_ok', 'niche_ok', 'tagged_err', 'fake_result', 'missing']
selection = work / 'selection.json'
selection.write_text(json.dumps(entries) + '\n')
source = root / 'tests/result_test_fixture.rs'
records = []
receipt = dict(controller_pid=os.getpid(), started_at=time.time(), controls_sha256=sha(CONTROLS), source_sha256=sha(source),
               selection_sha256=sha(selection), tool_keys={mode: value['tool_key'] for mode, value in bundles.items()},
               configurations=[], status='running')
out = b / 'local-export-audit-parity-validation.json'
with out.open('x') as f: json.dump(receipt, f, indent=2)
def normalize(value):
    if isinstance(value, list): return [normalize(v) for v in value]
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in value.items()
                if k not in ['lowering_ms', 'lowering_seconds', 'artifact_retention_seconds']}
    return value
try:
    for index, (inline, retain) in enumerate([(False, False), (True, False), (False, True), (True, True)]):
        reports = {}
        order = ['baseline', 'candidate'] if index % 2 == 0 else ['candidate', 'baseline']
        for mode in order:
            run = work / f'{index}-{mode}'
            run.mkdir()
            report_path = run / 'report.json'
            command = [str(Path(bundles[mode]['directory']) / 'rust-interp-mir-export'), str(source),
                       '--crate-name', 'scalar_output_audit_parity', '--edition=2024', '--test',
                       '--emit=metadata', '-o', str(run / 'program.rmeta')]
            env = os.environ.copy()
            for name in list(env):
                if name.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_')): env.pop(name)
            env.update(RUST_INTERP_OUTPUT=str(report_path), RUST_INTERP_EXPORT_TEST='1',
                       RUST_INTERP_AUDIT_SELECTION=str(selection))
            if inline: env['RUST_INTERP_INLINE_LEAVES'] = '1'
            if retain: env['RUST_INTERP_RETAIN_AUDIT_BODIES'] = '1'
            row = dict(mode=mode, inline=inline, retain=retain, command=command, cwd=str(root),
                       started_at=time.time(), controller_pid=os.getpid(), environment_additions={
                           name: value for name, value in env.items() if name.startswith('RUST_INTERP_')})
            child = subprocess.Popen(command, cwd=root, env=env, stdin=subprocess.DEVNULL,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            row['child_pid'] = child.pid
            (work / 'active-command.json').write_text(json.dumps(row, indent=2) + '\n')
            stdout, stderr = child.communicate()
            row.update(returncode=child.returncode, stdout=stdout, stderr=stderr, finished_at=time.time())
            records.append(row)
            (work / 'records.json').write_text(json.dumps(records, indent=2) + '\n')
            (work / 'active-command.json').write_text(json.dumps(row, indent=2) + '\n')
            assert child.returncode == 0 and 'internal compiler error' not in stderr, row
            report = json.loads(report_path.read_text())
            assert report['strict_frontend'] is True and report['executed'] is False
            assert report['requested'] == 6 and report['lowered'] == 4 and report['blocked'] == 2
            assert [item['entry'] for item in report['entries']] == entries
            assert [item['status'] for item in report['entries']] == ['lowered'] * 4 + ['blocked'] * 2
            assert ('artifacts' in report) == retain
            if retain:
                directory = Path(report['artifacts']['directory'])
                assert directory.is_relative_to(run) and report['artifacts']['files'] == 4
                for item in report['entries'][:4]:
                    artifact = directory / item['artifact']['file']
                    assert sha(artifact) == item['artifact']['sha256']
                    assert artifact.stat().st_size == item['artifact']['bytes']
                report['artifacts']['directory'] = '<generated pack directory>'
            reports[mode] = normalize(report)
            row['report_path'] = str(report_path)
            row['report_sha256'] = sha(report_path)
            (work / 'records.json').write_text(json.dumps(records, indent=2) + '\n')
        assert reports['baseline'] == reports['candidate'], (inline, retain, reports)
        receipt['configurations'].append(dict(inline=inline, retained_bodies=retain, order=order,
                                              normalized_reports_identical=True, paired_artifacts=4 if retain else 0))
        out.write_text(json.dumps(receipt, indent=2) + '\n')
    checked_controls()
    receipt.update(status='passed', commands=len(records), retained_artifact_pairs=8, finished_at=time.time())
except BaseException as error:
    receipt.update(status='failed', error=repr(error), commands=len(records), finished_at=time.time())
    raise
finally:
    out.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
