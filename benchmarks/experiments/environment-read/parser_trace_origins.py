"""Use the qualified origin inspector on saved parser allocation traces."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'artifact-diff'))
from compare_saved_runtime import acquire_lock, sha
from inspect_allocation_origins import inspect
from workflow_io import require_space, write_json as write


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45); require_space(ROOT, 8)
        proof_path = ROOT / 'results/parser-allocation-history-01/summary.json'
        proof = json.loads(proof_path.read_text()); assert proof['status'] == 'passed' and proof['commands'] == 8
        work = ROOT / proof['raw']; assert sha(work / 'records.json') == proof['records_sha256']
        assert sha(work / 'plan.json') == proof['plan_sha256']
        rows = json.loads((work / 'records.json').read_text())
        selected = [r for r in rows if r['mode'] == 'traced']; assert len(selected) == 4
        out = ROOT / '.work/parser-allocation-origins-01'; out.mkdir(exist_ok=False)
        helpers = [Path(__file__), Path(__file__).parent.parent / 'artifact-diff/inspect_allocation_origins.py',
                   Path(__file__).parent.parent / 'artifact-diff/check_allocation_trace.py', proof_path, work / 'records.json']
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in helpers}
        write(out / 'plan.json', dict(owner=str(ROOT), frozen=frozen, query='syntax error',
            inspections=4, guest_commands=0, performance_measurement=False))
        summaries = []
        for row in selected:
            trace = row['allocation_trace']; trace_path = ROOT / trace['saved_path']
            artifact = row['artifact']; artifact_path = ROOT / artifact['path']
            assert sha(trace_path) == trace['sha256'] and sha(artifact_path) == artifact['sha256']
            result = inspect(trace_path, artifact_path, b'syntax error')
            path = out / f"{row['state']}-origins.json"; write(path, result)
            matches = []
            for match in result['matches']:
                allocation = match['materialization']
                origins = []
                for origin in match['origins']:
                    function = origin.get('function') or {}
                    origins.append(dict(function=function,
                        request=origin['request'], ancestry=origin['ancestry']))
                matches.append(dict(materialization=allocation, origins=origins))
            summaries.append(dict(state=row['state'], source_state=row['source_state'],
                source_sha256=row['source_sha256'], artifact_sha256=artifact['sha256'],
                trace_sha256=trace['sha256'], exact_literal_allocations=len(matches),
                report=str(path.relative_to(ROOT)), report_sha256=sha(path), matches=matches))
            print(row['state'], 'exact literal allocations', len(matches), flush=True)
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        result = ROOT / 'results/parser-allocation-origins-01'; result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', inspections=4, guest_commands=0,
            raw=str(out.relative_to(ROOT)), plan_sha256=sha(out / 'plan.json'),
            states=summaries, equivalence_proof=False, performance_measurement=False))


if __name__ == '__main__':
    main()
