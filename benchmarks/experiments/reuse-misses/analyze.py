"""Summarize the five edited diagnostic exports; no benchmark execution."""
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import write_json as write
from observe import observation


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        source = ROOT / 'results/reuse-misses-token-01/summary.json'
        proof = json.loads(source.read_text())
        assert proof['status'] == 'passed' and proof['commands'] == 16
        raw = ROOT / proof['raw']
        assert sha(raw / 'plan.json') == proof['plan_sha256']
        assert sha(raw / 'records.json') == proof['records_sha256']
        rows = json.loads((raw / 'records.json').read_text())
        selected = [r for r in rows if r['mode'] == 'on' and r['state'] in range(1, 6)]
        assert [r['state'] for r in selected] == [1, 2, 3, 4, 5]
        results = []
        for row in selected:
            report = observation(row['stderr'], True)
            assert report == row['observer']
            groups = report['by_lookup']
            reasons = {}
            for function in report['functions']:
                if function['action']['kind'] != 'declined':
                    continue
                reason = function['action']['first_reason']
                target = reasons.setdefault(reason, dict(functions=0, prepare_and_lower_seconds=0.0))
                target['functions'] += 1
                target['prepare_and_lower_seconds'] += function['prepare_seconds'] + function['lower_seconds']
            assert sum(r['functions'] for r in reasons.values()) == report['declined']
            results.append(dict(state=row['state'], lowered=report['lowered'], reused=report['reused'],
                groups=groups, decline_reasons=reasons))
        median = statistics.median
        metrics = ['functions', 'reused', 'staged', 'declined', 'prepare_seconds', 'lower_seconds',
            'template_encode_seconds', 'template_decode_seconds', 'binding_seconds',
            'replay_body_required_functions', 'replay_body_free_functions',
            'replay_current_context_seconds', 'replay_body_free_context_seconds']
        medians = {key: {metric: median(r['groups'][key][metric] for r in results) for metric in metrics}
                   for key in results[0]['groups']}
        # Sum within each observation before aggregating; independent medians
        # cannot be assumed to add to a median total.
        combined = dict(
            total_lowering_seconds=median(sum(g['prepare_seconds'] + g['lower_seconds'] for g in r['groups'].values()) for r in results),
            declined_lowering_seconds=median(sum(g['prepare_and_lower_seconds'] for g in r['decline_reasons'].values()) for r in results),
            nondeclined_lowering_seconds=median(sum(g['prepare_seconds'] + g['lower_seconds'] for g in r['groups'].values())
                - sum(g['prepare_and_lower_seconds'] for g in r['decline_reasons'].values()) for r in results))
        paths = [source, raw / 'plan.json', raw / 'records.json', Path(__file__), Path(__file__).with_name('observe.py')]
        out = ROOT / 'results/reuse-misses-analysis-01'
        out.mkdir(exist_ok=False)
        value = dict(status='passed', observed_edits=5, new_compiler_or_guest_commands=0,
            tool_key=proof['tool_key'], performance_measurement=False, edits=results,
            independent_group_medians=medians, combined_medians=combined,
            input_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},
            limitations=['Diagnostic intervals include observation overhead.',
                'Body-free current-context cost is an upper bound, not a promised saving.',
                'Red absent does not identify a new instance or a specific invalidation cause.',
                'Only the first reason for declining a template is recorded.'])
        write(out / 'summary.json', value)
        print(json.dumps(dict(medians=medians, combined=combined,
            counts=[dict(state=r['state'],lowered=r['lowered'],reused=r['reused'],
                         reasons=r['decline_reasons']) for r in results]),indent=2))


if __name__ == '__main__':
    main()
