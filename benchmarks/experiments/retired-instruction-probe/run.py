#!/usr/bin/env python3
"""Launch only an owned original test to discover local counter availability."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write

RUN = 'retired-instruction-probe-01'
NAME = 'token_phrase::tests::exhaustive_small_byte_semantics_match_pinned_regex'


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 3)
        reference = ROOT / 'results/composed-development-edit-anchor-01/summary.json'
        summary = json.loads(reference.read_text())
        assert summary['status'] == 'passed' and summary['source_restored']
        raw = ROOT / summary['raw']
        records = raw / 'records.json'
        assert sha(records) == summary['records_sha256']
        row, = [r for r in json.loads(records.read_text()) if r['mode'] == 'native' and r['phase'] == 'restored']
        binary, = re.findall(r'Running unittests .* \((.*)\)', row['stderr'])
        binary = Path(binary).resolve(strict=True)
        assert binary.is_relative_to(raw / 'native') and row['returncode'] == 0
        terminal = json.loads((ROOT / '.work/experiments/composed-development-edit-anchor-01/status.json').read_text())
        assert terminal['owner'] == str(ROOT) and terminal['status'] == 'finished' and terminal['returncode'] == 0
        xctrace = Path(subprocess.check_output(['xcrun', '--find', 'xctrace'], text=True).strip()).resolve(strict=True)
        paths = [Path(__file__), Path(__file__).with_name('PLAN.md'), reference, records, binary, xctrace,
                 ROOT / 'scripts/workflow_io.py', ROOT / 'scripts/compare_saved_runtime.py']
        frozen = {str(p): sha(p) for p in paths}
        work = ROOT / '.work' / RUN
        work.mkdir(exist_ok=False)
        target_output = work / 'target.stdout'
        command = [xctrace, 'record', '--template', 'CPU Counters', '--output', work / 'native.trace',
                   '--time-limit', '5s', '--target-stdout', target_output, '--no-prompt', '--launch', '--',
                   binary, '--exact', NAME, '--test-threads=1']
        command = list(map(str, command))
        write(work / 'plan.json', dict(owner=str(ROOT), frozen=frozen, command=command, test=NAME,
                                      scope='one owned launched test process', performance_measurement=False))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        child, stdout, stderr = capture(command, cwd=ROOT, env=env, receipt_path=work / 'active.json',
                                       receipt=dict(kind='owned counter capability probe'))
        (work / 'record.stdout').write_text(stdout)
        (work / 'record.stderr').write_text(stderr)
        commands = [dict(command=command, pid=child.pid, returncode=child.returncode)]
        write(work / 'commands.json', commands)
        result = dict(status='unavailable', recording_returncode=child.returncode,
                      performance_measurement=False, retired_instruction_comparison=False)
        if child.returncode == 0:
            command = list(map(str, [xctrace, 'export', '--input', work / 'native.trace', '--toc',
                                    '--output', work / 'toc.xml']))
            exported, out, err = capture(command, cwd=ROOT, env=env, receipt_path=work / 'active.json',
                                        receipt=dict(kind='counter table discovery'))
            (work / 'export.stdout').write_text(out)
            (work / 'export.stderr').write_text(err)
            commands.append(dict(command=command, pid=exported.pid, returncode=exported.returncode))
            write(work / 'commands.json', commands)
            result.update(status='recorded-needs-event-validation' if exported.returncode == 0 else 'export-failed',
                          export_returncode=exported.returncode)
        assert all(sha(p) == digest for p, digest in frozen.items())
        evidence = {p.name: sha(p) for p in work.iterdir() if p.is_file() and p.name != 'active.json'}
        result.update(raw=str(work.relative_to(ROOT)), evidence=evidence,
                      limitation='Availability only. Actual event tables, process scope and original test completion require inspection.')
        out = ROOT / 'results' / RUN
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', result)
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
