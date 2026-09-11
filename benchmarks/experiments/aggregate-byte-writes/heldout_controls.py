"""Exact case controls and independently recomputed 5% held-out gates."""
import math
import statistics
from build_relocation import ROOT,read,require
from check_comparison import expected_tools
from verify_heldouts import verify

ORDER=['nushell-type-relations','ruff','nushell','forward-anchored-tls','pgrust-sha1-inline8','pgrust','rg-aot']

def case(label):
    require(label in ORDER,'unplanned heldout case')
    return next(c for c in read(ROOT/'benchmarks/workflow-corpus.json')['cases'] if c['label']==label)

def guest_flags(c):
    flags=c['flags'];result=[]
    if '--guest-mir-opt-level' in flags:
        level=int(flags[flags.index('--guest-mir-opt-level')+1]);require(level in range(4),'invalid MIR level')
        result.append('-Zmir-opt-level='+str(level))
    if '--guest-mir-inline-scale' in flags:
        scale=int(flags[flags.index('--guest-mir-inline-scale')+1]);require(scale in [1,2,4,8],'invalid MIR scale')
        result += ['-Z'+name+'='+str(base*scale) for name,base in [('inline-mir-threshold',50),('inline-mir-hint-threshold',100),('inline-mir-forwarder-threshold',30)]]
    return result

def compare_controls(report,c,tools):
    require(report['project']==c['project'] and report['workflow']==c['workflow'],'heldout case identity differs')
    require(report['native_control']==dict(profile='o0-incremental',jobs=18,test_threads='default',rustflags=[]) and
        report['build_jobs']==4 and report['custom_build_jobs']==dict(baseline=4,candidate=4),'heldout native/worker controls differ')
    common=dict(engine='jit',jit_persistent_registers=True,jit_resumable_calls=True,inline_leaves=True,
        jit_native_calls=False,jit_native_call_stubs=False,trap_unsupported_calls='--trap-unsupported-calls' in c['flags'],
        run_try_callbacks='--run-try-callbacks' in c['flags'],guest_rustflags=guest_flags(c))
    expected={m:{**common,**{k:t[k] for k in ['tool_key','vm_sha256','exporter_sha256']}} for m,t in tools.items()}
    require(report['tool_builds']==expected,'heldout runtime or compiler controls differ')

def paired(rows):
    require(all(all(isinstance(r[k],(int,float)) and math.isfinite(r[k]) and r[k]>0 for k in ['seconds','cpu_seconds']) for r in rows),
        'non-finite or invalid measurement')
    pairs=[]
    for cycle in range(3):
        for state in range(1,6):
            selected=[r for r in rows if r['cycle']==cycle and r['state']==state]
            require(len(selected)==3 and {r['mode'] for r in selected}=={'native','baseline','candidate'},'missing paired command')
            modes={r['mode']:r for r in selected};a,b=modes['candidate'],modes['baseline']
            pairs.append(dict(cycle=cycle,state=state,wall_ratio=a['seconds']/b['seconds'],cpu_ratio=a['cpu_seconds']/b['cpu_seconds']))
    wall,cpu=(statistics.median(p[k] for p in pairs) for k in ['wall_ratio','cpu_ratio'])
    return dict(pairs=pairs,wall_ratio=wall,cpu_ratio=cpu,wall_limit=1.05,cpu_limit=1.05,passed=wall<=1.05 and cpu<=1.05)

def assess(report,c):
    tools=expected_tools();compare_controls(report,c,tools)
    checked=verify(report,tools,guest_flags(c))
    require((checked['commands'],checked['check_commands'],checked['edited_pairs'],checked['exact_artifact_hashes_verified'])==(63,21,15,42),
        'incomplete heldout coverage')
    rows=read(ROOT/report['raw']/'records.json');result=paired(rows)
    for mode in ['native','baseline','candidate']:
        for field,key in [('median_seconds','seconds'),('median_cpu_seconds','cpu_seconds')]:
            actual=statistics.median(r[key] for r in rows if r['state']>0 and r['mode']==mode)
            require(abs(actual-report[field][mode])<1e-9,'heldout reported median differs')
    return dict(result,verification=checked,median_seconds=report['median_seconds'],median_cpu_seconds=report['median_cpu_seconds'],
        exporter_seconds=report.get('exporter_seconds'),expected_guest_flags=guest_flags(c))
