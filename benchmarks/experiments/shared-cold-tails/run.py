"""Census exact cold tails using two retained adopted-VM native captures."""
from bisect import bisect_right
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
from tails import census

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from summarize_owned_sample import parse_tree, self_samples
from workflow_io import capture, require_space, write_json as write
RUN = 'shared-cold-tail-census-01'


def read(p):
    assert p.stat().st_size <= 256 * 1024**2
    return json.loads(p.read_text())


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 12)
        frozen = {}
        def bind(path, expected=None):
            value = sha(path)
            if expected is not None: assert value == expected, path
            frozen[str(path.relative_to(ROOT))] = value
            return read(path) if path.suffix == '.json' else value
        prior = ROOT / 'results/adopted-current-runtime-sampling-02'
        closed = bind(prior / 'closure.json')
        assert closed['status'] == 'closed' and closed['all_hashes_verified']
        summary = bind(prior / 'summary.json', closed['summary_sha256'])
        evidence = bind(ROOT / closed['evidence'], closed['evidence_sha256'])
        for path,digest in evidence.items(): bind(ROOT/path,digest)
        for path in HERE.iterdir():
            if path.suffix in ['.py','.md']: bind(path)
        for name in ['compare_saved_runtime.py','summarize_owned_sample.py','workflow_io.py','vmmap_ranges.py']:
            bind(ROOT/'scripts'/name)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw = ROOT/'.work'/RUN
        raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            guest_commands=0,builds=0,executable_code_publications=0,performance_measurement=False,
            maximum_keys_per_function=256,minimum_initial_gib=12,minimum_child_gib=8,
            archived_vm_source_receipt=closed['source_revision'],expected_controls=6))
        command=[sys.executable,'-m','unittest','test_tails','-v']
        require_space(ROOT,8)
        child,out,err=capture(command,cwd=HERE,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),
            receipt_path=raw/'active.json',receipt=dict(stage='exact-tail model controls'))
        (raw/'controls.stdout').write_text(out)
        (raw/'controls.stderr').write_text(err)
        write(raw/'record.json',dict(command=command,pid=child.pid,returncode=child.returncode,
            stdout_sha256=sha(raw/'controls.stdout'),stderr_sha256=sha(raw/'controls.stderr')))
        assert child.returncode==0 and 'Ran 6 tests' in err and err.rstrip().endswith('OK'),err
        results,details=[],[]
        for case in summary['cases']:
            label=case['case']
            folder=ROOT/'.work'/case['run_id']/'0'
            mapping=read(folder/'jit-code/operations.json')
            code=(folder/'jit-code/code.bin').read_bytes()
            assert len(code)<=16*1024**2 and len(code)==mapping['code_bytes']
            assert hashlib.sha256(code).hexdigest()==mapping['code_sha256']
            assert mapping['schema_version']==2 and mapping['complete'] and mapping['reconstructed_bytes_match']
            assert not mapping['profiled'] and mapping['persistent_registers'] and mapping['resumable_calls']
            functions=mapping['functions']
            starts=[f['offset'] for f in functions]
            assert starts==sorted(set(starts)) and starts[0]==0 and functions[-1]['end']==len(code)
            assert all(a['end']==b['offset'] for a,b in zip(functions,functions[1:]))
            sampled=Counter()
            generated=0
            for root in parse_tree((folder/'sample.txt').read_text()):
                for n,frame,_ in self_samples(root):
                    if '<unknown binary>' not in frame: continue
                    assert '...' not in frame
                    offsets=[int(a,16)-mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)',frame)]
                    assert offsets
                    owners=[]
                    for offset in offsets:
                        pos=bisect_right(starts,offset)-1
                        assert pos>=0 and starts[pos]<=offset<functions[pos]['end'] and offset%4==0
                        owners.append(pos)
                    assert len(set(owners))==1
                    sampled[owners[0]]+=n
                    generated+=n
            assert generated==case['attributed_generated_samples']
            rows=[]
            for index,f in enumerate(functions):
                tails=[]
                for span in f['spans']:
                    if span['kind']!='fault_tail': continue
                    assert span['pc'] is None and f['offset']<=span['offset']<span['end']<=f['end']
                    data=code[span['offset']:span['end']]
                    words=struct.unpack('<'+'I'*(len(data)//4),data)
                    tails.append((span['offset'],words))
                result=census(tails)
                for replacement in result['replacements']:
                    assert f['offset']<=replacement['target']<replacement['offset']<f['end']
                size=f['end']-f['offset']
                rows.append(dict(function=f['function'],name=f['name'],offset=f['offset'],
                    original_bytes=size,projected_bytes=size-result['saved_bytes'],
                    original_fault_tails=len(tails),original_fault_bytes=sum(len(w)*4 for _,w in tails),
                    generated_self_samples=sampled[index],**result))
            removed=sum(r['saved_bytes'] for r in rows)
            changed=[r for r in rows if r['saved_bytes']]
            report=dict(case=label,original_bytes=len(code),projected_bytes=len(code)-removed,
                saved_bytes=removed,saved_fraction=removed/len(code),functions=len(rows),
                changed_functions=len(changed),fault_tails=sum(r['original_fault_tails'] for r in rows),
                original_fault_bytes=sum(r['original_fault_bytes'] for r in rows),
                replaced_tails=sum(len(r['replacements']) for r in rows),
                declined_tails=sum(r['declined'] for r in rows),generated_samples=generated,
                samples_in_changed_functions=sum(r['generated_self_samples'] for r in changed),
                sampled_functions=[{k:v for k,v in r.items() if k!='replacements'}
                    for r in sorted(changed,key=lambda r:r['generated_self_samples'],reverse=True)[:15]])
            results.append(report)
            details.append(dict(case=label,functions=rows))
            print(json.dumps({k:v for k,v in report.items() if k!='sampled_functions'}),flush=True)
        assert all(sha(ROOT/path)==digest for path,digest in frozen.items())
        write(raw/'details.json',details)
        destination=ROOT/'results'/RUN
        destination.mkdir(exist_ok=False)
        write(destination/'summary.json',dict(status='passed',source_revision=revision,
            raw=str(raw.relative_to(ROOT)),plan_sha256=sha(raw/'plan.json'),record_sha256=sha(raw/'record.json'),
            details_sha256=sha(raw/'details.json'),controls=6,cases=results,guest_commands=0,builds=0,
            executable_code_publications=0,production_runtime_changes=0,performance_measurement=False,
            limitation='Exact complete fault-tail interning model within each function. Projected bytes exclude future emitter preparation costs. Whole-function sample context is not removable time or evidence of a speedup.'))


if __name__ == '__main__': main()
