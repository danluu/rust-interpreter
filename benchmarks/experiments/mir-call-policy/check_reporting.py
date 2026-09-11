#!/usr/bin/env python3
"""Keep historical verifier source explicit without weakening measured-file checks."""
import fcntl
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import update_status as status


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        bindings = json.loads((ROOT / 'results/historical-source-bindings.json').read_text())
        source = 'scripts/verify_repeated_workflow.py'
        digest = bindings['sources'][source]['sha256']
        status.verify_evidence(source, digest)
        path = 'results/mir-call-policy-01/summary.json'
        status.verify_evidence(path, hashlib.sha256((ROOT / path).read_bytes()).hexdigest())
        rejected = []
        for p in [source, path]:
            try: status.verify_evidence(p, '0' * 64)
            except RuntimeError: rejected.append(p + ': false digest')
            else: raise RuntimeError('false evidence hash accepted')
        with patch.object(status.subprocess, 'check_output', return_value=b'changed Git object'):
            try: status.verify_evidence(source, digest)
            except RuntimeError: rejected.append('changed Git object')
            else: raise RuntimeError('changed historical source accepted')
        # Even a mistakenly added binding cannot substitute a measured record.
        altered = dict(bindings, sources={path: dict(sha256='0' * 64, commit='unused')})
        with patch.object(status.json, 'loads', return_value=altered), patch.object(status.subprocess, 'check_output') as git:
            try: status.verify_evidence(path, '0' * 64)
            except RuntimeError: rejected.append('record substitution')
            else: raise RuntimeError('measured file substitution accepted')
            assert not git.called
        generated = status.render()
        assert 'Ordinary inlining budgets lose' in generated['STATUS.md']
        assert 'All seven histories verify together' in generated['STATUS.md']
        for name, text in generated.items():
            (ROOT / name).write_text(text + ('' if text.endswith('\n') else '\n'))
        out = ROOT / 'results/mir-call-policy-reporting-01'
        out.mkdir(exist_ok=False)
        paths = [Path(__file__), ROOT / 'scripts/update_status.py', ROOT / 'results/historical-source-bindings.json']
        result = dict(status='passed', current_evidence_verified=True, historical_verifier_object_verified=True,
            rejected=rejected, measured_records_changed=False,
            sources={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
        (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result))


if __name__ == '__main__': main()
