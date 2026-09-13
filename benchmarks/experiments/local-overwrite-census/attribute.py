"""Bind typed overwrite candidates to unchanged native code and saved samples."""
from bisect import bisect_right
from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from profile_vm_transitions import counts
from summarize_owned_sample import parse_tree,self_samples
from workflow_io import require_space,write_json as write


def locate(rows,starts,offset):
    i=bisect_right(starts,offset)-1
    assert i>=0 and rows[i]['offset']<=offset<rows[i]['end'] and offset%4==0
    return rows[i]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    args=parser.parse_args();assert re.fullmatch(r'local-overwrite-coverage-\d{2}',args.run_id)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        frozen={};bindings=[]
        def bind(path,digest=None):
            path=ROOT/path;h=sha(path)
            if digest is not None:assert h==digest,path
            key=str(path.relative_to(ROOT));assert key not in frozen or frozen[key]==h
            frozen[key]=h
            return json.loads(path.read_text()) if path.suffix=='.json' else h
        def source(file,digest,revision):
            spec=revision+':'+file
            assert hashlib.sha256(subprocess.check_output(['git','show',spec],cwd=ROOT)).hexdigest()==digest,spec
            bindings.append(dict(path=file,sha256=digest,git_source=spec))
        def terminal(name):
            t=bind('results/'+name+'/terminal.json');outer=Path('.work/experiments')/name
            assert t['status']=='finished' and t['returncode']==0 and t['owner']==t['cwd']==str(ROOT)
            bind(outer/'status.json',sha(ROOT/'results'/name/'terminal.json'))
            bind(outer/'plan.json',t['plan_sha256']);bind(outer/'command.log',t['log_sha256'])
        def historical_plan(path,digest):
            plan=bind(path,digest);assert plan['owner']==str(ROOT)
            for file,h in plan['frozen'].items():
                if file.startswith(('.work/','/')):bind(file,h)
                else:source(file,h,plan['source_revision'])
            return plan
        build_name='local-overwrite-census-build-01';build=bind('results/'+build_name+'/summary.json')
        assert build['status']=='passed' and build['tests']=={'debug':6,'release':6}
        assert build['oracle_cases_per_profile']==10000 and build['commands']==5
        terminal(build_name);raw=Path(build['raw'])
        historical_plan(raw/'plan.json',build['plan_sha256'])
        records=bind(raw/'records.json',build['records_sha256']);assert len(records)==5 and all(r['returncode']==0 for r in records)
        for row in records:
            for suffix in ['stdout','stderr']:bind(raw/(row['label']+'.'+suffix),row[suffix+'_sha256'])
        bind(raw/'local-overwrite-census',build['binary_sha256'])
        bind('results/'+build_name+'/source-bindings.json',build['source_bindings_sha256'])
        old_name='memory-operation-parts-census-01';old_base=Path('results')/old_name
        closure=bind(old_base/'closure.json');assert closure['status']=='passed' and closure['all_frozen_inputs_verified']
        old=bind(old_base/'attribution.json',closure['attribution_sha256']);assert old['status']=='passed'
        old_sources=bind(old_base/'source-bindings.json',closure['source_bindings_sha256'])
        for item in old_sources['files']:
            assert hashlib.sha256(subprocess.check_output(['git','show',item['git_source']],cwd=ROOT)).hexdigest()==item['sha256']
            bindings.append(item)
        for file,h in closure['evidence'].items():bind(file,h)
        for file,h in old['evidence'].items():
            if file.startswith('.work/'):bind(file,h)
            else:source(file,h,old_sources['source_revision'])
        old_summary=bind(old_base/'summary.json');historical_plan(Path('.work')/old_name/'plan.json',old_summary['plan_sha256'])
        terminal(old_name)
        for name in ['attribute.py','PLAN.md']:
            bind(Path('benchmarks/experiments/local-overwrite-census')/name)
        for file in ['compare_saved_runtime.py','profile_vm_transitions.py','summarize_owned_sample.py','workflow_io.py']:
            bind(Path('scripts')/file)
        profile_proof=bind('results/guarded-local-facts-profile-01/summary.json')
        assert profile_proof['status']=='passed' and profile_proof['exact_per_pc_counts'] and profile_proof['exact_operation_map_reconstruction']
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False);cases=[]
        for index,label in enumerate(['block','exhaustive']):
            require_space(ROOT,8)
            typed=bind(raw/(label+'.json'),build['cases'][index]['typed_sha256']);assert typed['status']=='passed'
            folder=Path('.work')/('adopted-runtime-sample-'+label+'-01')/'0'
            mapping=bind(folder/'jit-code/operations.json');bind(folder/'jit-code/code.bin',mapping['code_sha256'])
            bind(folder/'sample.txt')
            fine=bind(Path('.work')/old_name/(label+'.json'))
            assert fine['code_sha256']==mapping['code_sha256'] and fine['complete_small_memory_partition']
            profile=bind(Path(profile_proof['raw'])/(str(index)+'-profile.json'),profile_proof['comparisons'][index]['profile_sha256'])
            accounting=counts(profile,profile_proof['comparisons'][index]['statistics'])
            coarse=[dict(s,function=f['function']) for f in mapping['functions'] for s in f['spans'] if s['offset']<s['end']]
            coarse_starts=[s['offset'] for s in coarse];assert coarse_starts==sorted(set(coarse_starts))
            fine_rows=[dict(s,function=f['function']) for f in fine['functions'] for s in f['memory_spans']]
            fine_starts=[s['offset'] for s in fine_rows];assert fine_starts==sorted(set(fine_starts))
            selected={(f['function'],s['pc']):(s['operation'],s['size']) for f in fine['functions'] for s in f['selected']}
            spans={(f['function'],s['pc']):s for f in mapping['functions'] for s in f['spans'] if s['pc'] is not None}
            candidates={};declines=[];weighted=Counter();static=Counter()
            represented=set()
            for f in typed['functions']:
                fid=f['function'];assert fid not in represented;represented.add(fid);pf=profile['functions'][fid]
                assert (f['name'],f['frame_size'],f['registers'])==(pf['name'],pf['frame_size'],pf['registers'])
                for region in f['regions']:
                    start,end=region['start'],region['end'];proof=region['proof'];hits=pf['jit_blocks'][start]
                    assert pf['jit_block_ends'][start]==end
                    if proof['decline'] is not None:
                        assert not proof['candidates'];declines.append(dict(function=fid,start=start,end=end,
                            reason=proof['decline'],native_instructions=hits*(end-start)))
                    for c in proof['candidates']:
                        pc=c['pc'];key=(fid,pc);assert key not in candidates
                        assert start<=pc<c['overwritten_at']<end and c['offset']+c['size']<=max(f['frame_size'],1)
                        span=spans[key];assert span['region_pc']==start and span['kind']=='operation'
                        if key in selected:assert selected[key]==(c['operation'],c['size'])
                        words=(span['end']-span['offset'])//4
                        candidates[key]=dict(c,function=fid,region_start=start,region_end=end,hits=hits,
                            emitted_words=words,samples=0,transfer_samples=0,parts=Counter())
                        kind=c['operation'];static[kind]+=1;weighted[kind]+=hits
            generated=whole=transfers=unpartitioned=0
            for root in parse_tree((ROOT/folder/'sample.txt').read_text()):
                for n,frame,_ in self_samples(root):
                    if '<unknown binary>' not in frame:continue
                    assert '...' not in frame
                    offsets=[int(a,16)-mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)',frame)];assert offsets
                    rows=[locate(coarse,coarse_starts,o) for o in offsets]
                    assert len({(s['function'],s['region_pc'],s['pc'],s['kind']) for s in rows})==1
                    generated+=n;s=rows[0];key=(s['function'],s['pc'])
                    if key not in candidates:continue
                    c=candidates[key];whole+=n;c['samples']+=n
                    if key not in selected:
                        unpartitioned+=n;c['parts']['unpartitioned']+=n;continue
                    parts=[locate(fine_rows,fine_starts,o) for o in offsets]
                    assert all((p['function'],p['pc'])==key for p in parts)
                    kinds={p['part'] for p in parts};assert len(kinds)==1
                    part=next(iter(kinds));c['parts'][part]+=n
                    if part in ['load_data','store_data']:transfers+=n;c['transfer_samples']+=n
            assert generated==old['cases'][index]['generated_samples']
            omitted=[]
            for fid,pf in enumerate(profile['functions']):
                if fid not in represented:
                    n=sum(h*(pf['jit_block_ends'][pc]-pc) for pc,h in enumerate(pf['jit_blocks']) if h)
                    if n:omitted.append(dict(function=fid,native_instructions=n))
            report=work/(label+'.json');write(report,dict(status='passed',candidates=list(candidates.values()),declines=declines,
                omitted_executed_functions=omitted))
            cases.append(dict(case=label,candidates=len(candidates),static_by_operation=static,weighted_by_operation=weighted,
                zero_word_candidates=sum(c['emitted_words']==0 for c in candidates.values()),
                emitted_candidate_words=sum(c['emitted_words'] for c in candidates.values()),
                weighted_candidate_words=sum(c['emitted_words']*c['hits'] for c in candidates.values()),
                generated_samples=generated,whole_operation_samples=whole,transfer_only_samples=transfers,
                unpartitioned_candidate_samples=unpartitioned,
                declined_regions=len(declines),declined_native_instructions=sum(d['native_instructions'] for d in declines),
                native_instructions=accounting['native_instructions'],omitted_executed_functions=omitted,
                report_sha256=sha(report),top_sites=sorted(candidates.values(),key=lambda c:(-c['samples'],-c['hits']))[:12]))
            print(label,'whole-operation samples',whole,'transfer-only',transfers,'unpartitioned',unpartitioned,flush=True)
        assert all(sha(ROOT/file)==h for file,h in frozen.items())
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        for file,h in frozen.items():
            if not file.startswith('.work/'):source(file,h,revision)
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,guest_commands=0,performance_measurement=False))
        result=ROOT/'results'/args.run_id;result.mkdir(exist_ok=False)
        write(result/'source-bindings.json',dict(source_revision=revision,files=bindings))
        write(result/'summary.json',dict(status='passed',cases=cases,raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),unique_frozen_inputs=len(frozen),all_frozen_inputs_verified=True,
            source_bindings_sha256=sha(result/'source-bindings.json'),git_bindings=len(bindings),
            guest_commands=0,runtime_changes=0,performance_measurement=False,
            limitation='Whole-operation samples include work that may remain. Transfer-only samples omit fused fills and copies larger than 16 bytes. Weighted emitted words are not retired instructions; no latency gain is established.'))


if __name__=='__main__':main()
