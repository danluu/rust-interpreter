"""Current bounded-tree eligibility and native protocol coverage, without timing."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/native-call-cost-census'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
from summarize_owned_sample import parse_tree,self_samples
from analyze import call_index,attribute,locate


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True);args=p.parse_args()
    assert re.fullmatch(r'bounded-tree-bridge-coverage-\d{2}',args.run_id)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        frozen={};bindings=[]
        def bind(path,h=None):
            path=ROOT/path;digest=sha(path)
            if h is not None:assert digest==h,path
            key=str(path.relative_to(ROOT));assert key not in frozen or frozen[key]==digest;frozen[key]=digest
            return json.loads(path.read_text()) if path.suffix=='.json' else digest
        def source(file,h,revision):
            spec=revision+':'+file
            assert hashlib.sha256(subprocess.check_output(['git','show',spec],cwd=ROOT)).hexdigest()==h,spec
            bindings.append(dict(path=file,sha256=h,git_source=spec))
        def history(name):
            result=Path('results')/name;summary=bind(result/'summary.json');assert summary['status']=='passed'
            terminal=bind(result/'terminal.json');assert terminal['status']=='finished' and terminal['returncode']==0
            assert terminal['owner']==terminal['cwd']==str(ROOT)
            outer=Path('.work/experiments')/name
            bind(outer/'status.json',sha(ROOT/result/'terminal.json'))
            bind(outer/'plan.json',terminal['plan_sha256']);bind(outer/'command.log',terminal['log_sha256'])
            raw=Path(summary['raw']);plan=bind(raw/'plan.json',summary['plan_sha256']);assert plan['owner']==str(ROOT)
            for file,h in plan['frozen'].items():
                if file.startswith('.work/'):bind(file,h)
                else:source(file,h,plan['source_revision'])
            records=bind(raw/'records.json',summary['records_sha256']);assert all(r['returncode']==0 for r in records)
            bind(result/'source-bindings.json',summary['source_bindings_sha256'])
            return summary,records
        build,records=history('bounded-tree-bridge-build-01')
        assert build['tests']=={'debug':5,'release':5} and build['interpreter_bound_fixtures'] and len(records)==4
        for row in records:
            for suffix in ['stdout','stderr']:bind(Path(build['raw'])/(row['label']+'.'+suffix),row[suffix+'_sha256'])
        bind(Path(build['raw'])/'bounded-tree-bridge-census',build['binary_sha256'])
        typed=bind(Path(build['raw'])/'typed.json',build['typed_sha256']);functions=typed['functions']
        assert len(functions)==build['functions'] and [f['function'] for f in functions]==list(range(len(functions)))
        eligible={f['function'] for f in functions if f['plan'] is not None}
        assert len(eligible)==build['eligible_functions']
        typed_calls={(f['function'],c['pc']):c['callee'] for f in functions for c in f['calls']}
        for fid in eligible:assert all(c['callee'] in eligible for c in functions[fid]['calls'])
        old,records=history('native-call-cost-census-01')
        assert old['all_frozen_inputs_verified'] and old['controls']==2 and len(records)==1
        old_plan=json.loads((ROOT/old['raw']/'plan.json').read_text())
        for file in ['benchmarks/experiments/native-call-cost-census/analyze.py','benchmarks/experiments/native-call-cost-census/test_analyze.py']:
            bind(file,old_plan['frozen'][file])
        assert 'Ran 2 tests' in records[0]['stderr'] and records[0]['stderr'].rstrip().endswith('OK')
        for name in ['attribute.py','PLAN.md']:bind(Path('benchmarks/experiments/bounded-tree-bridge-census')/name)
        for path in ['benchmarks/experiments/native-call-cost-census/analyze.py','scripts/compare_saved_runtime.py',
            'scripts/workflow_io.py','scripts/summarize_owned_sample.py']:bind(path)
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False);cases=[]
        for index,label in enumerate(['block','exhaustive']):
            require_space(ROOT,8)
            profile=bind(Path('.work/guarded-local-facts-profile-01')/(str(index)+'-profile.json'))
            assert len(profile['functions'])==len(functions)
            assert all((f['name'],f['frame_size'],f['registers'],f['bytecode_operations'])==
                (pf['name'],pf['frame_size'],pf['registers'],len(pf['operations'])) for f,pf in zip(functions,profile['functions']))
            continuation=bind(Path('.work/native-continuation-census-01')/(label+'.json'))
            calls=call_index(continuation,profile);assert all(c['callee']==typed_calls[key] for key,c in calls.items())
            folder=Path('.work')/('adopted-runtime-sample-'+label+'-01')/'0'
            mapping=bind(folder/'jit-code/operations.json');bind(folder/'jit-code/code.bin',mapping['code_sha256'])
            fine=bind(Path('.work/native-protocol-census-01')/(label+'.json'));bind(folder/'sample.txt')
            assert mapping['code_sha256']==fine['code_sha256']==continuation['code_sha256']
            samples=[frame for root in parse_tree((ROOT/folder/'sample.txt').read_text()) for frame in self_samples(root)]
            sampled,returns,parts,generated=attribute({key:dict(callee=key) for key in calls},mapping,fine,samples)
            assert generated==old['cases'][index]['generated_samples']
            assert sum(c['hits'] for c in calls.values())==old['cases'][index]['native_calls']
            hist={key:Counter() for key in ['sites','calls','call_samples']};sites=[];by_part=Counter()
            for key,c in calls.items():
                caller,pc=key;callee=c['callee'];f=functions[callee]
                kind=('eligible_from_eligible' if caller in eligible else 'eligible_from_ineligible') if callee in eligible else 'callee_declined/'+f['decline']
                n=sum(sampled[key].values());hist['sites'][kind]+=1;hist['calls'][kind]+=c['hits'];hist['call_samples'][kind]+=n
                if callee in eligible:by_part.update(sampled[key])
                sites.append(dict(function=caller,pc=pc,callee=callee,kind=kind,native_calls=c['hits'],samples=n,
                    parts=sampled[key],callee_plan=f['plan']))
            assert sum(hist['call_samples'].values())==old['cases'][index]['call_samples']
            return_parts=Counter()
            for fid,counts in returns.items():
                if fid in eligible:return_parts.update(counts)
            assert sum(sum(c.values()) for c in returns.values())==old['cases'][index]['return_samples']
            represented={f['function'] for f in mapping['functions']}
            needed=set();pending=[c['callee'] for c in calls.values() if c['hits'] and c['callee'] in eligible]
            while pending:
                fid=pending.pop()
                if fid in needed:continue
                assert fid in eligible;needed.add(fid);pending.extend(c['callee'] for c in functions[fid]['calls'])
            body_rows=[dict(s,function=f['function']) for f in mapping['functions'] for s in f['spans'] if s['offset']<s['end']]
            starts=[s['offset'] for s in body_rows];assert starts==sorted(set(starts));body_samples=Counter()
            for n,frame,_ in samples:
                if '<unknown binary>' not in frame:continue
                offsets=[int(a,16)-mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)',frame)]
                rows=[locate(body_rows,starts,o) for o in offsets];assert rows
                assert len({(s['function'],s['kind']) for s in rows})==1;s=rows[0]
                if s['function'] in eligible and s['kind']!='transition':body_samples[s['kind']]+=n
            guarded={f['function'] for f in mapping['functions'] if any(s['kind']=='range_guard' and s['offset']<s['end'] for s in f['spans'])}
            report=work/(label+'.json');write(report,dict(status='passed',sites=sites,needed_functions=sorted(needed),
                missing_needed_functions=sorted(needed-represented),guarded_eligible_functions=sorted(guarded&eligible)))
            eligible_calls=sum(c['hits'] for c in calls.values() if c['callee'] in eligible)
            exceeds_spare=sum(c['hits'] for c in calls.values() if c['callee'] in eligible and (
                functions[c['callee']]['plan']['register_slots']>16384 or
                functions[c['callee']]['plan']['frame_span']+functions[c['callee']]['plan']['frame_align']-1>1024*1024 or
                functions[c['callee']]['plan']['depth']>64))
            cases.append(dict(case=label,native_calls=old['cases'][index]['native_calls'],eligible_native_calls=eligible_calls,
                histograms=hist,eligible_call_samples_by_part=by_part,eligible_return_samples_by_part=return_parts,
                generated_samples=generated,eligible_body_samples_by_kind=body_samples,
                represented_eligible_functions=len(represented&eligible),needed_functions=len(needed),
                missing_needed_functions=len(needed-represented),guarded_eligible_functions=len(guarded&eligible),
                existing_needed_code_bytes=sum(f['end']-f['offset'] for f in mapping['functions'] if f['function'] in needed),
                calls_exceeding_one_existing_spare_quota=exceeds_spare,report_sha256=sha(report),
                top_sites=sorted(sites,key=lambda s:(-s['samples'],-s['native_calls']))[:12]))
            print(label,'eligible calls',eligible_calls,'call samples',sum(by_part.values()),
                'return-sample upper bound',sum(return_parts.values()),'missing dependencies',len(needed-represented),flush=True)
        assert all(sha(ROOT/file)==h for file,h in frozen.items())
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        for file,h in frozen.items():
            if not file.startswith('.work/'):source(file,h,revision)
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,guest_benchmark_commands=0,performance_measurement=False))
        result=ROOT/'results'/args.run_id;result.mkdir(exist_ok=False)
        write(result/'source-bindings.json',dict(source_revision=revision,files=bindings))
        write(result/'summary.json',dict(status='passed',cases=cases,raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),unique_frozen_inputs=len(frozen),all_frozen_inputs_verified=True,
            source_bindings_sha256=sha(result/'source-bindings.json'),git_bindings=len(bindings),reused_join_controls=2,
            guest_benchmark_commands=0,runtime_changes=0,performance_measurement=False,
            limitation='Static eligibility and saved sample coverage are upper bounds. Current code presence does not establish bridge readiness. Returning-function samples do not identify the entering call path. No duplicated-code size, available-storage admission, bridge overhead or latency gain is measured.'))


if __name__=='__main__':main()
