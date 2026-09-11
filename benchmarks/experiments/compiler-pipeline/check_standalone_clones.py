#!/usr/bin/env python3
"""Check explicit standalone clone selection and three real completed histories."""
import argparse
from copy import deepcopy
import fcntl
import json
from pathlib import Path
from types import SimpleNamespace
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import clone_workflow_artifacts as clones
from reclaim_workflow_objects import sha, identifier
from verify_repeated_workflow import require
from workflow_io import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    identifier(args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        base = dict(prepare='fixture', apply=None, workflow=[], corpus=[], standalone_workflow=[], plan_sha256=None)
        positive = [
            (dict(base, workflow=['a'], corpus=['parent']), [('a', 'parent')]),
            (dict(base, standalone_workflow=['s']), [('s', None)]),
            (dict(base, workflow=['a'], corpus=['parent'], standalone_workflow=['s']), [('a', 'parent'), ('s', None)]),
            (dict(base, standalone_workflow=['s' + str(i) for i in range(8)]), [('s' + str(i), None) for i in range(8)]),
            (dict(base, prepare=None, apply='fixture', plan_sha256='a' * 64), []),
        ]
        for value, expected in positive:
            require(clones.selected_histories(SimpleNamespace(**value)) == expected, 'clone selection differs')
        rejected = []
        invalid = [
            ('empty', base),
            ('missing-corpus', dict(base, workflow=['a'])),
            ('extra-corpus', dict(base, corpus=['parent'])),
            ('nine-standalone', dict(base, standalone_workflow=['s' + str(i) for i in range(9)])),
            ('mixed-over-limit', dict(base, workflow=['a'], corpus=['parent'], standalone_workflow=['s' + str(i) for i in range(8)])),
            ('duplicate-standalone', dict(base, standalone_workflow=['a', 'a'])),
            ('duplicate-mixed', dict(base, workflow=['a'], corpus=['parent'], standalone_workflow=['a'])),
            ('implicit-empty-corpus', dict(base, workflow=['a'], corpus=[''])),
            ('workflow-traversal', dict(base, standalone_workflow=['../outside'])),
            ('corpus-traversal', dict(base, workflow=['a'], corpus=['../outside'])),
            ('both-actions', dict(base, apply='fixture', standalone_workflow=['s'])),
            ('missing-action', dict(base, prepare=None, standalone_workflow=['s'])),
            ('prepare-hash', dict(base, standalone_workflow=['s'], plan_sha256='a' * 64)),
            ('apply-standalone', dict(base, prepare=None, apply='fixture', standalone_workflow=['s'], plan_sha256='a' * 64)),
            ('apply-workflow', dict(base, prepare=None, apply='fixture', workflow=['a'], corpus=['parent'], plan_sha256='a' * 64)),
            ('apply-without-hash', dict(base, prepare=None, apply='fixture')),
        ]
        for label, value in invalid:
            try:
                clones.selected_histories(SimpleNamespace(**deepcopy(value)))
            except RuntimeError:
                rejected.append(label)
            else:
                raise RuntimeError('invalid clone selection accepted: ' + label)
        actual = []
        for run in ['interface-nushell-repeated-01', 'worker-count-nushell-repeated-01',
                    'lightweight-wrapper-nushell-repeated-01']:
            history = clones.snapshots(run, None)
            require(history['corpus'] is None and len(history['entries']) == 90 and
                    history['verification']['exact_artifact_hashes_verified'] == 90,
                    'standalone history verification differs')
            actual.append(dict(workflow=run, snapshots=len(history['entries']),
                proofs=history['proofs'], verification=history['verification'],
                duplicate_logical_bytes=sum(e['bytes'] for e in history['entries'] if e['path'] != e['anchor'])))
        out = ROOT / 'results' / args.run_id
        out.mkdir(exist_ok=False)
        write_json(out / 'summary.json', dict(status='passed', positive_selections=len(positive),
            rejected=rejected, actual_standalone_histories=actual, snapshots_modified=False,
            sources={str(Path(__file__).relative_to(ROOT)): sha(Path(__file__)), **clones.source_hashes()}))
        (out / 'assessment.md').write_text(
            'Five valid selector configurations and sixteen invalid configurations pass their checks. '
            'All 270 executed snapshots across three real standalone histories verify with their '
            'original command evidence. No snapshot was changed. The underlying file-clone primitive '
            'is unchanged from its existing independent-write qualification.\n')
        print(json.dumps(dict(status='passed', positive=5, rejections=len(rejected), actual_histories=3,
                              snapshots=sum(h['snapshots'] for h in actual))))


if __name__ == '__main__':
    main()
