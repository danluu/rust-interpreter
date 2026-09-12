#!/usr/bin/env python3
"""Read-only provenance adapter for completed guarded-Call benchmark caches.

Only evidence selection is injected into the unchanged qualified archive
lifecycle. Existing build archive and guest workflow selectors are untouched.
"""
import fcntl
from pathlib import Path
import subprocess
import sys
import archive as driver

ROOT = driver.ROOT
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/call-slot-fast-path'))
import workflows as workflow
from workflow_cache_evidence import derive, cache_guard
PRIMARY = ROOT / 'results/call-slot-primary-01/summary.json'
PRIMARY_SHA = '24e3383754a3b131c49915721716a14d1fb62f550f100e3a49a58a1b8a153576'
ALLOWED = {workflow.run_id(phase,label)+':'+mode: (phase,label,mode)
    for phase,label in workflow.ORDER for mode in ['native','check','baseline','candidate']}
BASE_SOURCES = driver.sources
BASE_PREPARE, BASE_APPLY = driver.prepare, driver.apply


def select(selection):
    driver.require(selection in ALLOWED, 'uncatalogued public workflow/mode')
    return ALLOWED[selection]


def evidence(selection):
    phase,label,mode = select(selection)
    run = workflow.run_id(phase,label)
    driver.require(driver.sha(PRIMARY)==PRIMARY_SHA, 'completed primary decision changed')
    primary=driver.read(PRIMARY)
    driver.require(primary['status']=='passed' and not primary['primary_gates_passed'] and
        primary['source_restored'], 'parked experiment completion differs')
    proofs=dict(primary['evidence']);proofs[str(PRIMARY.relative_to(ROOT))]=PRIMARY_SHA
    report=driver.read(ROOT/'results'/run/'summary.json')
    saved=driver.read(ROOT/'results'/run/'slot-assessment.json')
    case=next(c for c in driver.read(ROOT/'benchmarks/workflow-corpus.json')['cases'] if c['label']==label)
    checked=workflow.assess(report,case,phase)
    driver.require(all(saved[k]==v for k,v in checked.items()), 'completed assessment differs')
    supervisor=driver.read(ROOT/'.work/experiments'/run/'status.json')
    controller=driver.read(ROOT/'.work'/run/'status.json')
    driver.require(supervisor['status']==controller['status']=='finished' and
        supervisor['returncode']==controller['returncode']==controller['child_returncode']==0 and
        supervisor['owner']==supervisor['cwd']==str(ROOT) and
        supervisor['child_pid']==controller['pid'] and supervisor['supervisor_pid']==controller['parent_pid'] and
        supervisor['command']==['python3','benchmarks/experiments/call-slot-fast-path/workflows.py','--phase',phase,'--case',label],
        'completed process ownership differs')
    raw=ROOT/report['raw'];rows=driver.read(raw/'records.json');checks=driver.read(raw/'check-records.json')
    target,_,snapshots=derive(ROOT,run,report,rows,checks,'check' if mode=='native' else mode)
    if mode=='native':target=raw/'native'  # derive checked every exact native target command.
    for path in snapshots:proofs[str(path.relative_to(ROOT))]=driver.sha(path)
    proofs.update(saved['evidence'])
    driver.require(all(driver.sha(ROOT/p)==h for p,h in proofs.items()), 'external workflow evidence changed')
    driver.require(all(target not in (ROOT/p).parents for p in proofs), 'proof inside retirement target')
    pids=[supervisor['supervisor_pid'],controller['pid'],controller['child_pid']]
    observed=subprocess.run(['ps','-p',','.join(map(str,pids)),'-o','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
    driver.require(observed.returncode in [0,1] and not observed.stderr and
        all(run not in line for line in observed.stdout.splitlines()[1:]), 'owned benchmark process still live')
    return target,proofs


def sources():
    result=BASE_SOURCES()
    for path in [Path(__file__),Path(workflow.__file__),ROOT/'scripts/workflow_cache_evidence.py']:
        result[str(path.relative_to(ROOT))]=driver.sha(path)
    return result


def prepare(selection, name):
    target, _ = evidence(selection)
    with cache_guard(target, select(selection)[2]):
        BASE_PREPARE(selection, name)


def apply(name):
    _, plan, _, target = driver.load(name)
    with cache_guard(target, select(plan['run'])[2]):
        BASE_APPLY(name)


def check():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        selected=[]
        for mode in ['native','check','baseline','candidate']:
            identity='call-slot-e2e-01-token-phrase:'+mode
            target,proofs=evidence(identity)
            selected.append(dict(selection=identity,target=str(target),proofs=len(proofs)))
        rejected=0
        for bad in ['rg-aot:native','../call-slot-e2e-01-token-phrase:native',
                    'call-slot-e2e-01-token-phrase:host','whole-call-e2e-02-token-phrase:native']:
            try: select(bad)
            except RuntimeError:rejected+=1
            else:raise RuntimeError('invalid workflow selection accepted')
        driver.require(len({x['target'] for x in selected})==4, 'shared workflow target')
        out=ROOT/'results/parked-workflow-cache-controls-01';out.mkdir(exist_ok=False)
        driver.write_json(out/'summary.json',dict(status='passed',selected=selected,rejected=rejected,
            sources=sources(),cache_mutations=0,original_workflow_checks_recomputed=True))
        print('four exact target modes, all workflow checks and 4 invalid selections pass')


def main():
    driver.evidence=evidence
    driver.sources=sources
    driver.prepare, driver.apply = prepare, apply
    if sys.argv[1:]==['--check']:check()
    else:driver.main()


if __name__=='__main__':main()
