"""Stage scalar transport additions without changing original benchmark asserts."""
import ast
from common import ROOT,CONTROL,CANDIDATE,LAUNCHER,require

def replace(text,old,new):
    require(text.count(old)==1,'staging anchor changed: '+old[:100]);return text.replace(old,new)

DISTINCT='''        if (baseline_key==key and baseline_guest_flags==guest_flags and
            args.baseline_inline_leaves==args.inline_leaves and
            resolved_jobs['baseline']==resolved_jobs['candidate'] and
            not args.candidate_jit_native_calls and
            args.candidate_jit_persistent_registers==args.baseline_jit_persistent_registers and
            args.candidate_jit_resumable_calls==args.baseline_jit_resumable_calls):
            parser.error('baseline and candidate must differ in tool build, guest settings, or Cargo worker count')'''

def stage(original,phase):
    require(phase in ['aa','e2e'],'unknown staged phase')
    key=CONTROL if phase=='aa' else CANDIDATE
    guard=f'''        if baseline_key != {CONTROL!r} or key != {key!r}:
            parser.error('scalar workflow requires its exact phase tools')'''
    text=replace(original,DISTINCT,guard if phase=='aa' else guard+'\n'+DISTINCT)
    text=replace(text,"    for mode,config in mode_tools.items():",f"    for mode,config in mode_tools.items():\n        config['scalar_values']=mode=='candidate' and {phase=='e2e'}")
    text=replace(text,"tool_builds={mode:dict(engine=config['engine'],", "tool_builds={mode:dict(scalar_values=config['scalar_values'],engine=config['engine'],")
    text=replace(text,'    frozen_scripts={',f"    script_paths.append(ROOT/{str(LAUNCHER.relative_to(ROOT))!r})\n    frozen_scripts={{")
    text=replace(text,"base=[sys.executable,str(ROOT/'scripts/interpreter.py'),'--manifest-path',manifest,",f"base=[sys.executable,str(ROOT/{str(LAUNCHER.relative_to(ROOT))!r}),'--manifest-path',manifest,")
    text=replace(text,"            if config['inline_leaves']:base+=['--inline-leaves']", "            if config['scalar_values']:base+=['--scalar-values']\n            if config['inline_leaves']:base+=['--inline-leaves']")
    text=replace(text,"                assert launch['tool_key']==config['tool_key'] and launch['engine']==config['engine']", "                assert type(launch.get('scalar_values')) is bool and launch['scalar_values']==config['scalar_values']\n                assert launch['tool_key']==config['tool_key'] and launch['engine']==config['engine']")
    text=replace(text,"                payload=artifact.read_bytes()", "                payload=artifact.read_bytes()\n                assert len(payload)>=4 and int.from_bytes(payload[:4],'little')==(6 if config['scalar_values'] else 5)")
    # Original assertions must remain, in their original traversal order.
    assertions=lambda code:[ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(code)) if isinstance(n,ast.Assert)]
    before=assertions(original);after=assertions(text);remaining=iter(after)
    require(all(any(item==old for item in remaining) for old in before),'original benchmark assertion changed')
    require(len(after)==len(before)+2,'unexpected added benchmark assertions')
    compile(text,'scalar-workflow-'+phase,'exec');return text
