"""Retain the single completed original native control after workspace-path parsing failed."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_controls import native_command
from workflow_io import require_space, write_json as write
from screen import native_outcomes


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45); require_space(ROOT, 8)
        raw = ROOT / '.work/guarded-local-facts-screen-token-01'
        outer = ROOT / '.work/experiments/guarded-local-facts-screen-token-01'
        terminal = json.loads((outer / 'status.json').read_text())
        assert terminal['status'] == 'finished' and terminal['returncode'] == 1
        assert terminal['owner'] == str(ROOT)
        assert 'ValueError: not enough values to unpack (expected 1, got 0)' in (outer / 'command.log').read_text()
        plan = json.loads((raw / 'plan.json').read_text())
        assert plan['owner'] == str(ROOT) and plan['expected_commands'] == 40 and plan['case']['package'] == 'fre-kernels'
        assert all(sha(ROOT / p) == h for p, h in plan['frozen'].items())
        rows = json.loads((raw / 'records.json').read_text()); row, = rows
        assert {k: row[k] for k in ['cycle', 'state', 'mode', 'returncode']} == dict(cycle=0, state=0, mode='native', returncode=0)
        source = ROOT / '.work/sources/fre'
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source).strip()
        assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == plan['revision']
        assert sha(source / plan['case']['file']) == row['source_sha256'] == plan['original_source_sha256']
        command = native_command('nightly-2026-09-08', source / 'Cargo.toml', plan['case']['package'],
                                 raw / 'native', 2, 'default', plan['names'])
        command.insert(command.index('--'), '--message-format=json')
        assert list(map(str, command)) == row['command']
        row['outcomes'] = native_outcomes(row['stdout'], plan['names'], True)
        targets = []
        for line in row['stdout'].splitlines():
            if not line.startswith('{'): continue
            unit = json.loads(line)
            if unit.get('reason') == 'compiler-artifact' and unit.get('profile', {}).get('test') and unit.get('executable'):
                if unit['target']['kind'] == ['lib']: targets.append(unit)
        unit, = targets
        executable = Path(unit['executable']).resolve(strict=True)
        library = Path(unit['target']['src_path']).resolve(strict=True)
        assert executable.is_relative_to((raw / 'native').resolve())
        assert library == source / 'crates/fre-kernels/src/lib.rs'
        assert sha(library) == plan['frozen'][str(library.relative_to(ROOT))]
        assert terminal['started_at'] <= executable.stat().st_mtime <= terminal['finished_at']
        work = ROOT / '.work/guarded-local-facts-prefix-audit-01'; work.mkdir(exist_ok=False)
        (work / 'artifacts').mkdir()
        saved = work / 'artifacts' / (sha(executable) + '.native'); shutil.copy2(executable, saved)
        assert sha(saved) == sha(executable)
        row['native_executable'] = dict(path=str(saved.relative_to(ROOT)), sha256=sha(saved))
        row['native_build_executable'] = str(executable.relative_to(ROOT))
        import re
        duration, = re.findall(r'test result: (?:ok|FAILED)\..*?finished in ([0-9.]+)s', row['stdout'])
        row['native_reported_suite_seconds'] = float(duration)
        row['native_build_and_residual_seconds'] = row['seconds'] - float(duration)
        row['outcomes'] = [list(x) for x in row['outcomes']]
        write(work / 'audited-records.json', rows)
        paths = [raw / (name + '.json') for name in ['plan', 'records', 'transitions', 'space']]
        paths += [outer / 'status.json', outer / 'command.log', Path(__file__), library, executable, saved]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        write(work / 'inputs.json', frozen)
        assert all(sha(ROOT / p) == h for p, h in plan['frozen'].items())
        result = ROOT / 'results/guarded-local-facts-screen-token-01-failure'; result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='audited native-control parser failure', commands=1,
            edited_pairs=0, candidate_commands=0, native_tests=len(plan['names']), source_restored=True,
            frozen_inputs_verified=len(plan['frozen']), original_raw=str(raw.relative_to(ROOT)),
            raw=str(work.relative_to(ROOT)), native_cache=str((raw / 'native').relative_to(ROOT)),
            original_plan_sha256=sha(raw / 'plan.json'), original_records_sha256=sha(raw / 'records.json'),
            terminal_sha256=sha(outer / 'status.json'), inputs_sha256=sha(work / 'inputs.json'),
            audited_records_sha256=sha(work / 'audited-records.json'), performance_measurement=False,
            next_action='correct workspace target extraction; retain this native control and run only the 39 unstarted commands'))
        print('PASS: one original native control retained; 12 tests; no edited pairs', flush=True)


if __name__ == '__main__': main()
