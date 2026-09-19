"""Join qualified typed initialization proofs to closed adopted Call evidence."""
import hashlib, subprocess, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus
ROOT=focus.ROOT
sys.path.insert(0,str(ROOT/'benchmarks/experiments/native-call-cost-census'))
from analyze import attribute,variant
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
from summarize_owned_sample import parse_tree,self_samples
read=focus.read
RUN='frame-initialization-slot-coverage-01'
TOOL='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();frozen={}
        def bind(p,expected=None):
            digest=sha(p)
            if expected is not None:assert digest==expected,p
            key=str(p.relative_to(ROOT));assert key not in frozen or frozen[key]==digest;frozen[key]=digest
            return read(p) if p.suffix=='.json' else None
        def closed(name):
            out=ROOT/'results'/name;c=bind(out/'closure.json')
            assert c['status']=='closed' and c['all_hashes_verified']
            s=bind(out/'summary.json',c['summary_sha256']);t=bind(out/'terminal.json',c['terminal_sha256'])
            assert s['status']=='passed' and t['status']=='finished' and t['returncode']==0
            assert t['owner']==t['cwd']==str(ROOT)
            return s,c
        build,bc=closed('frame-initialization-slots-build-01')
        assert build['tests']==dict(debug=18,release=18) and build['commands']==4
        bp=bind(ROOT/build['raw']/'plan.json',build['plan_sha256'])
        bind(ROOT/bc['evidence'],bc['evidence_sha256']);bind(ROOT/bc['source_bindings'],bc['source_bindings_sha256'])
        typed=bind(ROOT/build['raw']/'typed.json',build['typed_sha256']);functions=typed['functions']
        assert len(functions)==5468 and [f['function'] for f in functions]==list(range(len(functions)))
        bind(ROOT/bp['artifact'],bp['artifact_sha256'])
        profiles,pc=closed('scratch-memory-values-profile-01')
        assert profiles['tool_key']==TOOL and profiles['exact_per_pc_counts'] and profiles['exact_operation_map_reconstruction']
        bind(ROOT/pc['bindings'],pc['bindings_sha256'])
        prior,fc=closed('scalar-protocol-census-03')
        bind(ROOT/fc['bindings'],fc['bindings_sha256'])
        fp=bind(ROOT/prior['raw']/'plan.json',prior['plan_sha256'])
        assert fp['frozen'][bp['artifact']]==bp['artifact_sha256']
        attribution=bind(ROOT/'results/scalar-protocol-census-03/attribution.json',prior['attribution_sha256'])
        inputs=[]
        for index,label in enumerate(['block','exhaustive']):
            row,=[r for r in profiles['comparisons'] if r['index']==index and r['mode']=='candidate']
            profile=ROOT/row['profile_path'];bind(profile,row['profile_sha256'])
            assert fp['frozen'][row['profile_path']]==row['profile_sha256']
            detail=attribution['cases'][index];assert detail['case']==label
            for p,h in detail['evidence'].items():bind(ROOT/p,h)
            fine=ROOT/prior['raw']/(label+'.json');bind(fine,prior['census_sha256'][label])
            folder=ROOT/'.work'/('scratch-scalar-runtime-sample-'+label+'-01')/'0'
            inputs.append(dict(case=label,profile=profile,metadata=row,fine=fine,folder=folder,expected=detail))
        for p in [*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md'),Path(focus.__file__),
                  ROOT/'benchmarks/experiments/native-call-cost-census/analyze.py',
                  *[ROOT/'scripts'/p for p in ['compare_saved_runtime.py','workflow_io.py','supervise_experiment.py','summarize_owned_sample.py']]]:bind(p)
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);write(raw/'records.json',[])
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=0,
            original_project_guest_commands=0,performance_measurement=False,production_runtime_changes=0,
            adopted_tool_key=TOOL,artifact_sha256=bp['artifact_sha256']))
        modes=['previous_initialization','cfg_with_callee_effects'];cases=[];outputs={}
        for entry in inputs:
            require_space(ROOT,8)
            label=entry['case'];profile=read(entry['profile']);fine=read(entry['fine']);folder=entry['folder']
            mapping=read(folder/'jit-code/operations.json');expected=entry['expected']
            assert mapping['code_sha256']==fine['code_sha256']==sha(folder/'jit-code/code.bin')
            assert len(profile['functions'])==len(functions)
            calls={};typed_calls={}
            for f,pf in zip(functions,profile['functions']):
                assert (f['name'],f['frame_size'])==(pf['name'],pf['frame_size'])
                pcs=set()
                for c in f['calls']:
                    pc=c['pc'];key=(f['function'],pc);assert pc not in pcs;pcs.add(pc)
                    assert variant(pf['operations'][pc])=='Call'
                    hits=pf['jit_blocks'][pc];assert hits>=0
                    if hits:assert pf['jit_block_ends'][pc]==pc+1
                    calls[key]=dict(callee=key,hits=hits);typed_calls[key]=c
                assert pcs=={pc for pc,op in enumerate(pf['operations']) if variant(op)=='Call'}
            total_calls=sum(r['hits'] for r in calls.values())
            assert total_calls==entry['metadata']['statistics']['jit_resumable_calls']
            samples=[f for root in parse_tree((folder/'sample.txt').read_text()) for f in self_samples(root)]
            sampled,returns,parts,generated=attribute(calls,mapping,fine,samples)
            assert dict(parts)==expected['fine_samples']
            assert generated==expected['generated_samples'] and expected['unassigned_fine_samples']==0
            hist={mode:{key:Counter() for key in ['calls','clear_samples','sites']} for mode in modes}
            changes=Counter();sites=[];relaxed=Counter()
            active={key for key,r in calls.items() if r['hits']} | set(sampled)
            for key in sorted(active):
                c=typed_calls[key];callee=functions[c['callee']];hits=calls[key]['hits'];clear=sampled[key]['call_frame_clear']
                verdicts={}
                for mode in modes:
                    proof=callee[mode]
                    reason='unproved_caller_arguments' if not c['caller_local_arguments'] else (
                        'eligible' if proof['eligible'] else proof['decline']['reason'])
                    verdicts[mode]=reason
                    for field,value in [('calls',hits),('clear_samples',clear),('sites',1)]:hist[mode][field][reason]+=value
                    if proof['eligible']:relaxed[mode]+=clear
                transition=('eligible' if verdicts[modes[0]]=='eligible' else 'declined')+'->'+('eligible' if verdicts[modes[1]]=='eligible' else 'declined')
                changes[transition]+=clear
                sites.append(dict(function=key[0],pc=key[1],callee=c['callee'],native_calls=hits,
                    clear_samples=clear,frame_bytes=callee['frame_size'],verdicts=verdicts))
            total_clear=parts['Call/call_frame_clear']
            assert sum(s['native_calls'] for s in sites)==total_calls
            assert sum(s['clear_samples'] for s in sites)==sum(changes.values())==total_clear
            for mode in modes:
                assert sum(hist[mode]['calls'].values())==total_calls
                assert sum(hist[mode]['clear_samples'].values())==total_clear
            report=raw/(label+'.json');write(report,dict(status='passed',sites=sites,histograms=hist,changes=changes,
                relaxed_clear_samples_without_caller_proof=relaxed))
            outputs[str(report.relative_to(ROOT))]=sha(report)
            cases.append(dict(case=label,native_calls=total_calls,profile_scalar_calls=entry['metadata']['scalar_calls'],
                generated_samples=generated,clear_samples=total_clear,histograms=hist,changes=changes,
                relaxed_clear_samples_without_caller_proof=relaxed,report_sha256=sha(report)))
            print(label,'clearing samples',total_clear,'old/new',[hist[m]['clear_samples']['eligible'] for m in modes],flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),commands=0,
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),outputs=outputs,cases=cases,
            original_project_guest_commands=0,production_runtime_changes=0,performance_measurement=False,
            scope='Upper bound from partial perturbed saved samples; logical profiles are separate executions. Caller guards, padding and arbitrary native entry remain obligations.'))

if __name__=='__main__':
    if sys.argv[1:]==['--close']:focus.RUN=RUN;focus.close()
    else:assert len(sys.argv)==1;main()
