#!/usr/bin/env python3
"""Check failed-next-child classification and real archive receipt assessments."""
import argparse
import copy
import fcntl
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from assess_archive_batch import assess, preapplication_rejection, sha
from verify_repeated_workflow import require
from workflow_io import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['', '.', '..'], 'invalid run ID')
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        out = ROOT / 'results' / args.run_id
        require(not out.exists(), 'qualification already exists')
        entries = [dict(archive=name) for name in ['one', 'two', 'three']]
        launches = [dict(entry, pid=index + 1, action='apply') for index, entry in enumerate(entries[:2])]
        prefix = '\n'.join(json.dumps(row) for row in launches) + '\n'
        messages = {
            'lock unavailable': 'BlockingIOError: [Errno 35] Resource temporarily unavailable',
            'space preflight rejected': 'RuntimeError: insufficient space to finish a worst-case archive before retiring originals',
        }
        for reason, line in messages.items():
            require(preapplication_rejection(prefix + line, launches, entries, 1) == reason,
                    'recognized next-child failure differs')
        rejected = []

        def reject(label, log=prefix + messages['space preflight rejected'], rows=launches, count=1):
            try:
                preapplication_rejection(log, rows, entries, count)
            except RuntimeError:
                rejected.append(label)
            else:
                raise RuntimeError('invalid failed prefix accepted: ' + label)

        for count in [0, -1, 3, True, 1.0]:
            reject('invalid-prefix-' + repr(count), count=count)
        reject('missing-next-child', rows=launches[:1])
        reject('extra-next-child', rows=launches + [dict(entries[2], pid=3, action='apply')])
        wrong = copy.deepcopy(launches)
        wrong[-1]['archive'] = 'three'
        reject('wrong-next-child', rows=wrong)
        reject('unknown-failure', log=prefix + 'RuntimeError: something failed')
        reject('in-application-disk-full', log=prefix + 'OSError: [Errno 28] No space left on device')
        reject('two-recognized-failures', log=prefix + '\n'.join(messages.values()))
        reject('failure-before-next-launch', log=messages['space preflight rejected'] + '\n' + prefix)
        reject('missing-launch-line', log=messages['space preflight rejected'])
        reject('duplicated-launch-line', log=prefix + prefix + messages['space preflight rejected'])
        reject('similar-unrecognized-message', log=prefix + messages['space preflight rejected'] + ' (later)')
        partial = assess('worker-cold-storage-batch-03', 7)
        require(partial['completed_entries'] == 7 and partial['total_entries'] == 8 and
                partial['preapplication_rejection'] == 'space preflight rejected' and
                partial['remaining_original_inventories_verified'] == 1,
                'real preflight failure evidence differs')
        complete = assess('worker-cold-storage-batch-02')
        stored_path = ROOT / 'results/worker-cold-storage-batch-02/summary.json'
        stored = json.loads(stored_path.read_text())
        require(all(complete[key] == value for key, value in stored.items() if key != 'assessor_sha256') and
                complete['preapplication_rejection'] is None and
                complete['remaining_original_inventories_verified'] == 0,
                'earlier complete assessment changed apart from added fields and assessor hash')
        sources = [Path(__file__), Path(__file__).with_name('assess_archive_batch.py'), stored_path]
        out.mkdir()
        write_json(out / 'summary.json', dict(status='passed', classification_rejections=rejected,
            recognized_rejections=list(messages), partial_assessment=partial,
            complete_assessment=complete, sources_sha256={str(p.relative_to(ROOT)): sha(p) for p in sources},
            note='No archive mutation. Rechecks seven completed targets, the full unchanged remaining original inventory, and the previous 24-target completed batch. In-application failures are deliberately rejected.'))
        print(json.dumps(dict(classification_rejections=len(rejected), completed_archives=31,
                              untouched_original_inventories=1)))


if __name__ == '__main__':
    main()
