#!/usr/bin/env python3
"""Preserve the first copy held-out history stopped by its disk guard."""
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_repeated_workflow import require
from workflow_io import write_json

RUN = 'resumable-copy-heldout-01-case-01'
LABEL = 'nushell-type-relations'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        experiment = ROOT / '.work/experiments' / RUN
        corpus = ROOT / '.work/corpus-runs' / RUN
        raw = ROOT / '.work/runs' / (RUN + '-' + LABEL)
        status, controller = read(experiment / 'status.json'), read(corpus / 'status.json')
        require(status['owner'] == str(ROOT) and status['cwd'] == str(ROOT) and
                status['status'] == 'finished' and status['returncode'] == 1,
                'expected terminal owned failed supervisor')
        require(controller['status'] == 'failed' and controller['completed'] == [] and
                controller['case'] == LABEL and controller['child_returncode'] == 1,
                'unexpected corpus termination')
        require(sha(experiment / 'plan.json') == status['plan_sha256'] and
                sha(experiment / 'command.log') == status['log_sha256'],
                'supervisor evidence changed')
        log = (corpus / (LABEL + '.log')).read_text()
        reason = 'insufficient free disk: 8408752128 bytes; no child started or automatic cleanup attempted'
        require(reason in log and 'No space left on device' not in log,
                'expected pre-command space rejection, not ENOSPC')
        plan = read(corpus / 'plan.json')
        for path, digest in plan['frozen'].items():
            require(sha(ROOT / path) == digest, 'measured input changed: ' + path)
        active = read(raw / 'active-command.json')
        rows, checks = read(raw / 'records.json'), read(raw / 'check-records.json')
        require([(r['cycle'], r['state'], r['mode']) for r in rows] ==
                [(0, 0, 'native'), (0, 0, 'baseline'), (0, 0, 'candidate'),
                 (0, -1, 'candidate'), (0, -1, 'baseline')], 'partial sequence differs')
        require(len(checks) == 1 and checks[0]['cycle'] == 0 and
                checks[0]['state'] == 0 and checks[0]['returncode'] == 0,
                'partial checking control differs')
        require(active['status'] == 'finished' and active['command'] == rows[-1]['calls'][0]['command'] and
                active['pid'] == rows[-1]['calls'][0]['pid'] and active['returncode'] == 1,
                'last executed command is not the completed wrong-edit control')
        snapshots = {}
        for row in rows:
            call = row['calls'][0]
            require(len(row['calls']) == 1 and (call['returncode'] == 0) == (row['state'] == 0),
                    'unexpected partial command outcome')
            if row['mode'] == 'native':
                require('14 passed' in call['stdout'], 'native originals did not pass')
                continue
            if row['state'] == 0:
                require(call['stdout'].strip() == '0', 'custom originals did not pass')
            else:
                require('rust-interp-vm: guest trap: core::panicking::panic at crates/nu-protocol/src/ty.rs:452:17: 452:54 in ty::tests::subtype_relation::test_any_is_top_type[]' in call['stderr'],
                        'wrong edit did not reach the original top-type assertion')
            require(len(row['artifacts']) == 1, 'missing partial artifact')
            item = row['artifacts'][0]
            path = ROOT / item['path']
            require(path.resolve() == path and path.is_relative_to(raw / 'artifacts') and
                    sha(path) == item['sha256'] and path.stat().st_size == item['bytes'],
                    'partial snapshot changed')
            require(item['sha256'] == call['launch']['artifact_sha256'], 'executed artifact differs')
            snapshots[item['path']] = item['sha256']
        for state in [0, -1]:
            pair = [r for r in rows if r['state'] == state and r['mode'] != 'native']
            require(pair[0]['source_sha256'] == pair[1]['source_sha256'] and
                    pair[0]['artifacts'][0]['sha256'] == pair[1]['artifacts'][0]['sha256'],
                    'partial custom pair differs')
        source = ROOT / '.work/sources/nushell'
        marker = read(source / '.rust-interp-owned.json')
        pin = read(ROOT / 'benchmarks/corpus.json')['projects']['nushell']['revision']
        require(marker['owner'] == str(ROOT) and marker['revision'] == pin,
                'source ownership differs')
        require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == pin and
                not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source, text=True).strip(),
                'source revision or restoration differs')
        source_file = source / 'crates/nu-protocol/src/ty.rs'
        require(sha(source_file) == rows[0]['source_sha256'], 'original source was not restored')
        pids = [status['supervisor_pid'], status['child_pid'], controller['child_pid'], active['pid']]
        process = subprocess.run(['ps', '-p', ','.join(map(str, pids)), '-o',
                                  'pid,ppid,lstart,tty,command'], capture_output=True, text=True)
        require(process.returncode in [0, 1] and not process.stderr and
                not any(RUN in line for line in process.stdout.splitlines()[1:]),
                'original workload still live or process check failed')
        paths = [experiment / name for name in ['plan.json', 'status.json', 'command.log', 'supervisor.log']]
        paths += [corpus / name for name in ['plan.json', 'status.json', LABEL + '.log']]
        paths += [raw / name for name in ['records.json', 'check-records.json', 'source-transitions.json', 'active-command.json']]
        paths += [ROOT / 'results/resumable-copy-heldout-01-case-01-preflight/summary.json']
        out = ROOT / 'results/resumable-copy-heldout-01-case-01-stop'
        out.mkdir(exist_ok=False)
        evidence = {}
        for i, path in enumerate(paths):
            payload = path.read_bytes()
            name = 'evidence-%02d%s' % (i, path.suffix)
            (out / name).write_bytes(payload)
            evidence[str(path.relative_to(ROOT))] = dict(snapshot=name,
                sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload))
        result = dict(status='incomplete: pre-command disk guard', run_id=RUN,
            assessed_at=time.time(), reason=reason, primary_records=len(rows), check_records=len(checks),
            measured_successful_edit_pairs=0, snapshots=snapshots, source_pin=pin,
            restored_source_sha256=sha(source_file), source_restored=True,
            completed_workflows=0, retained=False, evidence=evidence,
            process_check=dict(command=process.args, returncode=process.returncode, stdout=process.stdout),
            original_records_unchanged=True, cache_cleanup_performed=False, process_signals_sent=False,
            assessor_sha256=sha(Path(__file__)))
        write_json(out / 'summary.json', result)
        (out / 'assessment.md').write_text(
            '# Nushell held-out history stopped by the space guard\n\n'
            'Five primary commands and one check completed. All fourteen original bodies passed in '
            'native, baseline and candidate modes; both custom wrong-edit controls failed at assertions. '
            'Four executed snapshots verify. No successful production-edit pair was measured.\n\n'
            'The guard rejected the next command at 7.83 GiB free, below its 8 GiB floor. '
            'The source was restored automatically and matches its pinned original. '
            'This was a pre-command rejection, not a disk-full write or an engine failure.\n\n'
            'The launch preflight omitted the 8 GiB running floor from its total reserve. '
            'A retry needs a corrected preflight and a new history ID; this incomplete history '
            'and its raw evidence remain unchanged and excluded from performance gates.\n')
        print(json.dumps({k: result[k] for k in ['status', 'primary_records', 'check_records',
                                                'measured_successful_edit_pairs', 'source_restored']}))


if __name__ == '__main__':
    main()
