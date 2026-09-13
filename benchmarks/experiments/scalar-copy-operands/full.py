#!/usr/bin/env python3
"""Run required scalar Copy cases in order, stopping at the first failed gate."""
import argparse
import json
import os
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import sha
from workflow_io import capture,write_json as write

CASES=['token','folded','pgrust','rg-aot','nushell']


def next_case(completed):
    assert len(completed)<=len(CASES)
    for index,result in enumerate(completed):
        assert result['case']==CASES[index]
        assert result['status']=='passed' and result['source_restored']
        assert result['commands']==(154 if index<3 else 132)
        if not result['gate_passed']:
            assert index==len(completed)-1, 'a case started after a failed guard'
            return None
    return CASES[len(completed)] if len(completed)<len(CASES) else None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    args=parser.parse_args();assert re.fullmatch(r'scalar-copy-operands-full-\d{2}',args.run_id)
    work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
    directory=Path(__file__).parent
    paths=[p for p in directory.iterdir() if p.suffix in ['.py','.md']]
    paths+=list((ROOT/'scripts').glob('*.py'))
    harness=ROOT/'results/scalar-copy-operands-full-python-tests-01/summary.json'
    proof=json.loads(harness.read_text());assert proof['status']=='passed' and proof['tests']==125
    inputs=ROOT/proof['raw']/'inputs.json';assert sha(inputs)==proof['inputs_sha256']
    assert all(sha(ROOT/p)==h for p,h in json.loads(inputs.read_text()).items())
    paths += [harness,inputs]
    frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
    write(work/'plan.json',dict(owner=str(ROOT),cases=CASES,frozen=frozen,maximum_commands=726,
        stop_on_failed_gate=True,all_five_required_for_adoption=True))
    completed=[];records=[]
    while (case:=next_case(completed)) is not None:
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        run='scalar-copy-operands-edit-'+case+'-01'
        script='workflows.py' if case in CASES[:3] else 'large_compare.py'
        command=[sys.executable,str(directory/script),'--case',case,'--run-id',run]
        if case in CASES[:3]:
            command+=['--build','results/scalar-copy-operands-build-02/summary.json',
                '--cache-qualification','results/scalar-copy-operands-cache-01/summary.json',
                '--execution-qualification','results/scalar-copy-operands-qualification-01/summary.json',
                '--serial-qualification','results/scalar-copy-operands-serial-01/summary.json']
        child,out,err=capture(command,cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),
            receipt_path=work/'active.json',receipt=dict(case=case))
        (work/(case+'.stdout')).write_text(out);(work/(case+'.stderr')).write_text(err)
        records.append(dict(case=case,command=command,pid=child.pid,returncode=child.returncode,
            stdout_sha256=sha(work/(case+'.stdout')),stderr_sha256=sha(work/(case+'.stderr'))))
        write(work/'records.json',records)
        assert child.returncode==0,err
        result_path=ROOT/'results'/run/'summary.json';result=json.loads(result_path.read_text())
        completed.append(result);next_case(completed)
        records[-1]['summary_sha256']=sha(result_path);write(work/'records.json',records)
        print(case,'correctness passed; gate',result['gate_passed'],flush=True)
    assert all(sha(ROOT/p)==h for p,h in frozen.items())
    passed=len(completed)==len(CASES) and all(r['gate_passed'] for r in completed)
    destination=ROOT/'results'/args.run_id;destination.mkdir(exist_ok=False)
    write(destination/'summary.json',dict(status='passed' if passed else 'rejected',
        all_five_gates_passed=passed,completed_cases=[r['case'] for r in completed],
        unstarted_cases=CASES[len(completed):],commands=sum(r['commands'] for r in completed),
        raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),
        private_details_redacted=True))


if __name__=='__main__':main()
