"""Seal the first parser support failure without repeating either command."""
import json
from pathlib import Path
import subprocess
import sys

from probe import ROOT, PIN, fingerprint, native_inventory, native_target
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import require_space, write_json as write


def main():
    run = 'pgrust-parser-support-01'
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        work = ROOT / '.work' / run
        supervisor = ROOT / '.work/experiments' / run
        status = json.loads((supervisor / 'status.json').read_text())
        assert status['status'] == 'finished' and status['returncode'] == 1
        assert sha(supervisor / 'command.log') == status['log_sha256']
        plan = json.loads((work / 'plan.json').read_text())
        records = json.loads((work / 'records.json').read_text())
        assert [(r['stage'], r['returncode']) for r in records] == [('native', 0), ('custom', 101)]
        for row in records:
            for stream in ['stdout', 'stderr']:
                assert sha(work / (row['stage'] + '.' + stream)) == row[stream + '_sha256']
        assert all(fingerprint(ROOT / p) == digest for p, digest in plan['frozen'].items())
        source = ROOT / '.work/sources/pgrust'
        assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == PIN
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source).strip()
        out = (work / 'native.stdout').read_text()
        names = native_inventory(out)
        assert names == json.loads((work / 'native-tests.json').read_text())
        executable = native_target(out, source / 'crates/backend/parser/gram_core/src/lib.rs')
        assert str(executable.relative_to(ROOT)) == records[0]['executable']
        assert sha(executable) == records[0]['executable_sha256']
        command = records[1]['command']
        assert [command[i + 1] for i, item in enumerate(command) if item == '--entry'] == names
        error = '<std::boxed::Box<F, A> as std::ops::FnOnce<Args>>::call_once: virtual call requires a fat-pointer receiver'
        assert error in (work / 'custom.stderr').read_text()
        assert not (work / 'suite.json').exists()
        result = ROOT / 'results' / (run + '-failure')
        result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='custom lowering failed', commands=2,
              native_tests_passed=114, custom_guest_tests=0, source_edits=0,
              source_unchanged=True, frozen_inputs_verified=len(plan['frozen']),
              failure=error, performance_measurement=False, audit_guest_commands=0,
              raw=str(work.relative_to(ROOT)), tool_key=plan['tool_key'],
              plan_sha256=sha(work / 'plan.json'), records_sha256=sha(work / 'records.json'),
              test_names_sha256=sha(work / 'native-tests.json'),
              supervisor_status_sha256=sha(supervisor / 'status.json'),
              audit_source_sha256=sha(Path(__file__))))
        print('PASS: retained native114/custom lowering failure; all frozen inputs verified; no rerun', flush=True)


if __name__ == '__main__':
    main()
