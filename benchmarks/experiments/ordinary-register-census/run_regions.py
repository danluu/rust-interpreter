"""Region-level register census on the same exact adopted native captures."""
from bisect import bisect_right
from collections import Counter
import hashlib,json,os,re,struct,subprocess,sys
from pathlib import Path
from linear import analyze,direct_target
from regions import groups
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from summarize_owned_sample import parse_tree,self_samples
RUN='ordinary-register-census-02'
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
            if p.suffix in ['.py','.md']:bind(p)
        for name in ['words.py','test_words.py']:bind(ROOT/'benchmarks/experiments/scalar-word-census'/name)
        for name in ['workflow_io.py','compare_saved_runtime.py','summarize_owned_sample.py']:bind(ROOT/'scripts'/name)
        for label in ['block','exhaustive']:
            folder=ROOT/'.work'/('scratch-scalar-runtime-sample-'+label+'-01')/'0'
            for p in [folder/'sample.txt',folder/'jit-code/operations.json',folder/'jit-code/code.bin']:
                assert str(p.relative_to(ROOT)) in artifacts
            old=bind(ROOT/'results'/('scratch-scalar-runtime-sample-'+label+'-01')/'operation-attribution.json')
            assert old['status']=='passed' and old['unassigned_generated_samples']==0
            for p,h in old['evidence'].items():bind(ROOT/p,h)
        prior_path=ROOT/'results/ordinary-register-census-01/summary.json'
        prior_closure=bind(prior_path.with_name('closure.json'));assert prior_closure['status']=='closed'
        prior=bind(prior_path,prior_closure['summary_sha256'])
        prior_details=bind(ROOT/prior['raw']/'details.json',prior['details_sha256'])
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,controls=16,
            guest_commands=0,host_builds=0,executable_code_publications=0,production_changes=0,performance_measurement=False))
        records=[]
        for label,directory,module,count in [('linear',Path(__file__).parent,'test_linear',5),
                ('recognizer',ROOT/'benchmarks/experiments/scalar-word-census','test_words',9),
                ('regions',Path(__file__).parent,'test_regions',2)]:
            child,out,err=capture([sys.executable,'-m','unittest',module,'-v'],cwd=directory,
                env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),receipt_path=raw/'active.json',receipt=dict(stage=label))
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
            assert mapping['complete'] and mapping['reconstructed_bytes_match'] and not mapping['profiled']
            assert hashlib.sha256(code).hexdigest()==mapping['code_sha256'] and len(code)==mapping['code_bytes']
            words=list(struct.unpack('<'+'I'*(len(code)//4),code))
            targets={target for pc,word in enumerate(words) if (target:=direct_target(word,pc)) is not None}
            spans=[dict(s,function=f['function'],name=f['name']) for f in mapping['functions'] for s in f['spans'] if s['offset']<s['end']]
            starts=[s['offset'] for s in spans];assert starts==sorted(set(starts))
            dead=set();sites={};counts=Counter();kinds=Counter();span_kinds=Counter()
            for region in groups(spans):
                start,end=region['offset']//4,region['end']//4
                counts['regions']+=1;counts['region_words']+=end-start
                if end-start>65536:counts['declined_regions']+=1;continue
                local_entries={pc-start for pc in range(start,end) if pc in targets}
                result=analyze(words[start:end],local_entries)
                counts['recognized_words']+=result['recognized'];counts['barrier_words']+=result['barriers']
                for pc,kind in result['dead']:
                    offset=4*(start+pc);assert offset not in dead;dead.add(offset)
                    span=locate(spans,starts,offset)
                    assert (span['function'],span['region_pc'])==region['key']
                    sites[offset]=span;kinds[kind]+=1;span_kinds[span['kind']]+=1
                    details.append(dict(case=label,function=span['function'],name=span['name'],pc=span['pc'],
                        offset=offset,word=f'{words[start+pc]:08x}',kind=kind,span_kind=span['kind']))
            old_dead={r['offset'] for r in prior_details if r['case']==label}
            assert old_dead<=dead,'lost a narrower candidate'
            generated=certain=ambiguous=0;sample_sites=Counter();sample_kinds=Counter()
            for root in parse_tree((folder/'sample.txt').read_text()):
                for n,frame,_ in self_samples(root):
                    if '<unknown binary>' not in frame:continue
                    assert '...' not in frame
                    offsets=[int(a,16)-mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)',frame)];assert offsets
                    owners=[locate(spans,starts,o) for o in offsets]
                    assert len({(s['function'],s['pc'],s['region_pc'],s['kind']) for s in owners})==1
                    generated+=n
                    selected=[offset in dead for offset in offsets]
                    if all(selected):
                        certain+=n;s=owners[0];sample_sites[s['function'],s['name'],s['pc']]+=n
                        sample_kinds[s['kind']]+=n
                    elif any(selected):ambiguous+=n
            old=read(ROOT/'results'/('scratch-scalar-runtime-sample-'+label+'-01')/'operation-attribution.json')
            assert generated==old['attributed_generated_samples']
            observations.append(dict(case=label,generated_samples=generated,certain_dead_samples=certain,
                ambiguous_dead_samples=ambiguous,static_dead_words=len(dead),counts=dict(counts),dead_words_by_kind=dict(kinds),dead_words_by_span_kind=dict(span_kinds),samples_by_span_kind=dict(sample_kinds),
                top_sample_sites=[dict(function=fid,name=name,pc=pc,samples=n) for (fid,name,pc),n in sample_sites.most_common(15)]))
            print(json.dumps(observations[-1]),flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        write(raw/'details.json',details)
        result=ROOT/'results'/RUN;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),details_sha256=sha(raw/'details.json'),
            controls=16,cases=observations,guest_commands=0,host_builds=0,executable_code_publications=0,
            production_changes=0,performance_measurement=False,
            limitation='Pure register definitions within individual ordinary native regions only; barriers and all final registers preserved. Same-process partial, perturbed self-PC samples; not retired instructions or a speedup.'))


def close():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);out=ROOT/'results'/RUN;s=read(out/'summary.json');raw=ROOT/s['raw']
        assert s['status']=='passed' and s['controls']==16
        for key in ['plan','records','details']:assert sha(raw/(key+'.json'))==s[key+'_sha256']
        plan=read(raw/'plan.json');bindings={}
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
