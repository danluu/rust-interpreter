#!/usr/bin/env python3
"""Reverify both complete primary histories and apply the predeclared decision."""
import fcntl
import math
import statistics
from pathlib import Path
from run_relocation import ROOT,HERE,TOOLS,sha,read,write,assess,require

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        cases=[];evidence={}
        for label,workflow in [('folded-literal-trie','folded-literal-trie'),('token-phrase','token-phrase-allocation')]:
            run='aggregate-relocation-e2e-01-'+label
            receipt=ROOT/'.work/experiments'/run/'status.json'
            terminal=read(receipt)
            require(terminal['status']=='finished' and terminal['returncode']==0,'primary process incomplete')
            path=ROOT/'results'/run/'summary.json';report=read(path)
            require(report['workflow']==workflow,'workflow identity differs')
            result=assess(report);recorded=read(path.with_name('relocation-assessment.json'))
            require(all(recorded[k]==v for k,v in result.items()),'recorded assessment differs')
            for name,digest in recorded['evidence'].items():
                require(sha(ROOT/name)==digest,'measured or frozen evidence changed');evidence[name]=digest
            rows_path=ROOT/report['raw']/'records.json';rows=read(rows_path)
            for r in rows:
                require(all(math.isfinite(r[k]) and r[k]>0 for k in ['seconds','cpu_seconds']),'non-finite measurement')
            for mode in ['native','baseline','candidate']:
                for key,field in [('seconds','median_seconds'),('cpu_seconds','median_cpu_seconds')]:
                    actual=statistics.median(r[key] for r in rows if r['state']>0 and r['mode']==mode)
                    require(abs(actual-report[field][mode])<1e-9,'reported median differs from raw commands')
            for p in [receipt,rows_path,path.with_name('relocation-assessment.json')]:evidence[str(p.relative_to(ROOT))]=sha(p)
            cases.append(dict(label=label,run_id=run,assessment=result))
        for p in [Path(__file__),HERE/'RELOCATION-NEXT.md',HERE/'CORRECTNESS.md',HERE/'run_relocation.py',HERE/'verify_relocation.py']:
            evidence[str(p.relative_to(ROOT))]=sha(p)
        passed=all(c['assessment']['passed'] for c in cases)
        decision=('Both primary gates pass. Proceed to fresh broad native/TLS/fre qualification and all seven held-outs; do not retain the compiler change before those pass.' if passed else
            'At least one primary gate fails. Park this transformation without a threshold sweep; proceed to the separate unfiltered-suite compatibility direction.')
        result=dict(status='passed',primary_performance_gates_passed=passed,production_retained=False,expected_tools=TOOLS,
            commands=168,edited_pairs=30,artifacts=84,cases=cases,evidence=evidence,decision=decision)
        out=ROOT/'results/aggregate-relocation-e2e-01';out.mkdir(exist_ok=False);write(out/'summary.json',result)
        lines=['# Private aggregate frame relocation: complete primary edit benchmarks','',
            '| Workflow | Paired wall change | Paired CPU change | Native median | Control median | Candidate median | Gate |',
            '| --- | ---: | ---: | ---: | ---: | ---: | --- |']
        for c in cases:
            r=c['assessment'];m=r['median_seconds']
            lines.append(f"| {c['label']} | {(r['wall_ratio_candidate_over_baseline']-1)*100:+.2f}% | {(r['cpu_ratio_candidate_over_baseline']-1)*100:+.2f}% | {m['native']:.3f}s | {m['baseline']:.3f}s | {m['candidate']:.3f}s | {'pass' if r['passed'] else 'fail'} |")
        lines += ['',decision,'','All 168 commands, 30 edited pairs and 84 artifact hashes verify. These are real production-source edits, including wrong-edit rejection and source restoration; no unchanged-build timings enter the paired result. Three cycles rotate mode order. Native/check controls are retained. Only the exporter changes between custom modes: VM, wrapper, frontend flags and runtime options match. Candidate times include all added analysis and relocation work.','',
            'Artifacts can differ across this compiler transformation. Original assertions and focused differentials pass; this does not formally prove semantic equivalence or full Rust support. Three cycles on a shared host are descriptive, not independent statistical trials. Setup and target-cache-cold commands are recorded separately.','']
        (out/'assessment.md').write_text('\n'.join(lines))
        print(dict(primary_performance_gates_passed=passed,commands=168,edited_pairs=30,artifacts=84))

if __name__=='__main__':main()
