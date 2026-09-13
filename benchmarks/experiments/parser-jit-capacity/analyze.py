"""Audit the stopped capacity screen and count reached PCs in its earlier profile."""
import collections
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'pgrust-parser-probe'))
from compare_saved_runtime import acquire_lock, sha
from probe import fingerprint
from workflow_io import require_space, write_json as write
from suite_reports import read_report
from protocol import measurement, runtime_statistics, LIMITS


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45); require_space(ROOT, 8)
        proof_path = ROOT / 'results/parser-jit-capacity-screen-continuation-01/summary.json'
        proof = json.loads(proof_path.read_text()); old = ROOT / proof['raw']
        assert proof['status'] == 'passed' and proof['commands'] == 32
        for name in ['plan', 'records']: assert sha(old / (name + '.json')) == proof[name + '_sha256']
        plan = json.loads((old / 'plan.json').read_text()); rows = json.loads((old / 'records.json').read_text())
        assert all(fingerprint(ROOT / p) == h for p, h in plan['frozen'].items())
        assert measurement(rows, 1) == proof['measurement'] and not proof['measurement']['gate']['passed']
        assert sha(ROOT / '.work/sources/pgrust/crates/backend/parser/gram_core/src/parse.rs') == plan['original_source_sha256']
        terminal_path = ROOT / '.work/experiments/parser-jit-capacity-screen-continuation-01/status.json'
        terminal = json.loads(terminal_path.read_text())
        assert terminal['status'] == 'finished' and terminal['returncode'] == 0
        assert sha(terminal_path.parent / 'command.log') == terminal['log_sha256']
        suites = {}
        evidence = {str(p.relative_to(ROOT)): sha(p) for p in [proof_path, old / 'plan.json', old / 'records.json', terminal_path, Path(__file__)]}
        for row in rows:
            raw = ROOT / row['log_raw']
            for stream in ['stdout', 'stderr']:
                p = raw / f"{row['index']}.{stream}"
                assert sha(p) == row[stream + '_sha256']; evidence[str(p.relative_to(ROOT))] = sha(p)
            for kind in ['executable'] if row['mode'] == 'native' else ['artifact', 'entry_catalog']:
                assert sha(ROOT / row[kind]['path']) == row[kind]['sha256']
            if row['mode'] != 'native':
                p = raw / f"{row['index']}-suite.json"
                report, digest = read_report(p, row['suite_sha256'])
                evidence[str(p.relative_to(ROOT))] = digest
                stats = runtime_statistics(report, LIMITS[row['mode']])
                assert all(row[k] == v for k, v in stats.items())
                suites[row['index']] = report
        stages = {}
        for mode in LIMITS:
            selected = [r for r in rows if r['mode'] == mode and r['state'] > 0]
            stage_rows = []
            for r in selected:
                report = suites[r['index']]
                vector, = [t for t in report['tests'] if t['name'] == 'tests_dump::c_reference_vectors']
                stage_rows.append(dict(cargo_seconds=r['launch']['cargo_seconds'],
                    build_to_ready_seconds=r['build']['build_to_ready_seconds'],
                    execution_seconds=r['launch']['execution_seconds'],
                    frontend_seconds=r['stages']['frontend'], lowering_seconds=r['stages']['lowering'],
                    vector_seconds=vector['seconds'], vector_instructions=vector['instructions'],
                    vector_interpreted=vector['instructions']-vector['jit_instructions'],
                    vector_jit_entries=vector['jit_entries'], vector_compile_ns=vector['jit_compile_ns'],
                    maximum_owner_code_bytes=r['maximum_owner_code_bytes'],
                    maximum_owner_declines=r['maximum_owner_declines']))
            stages[mode] = {k: statistics.median(r[k] for r in stage_rows) for k in stage_rows[0]}
        profile_path = ROOT / 'results/parser-runtime-profile-01/summary.json'
        profile_proof = json.loads(profile_path.read_text()); profile_raw = ROOT / profile_proof['raw']
        assert profile_proof['status'] == 'passed'
        assert all(sha(profile_raw / p) == h for p, h in profile_proof['evidence'].items())
        missing, = profile_proof['executed_without_published_code']
        profile = json.loads((profile_raw / 'profile.json').read_text())
        f = profile['functions'][missing['function']]
        assert f['name'] == missing['name'] and len(f['operations']) == missing['operations']
        assert sum(f['jit_blocks']) == sum(f['jit_tree_blocks']) == 0
        assert len(f['interpreted']) == len(f['operations'])
        counts = f['interpreted']; reached = sum(n > 0 for n in counts)
        by_kind = collections.Counter()
        for op, count in zip(f['operations'], counts): by_kind[op.split(' ', 1)[0]] += count
        shape = dict(function=missing['function'], name=f['name'], operations=len(counts),
            reached_operations=reached, reached_fraction=reached/len(counts),
            interpreted_operations=sum(counts), entry_pc_zero_hits=counts[0],
            entry_hits_are_not_proven_call_counts=True, frame_size=f['frame_size'], registers=f['registers'],
            initial_zeroing_requirement='not yet measured',
            dynamic_operations_by_rendered_kind=dict(by_kind.most_common()),
            top_pcs=[dict(pc=pc, hits=n, operation=f['operations'][pc])
                     for pc, n in sorted(enumerate(counts), key=lambda x: x[1], reverse=True)[:20]],
            scope='earlier original/restored artifact; one profiled fresh owner; no native code in this function; no entropy replay')
        evidence.update({str(profile_path.relative_to(ROOT)): sha(profile_path),
                         str((profile_raw / 'profile.json').relative_to(ROOT)): sha(profile_raw / 'profile.json')})
        result = ROOT / 'results/parser-jit-capacity-screen-analysis-01'; result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', guest_commands=0, screen_commands_audited=32,
            repeated_commands=0, performance_gate=proof['measurement']['gate'],
            independent_stage_medians=stages, earlier_profile_function_shape=shape, evidence=evidence,
            stage_scope='independent medians, nested timers; do not sum or subtract as causal costs',
            decision='park unchanged capacity treatment; no full study', terminal=terminal))
        print(json.dumps(dict(stages=stages, shape={k:v for k,v in shape.items() if k not in ['top_pcs','dynamic_operations_by_rendered_kind']})), flush=True)


if __name__ == '__main__': main()
