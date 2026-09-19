"""Source transformation only; does not import or execute any target module."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
H=Path(__file__).resolve().parent
base=json.loads((H/'base-sources.json').read_text())
for path,row in base['sources'].items():
 assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==row['sha256']

def replace(text,old,new,count=1):
 assert text.count(old)==count,(old,text.count(old),count)
 return text.replace(old,new)

s=(H/'before/bench_e2e_workflow.py').read_text()
s=replace(s,'import workflow_compiler\n','import workflow_compiler\nimport workflow_runtime_arms\n')
s=replace(s,"    args=parser.parse_args()\n", "    workflow_runtime_arms.add_arguments(parser)\n    args=parser.parse_args()\n")
s=replace(s,"        compiler_arguments=workflow_compiler.arguments(args.runtime_compiler_key,args.std_mir_key)\n", "        arm_selection=workflow_runtime_arms.select(args)\n        compiler_arguments=workflow_compiler.arguments(args.runtime_compiler_key,args.std_mir_key)\n")
s=replace(s,"    runtime=None\n    runtime_proof=None\n", "    runtime=None\n    runtime_proof=None\n    arm_runtimes={}; arm_proofs={}; arm_standards={}; arm_std_options={}\n    arm_std_selections={}; arm_receipts=None\n    if arm_selection is not None:\n        from runtime_compiler import load_runtime_compiler\n        from runtime_tools import validate_tool_runtime\n        arm_runtimes,arm_proofs=workflow_runtime_arms.bind(arm_selection,mode_tools,\n            load_runtime=lambda key:load_runtime_compiler(ROOT,key),\n            validate_tool=validate_tool_runtime,environment=os.environ,\n            runtime_receipt=workflow_compiler.runtime_receipt)\n")
s=replace(s,"    if args.std_mir:\n        from std_mir import checked_std_mir\n", "    if args.std_mir and arm_selection is None:\n        from std_mir import checked_std_mir\n")
s=replace(s,"    std_selection=None if std is None else dict(key=std[2],sysroot=str(std[0]),target=std[1])\n", "    std_selection=None if std is None else dict(key=std[2],sysroot=str(std[0]),target=std[1])\n    if arm_selection is not None:\n        standard_cache={}\n        if args.std_mir:\n            from std_mir import checked_std_mir\n        for mode in workflow_runtime_arms.MODES:\n            row=arm_selection['arms'][mode]\n            selected=None\n            if args.std_mir:\n                options=dict(custom=arm_runtimes[mode],policy='source-paths-v2-shared',prepared_key=row['std_key'])\n                arm_std_options[mode]=options\n                pair=(row['runtime_key'],row['std_key'])\n                if pair not in standard_cache:\n                    standard_cache[pair]=checked_std_mir(TOOLCHAIN,**options)\n                selected=standard_cache[pair]\n            arm_standards[mode]=selected\n            arm_std_selections[mode]=None if selected is None else dict(key=selected[2],sysroot=str(selected[0]),target=selected[1])\n        arm_receipts=workflow_runtime_arms.receipts(arm_selection,arm_proofs,arm_std_selections,mode_tools)\n")
s=replace(s,"ROOT/'scripts/workflow_compiler.py']\n", "ROOT/'scripts/workflow_compiler.py',ROOT/'scripts/workflow_runtime_arms.py']\n")
s=replace(s,"    if runtime is not None:\n        script_paths", "    if runtime is not None or arm_selection is not None:\n        script_paths")
s=replace(s,"            base+=compiler_arguments\n            if runtime is not None:base+=['--rustflag='+flag for flag in config['guest_flags']]", "            base+=compiler_arguments if arm_selection is None else workflow_runtime_arms.arguments(arm_selection,mode)\n            if runtime is not None or arm_selection is not None:base+=['--rustflag='+flag for flag in config['guest_flags']]")
s=replace(s,"            if std:base+=['--std-mir']", "            if std or (arm_selection is not None and arm_standards[mode] is not None):base+=['--std-mir']")
s=replace(s,"        if mode!='native' and runtime is None:\n", "        if mode!='native' and runtime is None and arm_selection is None:\n")
s=replace(s,"                workflow_compiler.verify_flags(call,config['guest_flags'],encoded_guest_flags,runtime is not None)\n                if runtime is not None:workflow_compiler.verify_runtime_call(call,runtime_proof,std_selection)\n", "                workflow_compiler.verify_flags(call,config['guest_flags'],encoded_guest_flags,runtime is not None or arm_selection is not None)\n                if runtime is not None:workflow_compiler.verify_runtime_call(call,runtime_proof,std_selection)\n                if arm_selection is not None:\n                    workflow_runtime_arms.verify_call(arm_receipts,mode,call,verify_runtime_call=workflow_compiler.verify_runtime_call)\n")
s=replace(s,"    med={m:statistics.median", "    if arm_selection is not None:\n        for mode,compiler in arm_runtimes.items():\n            if load_runtime_compiler(ROOT,compiler.key)!=compiler:\n                raise RuntimeError('arm runtime compiler changed during workflow')\n            validate_tool_runtime(mode_tools[mode]['directory'],mode_tools[mode]['tool_key'],compiler)\n            if arm_standards[mode] is not None and checked_std_mir(TOOLCHAIN,**arm_std_options[mode])!=arm_standards[mode]:\n                raise RuntimeError('arm prepared standard library changed during workflow')\n    med={m:statistics.median")
s=replace(s,"    if runtime is not None:result['guest_rustflag_encoding']='launcher-arguments'", "    if runtime is not None or arm_selection is not None:result['guest_rustflag_encoding']='launcher-arguments'")
s=replace(s,"    if runtime is not None:result['runtime_compiler']=dict(runtime_proof,prepared_std=std_selection)\n", "    if runtime is not None:result['runtime_compiler']=dict(runtime_proof,prepared_std=std_selection)\n    if arm_selection is not None:\n        result['runtime_arms']=arm_receipts\n        result['std_mir_by_mode']={mode:None if selected is None else dict(key=selected[2],\n            setup_seconds=selected[3]['setup_seconds'],build_seconds=selected[3]['build_seconds'],\n            metadata_bytes=selected[3]['metadata_bytes']) for mode,selected in arm_standards.items()}\n")
s=replace(s,"    if runtime is not None or encoded_guest_flags:\n", "    if runtime is not None or arm_selection is not None or encoded_guest_flags:\n")
s=replace(s,"if runtime is not None else 'Cargo receives each argument", "if runtime is not None or arm_selection is not None else 'Cargo receives each argument")
ast.parse(s)
with (H/'proposed/bench_e2e_workflow.py').open('x') as f:f.write(s)

s=(H/'before/verify_repeated_workflow.py').read_text()
s=replace(s,'import workflow_compiler\n','import workflow_compiler\nimport workflow_runtime_arms\n')
s=replace(s,"    runtime=report.get('runtime_compiler')\n    require((runtime is not None)==(flag_encoding=='launcher-arguments'), 'runtime compiler transport differs')\n", "    runtime=report.get('runtime_compiler')\n    arm_receipts=report.get('runtime_arms')\n    require(runtime is None or arm_receipts is None,'shared and per-arm runtime receipts cannot coexist')\n    require((runtime is not None or arm_receipts is not None)==(flag_encoding=='launcher-arguments'), 'runtime compiler transport differs')\n    if arm_receipts is not None:\n        require('comparison' in report and report['batch'] and report.get('std_mir') is None,\n                'per-arm runtime comparison must not claim a shared std')\n        arm_receipts=workflow_runtime_arms.validate_receipts(arm_receipts,report['tool_builds'])\n        standards=report.get('std_mir_by_mode')\n        require(type(standards) is dict and set(standards)==set(workflow_runtime_arms.MODES),\n                'complete per-arm standard-library report required')\n        for mode,row in arm_receipts['arms'].items():\n            standard=row['prepared_std']; summary=standards[mode]\n            require((standard is None)==(summary is None) and\n                (standard is None or standard['key']==summary['key']),'prepared arm std report differs')\n        if report.get('aa_control',False):\n            require(arm_receipts['arms']['baseline']==arm_receipts['arms']['candidate'],\n                    'A/A runtime/std/tool associations differ')\n    else:\n        require('std_mir_by_mode' not in report,'per-arm std report lacks per-arm runtime proof')\n")
s=replace(s,"                    if runtime is not None:workflow_compiler.verify_runtime_call(call,runtime,prepared_std)\n", "                    if runtime is not None:workflow_compiler.verify_runtime_call(call,runtime,prepared_std)\n                    if arm_receipts is not None:\n                        workflow_runtime_arms.verify_call(arm_receipts,mode,call,verify_runtime_call=workflow_compiler.verify_runtime_call)\n")
ast.parse(s)
with (H/'proposed/verify_repeated_workflow.py').open('x') as f:f.write(s)

patch=[]
for name in ['bench_e2e_workflow.py','verify_repeated_workflow.py','workflow_runtime_arms.py','test_workflow_runtime_arms.py']:
 before=(H/'before'/name).read_text() if (H/'before'/name).exists() else ''
 after=(H/'proposed'/name).read_text()
 patch.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/scripts/'+name if before else '/dev/null',tofile='b/scripts/'+name))
with (H/'proposal.patch').open('x') as f:f.write(''.join(patch))
print('Source proposal generated; no target imports or executions.')
