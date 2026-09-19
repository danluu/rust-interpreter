"""Explicit arm options; historical anchor and session controls keep distinct roles."""
import sys
from workflow_controls import native_command
from accounting import CUSTOM,MODES,SESSION_MODES
TOOLCHAIN='nightly-2026-09-08'
def command(root,source,case,reference,names,pattern,raw,index,mode,builds,endpoints,namespace=None):
    assert mode in MODES
    if mode not in CUSTOM:
        result=native_command(TOOLCHAIN,source/'Cargo.toml',case['package'],raw/mode,2,'2',names,check=mode=='check')
        if mode!='check':result.insert(result.index('--'),'--message-format=json')
        return list(map(str,result))
    result=[sys.executable,root/'scripts/interpreter.py','--manifest-path',source/'Cargo.toml',
        '--package',case['package'],'--jobs','2','--tool-key',builds[mode]['tool_key'],
        '--cache-namespace',namespace or raw.name+':'+mode,'--test-body','--std-mir','--engine','jit',
        '--jit-resumable-calls','--jit-persistent-registers','--instruction-limit',str(reference['instruction_limit']),
        '--isolated-batch','prepared','--suite-workers','2','--suite-report',raw/(str(index)+'-suite.json'),
        '--test-filter',pattern]
    if reference['allocation_limit'] is not None:result+=['--allocation-limit',str(reference['allocation_limit'])]
    for option in ['inline_leaves','trap_unsupported_calls','run_try_callbacks']:
        if reference.get(option):result+=['--'+option.replace('_','-')]
    if mode!='anchor':result+=['--function-cache','auto','--jit-scalar-calls']
    result+=['--toolchain-lookup','fresh' if mode=='anchor' else 'cached']
    if mode in SESSION_MODES:result+=['--jit-template-session',endpoints[mode],'--jit-indirect-calls']
    return list(map(str,result))

def validate_options(launch,cmd,mode):
    assert mode in CUSTOM
    assert launch['jit_scalar_calls']==(mode!='anchor') and ('--jit-scalar-calls' in cmd)==(mode!='anchor')
    assert launch.get('jit_indirect_calls',False)==(mode=='candidate')
    assert ('--jit-indirect-calls' in cmd)==(mode=='candidate')
    assert launch['function_cache']==('off' if mode=='anchor' else 'auto') and launch['borrowck_cache']=='off'
    lookup=launch['toolchain_lookup'];assert lookup['mode']==('fresh' if mode=='anchor' else 'cached')
    assert lookup['outcome'] in (['fresh'] if mode=='anchor' else ['miss','hit'])
    assert ('--jit-template-session' in cmd)==(mode in SESSION_MODES)
    assert ('template_session' in launch)==(mode in SESSION_MODES)
    return True
