"""Attribute recorded stages descriptively after the fixed primary decision."""
import fcntl
from pathlib import Path
import re
import statistics
import workflows as workflow


def inline(stderr):
    matches=re.findall(r'^rust-interp-inline: sites=(\d+) operations=(\d+) seconds=(\d+\.\d+)$',stderr,re.M)
    workflow.require(len(matches)==1,'missing or duplicate inlining timer')
    sites,operations,seconds=matches[0]
    return dict(sites=int(sites),operations=int(operations),seconds=float(seconds))


def main():
    root=workflow.ROOT
    with (root/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        primary=root/'results/whole-call-primary-02/summary.json'
        decision=workflow.read(primary)
        workflow.require(decision['status']=='passed' and not decision['primary_gates_passed'], 'fixed decision differs')
        evidence={str(primary.relative_to(root)):workflow.sha(primary),str(Path(__file__).relative_to(root)):workflow.sha(Path(__file__))}
        cases=[]
        for label in ['folded-literal-trie','token-phrase']:
            name=workflow.run_id('e2e',label);folder=root/'results'/name
            report=workflow.read(folder/'summary.json');saved=workflow.read(folder/'whole-call-assessment.json')
            case=next(c for c in workflow.read(root/'benchmarks/workflow-corpus.json')['cases'] if c['label']==label)
            checked=workflow.assess(report,case,'e2e')
            workflow.require(all(saved[k]==v for k,v in checked.items()),'fixed assessment changed')
            rows=workflow.read(root/report['raw']/'records.json');pairs=[]
            for cycle in range(3):
                for state in range(1,6):
                    selected={r['mode']:r for r in rows if r['cycle']==cycle and r['state']==state}
                    a,b=[selected[m]['calls'][0] for m in ['baseline','candidate']]
                    aa,bb=inline(a['stderr']),inline(b['stderr'])
                    workflow.require(aa['seconds']<=a['launch']['cargo_seconds'] and bb['seconds']<=b['launch']['cargo_seconds'],
                        'pass timer exceeds Cargo command')
                    pairs.append(dict(cycle=cycle,state=state,control_inline=aa,candidate_inline=bb,
                        inline_delta_seconds=bb['seconds']-aa['seconds'],
                        cargo_delta_seconds=b['launch']['cargo_seconds']-a['launch']['cargo_seconds'],
                        execution_delta_seconds=b['launch']['execution_seconds']-a['launch']['execution_seconds'],
                        command_delta_seconds=selected['candidate']['seconds']-selected['baseline']['seconds']))
            fields=['inline_delta_seconds','cargo_delta_seconds','execution_delta_seconds','command_delta_seconds']
            cases.append(dict(label=label,pairs=pairs,medians={k:statistics.median(p[k] for p in pairs) for k in fields},
                control_operations_range=[min(p['control_inline']['operations'] for p in pairs),max(p['control_inline']['operations'] for p in pairs)],
                candidate_operations_range=[min(p['candidate_inline']['operations'] for p in pairs),max(p['candidate_inline']['operations'] for p in pairs)]))
            for path in [folder/'summary.json',folder/'whole-call-assessment.json',root/report['raw']/'records.json']:
                evidence[str(path.relative_to(root))]=workflow.sha(path)
        note='Paired stage medians are observations, not causal attribution, and need not sum to the command median. Original entropy and every pair remain. No new build, guest execution or changed gate.'
        out=root/'results/whole-call-costs-01';out.mkdir(exist_ok=False)
        workflow.write(out/'summary.json',dict(status='passed',cases=cases,evidence=evidence,new_guest_executions=0,note=note))
        lines=['# Recorded whole-call stage costs','','| Case | Inlining timer delta | Cargo delta | Execution delta | Command delta |',
            '| --- | ---: | ---: | ---: | ---: |']
        for c in cases:
            m=c['medians'];lines.append('| '+c['label']+' | '+' | '.join(f'{1000*m[k]:+.1f} ms' for k in fields)+' |')
        lines+=['',note,'','The next investigation should examine scalar argument/result materialization at call boundaries. Existing native Calls already cross guest frames without returning to the Rust VM; simply adding native branches would repeat implemented work. Any new ABI needs typed eligibility, exact interpreter/JIT agreement and a new fixed end-to-end gate.','']
        (out/'assessment.md').write_text('\n'.join(lines))
        print({c['label']:c['medians'] for c in cases})


if __name__=='__main__':main()
