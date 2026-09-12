"""Narrow history mapping for the declared Ruff disk-guard retry."""
import copy
import json
import math
import os
import threading
import time

from build_relocation import ROOT, HERE, read, sha, require
from heldout_controls import case
from heldout_space import estimate
from report_heldouts import receipt_controls

ORIGINAL = 'aggregate-relocation-heldout-01-ruff'
RETRY = ORIGINAL + '-retry-01'
RUNNER = 'benchmarks/experiments/aggregate-byte-writes/run_heldout_recovery.py'
STOP = ROOT/'results/aggregate-relocation-ruff-stop-01/summary.json'
QUALIFICATION = ROOT/'results/aggregate-relocation-recovery-controls-01/summary.json'
CADENCE = 5.0
EXTRA_RESERVE = 8 * 1024**3


def run_id(label):
    require(label in ['ruff', 'nushell'], 'case outside recovery amendment')
    return RETRY if label == 'ruff' else 'aggregate-relocation-heldout-01-nushell'


def stop_evidence():
    r = read(STOP)
    require(r['status'] == 'incomplete: pre-command disk guard' and
            r['run_id'] == ORIGINAL and r['completed_cycles'] == 1 and
            r['primary_records'] == 21 and r['check_records'] == 7 and
            r['measured_successful_edit_pairs'] == 5 and r['source_restored'] is True and
            r['included_in_performance_gate'] is False, 'unexpected original stop')
    evidence = {str(STOP.relative_to(ROOT)): sha(STOP)}
    for path, item in r['evidence'].items():
        snapshot = STOP.parent/item['snapshot']
        require(sha(ROOT/path) == sha(snapshot) == item['sha256'], 'stop evidence changed')
        evidence[path] = item['sha256']
        evidence[str(snapshot.relative_to(ROOT))] = item['sha256']
    for path, digest in r['snapshots'].items():
        require(sha(ROOT/path) == digest, 'original stopped artifact changed')
        evidence[path] = digest
    original = read(ROOT/'.work'/ORIGINAL/'plan.json')
    require(all(sha(ROOT/p) == h for p, h in original['frozen'].items()),
            'original measured sources changed')
    evidence.update(original['frozen'])
    amendment = HERE/'HELDOUT-RETRY-NEXT.md'
    evidence[str(amendment.relative_to(ROOT))] = sha(amendment)
    return evidence


def command(label):
    # Starting from the preserved command prevents drift in any benchmark flag.
    c = read(ROOT/'.work'/ORIGINAL/'plan.json')['command'].copy()
    require(c[1:4] == [str(ROOT/'scripts/bench_e2e_workflow.py'), '--run-id', ORIGINAL],
            'unexpected original command')
    c[3] = run_id(label)
    if label == 'nushell':
        require(case('ruff')['flags'] == [], 'original suffix is no longer empty')
        for flag, value in [('--project', case(label)['project']),
                            ('--workflow', case(label)['workflow'])]:
            c[c.index(flag)+1] = value
        c += case(label)['flags']
    return c


def admission_estimate(label):
    needed, evidence = estimate(label)
    needed = dict(needed)
    needed['retry_extra_reserve_bytes'] = EXTRA_RESERVE if label == 'ruff' else 0
    needed['minimum_free_bytes'] += needed['retry_extra_reserve_bytes']
    return needed, evidence


def free_bytes():
    fs = os.statvfs(ROOT)
    return fs.f_bavail * fs.f_frsize


class SpaceMonitor:
    """An owned thread; Event.stop never signals or controls a process."""
    def __init__(self, path, child_pid, cadence=CADENCE, sample=free_bytes):
        self.path, self.child_pid = path, child_pid
        self.cadence, self.sample = cadence, sample
        self.done = threading.Event()
        self.thread = threading.Thread(target=self._run, name='heldout-free-space')
        self.error = None

    def _run(self):
        try:
            with self.path.open('x') as log:
                sequence = 0
                while True:
                    stopped = self.done.is_set() and sequence > 0
                    row = dict(sequence=sequence, time=time.time(), monotonic=time.monotonic(),
                        pid=os.getpid(), thread_id=threading.get_native_id(),
                        child_pid=self.child_pid, cadence_seconds=self.cadence,
                        event='stopped' if stopped else 'sample', free_bytes=self.sample())
                    log.write(json.dumps(row)+'\n')
                    log.flush()
                    sequence += 1
                    if stopped:
                        break
                    self.done.wait(self.cadence)
        except BaseException as error:
            self.error = repr(error)

    def start(self):
        self.thread.start()

    def stop(self):
        self.done.set()
        self.thread.join()
        require(self.error is None, 'space monitor failed: '+str(self.error))


def monitor_controls(rows, controller):
    require(len(rows) >= 2 and rows[-1]['event'] == 'stopped' and
            all(r['event'] == 'sample' for r in rows[:-1]), 'monitor completion differs')
    for index, row in enumerate(rows):
        require(row['sequence'] == index and row['pid'] == controller['pid'] and
                row['child_pid'] == controller['child_pid'] and row['thread_id'] > 0 and
                row['thread_id'] == rows[0]['thread_id'] and row['cadence_seconds'] == CADENCE and
                type(row['free_bytes']) is int and row['free_bytes'] >= 0 and
                all(math.isfinite(row[k]) for k in ['time', 'monotonic']) and
                controller['child_started_at'] <= row['time'] <= controller['monitor_finished_at'],
                'monitor identity or sample differs')
        if index:
            require(rows[index-1]['monotonic'] <= row['monotonic'], 'monitor order differs')
    require(controller['child_finished_at'] <= rows[-1]['time'] <=
            controller['monitor_finished_at'] <= controller['finished_at'],
            'monitor stopped before child or after controller')


def recovery_receipts(label, launch, supervisor, plan, controller, rows):
    run = run_id(label)
    require(launch['command'][1:] == [RUNNER, '--case', label] and
            supervisor['command'] == launch['command'], 'recovery launch differs')
    require(plan['command'] == controller['command'] == command(label), 'recovery command differs')
    require(plan['recovery'] == dict(original_run=ORIGINAL, retry_run=RETRY,
            excluded_partial_pairs=5, predecessor=(
                'aggregate-relocation-heldout-01-nushell-type-relations' if label == 'ruff' else RETRY)),
            'recovery history or predecessor differs')
    needed, _ = admission_estimate(label)
    require(plan['admission']['estimate'] == needed and
            plan['admission']['observed_free_bytes'] >= needed['minimum_free_bytes'] and
            0 <= controller['child_started_at']-plan['admission']['checked_at'] < 60,
            'recovery reserve or live admission differs')
    # Validate the exact amended identities above before applying the original
    # receipt validator to copies. Never rewrite a recorded receipt on disk.
    normalized = copy.deepcopy([launch, supervisor, plan, controller])
    for receipt in normalized[:2]:
        receipt['command'][1] = 'benchmarks/experiments/aggregate-byte-writes/run_heldout.py'
    for receipt in normalized[2:]:
        receipt['command'][3] = 'aggregate-relocation-heldout-01-'+label
    receipt_controls(label, *normalized)
    require(plan['command'][3] == run, 'unexpected actual history')
    monitor_controls(rows, controller)
