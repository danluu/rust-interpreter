"""Close both owned samples and count exact old translation instructions."""
from pathlib import Path
import hashlib,importlib.util,json,re,struct,subprocess,sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
from summarize_owned_sample import parse_tree,self_samples
from attribute_generated_sample import attribute
spec=importlib.util.spec_from_file_location('recognizer',ROOT/'benchmarks/experiments/selected-native-sampling/address_profile.py')
recognizer=importlib.util.module_from_spec(spec);spec.loader.exec_module(recognizer)

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        proofs={};frozen={}
        def retain(path,expected=None):
            path=Path(path);h=sha(path)
            if expected is not None:assert h==expected,path
            key=str(path.relative_to(ROOT));assert key not in proofs or proofs[key]==h
            proofs[key]=h
        for run in ['tree-bridge-native-sampling-controls-01','tree-bridge-native-sampling-01']:
            summary=ROOT/'results'/run/'summary.json';p=json.loads(summary.read_text());assert p['status']=='passed'
            retain(summary);raw=ROOT/p['raw'];retain(raw/'plan.json',p['plan_sha256'])
            name='record' if 'record_sha256' in p else 'records';retain(raw/(name+'.json'),p[name+'_sha256'])
            for path,h in json.loads((raw/'plan.json').read_text())['frozen'].items():
                assert path not in frozen or frozen[path]==h;frozen[path]=h;retain(ROOT/path,h)
            outer=ROOT/'.work/experiments'/run;t=ROOT/'results'/run/'terminal.json';terminal=json.loads(t.read_text())
            assert terminal==json.loads((outer/'status.json').read_text()) and terminal['status']=='finished' and terminal['returncode']==0
            retain(t);retain(outer/'plan.json',terminal['plan_sha256']);retain(outer/'command.log',terminal['log_sha256'])
        cases=[]
        for label in ['block','exhaustive']:
            run='tree-bridge-native-sample-'+label+'-01';raw=ROOT/'.work'/run
            summary=ROOT/'results'/run/'summary.json';s=json.loads(summary.read_text());retain(summary)
            result=ROOT/'results'/run/'generated-attribution.json';d=json.loads(result.read_text());retain(result)
            assert s['options']['jit_tree_bridge'] and not s['options'].get('jit_operation_map',False)
            sample,=s['samples'];folder=raw/'0';record=json.loads((folder/'record.json').read_text())
            assert record['identity']['status']=='finished' and record['identity']['returncode']==0
            assert d['samples']==[attribute(folder,sample)]
            for p in raw.rglob('*'):
                if p.is_file():retain(p)
            for path,h in json.loads((raw/'plan.json').read_text())['source_files'].items():
                assert path not in frozen or frozen[path]==h;frozen[path]=h;retain(ROOT/path,h)
            native=json.loads((folder/'jit-code/map.json').read_text());code=(folder/'jit-code/code.bin').read_bytes()
            words=[w[0] for w in struct.iter_unpack('<I',code)];classes={};sequences=[]
            for row in native['ranges']:
                for i in range(row['offset']//4,row['end']//4):
                    found=recognizer.decode(words,i)
                    if found is None:continue
                    assert found['end']*4<=row['end'] and found['fault']*4<row['end']
                    sequences.append(found)
                    for at in range(i,found['end']):
                        assert at not in classes
                        classes[at]=('offset_subtract' if at==i+3 else 'offset_select' if at==i+4 else
                            'unused_readonly_select' if at==i+7 and not found['write'] else 'retained',row['kind'])
            removed={};ambiguous=matched=0;base=native['arena_base']
            for root in parse_tree((folder/'sample.txt').read_text()):
                for count,frame,_ in self_samples(root):
                    if '<unknown binary>' not in frame:continue
                    addresses=re.findall(r'0x([0-9a-f]+)',frame)
                    if not addresses or '...' in frame:continue
                    found={classes.get((int(a,16)-base)//4) for a in addresses}
                    if len(found)!=1:
                        if any(x is not None for x in found):ambiguous+=count
                        continue
                    item=found.pop()
                    if item is None:continue
                    matched+=count
                    if item[0]!='retained':removed[item[0]]=removed.get(item[0],0)+count
            cases.append(dict(case=label,generated_samples=d['attributed_generated_samples'],matched_fixed_address_samples=matched,
                exact_sequences=len(sequences),potential_removed_word_samples=removed,ambiguous_sequence_samples=ambiguous,
                potential_removed_fraction=sum(removed.values())/d['attributed_generated_samples'],
                by_entry_kind=d['by_entry_kind'],by_instruction_class=d['by_instruction_class']))
        for path in [Path(__file__),ROOT/'benchmarks/experiments/selected-native-sampling/address_profile.py']:retain(path)
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();bindings=[]
        for p,h in sorted(frozen.items()):
            if p.startswith(('crates/','scripts/','benchmarks/','tests/')) or p in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:
                spec=revision+':'+p;body=subprocess.check_output(['git','show',spec]);assert hashlib.sha256(body).hexdigest()==h
                bindings.append(dict(path=p,sha256=h,git_source=spec))
        assert all(sha(ROOT/p)==h for p,h in proofs.items())
        out=ROOT/'results/tree-bridge-native-sampling-01';assert not (out/'closure.json').exists()
        write(out/'source-bindings.json',dict(files=bindings))
        write(out/'closure.json',dict(status='passed',evidence=proofs,source_bindings=len(bindings),
            source_bindings_sha256=sha(out/'source-bindings.json'),guest_executions=2,performance_measurement=False))
        write(out/'translation-census.json',dict(status='passed',cases=cases,performance_measurement=False,
            scope='Exact fixed-width check sequences only. Potentially removable old offset SUB/CSEL and unused read-only CSEL self-PCs; not cycle savings. No x5/x6 reuse: those registers contain the value cache. A heap-bias ABI would need x7/x8 and every external entry/guard qualified. No runtime change or timing is authorized by this census.'))
        print(json.dumps(cases),flush=True)

if __name__=='__main__':main()
