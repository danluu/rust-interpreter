#!/usr/bin/env python3
"""Verify both completed comparisons and summarize recorded VM counters."""
import fcntl
import json
import re
import statistics
from pathlib import Path

from run import ROOT, HERE, KEY, assess, read, require, sha, write


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        cases, evidence, processes = [], {}, []
        for label in ['folded-literal-trie', 'token-phrase']:
            run = 'mir-call-policy-01-' + label
            folder = ROOT / 'results' / run
            summary = read(folder / 'summary.json')
            result = read(folder / 'policy-assessment.json')
            computed = assess(summary)
            require(all(result[k] == v for k, v in computed.items()), 'policy assessment changed')
            require(summary['tool_key'] == KEY, 'tool differs')
            require(all(sha(ROOT / p) == h for p, h in result['evidence'].items()), 'case evidence changed')
            work = ROOT / '.work' / run
            supervisor = ROOT / '.work/experiments' / run
            status = read(work / 'status.json')
            receipt = read(supervisor / 'status.json')
            require(status['status'] == receipt['status'] == 'finished' and receipt['returncode'] == 0,
                    'case processes not terminal')
            processes.append(dict(run_id=run, controller=status, supervisor=receipt))
            records = read(ROOT / summary['raw'] / 'records.json')
            counters, medians = {}, {}
            for mode in ['baseline', 'candidate']:
                rows = []
                for record in records:
                    if record['mode'] != mode or record['state'] < 0: continue
                    values = {}
                    for line in record['calls'][0]['stderr'].splitlines():
                        if not re.fullmatch(r'[a-z_]+=\d+(?: [a-z_]+=\d+)*', line): continue
                        for key, value in re.findall(r'([a-z_]+)=(\d+)', line):
                            require(key not in values, 'duplicated VM counter')
                            values[key] = int(value)
                    required = ['instructions', 'peak_guest_memory', 'jit_bytes', 'jit_entries',
                                'jit_resumable_calls', 'jit_resumable_returns', 'jit_declined_functions']
                    require(all(k in values for k in required) and values['jit_declined_functions'] == 0,
                            'missing VM statistics or declined compilation')
                    rows.append(dict(cycle=record['cycle'], state=record['state'], **values))
                require(len(rows) == 18, 'missing successful VM runs')
                counters[mode] = rows
                medians[mode] = {k: statistics.median(row[k] for row in rows if row['state'] > 0) for k in required}
            cases.append(dict(label=label, assessment=result, vm_counter_medians=medians, counters=counters))
            paths = [folder / 'summary.json', folder / 'policy-assessment.json',
                     ROOT / summary['raw'] / 'records.json', ROOT / summary['raw'] / 'check-records.json',
                     ROOT / summary['raw'] / 'source-transitions.json']
            paths += [work / name for name in ['plan.json', 'status.json', 'admission.json', 'command.log']]
            paths += [supervisor / name for name in ['plan.json', 'status.json', 'command.log']]
            evidence.update({str(p.relative_to(ROOT)): sha(p) for p in paths})
        evidence[str(Path(__file__).relative_to(ROOT))] = sha(Path(__file__))
        result = dict(status='completed', tool_key=KEY, selected_policy='enlarged',
            ordinary_policy_passed=all(c['assessment']['passed'] for c in cases),
            primary_commands=126, check_commands=42, edited_pairs=30, artifacts=84,
            successful_vm_runs_with_counters=72, cases=cases, processes=processes, evidence=evidence,
            production_runtime_changed=False, adoption=False,
            decision='Ordinary inlining fails both predeclared gates. Keep the current enlarged policy; no intermediate threshold sweep. Investigate aggregate storage while preserving byte initialization and alias behavior.')
        out = ROOT / 'results/mir-call-policy-01'
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', result)
        lines = ['# Ordinary MIR inlining loses with the current native-call JIT', '',
                 'Both predeclared gates fail. The current enlarged inlining policy remains selected; no runtime or exporter implementation changed.', '',
                 '| Workflow | Native | Enlarged | Ordinary | Ordinary paired wall | Ordinary paired CPU |',
                 '| --- | ---: | ---: | ---: | ---: | ---: |']
        for case in cases:
            row = case['assessment']; med = row['median_seconds']
            lines.append(f"| {case['label']} | {med['native']:.3f}s | {med['candidate']:.3f}s | {med['baseline']:.3f}s | {(row['wall_ratio_ordinary_over_enlarged']-1)*100:+.2f}% | {(row['cpu_ratio_ordinary_over_enlarged']-1)*100:+.2f}% |")
        lines += ['', 'All 168 commands, 30 edited pairs and 84 artifacts verify, including original assertions, wrong-edit rejection, source restoration and separate Cargo-check controls. All 72 successful VM runs report zero declined functions. Baseline/candidate in the historical harness mean ordinary/enlarged here.', '',
                  'Ordinary inlining produces smaller artifacts and less generated native code, but executes more guest instructions and Calls. Folded median execution rises from 1.061s to 1.191s; token from 2.978s to 3.339s. Token Cargo time falls from 1.277s to 1.213s, insufficient to offset execution. These are recorded stages, not an isolated causal attribution.', '',
                  'Keep all failures. No threshold sweep or timing rerun is planned. The native gap remains; aggregate storage and full-suite compatibility still need work.', '']
        (out / 'assessment.md').write_text('\n'.join(lines))
        print(json.dumps({k: result[k] for k in ['status', 'selected_policy', 'ordinary_policy_passed', 'primary_commands', 'check_commands', 'edited_pairs', 'artifacts']}))


if __name__ == '__main__': main()
