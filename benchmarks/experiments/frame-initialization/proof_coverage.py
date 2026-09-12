#!/usr/bin/env python3
"""Join conservative proof decisions to exact, previously captured clearing PCs."""
import argparse
from bisect import bisect_right
from collections import Counter
import fcntl
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from summarize_owned_sample import parse_tree, require, self_samples, sha

spec = importlib.util.spec_from_file_location('clearing', ROOT / 'benchmarks/experiments/register-clearing/attribute.py')
clearing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(clearing)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proof-run', required=True)
    args = parser.parse_args()
    require(Path(args.proof_run).name == args.proof_run, 'invalid run ID')
    run = 'fre-integration-es8-sample-01'
    artifact = ROOT / '.work/fre-integration-es8-edit-01/artifacts/restored.rbc'
    work = ROOT / '.work' / args.proof_run
    metadata = work / 'es8-proof.stdout'
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        summary = json.loads((work / 'summary.json').read_text())
        require(summary['status'] == 'passed', 'proof run incomplete')
        for path, digest in summary['evidence'].items():
            require(sha(ROOT / path) == digest, 'proof evidence changed')
        plan = json.loads((work / 'plan.json').read_text())
        require(sha(artifact) == plan['frozen'][str(artifact.relative_to(ROOT))], 'artifact differs')
        # Existing typed attribution verifies all code/sample/process/options
        # bindings and reconciles every zeroing instruction and sampled count.
        arenas = clearing.analyze(run, artifact, metadata)
        functions = json.loads(metadata.read_text())
        report = json.loads((ROOT / 'results' / run / 'summary.json').read_text())
        counts, hot, reasons = Counter(), Counter(), Counter()
        for sample in report['samples']:
            folder = ROOT / '.work' / run / str(sample['index'])
            dump = json.loads((folder / 'jit-code/map.json').read_text())
            data = (folder / 'jit-code/code.bin').read_bytes()
            spans = []
            for row in dump['ranges']:
                if row['kind'] != 'resumable_call':
                    continue
                call = next(c for c in functions[row['function']]['calls'] if c['pc'] == row['pc'])
                for lo, hi, arena, callee in clearing.call_spans(data[row['offset']:row['end']], row, functions):
                    if arena != 'guest_memory':
                        continue
                    proof = functions[callee]['proof']
                    reason = ('eligible' if call['eligible'] else 'nonlocal_argument_source'
                              if not call['local_arguments'] else proof['decline']['reason'])
                    spans.append((lo + row['offset'], hi + row['offset'], row['function'], row['pc'], callee, reason))
            starts = [s[0] for s in spans]
            for tree in parse_tree((folder / 'sample.txt').read_text()):
                for count, frame, _ in self_samples(tree):
                    if '<unknown binary>' not in frame:
                        continue
                    ids = []
                    for address in re.findall(r'0x([0-9a-f]+)', frame):
                        offset = int(address, 16) - dump['arena_base']
                        index = bisect_right(starts, offset) - 1
                        ids.append(spans[index][2:] if index >= 0 and spans[index][0] <= offset < spans[index][1] else None)
                    require(ids and len(set(ids)) == 1 and '...' not in frame, 'ambiguous sample identity')
                    if ids[0] is not None:
                        caller, pc, callee, reason = ids[0]
                        counts['guest_memory'] += count
                        counts['eligible' if reason == 'eligible' else 'declined'] += count
                        hot[(caller, pc, callee, reason)] += count
                        reasons[reason] += count
        require(counts['guest_memory'] == arenas['counts'].get('guest_memory', 0), 'sample totals differ')
        result = dict(status='passed', performance_measurement=False, guest_commands=0,
            proof_run=args.proof_run, sample_run=run, sample_scope='partial perturbed execution windows',
            total_thread_samples=report['total_samples'], counts=dict(counts), reasons=dict(reasons),
            eligible_share_of_thread_samples=counts['eligible'] / report['total_samples'],
            eligible_share_of_guest_frame_clearing=counts['eligible'] / max(1, counts['guest_memory']),
            alignment_padding_still_requires_clearing=True,
            limitation='Eligibility counts the whole current frame-clearing sequence, including padding that must remain. This is an upper bound on sampled opportunity, not a speedup prediction.',
            hot_call_sites=[dict(caller=caller, pc=pc, callee=callee, reason=reason, samples=count,
                callee_name=functions[callee]['name'], frame_size=functions[callee]['frame_size'],
                proof=functions[callee]['proof']) for (caller, pc, callee, reason), count in hot.most_common()],
            arenas=arenas, evidence=summary['evidence'] | {
                str(Path(__file__).relative_to(ROOT)): sha(Path(__file__)),
                'benchmarks/experiments/register-clearing/attribute.py': sha(ROOT / 'benchmarks/experiments/register-clearing/attribute.py')})
        output = work / 'coverage.json'
        with output.open('x') as out:
            out.write(json.dumps(result, indent=2) + '\n')
        print(json.dumps({k: v for k, v in result.items() if k not in ['hot_call_sites', 'arenas', 'evidence']}))


if __name__ == '__main__':
    main()
