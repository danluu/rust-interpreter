"""Qualify scalar transport and unchanged downstream benchmark verification."""
import argparse
import ast
import copy
import fcntl
import json
import os
from pathlib import Path
import re
import time
from common import ROOT,HERE,CONTROL,CANDIDATE,LAUNCHER,read,write,sha,require,qualifications,tools_for
from stage import stage
from scalar_checks import check_call
from verify_base import EXPECTED_TOOLS,admit_tools

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    run=parser.parse_args().run_id;require(re.fullmatch(r'scalar-workflow-controls-[0-9]{2}',run),'invalid run')
    work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
    status=dict(status='starting',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time());write(work/'status.json',status)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            paths=qualifications();original_path=ROOT/'scripts/bench_e2e_workflow.py';original=original_path.read_text()
            routes=0;settings=0;staged={}
            for phase in ['aa','e2e']:
                code=stage(original,phase);tree=ast.parse(code);staged[phase]=code
                guards=[n for n in ast.walk(tree) if isinstance(n,ast.If) and isinstance(n.test,ast.BoolOp) and
                    {x.id for x in ast.walk(n.test) if isinstance(x,ast.Name)}=={'baseline_key','key'} and
                    any(isinstance(x,ast.Constant) and x.value=='scalar workflow requires its exact phase tools' for child in n.body for x in ast.walk(child))]
                require(len(guards)==1,'phase tool guard missing');expression=compile(ast.Expression(guards[0].test),'scalar-phase-guard','eval')
                for left in [CONTROL,CANDIDATE,'0'*64]:
                    for right in [CONTROL,CANDIDATE,'0'*64]:
                        actual=eval(expression,{'__builtins__':{}},{'baseline_key':left,'key':right})
                        require(actual==(left!=CONTROL or right!=(CONTROL if phase=='aa' else CANDIDATE)),'phase route differs');routes+=1
                assignments=[n for n in ast.walk(tree) if isinstance(n,ast.Assign) and len(n.targets)==1 and ast.unparse(n.targets[0])=="config['scalar_values']"]
                require(len(assignments)==1,'scalar assignment missing');expression=compile(ast.Expression(assignments[0].value),'scalar-mode-setting','eval')
                for mode in ['baseline','candidate','interpreter','jit']:
                    actual=eval(expression,{'__builtins__':{}},{'mode':mode});require(type(actual) is bool and actual==(phase=='e2e' and mode=='candidate'),'scalar setting differs');settings+=1
                (work/('staged-'+phase+'.py')).write_text(code)
            rejected_stages=0
            for invalid in [original+original,original.replace('baseline and candidate must differ in tool build, guest settings, or Cargo worker count','changed guard'),original.replace("                payload=artifact.read_bytes()",'                payload=b""')]:
                for phase in ['aa','e2e']:
                    try:stage(invalid,phase)
                    except RuntimeError:rejected_stages+=1
                    else:raise RuntimeError('changed staging anchor accepted')
            tools={phase:tools_for(phase) for phase in ['aa','e2e']};require(tools['aa']['baseline']==tools['aa']['candidate'],'A/A tools differ')
            require(tools['e2e']==EXPECTED_TOOLS,'exact compiler/runtime admission differs');admit_tools(EXPECTED_TOOLS)
            rejected_tools=0
            for mode in EXPECTED_TOOLS:
                for field in EXPECTED_TOOLS[mode]:
                    bad=copy.deepcopy(EXPECTED_TOOLS);bad[mode][field]='0'*64
                    try:admit_tools(bad)
                    except RuntimeError:rejected_tools+=1
                    else:raise RuntimeError('mutated component admitted')
            # Compare every original verification statement. Only the separately
            # checked scalar control field is excluded from the common-setting
            # equality, and an incorrect old reporting label is corrected.
            base=HERE.parent/'whole-call-inline/verify_workflow.py'
            old_proof=ROOT/'results/whole-call-workflow-controls-02/summary.json';old=read(old_proof)
            require(old['status']=='passed' and sha(base)==old['frozen'][str(base.relative_to(ROOT))],'qualified prior verifier changed')
            function=lambda p:next(n for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='verify')
            before=function(base);after=function(HERE/'verify_base.py')
            class Allowed(ast.NodeTransformer):
                def __init__(self):self.count=0
                def visit_Assign(self,node):
                    if len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id=='ignored':
                        node.value.elts.append(ast.Constant(value='scalar_values'));self.count+=1
                    return self.generic_visit(node)
                def visit_keyword(self,node):
                    if node.arg=='identical_vm_wrapper_and_runtime_options':node.arg='identical_wrapper_and_runtime_options';self.count+=1
                    return self.generic_visit(node)
            allowed=Allowed();allowed.visit(before)
            require(allowed.count==2 and ast.dump(before,include_attributes=False)==ast.dump(after,include_attributes=False),'downstream verification changed')
            # Authentic Cargo process receipts and their immutable artifact
            # snapshots supply positive transport cases; no timings are invented.
            cargo_path=ROOT/'results/scalar-value-cargo-02/summary.json';cargo=read(cargo_path)
            positives=0;rejections=0
            for scalar,index in [(False,0),(True,1)]:
                row=next(c for c in cargo['commands'] if c['label']==f'toggle-{index}')
                stderr=next(ROOT/p for p in row['files'] if p.endswith('.stderr'))
                launches=[json.loads(line.split(': ',1)[1]) for line in stderr.read_text().splitlines() if line.startswith('rust-interp-launch: ')]
                require(len(launches)==1,'Cargo launch missing')
                call=dict(command=row['command'],launch=launches[0]);artifact=ROOT/next(s['copy'] for s in cargo['snapshots'] if s['label']==f'toggle-{index}-artifact')
                check_call(call,artifact,scalar);positives+=1
                variants=[]
                bad=copy.deepcopy(call);bad['command'][1]=str(ROOT/'scripts/interpreter.py');variants.append(bad)
                bad=copy.deepcopy(call);bad['command'].append('--scalar-values');variants.append(bad)
                bad=copy.deepcopy(call);bad['launch'].pop('scalar_values');variants.append(bad)
                bad=copy.deepcopy(call);bad['launch']['scalar_values']=not scalar;variants.append(bad)
                bad=copy.deepcopy(call);bad['launch']['scalar_values']=int(scalar);variants.append(bad)
                bad=copy.deepcopy(call);bad['launch']['artifact_sha256']='0'*64;variants.append(bad)
                bad=copy.deepcopy(call);bad['launch']['artifact_bytes']+=1;variants.append(bad)
                if scalar:
                    bad=copy.deepcopy(call);bad['command'].remove('--scalar-values');variants.append(bad)
                for bad in variants:
                    try:check_call(bad,artifact,scalar)
                    except RuntimeError:rejections+=1
                    else:raise RuntimeError('mutated scalar transport accepted')
                damaged=work/f'wrong-header-{index}.rbc';damaged.write_bytes((5 if scalar else 6).to_bytes(4,'little')+artifact.read_bytes()[4:])
                bad=copy.deepcopy(call);bad['launch']['artifact_sha256']=sha(damaged)
                try:check_call(bad,damaged,scalar)
                except RuntimeError as error:require('header differs' in str(error),'wrong header rejection');rejections+=1
                else:raise RuntimeError('hash-consistent wrong header accepted')
            require((routes,settings,rejected_stages,rejected_tools,positives,rejections)==(18,8,6,8,2,17),'control case totals differ')
            paths += [p for p in HERE.iterdir() if p.is_file()]+[original_path,base,old_proof,cargo_path,LAUNCHER]
            result=dict(status='passed',key_routes_checked=routes,scalar_settings_checked=settings,changed_stage_rejections=rejected_stages,
                changed_tool_rejections=rejected_tools,authentic_transport_cases=positives,scalar_transport_rejections=rejections,
                original_assertions_preserved=True,qualified_downstream_verifier_preserved=True,exact_wrapper_shared=True,tools=tools,
                new_guest_executions=0,performance_measurement=False,frozen={str(p.relative_to(ROOT)):sha(p) for p in paths})
            write(work/'summary.json',result);out=ROOT/'results'/run;out.mkdir(exist_ok=False);write(out/'summary.json',result)
            status.update(status='finished',returncode=0,finished_at=time.time());write(work/'status.json',status)
            print({k:v for k,v in result.items() if k not in ['frozen','tools']})
        except BaseException as error:
            status.update(status='failed',error=repr(error),finished_at=time.time());write(work/'status.json',status);raise

if __name__=='__main__':main()
