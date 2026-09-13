"""Audit exactly the four completed cases before the unstarted Nushell guard."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
FULL=ROOT/'benchmarks/experiments/guarded-local-facts-full'
sys.path.insert(0,str(FULL));sys.path.insert(0,str(ROOT/'scripts'))
import full as protocol
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write

PREFIX=protocol.CASES[:4]
OLD='guarded-local-facts-full-01'
HARNESS='guarded-local-facts-continuation-protocol-01'


def command_for(case):
    script='workflows.py' if case in PREFIX[:3] else 'large_compare.py'
    command=[sys.executable,str(FULL/script),'--case',case,'--run-id','guarded-local-facts-edit-'+case+'-01']
    if case in PREFIX[:3]:command+=['--build','results/guarded-local-facts-build-03/summary.json']
    return command


def validate_prefix(records,completed,unstarted):
    assert len(records)==5 and [r['case'] for r in records]==protocol.CASES
    assert len(completed)==4 and [r['case'] for r in completed]==PREFIX
    assert protocol.next_case(completed)=='nushell'
    assert sum(r['commands'] for r in completed)==594
    for index,row in enumerate(records):
        assert row['command'][1:]==command_for(row['case'])[1:]
        assert row['returncode']==(0 if index<4 else 1)
        assert ('summary_sha256' in row)==(index<4)
    assert unstarted, 'Nushell already has a case directory or result'
    return True


def harness_inputs():
    path=ROOT/'results'/HARNESS/'summary.json';proof=json.loads(path.read_text())
    assert proof['status']=='passed' and proof['tests']==27 and proof['guest_commands']==0
    inputs=ROOT/proof['raw']/'inputs.json';assert sha(inputs)==proof['inputs_sha256']
    frozen=json.loads(inputs.read_text());protocol.verify_manifest(frozen)
    return {str(path.relative_to(ROOT)):sha(path),str(inputs.relative_to(ROOT)):sha(inputs),**frozen}


def audit_original():
    raw=ROOT/'.work'/OLD;outer=ROOT/'.work/experiments'/OLD
    terminal=json.loads((outer/'status.json').read_text())
    assert terminal['owner']==str(ROOT) and terminal['cwd']==str(ROOT)
    assert terminal['status']=='finished' and terminal['returncode']==1
    assert terminal['supervisor_pid']==93275 and terminal['child_pid']==93278
    assert terminal['command'][1:]==['benchmarks/experiments/guarded-local-facts-full/full.py','--run-id',OLD]
    assert sha(outer/'plan.json')==terminal['plan_sha256'] and sha(outer/'command.log')==terminal['log_sha256']
    plan=json.loads((raw/'plan.json').read_text());assert plan['owner']==str(ROOT)
    assert plan['cases']==protocol.CASES and plan['maximum_commands']==726 and plan['stop_on_failed_gate']
    protocol.verify_manifest(plan['frozen'])
    records=json.loads((raw/'records.json').read_text())
    completed=[json.loads(protocol.case_path(case).read_text()) for case in PREFIX]
    pending=ROOT/'.work/guarded-local-facts-edit-nushell-01'
    assert validate_prefix(records,completed,not pending.exists() and not protocol.case_path('nushell').exists())
    evidence={}
    for path in [outer/'status.json',outer/'plan.json',outer/'command.log',raw/'plan.json',raw/'records.json']:
        evidence[str(path.relative_to(ROOT))]=sha(path)
    for row in records:
        for stream in ['stdout','stderr']:
            path=raw/(row['case']+'.'+stream);assert sha(path)==row[stream+'_sha256'];evidence[str(path.relative_to(ROOT))]=sha(path)
        if row['case'] in PREFIX:
            path=protocol.case_path(row['case']);assert sha(path)==row['summary_sha256'];evidence[str(path.relative_to(ROOT))]=sha(path)
    assert (raw/'nushell.stderr').read_text().rstrip().endswith('AssertionError: insufficient pre-edit cache admission')
    audit=protocol.audit_cases(PREFIX)
    return evidence,audit


def load_prefix(path):
    proof=json.loads(path.read_text());assert proof['status']=='passed' and proof['commands_retained']==594
    assert proof['completed_cases']==PREFIX and proof['unstarted_cases']==['nushell'] and proof['new_guest_commands']==0
    assert proof['all_four_gates_passed'] and proof['final_source_and_input_audit_passed']
    raw=ROOT/proof['raw']
    for name in ['plan','audit']:
        assert sha(raw/(name+'.json'))==proof[name+'_sha256']
    plan=json.loads((raw/'plan.json').read_text());protocol.verify_manifest(plan['frozen'])
    evidence,audit=audit_original()
    assert evidence==plan['original_evidence']
    return proof,evidence,audit


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    args=parser.parse_args();assert args.run_id=='guarded-local-facts-full-prefix-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        frozen=harness_inputs();evidence,audit=audit_original()
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,original_evidence=evidence,new_guest_commands=0))
        write(work/'audit.json',audit)
        out=ROOT/'results'/args.run_id;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',commands_retained=594,new_guest_commands=0,
            completed_cases=PREFIX,unstarted_cases=['nushell'],all_four_gates_passed=True,
            final_source_and_input_audit_passed=True,raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),audit_sha256=sha(work/'audit.json'),private_details_redacted=True))
        print('PASS:594 completed commands retained; Nushell unstarted',flush=True)


if __name__=='__main__':main()
