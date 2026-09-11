#!/usr/bin/env python3
"""Join the verified four-state Nushell trace to historical artifact evidence."""
import fcntl
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from reclaim_workflow_objects import sha
from verify_repeated_workflow import require
from workflow_io import write_json
from inspect_allocation_origins import inspect


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        run = 'allocation-trace-nushell-history-01'
        report_path = ROOT / 'results' / run / 'summary.json'
        report = json.loads(report_path.read_text())
        status_path = ROOT / '.work/experiments' / run / 'status.json'
        status = json.loads(status_path.read_text())
        require(status['status'] == 'finished' and status['returncode'] == 0 and
                status['owner'] == status['cwd'] == str(ROOT) and report['status'] == 'passed' and
                report['commands'] == 8 and report['source_restored'] and report['original_assertions_unchanged'] and
                report['wrong_original_assertions_verified_both_modes'], 'history did not complete with its controls')
        require(all(sha(ROOT / p) == d for p, d in report['sources_sha256'].items()), 'history input changed')
        require(sha(status_path.with_name('plan.json')) == status['plan_sha256'] and
                sha(status_path.with_name('command.log')) == status['log_sha256'], 'supervisor evidence changed')
        rows_path = ROOT / report['raw'] / 'records.json'
        require(sha(rows_path) == report['records_sha256'], 'command evidence changed')
        historical_paths = [ROOT / '.work/runs' / name / 'records.json' for name in
                            ['worker-count-nushell-cold-04', 'worker-count-nushell-repeated-01']]
        cold, warm = [json.loads(p.read_text()) for p in historical_paths]
        historical = [next(r['artifacts'][0]['sha256'] for r in cold if r['mode'] == 'baseline' and r['state'] == state)
                      for state in [0, -1, 1]]
        historical.append(next(r['artifacts'][0]['sha256'] for r in warm
                               if r['mode'] == 'baseline' and r['cycle'] == 1 and r['state'] == 0))
        observed, proofs = [], {str(p.relative_to(ROOT)): sha(p) for p in
            [report_path, status_path, rows_path, *historical_paths, Path(__file__),
             Path(__file__).with_name('inspect_allocation_origins.py'),
             Path(__file__).with_name('check_allocation_trace.py')]}
        for label, snapshot, digest in zip(['original', 'wrong', 'api', 'restored'], report['snapshots'], historical):
            artifact, trace = [ROOT / snapshot[k] for k in ['artifact', 'trace']]
            require(sha(artifact) == digest == snapshot['verification']['artifact_sha256'] and
                    sha(trace) == snapshot['verification']['trace_sha256'], 'trace or historical artifact differs')
            query_path = ROOT / 'results' / ('allocation-origin-nushell-' + label + '-01') / 'summary.json'
            query = json.loads(query_path.read_text())
            reproduced = inspect(trace, artifact, b'Expected OneOf')
            require(all(query[k] == value for k, value in reproduced.items()), 'origin query does not reproduce')
            groups = []
            for match in query['matches']:
                materialization = match['materialization']
                groups.append(dict(allocation_id=materialization['allocation_id'], pointer=materialization['pointer'],
                    event=materialization['event'], size=materialization['size'], mutable=materialization['mutable'],
                    relocation_count=materialization['relocation_count'], origins=[dict(
                        function=o['function']['definition'], cache_hit=o['request']['cache_hit'],
                        source=[a['source'] for a in o['ancestry'] if a['kind'] == 'constant-origin'])
                        for o in match['origins']]))
            observed.append(dict(state=label, allocations=groups, artifact_sha256=digest,
                                 historical_artifact_identical=True))
            proofs.update({str(p.relative_to(ROOT)): sha(p) for p in [artifact, trace, query_path]})
        require(len(observed) == 4, 'missing history state')
        compiler = Path(subprocess.check_output(['rustc', '+nightly-2026-09-08', '--print', 'sysroot'], text=True).strip())
        compiler /= 'lib/rustlib/rustc-src/rust/compiler'
        compiler_sources = {name: dict(path=str(compiler / name), sha256=sha(compiler / name)) for name in
            ['rustc_mir_build/src/builder/expr/as_constant.rs', 'rustc_middle/src/mir/interpret/mod.rs',
             'rustc_middle/src/query/on_disk_cache.rs']}
        out = ROOT / 'results/allocation-origin-nushell-history-01'
        out.mkdir(exist_ok=False)
        write_json(out / 'summary.json', dict(status='verified attribution', observations=observed,
            proof_sha256=proofs, compiler_sources=compiler_sources,
            compiler_revision='cea272fa356e94bd2ee2cadf376630aa0683867a',
            inference='Fresh literal construction deduplicates; saved-allocation decoding reserves IDs independently. Mixed cached/recomputed MIR is consistent with the split, but the trace does not directly identify rustc cache hits. A reduced incremental-on/off comparison is next.',
            note='Compiler allocation IDs are local to each export. The extra materialization already has a distinct compiler ID; the exporter preserves that identity. This is not permission to merge allocations by contents or a proof of general cross-history semantic equivalence.'))
        print(json.dumps(dict(status='verified attribution', allocations_by_state=[len(r['allocations']) for r in observed],
                              historical_artifacts_matched=4)))


if __name__ == '__main__':
    main()
