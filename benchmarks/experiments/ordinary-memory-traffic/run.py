"""Exact ordinary virtual-register traffic in retained machine-code captures."""
from bisect import bisect_right
from collections import Counter
import hashlib,json,os,re,struct,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'benchmarks/experiments/ordinary-register-census'))
from linear import direct_target
from regions import groups
from traffic import analyze,memory
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from summarize_owned_sample import parse_tree,self_samples
RUN='ordinary-memory-traffic-01'
def read(p):return json.loads(p.read_text())
def locate(rows,starts,offset):
    index=bisect_right(starts,offset)-1
    assert index>=0 and rows[index]['offset']<=offset<rows[index]['end'] and offset%4==0
    return rows[index]


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        frozen={}
        def bind(p,expected=None):
            h=sha(p)
            if expected is not None:assert h==expected,p
            frozen[str(p.relative_to(ROOT))]=h
            return read(p) if p.suffix=='.json' else h
        path=ROOT/'results/scratch-scalar-runtime-sampling-01/closure.json';closed=bind(path)
        assert closed['status']=='closed' and closed['all_hashes_verified']
        bind(path.with_name('summary.json'),closed['summary_sha256'])
        artifacts=bind(ROOT/closed['artifact_bindings'],closed['artifact_bindings_sha256'])
        for p,h in artifacts.items():bind(ROOT/p,h)
        for p in Path(__file__).parent.iterdir():
            if p.suffix in ['.py','.md','.s']:bind(p)
        for name in ['words.py','test_words.py']:bind(ROOT/'benchmarks/experiments/scalar-word-census'/name)
        for name in ['workflow_io.py','compare_saved_runtime.py','summarize_owned_sample.py']:bind(ROOT/'scripts'/name)
        for label in ['block','exhaustive']:
            folder=ROOT/'.work'/('scratch-scalar-runtime-sample-'+label+'-01')/'0'
            for p in [folder/'sample.txt',folder/'jit-code/operations.json',folder/'jit-code/code.bin']:
                assert str(p.relative_to(ROOT)) in artifacts
            old=bind(ROOT/'results'/('scratch-scalar-runtime-sample-'+label+'-01')/'operation-attribution.json')
            assert old['status']=='passed' and old['unassigned_generated_samples']==0
            for p,h in old['evidence'].items():bind(ROOT/p,h)
        for name in ['linear.py','regions.py','test_regions.py','test_linear.py','test_memory.py','memory.py','cfg_memory.py','cfg.py']:
            bind(ROOT/'benchmarks/experiments/ordinary-register-census'/name)
        build=bind(ROOT/'results/scratch-memory-values-build-02/summary.json')
        build_plan=bind(ROOT/build['raw']/'plan.json',build['plan_sha256'])
        for name in ['crates/bytecode/src/jit.rs']+['crates/bytecode/src/jit/'+n+'.rs' for n in ['values','resumable','scalar_calls','native_calls']]:
            bind(ROOT/name,build_plan['frozen'][name])
        assembler=Path(subprocess.check_output(['xcrun','--find','clang'],text=True).strip()).resolve(strict=True)
        assembler_sha256=sha(assembler)
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,controls=8,
            guest_commands=0,host_builds=1,executable_code_publications=0,production_changes=0,performance_measurement=False,assembler=str(assembler),assembler_sha256=assembler_sha256))
        records=[]
        fixture=Path(__file__).with_name('fixture.s');object_path=raw/'traffic.o'
        command=[str(assembler),'-target','arm64-apple-macos14','-c',str(fixture),'-o',str(object_path)]
        child,out,err=capture(command,cwd=ROOT,env=dict(os.environ),receipt_path=raw/'active.json',receipt=dict(stage='host encoding oracle'))
        (raw/'assembler.stdout').write_text(out);(raw/'assembler.stderr').write_text(err)
        records.append(dict(label='assembler',command=command,pid=child.pid,returncode=child.returncode,
            stdout_sha256=sha(raw/'assembler.stdout'),stderr_sha256=sha(raw/'assembler.stderr')))
        write(raw/'records.json',records)
        assert child.returncode==0 and object_path.stat().st_size<512*1024,err
        for label,directory,module,count in [('traffic',HERE,'test_traffic',6),
                ('regions',ROOT/'benchmarks/experiments/ordinary-register-census','test_regions',2)]:
            child,out,err=capture([sys.executable,'-m','unittest',module,'-v'],cwd=directory,
                env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',ORDINARY_TRAFFIC_OBJECT=str(object_path)),receipt_path=raw/'active.json',receipt=dict(stage=label))
            (raw/(label+'.stdout')).write_text(out);(raw/(label+'.stderr')).write_text(err)
            records.append(dict(label=label,pid=child.pid,returncode=child.returncode,
                stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr'))))
            write(raw/'records.json',records)
            assert child.returncode==0 and f'Ran {count} tests' in err and err.rstrip().endswith('OK'),err
        observations=[];details=[]
        for label in ['block','exhaustive']:
            require_space(ROOT,8)
            folder=ROOT/'.work'/('scratch-scalar-runtime-sample-'+label+'-01')/'0'
            mapping=read(folder/'jit-code/operations.json');code=(folder/'jit-code/code.bin').read_bytes()
            assert mapping['schema_version']==2 and mapping['complete'] and mapping['reconstructed_bytes_match'] and not mapping['profiled']
            assert mapping['persistent_registers'] and mapping['resumable_calls']
            assert hashlib.sha256(code).hexdigest()==mapping['code_sha256'] and len(code)==mapping['code_bytes']
            words=list(struct.unpack('<'+'I'*(len(code)//4),code))
            targets={target for pc,word in enumerate(words) if (target:=direct_target(word,pc)) is not None}
            spans=[dict(s,function=f['function'],name=f['name']) for f in mapping['functions'] for s in f['spans'] if s['offset']<s['end']]
            starts=[s['offset'] for s in spans];assert starts==sorted(set(starts))
            assert spans[0]['offset']==0 and spans[-1]['end']==len(code)
            assert all(a['end']==b['offset'] for a,b in zip(spans,spans[1:]))
            accesses={};addresses={};counts=Counter();static=Counter();static_spans=Counter();memory_bases=Counter()
            for region in groups(spans):
                start,end=region['offset']//4,region['end']//4
                counts['regions']+=1;counts['ordinary_words']+=end-start
                local_entries={pc-start for pc in range(start,end) if pc in targets}
                local,recipes=analyze(words[start:end],local_entries)
                for pc,item in local.items():
                    offset=4*(start+pc);assert offset not in accesses;accesses[offset]=item
                    span=locate(spans,starts,offset)
                    static_spans[span['kind']+':'+item['direction']+':'+item['half']]+=1
                for pc,owner in recipes.items():
                    offset=4*(start+pc);assert offset not in addresses
                    addresses[offset]=4*(start+owner)
                for pc in range(start,end):
                    mem=memory(words[pc])
                    if mem:memory_bases[mem['direction']+':x'+str(mem['base'])]+=1
            def category(offset,span):
                if span['kind']=='scalar_leaf':return 'scalar_leaf'
                if offset in accesses:
                    item=accesses[offset]
                    return 'register_'+item['direction']+':'+item['half']+(':'+('zero' if item['zero_store'] else 'value') if item['direction']=='store' else '')
                if offset in addresses:return 'register_large_address'
                mem=memory(words[offset//4])
                if mem:return 'other_u64_'+mem['direction']
                return 'other_words'
            for span in spans:
                for offset in range(span['offset'],span['end'],4):static[category(offset,span)]+=1
            assert sum(static.values())==len(words)
            generated=0;samples=Counter();sample_spans=Counter();sample_memory_bases=Counter();sample_slots=Counter();sample_sites=Counter();ambiguous=0
            for root in parse_tree((folder/'sample.txt').read_text()):
                for n,frame,_ in self_samples(root):
                    if '<unknown binary>' not in frame:continue
                    assert '...' not in frame
                    offsets=[int(a,16)-mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)',frame)];assert offsets
                    owners=[locate(spans,starts,o) for o in offsets]
                    assert len({(s['function'],s['pc'],s['region_pc'],s['kind']) for s in owners})==1
                    generated+=n
                    cats={category(o,s) for o,s in zip(offsets,owners)}
                    cat=next(iter(cats)) if len(cats)==1 else 'ambiguous'
                    if len(cats)!=1:ambiguous+=n
                    samples[cat]+=n;sample_spans[owners[0]['kind']+':'+cat]+=n
                    mems=[memory(words[o//4]) if s['kind']!='scalar_leaf' else None for o,s in zip(offsets,owners)]
                    base_labels={(m['direction']+':x'+str(m['base'])) if m else 'not_u64_memory' for m in mems}
                    sample_memory_bases[next(iter(base_labels)) if len(base_labels)==1 else 'ambiguous']+=n
                    if cat.startswith('register_'):
                        items=[accesses[o] if o in accesses else accesses[addresses[o]] for o in offsets]
                        slots={(s['function'],s['name'],i['slot']) for s,i in zip(owners,items)}
                        if len(slots)==1:sample_slots[next(iter(slots))]+=n
                        sample_sites[owners[0]['function'],owners[0]['name'],owners[0]['pc'],cat]+=n
                    details.append(dict(case=label,samples=n,category=cat,function=owners[0]['function'],name=owners[0]['name'],
                        pc=owners[0]['pc'],region_pc=owners[0]['region_pc'],span_kind=owners[0]['kind'],
                        sites=[dict(offset=o,word=f'{words[o//4]:08x}',access=accesses.get(o),address_for=addresses.get(o)) for o in offsets]))
            old=read(ROOT/'results'/('scratch-scalar-runtime-sample-'+label+'-01')/'operation-attribution.json')
            assert generated==old['attributed_generated_samples']==sum(samples.values())==sum(sample_memory_bases.values())
            observations.append(dict(case=label,generated_samples=generated,ambiguous_samples=ambiguous,
                counts=dict(counts),static_categories=dict(static),static_accesses_by_span=dict(static_spans),static_u64_memory_bases=dict(memory_bases),
                sampled_categories=dict(samples),samples_by_span=dict(sample_spans),sampled_u64_memory_bases=dict(sample_memory_bases),
                top_register_slots=[dict(function=fid,name=name,slot=slot,samples=n) for (fid,name,slot),n in sample_slots.most_common(20)],
                top_register_sites=[dict(function=fid,name=name,pc=pc,category=cat,samples=n) for (fid,name,pc,cat),n in sample_sites.most_common(30)]))
            print(json.dumps({k:v for k,v in observations[-1].items() if not k.startswith('top_')}),flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        assert sha(assembler)==assembler_sha256
        write(raw/'details.json',details)
        result=ROOT/'results'/RUN;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),details_sha256=sha(raw/'details.json'),object_sha256=sha(object_path),
            controls=8,cases=observations,guest_commands=0,host_builds=1,executable_code_publications=0,
            production_changes=0,performance_measurement=False,
            limitation='Only exact ordinary x0 or emitter-derived x16 unsigned 64-bit register-file accesses; scalar bodies excluded. Other memory forms/bases stay separate. Same-process partial perturbed self-PC samples and static words are not retired instructions, removable accesses or an end-to-end speedup.'))


def close():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);out=ROOT/'results'/RUN;s=read(out/'summary.json');raw=ROOT/s['raw']
        assert s['status']=='passed' and s['controls']==8
        for key in ['plan','records','details']:assert sha(raw/(key+'.json'))==s[key+'_sha256']
        plan=read(raw/'plan.json');bindings={}
        assert sha(raw/'traffic.o')==s['object_sha256']
        assert sha(Path(plan['assembler']))==plan['assembler_sha256']
        for p,h in plan['frozen'].items():
            assert sha(ROOT/p)==h
            if p.startswith(('.work/','results/')):bindings[p]=dict(kind='retained',sha256=h)
            else:
                data=subprocess.check_output(['git','show',plan['source_revision']+':'+p],cwd=ROOT)
                assert hashlib.sha256(data).hexdigest()==h
                bindings[p]=dict(kind='git',revision=plan['source_revision'],sha256=h)
        for r in read(raw/'records.json'):
            assert r['returncode']==0
            for stream in ['stdout','stderr']:assert sha(raw/(r['label']+'.'+stream))==r[stream+'_sha256']
        outer=ROOT/'.work/experiments'/RUN;terminal=read(outer/'status.json')
        assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==str(ROOT)
        assert sha(outer/'command.log')==terminal['log_sha256']
        assert not (out/'closure.json').exists()
        (out/'terminal.json').write_bytes((outer/'status.json').read_bytes());write(raw/'bindings.json',bindings)
        write(out/'closure.json',dict(status='closed',frozen_inputs=len(bindings),all_hashes_verified=True,
            bindings=str((raw/'bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'bindings.json'),
            summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json')))
        print(len(bindings),'frozen bindings and all control/detail evidence verified')


if __name__=='__main__':
    if sys.argv[1:]==['--close']:close()
    else:assert len(sys.argv)==1;main()
