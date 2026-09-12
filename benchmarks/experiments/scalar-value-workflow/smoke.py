#!/usr/bin/env python3
"""One real-edit cycle per primary; screen before funding the full comparison."""
import argparse
import copy
import fcntl
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

from common import ROOT, HERE, CONTROL, CANDIDATE, LAUNCHER, read, write, sha, require, qualifications, tools_for
from stage import stage
from scalar_checks import check_call
from verify_base import verify
sys.path.insert(0, str(HERE.parent / 'aggregate-byte-writes'))
from heldout_controls import compare_controls

LABELS = ['token-phrase', 'folded-literal-trie']
BASE = ROOT / '.work/scalar-edit-smoke-01'
OUT = ROOT / 'results/scalar-edit-smoke-01'
ENVELOPE = ROOT / 'results/budget-register-aa-01-token-phrase/budget-assessment.json'


def screen(token, folded, envelope):
    threshold = max(.08, 2 * envelope)
    return dict(minimum_token_improvement=threshold,
                advance_to_full_comparison=1-token['wall_ratio'] >= threshold
                and token['cpu_ratio'] < 1 and folded['wall_ratio'] <= 1.05
                and folded['cpu_ratio'] <= 1.05)


def storage():
    """Full three-cycle cache sizes overbound this one-cycle pair of histories."""
    evidence = {}; cases = []
    for label in LABELS:
        sizes = []
        for phase in ['aa', 'e2e']:
            total = 0
            for mode in ['native', 'check', 'baseline', 'candidate']:
                p = ROOT / f'results/parked-budget-{phase}-{label}-{mode}-archive-01/plan.json'
                plan = read(p); evidence[str(p.relative_to(ROOT))] = sha(p)
                total += sum(g['bytes'] for g in plan['manifest']['groups'])
            sizes.append(total)
        p = ROOT / f'results/budget-register-e2e-01-{label}/summary.json'
        report = read(p); evidence[str(p.relative_to(ROOT))] = sha(p)
        records = ROOT / report['raw'] / 'records.json'
        evidence[str(records.relative_to(ROOT))] = sha(records)
        artifacts = [ROOT/a['path'] for r in read(records) for a in r['artifacts']]
        require(len(artifacts) == 42, 'incomplete storage reference')
        cases.append(dict(label=label, cache_bytes=max(sizes),
                          artifact_bytes=14 * max(p.stat().st_size for p in artifacts)))
    growth = (sum(c['cache_bytes']+c['artifact_bytes'] for c in cases)*120+99)//100
    return dict(cases=cases, evidence=evidence, growth_percent=20,
                command_floor_bytes=8*1024**3, metadata_bytes=256*1024**2,
                minimum_free_bytes=8*1024**3+256*1024**2+growth,
                note='Both fresh histories admitted together; full historical cache sizes plus 14 largest snapshots each, 20% growth. No additional archive batch is planned for this smoke.')


def assess(report, case, tools):
    normalized = copy.deepcopy(report)
    require(report['cycles'] == 1, 'smoke cycle count differs')
    require(report['scripts_sha256'][str(LAUNCHER.relative_to(ROOT))] == sha(LAUNCHER), 'launcher differs')
    for mode in ['baseline', 'candidate']:
        value = normalized['tool_builds'][mode].pop('scalar_values')
        require(type(value) is bool and value == (mode == 'candidate'), 'scalar configuration differs')
    compare_controls(normalized, case, tools)
    checked = verify(report, tools)
    require(tuple(checked[k] for k in ['commands','check_commands','edited_pairs','exact_artifact_hashes_verified'])
            == (21,7,5,14), 'incomplete smoke history')
    rows = read(ROOT / report['raw'] / 'records.json')
    for row in rows:
        if row['mode'] == 'native': continue
        require(len(row['calls']) == len(row['artifacts']) == 1, 'unbatched smoke')
        call = row['calls'][0]; mode = row['mode']
        require(call['command'].count('--tool-key') == 1 and
                call['command'][call['command'].index('--tool-key')+1] == call['launch']['tool_key'] == tools[mode]['tool_key'], 'executed tool differs')
        check_call(call, ROOT/row['artifacts'][0]['path'], mode == 'candidate')
    pairs = []
    for state in range(1,6):
        selected = {r['mode']:r for r in rows if r['state'] == state}
        a,b = selected['baseline'],selected['candidate']
        pairs.append(dict(state=state,wall_ratio=b['seconds']/a['seconds'],cpu_ratio=b['cpu_seconds']/a['cpu_seconds']))
    require(all(math.isfinite(p[k]) and p[k] > 0 for p in pairs for k in ['wall_ratio','cpu_ratio']), 'invalid ratios')
    for key, field in [('seconds','median_seconds'),('cpu_seconds','median_cpu_seconds')]:
        require(report[field] == {m:statistics.median(r[key] for r in rows if r['state']>0 and r['mode']==m)
                                  for m in ['native','baseline','candidate']}, 'reported median differs')
    return dict(label=case['label'], verification=checked, pairs=pairs,
                wall_ratio=statistics.median(p['wall_ratio'] for p in pairs),
                cpu_ratio=statistics.median(p['cpu_ratio'] for p in pairs),
                median_seconds=report['median_seconds'], median_cpu_seconds=report['median_cpu_seconds'],
                cold_seconds=report['cold_success_seconds'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args=parser.parse_args()
    if args.check:
        assert screen(dict(wall_ratio=.90,cpu_ratio=.99),dict(wall_ratio=1,cpu_ratio=1),.04)['advance_to_full_comparison']
        assert not screen(dict(wall_ratio=.93,cpu_ratio=.99),dict(wall_ratio=1,cpu_ratio=1),.04)['advance_to_full_comparison']
        assert not screen(dict(wall_ratio=.90,cpu_ratio=1.01),dict(wall_ratio=1,cpu_ratio=1),.04)['advance_to_full_comparison']
        assert not screen(dict(wall_ratio=.90,cpu_ratio=.99),dict(wall_ratio=1.06,cpu_ratio=1),.04)['advance_to_full_comparison']
        print('Four screen boundary checks passed'); return
    BASE.mkdir(exist_ok=False); OUT.mkdir(exist_ok=False)
    status=dict(status='preflight',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time())
    write(BASE/'status.json',status)
    try:
        with (ROOT/'.work/benchmark.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            prereqs=qualifications(); tools=tools_for('e2e')
            controls=read(ROOT/'results/scalar-workflow-controls-01/summary.json')
            require(controls['status']=='passed' and all(sha(ROOT/p)==h for p,h in controls['frozen'].items()), 'qualified harness changed')
            estimate=storage(); fs=os.statvfs(ROOT); free=fs.f_bavail*fs.f_frsize
            write(BASE/'admission.json',dict(estimate,observed_free_bytes=free,checked_at=time.time(),passed=free>=estimate['minimum_free_bytes']))
            require(free>=estimate['minimum_free_bytes'], 'both histories do not fit; no child started')
            paths=prereqs+[Path(__file__),ENVELOPE,HERE/'SMOKE.md']
            frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
            frozen.update(controls['frozen'])
            envelope=read(ENVELOPE)['wall_envelope']
            write(BASE/'plan.json',dict(frozen=frozen,tools=tools,labels=LABELS,
                minimum_token_improvement=max(.08,2*envelope),historical_aa_envelope=envelope,
                source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()))
        results=[]
        for label in LABELS:
            case=next(c for c in read(ROOT/'benchmarks/workflow-corpus.json')['cases'] if c['label']==label)
            run='scalar-edit-smoke-01-'+label
            harness=BASE/(label+'.py'); harness.write_text(stage((ROOT/'scripts/bench_e2e_workflow.py').read_text(),'e2e'))
            frozen[str(harness.relative_to(ROOT))]=sha(harness)
            command=[sys.executable,str(harness),'--run-id',run,'--project',case['project'],'--workflow',case['workflow'],
                     '--cycles','1','--jobs','4','--native-jobs','18','--native-profile','o0-incremental',
                     '--native-test-threads','default','--check-floor','--minimum-free-gib','8',
                     '--baseline-tool-key',CONTROL,'--candidate-tool-key',CANDIDATE,'--comparison-engine','jit',
                     '--baseline-jit-resumable-calls','--baseline-jit-persistent-registers',
                     '--candidate-jit-resumable-calls','--candidate-jit-persistent-registers',*case['flags']]
            env=os.environ.copy();env['PYTHONPATH']=str(ROOT/'scripts')
            with (BASE/(label+'.log')).open('x') as log:
                child=subprocess.Popen(command,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
                status.update(status='running',child_pid=child.pid,command=command,label=label,child_started_at=time.time())
                write(BASE/'status.json',status);code=child.wait()
            status.update(child_returncode=code);write(BASE/'status.json',status)
            require(code==0,'smoke failed; preserve history')
            with (ROOT/'.work/benchmark.lock').open('a') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                require(all(sha(ROOT/p)==h for p,h in frozen.items()),'frozen input changed')
                p=ROOT/'results'/run/'summary.json'; result=assess(read(p),case,tools)
                result.update(report=str(p.relative_to(ROOT)),report_sha256=sha(p),command=command,
                              log_sha256=sha(BASE/(label+'.log')),child_pid=child.pid,returncode=code)
                results.append(result);write(OUT/(label+'.json'),result)
                print(label,result['wall_ratio'],result['cpu_ratio'],flush=True)
        decision=screen(results[0],results[1],envelope)
        write(OUT/'summary.json',dict(status='passed',cases=results,**decision,frozen=frozen,
            historical_aa_envelope=envelope,performance_screen_only=True,
            note='Five changed-source pairs per case; 15 edited primary commands plus cold and wrong-edit controls. Screening is not retention evidence. Full original gates remain unchanged.'))
        status.update(status='finished',returncode=0,finished_at=time.time());write(BASE/'status.json',status)
        print(decision,flush=True)
    except BaseException as error:
        status.update(status='failed',error=repr(error),finished_at=time.time());write(BASE/'status.json',status)
        raise


if __name__=='__main__':main()
