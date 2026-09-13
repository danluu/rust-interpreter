"""Run only the unstarted Nushell case, retaining the audited594-command prefix."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys
from prefix import ROOT,FULL,PREFIX,protocol,harness_inputs,load_prefix,command_for
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    args=parser.parse_args();assert re.fullmatch(r'guarded-local-facts-full-continuation-\d{2}',args.run_id)
    prefix_path=ROOT/'results/guarded-local-facts-full-prefix-01/summary.json'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        estimate_path=ROOT/'results/aggregate-relocation-space-nu-native-01/summary.json'
        estimate=json.loads(estimate_path.read_text());assert estimate['status']=='completed'
        needed=8*1024**3+(estimate['unique_original_bytes']*6*120+99)//100
        assert shutil.disk_usage(ROOT).free>=needed,'insufficient unchanged Nushell cache admission'
        frozen=harness_inputs();proof,evidence,audit=load_prefix(prefix_path)
        frozen[str(prefix_path.relative_to(ROOT))]=sha(prefix_path)
        frozen[str(estimate_path.relative_to(ROOT))]=sha(estimate_path)
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),retained_commands=594,new_commands=132,
            completed_cases=PREFIX,new_cases=['nushell'],frozen=frozen,original_evidence=evidence,
            required_free_bytes=needed,admitted_free_bytes=shutil.disk_usage(ROOT).free))
        write(work/'prefix-audit.json',audit)
    command=command_for('nushell')
    child,out,err=capture(command,cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),
        receipt_path=work/'active.json',receipt=dict(case='nushell'))
    (work/'nushell.stdout').write_text(out);(work/'nushell.stderr').write_text(err)
    row=dict(case='nushell',command=command,pid=child.pid,returncode=child.returncode,
        stdout_sha256=sha(work/'nushell.stdout'),stderr_sha256=sha(work/'nushell.stderr'))
    write(work/'records.json',[row]);assert child.returncode==0,err
    result_path=protocol.case_path('nushell');result=json.loads(result_path.read_text())
    assert result['status']=='passed' and result['commands']==132 and result['source_restored']
    row['summary_sha256']=sha(result_path);write(work/'records.json',[row])
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        protocol.verify_manifest(frozen);protocol.verify_manifest(evidence)
        final=protocol.audit_cases(protocol.CASES)
        parser_path=ROOT/'results/guarded-local-facts-parser-01/summary.json'
        parser=json.loads(parser_path.read_text());assert parser['status']=='passed'
        assert parser['custom_tests_passed']==parser['native_tests_reused']==114 and parser['original_assertions_match']
        assert parser['tool_key']==result['tool_keys']['candidate']
        for name in ['plan','records']:
            assert sha(ROOT/parser['raw']/(name+'.json'))==parser[name+'_sha256']
        assert sha(ROOT/parser['raw']/'suite.json')==parser['suite_sha256']
        for item in parser['artifacts'].values():assert sha(ROOT/item['path'])==item['sha256']
        final['parser_compatibility_summary_sha256']=sha(parser_path)
        write(work/'final-audit.json',final)
    passed=result['gate_passed']
    destination=ROOT/'results'/args.run_id;destination.mkdir(exist_ok=False)
    write(destination/'summary.json',dict(status='passed' if passed else 'rejected',
        all_five_gates_passed=passed,completed_cases=protocol.CASES,unstarted_cases=[],commands=726,
        retained_commands=594,new_commands=132,repeated_commands=0,complete_parser_tests=114,
        final_source_and_input_audit_passed=True,raw=str(work.relative_to(ROOT)),
        plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),
        final_audit_sha256=sha(work/'final-audit.json'),private_details_redacted=True))
    print('Nushell complete; all five gates',passed,flush=True)

if __name__=='__main__':main()
