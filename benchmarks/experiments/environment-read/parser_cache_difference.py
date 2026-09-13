"""Preserve a stopped parser history and structurally compare its saved artifacts."""
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'pgrust-parser-probe'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'pgrust-parser-edits'))
from compare_saved_runtime import acquire_lock, sha
from probe import fingerprint, native_inventory
from states import native_outcomes
from suite_reports import read_report, validate_report, validate_runtime_limits
from workflow_io import capture, require_space, write_json as write


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        raw = ROOT / '.work/pgrust-parser-edits-incremental-01'
        outer = ROOT / '.work/experiments/pgrust-parser-edits-incremental-01'
        terminal = json.loads((outer / 'status.json').read_text())
        assert terminal['status'] == 'finished' and terminal['returncode'] == 1
        assert sha(outer / 'command.log') == terminal['log_sha256']
        assert 'custom A/A or repeated-state artifact differs' in (outer / 'command.log').read_text()
        plan = json.loads((raw / 'plan.json').read_text())
        rows = json.loads((raw / 'records.json').read_text())
        assert len(rows) == 22 and rows[-1]['index'] == 21 and rows[-1]['returncode'] == 0
        assert (rows[-1]['cycle'], rows[-1]['state'], rows[-1]['mode']) == (1, 0, 'custom-a')
        assert all(fingerprint(ROOT / p) == h for p, h in plan['frozen'].items())
        changed = ROOT / '.work/sources/pgrust/crates/backend/parser/gram_core/src/parse.rs'
        assert sha(changed) == plan['original_source_sha256']
        names = native_inventory((ROOT / '.work/pgrust-parser-support-01/native.stdout').read_text())
        outcomes = {}
        for row in rows:
            index = row['index']; success = row['state'] != -1
            assert {k: row[k] for k in plan['schedule'][index]} == plan['schedule'][index]
            assert row['returncode'] == (0 if success else (101 if row['mode'] == 'native' else 1))
            for stream in ['stdout', 'stderr']:
                assert sha(raw / f'{index}.{stream}') == row[stream + '_sha256']
            if row['mode'] == 'native':
                actual = native_outcomes((raw / f'{index}.stdout').read_text(), names, success)
                assert sha(ROOT / row['executable']['path']) == row['executable']['sha256']
            else:
                err = (raw / f'{index}.stderr').read_text()
                launch, = [json.loads(l.split(': ', 1)[1]) for l in err.splitlines() if l.startswith('rust-interp-launch: ')]
                assert launch['tool_key'] == plan['tool_key'] and launch['borrowck_cache'] == 'off'
                report, digest = read_report(raw / f'{index}-suite.json', launch['suite_report_sha256'])
                actual = validate_report(report, names, 'prepared', success)
                validate_runtime_limits(report, 100000000000, 150000, required=True)
                assert report['workers'] == report['requested_workers'] == 2
                if index == 21:
                    row.update(launch=launch, suite_sha256=digest)
                    for kind, suffix in [('artifact', 'rbc'), ('entry_catalog', 'json')]:
                        path = Path(launch[kind + '_path']); digest = launch[kind + '_sha256']
                        assert sha(path) == digest
                        saved = raw / 'artifacts' / (digest + '.' + suffix)
                        if not saved.exists(): shutil.copy2(path, saved)
                        assert sha(saved) == digest
                        row[kind] = dict(path=str(saved.relative_to(ROOT)), sha256=digest)
                for kind in ['artifact', 'entry_catalog']:
                    assert sha(ROOT / row[kind]['path']) == row[kind]['sha256']
            row['outcomes'] = actual
            prior = outcomes.setdefault(row['state'], actual)
            assert prior == actual
        assert rows[1]['artifact']['sha256'] == rows[2]['artifact']['sha256'] != rows[21]['artifact']['sha256']
        assert rows[1]['source_sha256'] == rows[21]['source_sha256'] == sha(changed)
        write(raw / 'audited-prefix.json', rows)
        failed = ROOT / 'results/pgrust-parser-edits-incremental-01-failure'; failed.mkdir(exist_ok=False)
        write(failed / 'summary.json', dict(status='repeated-original artifact mismatch', commands=22,
            complete_cycles=1, planned_commands=66, original_tests=114, original_and_restored_tests_passed=114,
            all_executed_outcomes_match_native=True, source_restored=True,
            frozen_inputs_verified=len(plan['frozen']), raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw / 'plan.json'), records_sha256=sha(raw / 'records.json'),
            audited_prefix_sha256=sha(raw / 'audited-prefix.json'), terminal=terminal,
            artifacts=[rows[i]['artifact'] for i in [1, 21]], no_performance_verdict=True))
        work = ROOT / '.work/parser-cache-difference-01'; work.mkdir(exist_ok=False)
        files = [Path(__file__), failed / 'summary.json', raw / 'audited-prefix.json']
        files += list((ROOT / 'crates/bytecode/src').rglob('*.rs'))
        files += [ROOT / 'crates/bytecode/Cargo.toml', *list((ROOT / 'benchmarks/experiments/artifact-diff').glob('*'))]
        frozen = {str(p.relative_to(ROOT)): fingerprint(p) for p in files if p.is_file()}
        write(work / 'plan.json', dict(owner=str(ROOT), frozen=frozen, commands=2, guest_commands=0,
            source_commit='current source hashes in frozen manifest', performance_measurement=False))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                             'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET', 'CARGO_BUILD_BUILD_DIR']}
        env.update(CARGO_TERM_COLOR='never', PYTHONDONTWRITEBYTECODE='1')
        target = ROOT / '.work/fixed-frame-clear-combined-build-01/target'
        commands = [
            ['cargo', '+nightly-2026-09-08', 'build', '--release', '--locked', '--offline', '--jobs', '2',
             '--manifest-path', str(ROOT / 'benchmarks/experiments/artifact-diff/Cargo.toml'), '--target-dir', str(target)],
            [str(target / 'release/artifact-diff'), *[str(ROOT / rows[i]['artifact']['path']) for i in [1, 21]]],
        ]
        records = []
        for index, command in enumerate(commands):
            require_space(ROOT, 8)
            child, out, err = capture(command, cwd=ROOT, env=env, receipt_path=work / 'active.json', receipt=dict(index=index))
            (work / f'{index}.stdout').write_text(out); (work / f'{index}.stderr').write_text(err)
            records.append(dict(command=command, pid=child.pid, returncode=child.returncode,
                stdout_sha256=sha(work / f'{index}.stdout'), stderr_sha256=sha(work / f'{index}.stderr')))
            write(work / 'records.json', records)
            assert child.returncode == 0
        assert all(fingerprint(ROOT / p) == h for p, h in frozen.items())
        report = json.loads((work / '1.stdout').read_text())
        result = ROOT / 'results/parser-cache-difference-01'; result.mkdir(exist_ok=False)
        write(result / 'difference.json', report)
        write(result / 'summary.json', dict(status='passed', commands=2, guest_commands=0,
            decoder_sha256=sha(target / 'release/artifact-diff'), raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work / 'plan.json'), records_sha256=sha(work / 'records.json'),
            difference_sha256=sha(result / 'difference.json'), equivalence_proof=False))
        print('PASS: stopped prefix preserved; typed artifact difference recorded without guest execution', flush=True)


if __name__ == '__main__':
    main()
