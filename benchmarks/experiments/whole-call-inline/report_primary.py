#!/usr/bin/env python3
"""Recompute both A/A controls and the fixed whole-call primary gates."""
import fcntl
import hashlib
import os
from pathlib import Path
import statistics
import subprocess
import time

import workflows as workflow
from build import ROOT, read, write, sha, require


def main():
    run = 'whole-call-primary-02'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        work = ROOT/'.work'/run
        work.mkdir(exist_ok=False)
        status = dict(status='preflight', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time())
        write(work/'status.json', status)
        try:
            cases, evidence = [], {str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))}
            # The workflow's measured source hash is checked below. Bind the
            # imported local helpers to that run's recorded Git revision too.
            helper_names = ['build.py','build_relocation.py',
                'heldout_controls.py','check_comparison.py','verify_heldouts.py','verify_relocation.py']
            config = read(ROOT/'benchmarks/workflow-corpus.json')
            previous_end = 0
            for phase, label in workflow.ORDER:
                name = workflow.run_id(phase, label)
                raw = ROOT/'.work'/name
                report_dir = ROOT/'results'/name
                supervisor_dir = ROOT/'.work/experiments'/name
                supervisor = read(supervisor_dir/'status.json')
                controller = read(raw/'status.json')
                plan = read(raw/'plan.json')
                require(supervisor['status'] == controller['status'] == 'finished' and
                        supervisor['returncode'] == controller['returncode'] == 0 and
                        supervisor['child_pid'] == controller['pid'], 'unfinished or mismatched workflow')
                require(controller['started_at'] >= previous_end, 'fixed workflow order overlaps')
                previous_end = supervisor['finished_at']
                require(supervisor['command'] == ['python3','benchmarks/experiments/whole-call-inline/workflows.py',
                        '--phase',phase,'--case',label], 'unexpected supervised driver')
                require(controller['command'] == plan['command'] and controller['child_returncode'] == 0,
                        'workflow command receipt differs')
                require(all(sha(ROOT/p) == h for p,h in plan['frozen'].items()), 'frozen workflow input changed')
                for name in helper_names:
                    path = ROOT/'benchmarks/experiments/aggregate-byte-writes'/name
                    relative = str(path.relative_to(ROOT))
                    original = subprocess.check_output(['git','show',plan['source_commit']+':'+relative], cwd=ROOT)
                    require(hashlib.sha256(original).hexdigest() == sha(path), 'imported helper differs from measured Git revision')
                    evidence[relative] = sha(path)
                report = read(report_dir/'summary.json')
                saved = read(report_dir/'whole-call-assessment.json')
                case = next(c for c in config['cases'] if c['label'] == label)
                checked = workflow.assess(report, case, phase)
                require(all(saved[k] == v for k,v in checked.items()), 'saved assessment differs from recomputation')
                require(all(sha(ROOT/p) == h for p,h in saved['evidence'].items()), 'assessment evidence changed')
                rows = read(ROOT/report['raw']/'records.json')
                stages = {}
                for mode in ['baseline','candidate']:
                    launches = [r['calls'][0]['launch'] for r in rows if r['state'] > 0 and r['mode'] == mode]
                    stages[mode] = {key:statistics.median(l[key] for l in launches)
                        for key in ['cargo_seconds','execution_seconds','launcher_seconds']}
                checked.update(run_id=workflow.run_id(phase,label), stage_medians=stages)
                cases.append(checked)
                paths = [raw/p for p in ['plan.json','status.json','admission.json','command.log']]
                paths += [supervisor_dir/p for p in ['plan.json','status.json','command.log']]
                paths += [report_dir/p for p in ['summary.json','whole-call-assessment.json']]
                paths += [ROOT/report['raw']/p for p in ['records.json','check-records.json','source-transitions.json']]
                evidence.update({str(p.relative_to(ROOT)):sha(p) for p in paths})
                evidence.update(plan['frozen'])
            source = ROOT/'.work/sources/fre'
            require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip() ==
                    'e0df0b010b156b030a02f073588d28703f4267f3', 'fre source pin differs')
            require(not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source,text=True).strip(),
                    'fre source not restored')
            candidate = [c for c in cases if c['phase'] == 'e2e']
            passed = all(c['passed'] for c in candidate)
            result = dict(status='passed', primary_gates_passed=passed, cases=cases, evidence=evidence,
                candidate_commands=168, candidate_edited_pairs=30, candidate_artifacts=84,
                aa_commands=168, aa_edited_pairs=30, aa_artifacts=84,
                source_restored=True, production_change=False, heldouts_complete=False,
                decision='run fresh native/TLS/fre qualification and the seven separate held-out guards' if passed else 'park bounded whole-call expansion; no threshold changes or tuning retries',
                limitation='Matched source-edit/build/test measurements on one host. A/A envelopes are descriptive, not confidence intervals; cycles and edit states are correlated. No fastest-native or whole-codebase compatibility claim.')
            out = ROOT/'results'/run
            out.mkdir(exist_ok=False)
            write(out/'summary.json', result)
            lines = ['# Whole-call primary decision', '',
                f"The fixed primary gates **{'pass' if passed else 'fail'}**. Next: {result['decision']}.", '',
                '| Phase / case | Paired wall ratio | Paired CPU ratio | Native median | Control median | Candidate median |',
                '| --- | ---: | ---: | ---: | ---: | ---: |']
            for c in cases:
                m = c['median_seconds']
                lines.append(f"| {c['phase']} / {c['label']} | {c['wall_ratio']:.6f} | {c['cpu_ratio']:.6f} | "
                    f"{m['native']:.3f}s | {m['baseline']:.3f}s | {m['candidate']:.3f}s |")
            lines += ['', 'Each phase verifies 168 complete commands, 30 edited pairs and 84 artifact hashes. '
                'Original assertions, wrong edits, independent Cargo checks and source restoration remain. '
                'Both exact VMs/exporters are independently bound; the wrapper is identical. Corresponding bytecode must match in A/A only.', '',
                'Token requires at least 10% complete-command wall improvement, lower child CPU, and a gain '
                'greater than its fixed A/A envelope. Folded must stay within 5% wall and CPU regression. '
                'All A/A pairs and all regressions remain in the report.', '', result['limitation']]
            (out/'assessment.md').write_text('\n'.join(lines)+'\n')
            status.update(status='finished', returncode=0, finished_at=time.time())
            write(work/'status.json', status)
            print(dict(primary_gates_passed=passed, decision=result['decision']), flush=True)
        except BaseException as error:
            status.update(status='failed', error=repr(error), finished_at=time.time())
            write(work/'status.json', status)
            raise


if __name__ == '__main__':
    main()
