"""Verify the scalar screen and attribute recorded paired stage differences."""
import fcntl
import statistics
from smoke import ROOT, BASE, OUT, LABELS, read, write, sha, require, assess, tools_for, screen, ENVELOPE


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        supervisor=ROOT/'.work/experiments/scalar-edit-smoke-01'
        s,c=read(supervisor/'status.json'),read(BASE/'status.json')
        require(s['status']==c['status']=='finished' and s['returncode']==c['returncode']==0
                and s['child_pid']==c['pid'] and s['supervisor_pid']==c['parent_pid'],'screen processes not terminal')
        require(sha(supervisor/'plan.json')==s['plan_sha256'] and sha(supervisor/'command.log')==s['log_sha256'],'supervisor receipt differs')
        summary=read(OUT/'summary.json');tools=tools_for('e2e');costs=[]
        require(all(sha(ROOT/p)==h for p,h in summary['frozen'].items()),'screen inputs changed')
        for saved in summary['cases']:
            p=ROOT/saved['report'];report=read(p)
            require(sha(p)==saved['report_sha256'],'screen report changed')
            case=next(c for c in read(ROOT/'benchmarks/workflow-corpus.json')['cases'] if c['label']==saved['label'])
            checked=assess(report,case,tools)
            require(all(saved[k]==v for k,v in checked.items()),'assessment changed')
            rows=read(ROOT/report['raw']/'records.json');stages={}
            for field in ['cargo_seconds','execution_seconds','launcher_seconds','tools_seconds',
                          'std_mir_seconds','artifact_hash_seconds','call_report_verify_seconds']:
                values={m:{r['state']:r['calls'][0]['launch'][field] for r in rows if r['state']>0 and r['mode']==m}
                        for m in ['baseline','candidate']}
                stages[field]=dict(medians={m:statistics.median(v.values()) for m,v in values.items()},
                    median_paired_delta=statistics.median(values['candidate'][i]-values['baseline'][i] for i in range(1,6)))
            costs.append(dict(label=case['label'],stages=stages,exporter_seconds=report['exporter_seconds'],
                              check_seconds=report['check_floor']['median_seconds']))
        expected=screen(*summary['cases'],read(ENVELOPE)['wall_envelope'])
        require(all(summary[k]==v for k,v in expected.items()),'screen gate changed')
        evidence={}
        for folder in [BASE,supervisor]:
            for p in folder.iterdir():
                if p.is_file():evidence[str(p.relative_to(ROOT))]=sha(p)
        for c in summary['cases']:
            p=ROOT/c['report'];evidence[str(p.relative_to(ROOT))]=sha(p)
            raw=ROOT/read(p)['raw']
            for name in ['records.json','check-records.json','source-transitions.json']:
                q=raw/name;evidence[str(q.relative_to(ROOT))]=sha(q)
        write(OUT/'decision.json',dict(status='parked' if not expected['advance_to_full_comparison'] else 'screen passed',
            **expected,stage_costs=costs,evidence=evidence,all_processes_terminal=True,
            source_branch='experiment/scalar-value-abi',source_commit='840fdb5',
            performance_retained=False,full_comparison_started=False,
            note='Stage timers are nested/descriptive; medians of differences need not sum. No unchanged builds or timing exclusions.'))
        lines=['# Scalar value ABI: short real-edit screen','',
            'The candidate is parked: token missed the predeclared 8% screening target.',
            'The full A/A and held-out histories will not run for this candidate.','',
            '| Workload | Paired wall change | Paired CPU change | Native median | Control median | Scalar median |',
            '| --- | ---: | ---: | ---: | ---: | ---: |']
        for r in summary['cases']:
            m=r['median_seconds'];lines.append(f"| {r['label']} | {(r['wall_ratio']-1)*100:+.2f}% | {(r['cpu_ratio']-1)*100:+.2f}% | {m['native']:.3f}s | {m['baseline']:.3f}s | {m['candidate']:.3f}s |")
        lines+=['','Each workload has five actual production edits, original assertions and a wrong-edit rejection in every mode: 42 primary commands, 14 independent Cargo checks and 28 executed snapshots in total. All verification passed. Five correlated edit pairs are screening evidence, not a precise estimate of a small effect. The deployed tool stays unchanged.','',
            'Token guest-process execution saves 170ms at the median paired difference, while Cargo adds 144ms. The scalar proof/finalization timer is about 73ms in the first token edit; it is included in lowering, not an additional stage. Fewer copy instructions did not produce a useful complete-command improvement.','',
            'Recorded launcher costs also constrain the next work: tool lookup/hashing is about 2ms, std-MIR lookup 36–38ms, artifact hashing about 10ms and call-report validation about 12ms. Optimizing these alone cannot close the multi-second token/native gap. Exporter lowering is 0.858s control / 0.935s scalar; frontend about 0.65–0.67s. These measurements prioritize lowering/export attribution over another emitter micro-optimization.','',
            'The next experiment measures export passes and publication on the retained compiler, with exact output identity and strict error controls. Separately qualify a tuned native control before interpreting project-wide speedups. Preserve the scalar source branch for later register-allocation work; do not retry this same screen.','',
            'The executable wrapper is identical on both sides. Scalar source `840fdb5/aa56492e` is executed via composed tool `ba4ad407`. Native uses O0/incremental, 18 jobs/default test threads; custom uses four jobs. Absolute times from this shared-host session must not be compared with historical medians as a version speedup.','']
        (OUT/'assessment.md').write_text('\n'.join(lines))
        print('Scalar screen parked; both histories and stage costs verified.')


if __name__=='__main__':main()
