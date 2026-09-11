#!/usr/bin/env python3
"""Read the candidate pass timers from already completed edit histories."""
import copy
import fcntl
import json
import math
import statistics
from pathlib import Path
from build_relocation import ROOT,HERE,read,write,sha,require
from run_relocation import assess

PREFIX='rust-interp-aggregate-frames: '

def pass_record(stderr):
    lines=[line[len(PREFIX):] for line in stderr.splitlines() if line.startswith(PREFIX)]
    require(len(lines)==1,'missing or duplicate aggregate timer')
    try:r=json.loads(lines[0])
    except (ValueError,TypeError) as error:raise RuntimeError('invalid aggregate timer JSON') from error
    require(isinstance(r,dict) and set(r)=={'capture_seconds','finalize_seconds','declines','functions','initialization_unchanged','static_bytes_saved'},'aggregate timer schema differs')
    require(r['initialization_unchanged'] is True,'initialization policy differs')
    require(all(type(r[k]) in [int,float] and math.isfinite(r[k]) and r[k]>=0 for k in ['capture_seconds','finalize_seconds']),'invalid aggregate timer')
    require(all(type(r[k]) is int and r[k]>=0 for k in ['functions','static_bytes_saved']) and
        ((r['functions']==0)==(r['static_bytes_saved']==0)),'invalid frame saving counters')
    require(isinstance(r['declines'],dict) and all(isinstance(k,str) and k and type(v) is int and v>0 for k,v in r['declines'].items()),'invalid decline counters')
    return r

def check():
    r=dict(capture_seconds=.125,finalize_seconds=.25,declines={},functions=2,initialization_unchanged=True,static_bytes_saved=32)
    encode=lambda x:PREFIX+json.dumps(x)
    require(pass_record(encode(r))==r,'valid timer changed')
    bad=['',encode(r)+'\n'+encode(r),PREFIX+'{']
    for key,value in [('capture_seconds',float('nan')),('capture_seconds',-1),('finalize_seconds',float('inf')),
        ('functions',True),('static_bytes_saved',-1),('functions',0),('initialization_unchanged',False),
        ('declines',{'bounded':0}),('declines',[]),('extra',1)]:
        x=copy.deepcopy(r);x[key]=value;bad.append(encode(x))
    x=copy.deepcopy(r);x.pop('finalize_seconds');bad.append(encode(x))
    for value in bad:
        try:pass_record(value)
        except RuntimeError:pass
        else:raise RuntimeError('accepted invalid timer')
    return len(bad)

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        rejected=check();cases=[];evidence={}
        for label in ['folded-literal-trie','token-phrase']:
            path=ROOT/'results'/('aggregate-relocation-e2e-01-'+label)/'summary.json';report=read(path)
            checked=assess(report);recorded=read(path.with_name('relocation-assessment.json'))
            require(all(recorded[k]==v for k,v in checked.items()),'original assessment differs')
            records=ROOT/report['raw']/'records.json';rows=read(records);pairs=[]
            for cycle in range(3):
                for state in range(1,6):
                    selected={r['mode']:r for r in rows if r['cycle']==cycle and r['state']==state}
                    a,b=(selected[m]['calls'][0] for m in ['candidate','baseline'])
                    require(PREFIX not in b['stderr'],'baseline contains candidate pass output')
                    timer=pass_record(a['stderr']);total=timer['capture_seconds']+timer['finalize_seconds']
                    require(total<=a['launch']['cargo_seconds']+1e-6,'pass timers exceed Cargo duration')
                    pairs.append(dict(cycle=cycle,state=state,**timer,observed_pass_seconds=total,
                        cargo_delta_seconds=a['launch']['cargo_seconds']-b['launch']['cargo_seconds'],
                        execution_delta_seconds=a['launch']['execution_seconds']-b['launch']['execution_seconds'],
                        command_delta_seconds=selected['candidate']['seconds']-selected['baseline']['seconds']))
            fields=['capture_seconds','finalize_seconds','observed_pass_seconds','cargo_delta_seconds','execution_delta_seconds','command_delta_seconds']
            cases.append(dict(label=label,edited_pairs=15,medians={k:statistics.median(p[k] for p in pairs) for k in fields},
                functions_range=[min(p['functions'] for p in pairs),max(p['functions'] for p in pairs)],
                static_bytes_saved_range=[min(p['static_bytes_saved'] for p in pairs),max(p['static_bytes_saved'] for p in pairs)],
                decline_totals={k:sum(p['declines'].get(k,0) for p in pairs) for k in {k for p in pairs for k in p['declines']}},pairs=pairs))
            for p in [path,records,path.with_name('relocation-assessment.json')]:evidence[str(p.relative_to(ROOT))]=sha(p)
        for p in [Path(__file__),HERE/'run_relocation.py',HERE/'verify_relocation.py',ROOT/'results/aggregate-relocation-e2e-01/summary.json']:
            evidence[str(p.relative_to(ROOT))]=sha(p)
        result=dict(status='passed',cases=cases,timer_parser_rejections=rejected,evidence=evidence,new_benchmark_run=False,
            note='Timers cover capture/finalization, not all earlier span/origin recording. Paired Cargo/execution deltas also contain other pass effects and host noise. Component medians need not add to command medians. No causal speedup claim or gate change follows from this diagnostic.')
        out=ROOT/'results/aggregate-relocation-pass-costs-01';out.mkdir(exist_ok=False);write(out/'summary.json',result)
        lines=['# Recorded aggregate pass cost in actual edits','',
            '| Workflow | Capture + finalize | Paired Cargo delta | Paired execution delta | Paired command delta |',
            '| --- | ---: | ---: | ---: | ---: |']
        for c in cases:
            m=c['medians'];lines.append(f"| {c['label']} | {m['observed_pass_seconds']*1000:.1f} ms | {m['cargo_delta_seconds']*1000:+.1f} ms | {m['execution_delta_seconds']*1000:+.1f} ms | {m['command_delta_seconds']*1000:+.1f} ms |")
        lines += ['',result['note'],'','All 30 source-edit pairs are reverified from the completed primary histories. No compilation, execution, source edit or timing rerun was performed.','']
        (out/'assessment.md').write_text('\n'.join(lines));print({c['label']:c['medians'] for c in cases})

if __name__=='__main__':main()
